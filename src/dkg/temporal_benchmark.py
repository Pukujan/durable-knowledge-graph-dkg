from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from .pack_corpus import retrieval_documents_from_pack_fixtures
from .real_retrieval import LifecycleIntentReranker, RerankedRetriever
from .services import BM25Retriever


NONCURRENT_STATES = frozenset(
    {
        "disputed",
        "invalidated",
        "rejected",
        "retracted",
        "stale_pending_review",
        "superseded",
    }
)


@dataclass(frozen=True)
class TemporalQueryCase:
    case_id: str
    query: str
    pack_ids: tuple[str, ...]
    relevant_ids: frozenset[str]
    limit: int = 5

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "TemporalQueryCase":
        return cls(
            case_id=str(value["case_id"]),
            query=str(value["query"]),
            pack_ids=tuple(str(item) for item in value["pack_ids"]),
            relevant_ids=frozenset(str(item) for item in value["relevant_ids"]),
            limit=int(value.get("limit", 5)),
        )

    def __post_init__(self) -> None:
        if not self.case_id or not self.query or not self.pack_ids or not self.relevant_ids:
            raise ValueError("temporal query cases require id/query/packs/relevant ids")
        if self.limit < 1:
            raise ValueError("temporal query limit must be positive")


@dataclass(frozen=True)
class TemporalPhase:
    phase_id: str
    as_of_recorded_at: str | None
    expected_states: Mapping[str, str]
    queries: tuple[TemporalQueryCase, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "TemporalPhase":
        cutoff = value.get("as_of_recorded_at")
        return cls(
            phase_id=str(value["phase_id"]),
            as_of_recorded_at=str(cutoff) if cutoff is not None else None,
            expected_states={str(key): str(state) for key, state in value["expected_states"].items()},
            queries=tuple(TemporalQueryCase.from_mapping(item) for item in value.get("queries", [])),
        )

    def __post_init__(self) -> None:
        if not self.phase_id or not self.expected_states:
            raise ValueError("temporal phases require an id and expected states")


def _documents_by_id(documents: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(document["id"]): dict(document) for document in documents}


def _state_checks(
    expected_states: Mapping[str, str],
    documents_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for identifier, expected in expected_states.items():
        document = documents_by_id.get(identifier)
        observed = str(document.get("current_state")) if document else None
        checks.append(
            {
                "id": identifier,
                "expected_state": expected,
                "observed_state": observed,
                "passed": observed == expected,
            }
        )
    return checks


def _query_observation(
    retriever: Any,
    case: TemporalQueryCase,
) -> dict[str, Any]:
    started = time.perf_counter()
    results = retriever.search(
        case.query,
        pack_ids=list(case.pack_ids),
        limit=case.limit,
    )
    latency_ms = (time.perf_counter() - started) * 1000.0
    returned_ids = [str(result["id"]) for result in results]
    relevant_found = case.relevant_ids & set(returned_ids)
    recall = len(relevant_found) / len(case.relevant_ids)
    first_relevant_rank = next(
        (rank for rank, identifier in enumerate(returned_ids, start=1) if identifier in case.relevant_ids),
        None,
    )
    intent = LifecycleIntentReranker.intent_for_query(case.query)
    leakage: list[dict[str, Any]] = []
    if intent == "current" and first_relevant_rank is not None:
        for rank, result in enumerate(results, start=1):
            if rank >= first_relevant_rank:
                break
            state = str(result.get("current_state", ""))
            if state in NONCURRENT_STATES:
                leakage.append({"id": str(result["id"]), "rank": rank, "state": state})

    return {
        "case_id": case.case_id,
        "query": case.query,
        "intent": intent,
        "returned_ids": returned_ids,
        "returned_states": [str(result.get("current_state", "")) for result in results],
        "relevant_ids": sorted(case.relevant_ids),
        "recall_at_k": recall,
        "first_relevant_rank": first_relevant_rank,
        "stale_before_current_relevant": leakage,
        "latency_ms": latency_ms,
        "passed": recall == 1.0 and not leakage,
    }


def run_temporal_evolution_benchmark(
    pack_roots: Iterable[Path],
    *,
    schemas_root: Path,
    phases: Iterable[TemporalPhase],
    benchmark_id: str = "post-gate2-evolving-corpus-v1",
) -> dict[str, Any]:
    """Replay durable packs at successive cutoffs and test temporal retrieval behavior.

    Every phase rebuilds the search projection from durable events. This intentionally
    measures correctness independently of any hosted embedding/reranker service and
    keeps lifecycle state as the authority path rather than allowing retrieval rank to
    manufacture current truth.
    """

    roots = [Path(root) for root in pack_roots]
    phase_list = list(phases)
    if not roots or not phase_list:
        raise ValueError("temporal benchmark requires pack roots and phases")

    phase_results: list[dict[str, Any]] = []
    previous_documents: dict[str, dict[str, Any]] | None = None

    for phase in phase_list:
        build_started = time.perf_counter()
        documents = retrieval_documents_from_pack_fixtures(
            roots,
            schemas_root=schemas_root,
            as_of_recorded_at=phase.as_of_recorded_at,
        )
        projection_build_ms = (time.perf_counter() - build_started) * 1000.0
        documents_by_id = _documents_by_id(documents)

        base = BM25Retriever(documents)
        retriever = RerankedRetriever(
            base,
            LifecycleIntentReranker(),
            candidate_multiplier=4,
            version="temporal-baseline-v1",
        )
        state_checks = _state_checks(phase.expected_states, documents_by_id)
        query_observations = [_query_observation(retriever, case) for case in phase.queries]

        transition: dict[str, Any] | None = None
        if previous_documents is not None:
            changed_states: list[dict[str, Any]] = []
            for identifier in sorted(set(previous_documents) | set(documents_by_id)):
                before = previous_documents.get(identifier)
                after = documents_by_id.get(identifier)
                before_state = str(before.get("current_state")) if before else None
                after_state = str(after.get("current_state")) if after else None
                if before_state != after_state:
                    changed_states.append(
                        {
                            "id": identifier,
                            "before_state": before_state,
                            "after_state": after_state,
                        }
                    )
            transition = {
                "document_count_delta": len(documents_by_id) - len(previous_documents),
                "state_changes": changed_states,
            }

        phase_passed = all(check["passed"] for check in state_checks) and all(
            observation["passed"] for observation in query_observations
        )
        phase_results.append(
            {
                "phase_id": phase.phase_id,
                "as_of_recorded_at": phase.as_of_recorded_at,
                "document_count": len(documents),
                "projection_build_ms": projection_build_ms,
                "state_checks": state_checks,
                "queries": query_observations,
                "transition_from_previous": transition,
                "passed": phase_passed,
            }
        )
        previous_documents = documents_by_id

    repeated_cases: dict[str, list[dict[str, Any]]] = {}
    for phase in phase_results:
        for observation in phase["queries"]:
            repeated_cases.setdefault(str(observation["case_id"]), []).append(observation)
    stability = {
        case_id: {
            "observations": len(observations),
            "all_full_recall": all(float(item["recall_at_k"]) == 1.0 for item in observations),
            "no_current_state_leakage": all(not item["stale_before_current_relevant"] for item in observations),
        }
        for case_id, observations in sorted(repeated_cases.items())
        if len(observations) > 1
    }

    return {
        "schema_version": "fossil.temporal-benchmark.v1",
        "benchmark_id": benchmark_id,
        "projection": "durable-event-replay->in-memory-bm25+lifecycle-intent-reranker",
        "authority_rule": "durable lifecycle/lineage state outranks retrieval score",
        "phase_count": len(phase_results),
        "phases": phase_results,
        "repeated_query_stability": stability,
        "passed": all(phase["passed"] for phase in phase_results)
        and all(
            item["all_full_recall"] and item["no_current_state_leakage"]
            for item in stability.values()
        ),
    }
