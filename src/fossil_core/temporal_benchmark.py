from __future__ import annotations

import json
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
_DISAGREEMENT_RELATION_TYPES = frozenset({"CHALLENGES", "CONTRADICTS"})
_DEPENDENCY_RELATION_TYPES = frozenset({"ASSUMES", "DEPENDS_ON"})


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


@dataclass(frozen=True)
class PositionChangeExpectation:
    subject_id: str
    event_id: str
    to_state: str
    evidence_refs: frozenset[str] = frozenset()
    caused_by_event_ids: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not self.subject_id or not self.event_id or not self.to_state:
            raise ValueError("position-change expectations require subject/event/to_state")


@dataclass(frozen=True)
class DependencyImpactExpectation:
    dependent_ref: str
    premise_ref: str
    relation_id: str
    premise_state: str

    def __post_init__(self) -> None:
        if not all((self.dependent_ref, self.premise_ref, self.relation_id, self.premise_state)):
            raise ValueError("dependency-impact expectations require dependent/premise/relation/state")


@dataclass(frozen=True)
class DisagreementExpectation:
    relation_id: str
    relation_type: str
    source_ref: str
    target_ref: str

    def __post_init__(self) -> None:
        if not all((self.relation_id, self.relation_type, self.source_ref, self.target_ref)):
            raise ValueError("disagreement expectations require relation/type/source/target")


@dataclass(frozen=True)
class LongitudinalPhase(TemporalPhase):
    expected_position_changes: tuple[PositionChangeExpectation, ...] = ()
    expected_dependency_impacts: tuple[DependencyImpactExpectation, ...] = ()
    expected_disagreements: tuple[DisagreementExpectation, ...] = ()

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "LongitudinalPhase":
        cutoff = value.get("as_of_recorded_at")
        return cls(
            phase_id=str(value["phase_id"]),
            as_of_recorded_at=str(cutoff) if cutoff is not None else None,
            expected_states={str(key): str(state) for key, state in value["expected_states"].items()},
            queries=tuple(TemporalQueryCase.from_mapping(item) for item in value.get("queries", [])),
            expected_position_changes=tuple(
                PositionChangeExpectation(
                    subject_id=str(item["subject_id"]),
                    event_id=str(item["event_id"]),
                    to_state=str(item["to_state"]),
                    evidence_refs=frozenset(str(ref) for ref in item.get("evidence_refs", [])),
                    caused_by_event_ids=frozenset(
                        str(ref) for ref in item.get("caused_by_event_ids", [])
                    ),
                )
                for item in value.get("expected_position_changes", [])
            ),
            expected_dependency_impacts=tuple(
                DependencyImpactExpectation(
                    dependent_ref=str(item["dependent_ref"]),
                    premise_ref=str(item["premise_ref"]),
                    relation_id=str(item["relation_id"]),
                    premise_state=str(item["premise_state"]),
                )
                for item in value.get("expected_dependency_impacts", [])
            ),
            expected_disagreements=tuple(
                DisagreementExpectation(
                    relation_id=str(item["relation_id"]),
                    relation_type=str(item["relation_type"]),
                    source_ref=str(item["source_ref"]),
                    target_ref=str(item["target_ref"]),
                )
                for item in value.get("expected_disagreements", [])
            ),
        )


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


def _load_cutoff_events(
    roots: Iterable[Path],
    *,
    as_of_recorded_at: str | None,
) -> list[dict[str, Any]]:
    """Read the same local durable pack event roots used by the rebuild benchmark.

    This function deliberately accepts only filesystem pack roots. The longitudinal
    query latency measurements therefore exclude remote canonical-object scans by
    construction; remote storage benchmarks remain separately owned by #87.
    """

    events: list[dict[str, Any]] = []
    for root in roots:
        manifest = json.loads((Path(root) / "manifest.json").read_text(encoding="utf-8"))
        for relative in manifest["event_roots"]:
            event_root = Path(root) / str(relative)
            for path in sorted(event_root.glob("*/*.json")):
                event = json.loads(path.read_text(encoding="utf-8"))
                if (
                    as_of_recorded_at is not None
                    and str(event["recorded_at"]) > as_of_recorded_at
                ):
                    continue
                events.append(event)
    return sorted(events, key=lambda event: (str(event["recorded_at"]), str(event["event_id"])))


def _epistemic_facts(
    events: Iterable[Mapping[str, Any]],
    documents: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    event_list = [dict(event) for event in events]
    document_list = [dict(document) for document in documents]
    claims = {
        str(document["id"]): document
        for document in document_list
        if document.get("document_type") == "claim"
    }
    relations = {
        str(document["id"]): document
        for document in document_list
        if document.get("document_type") == "relation"
    }

    claim_evidence: dict[str, set[str]] = {}
    claim_snapshots: dict[str, set[str]] = {}
    position_changes: list[dict[str, Any]] = []
    relation_metadata: dict[str, dict[str, Any]] = {}
    decision_refs: set[str] = set()
    ontology_refs: set[str] = set()

    for event in event_list:
        event_type = str(event.get("event_type", ""))
        payload = event.get("payload")
        payload_mapping = payload if isinstance(payload, Mapping) else {}
        subjects = event.get("subject_refs")
        subject = str(subjects[0]) if isinstance(subjects, list) and subjects else ""

        if event_type.startswith("claim.") and subject:
            claim_evidence.setdefault(subject, set()).update(
                str(ref) for ref in event.get("evidence_refs", [])
            )
            claim_snapshots.setdefault(subject, set()).update(
                str(ref) for ref in event.get("source_snapshot_refs", [])
            )

        if event_type in {"claim.state_changed", "claim.superseded"} and subject:
            to_state = (
                "superseded"
                if event_type == "claim.superseded"
                else str(payload_mapping.get("to_state", ""))
            )
            position_changes.append(
                {
                    "subject_id": subject,
                    "event_id": str(event["event_id"]),
                    "event_type": event_type,
                    "recorded_at": str(event["recorded_at"]),
                    "from_state": (
                        str(payload_mapping["from_state"])
                        if payload_mapping.get("from_state") is not None
                        else None
                    ),
                    "to_state": to_state,
                    "evidence_refs": sorted(str(ref) for ref in event.get("evidence_refs", [])),
                    "caused_by_event_ids": sorted(
                        str(ref) for ref in event.get("caused_by_event_ids", [])
                    ),
                }
            )

        if event_type == "relation.proposed":
            relation_id = str(payload_mapping.get("relation_id", ""))
            if relation_id:
                metadata = {str(key): value for key, value in payload_mapping.items()}
                relation_metadata[relation_id] = metadata
                ontology_ref = metadata.get("ontology_ref")
                if ontology_ref:
                    ontology_refs.add(str(ontology_ref))
                if metadata.get("source_type") == "Decision":
                    decision_refs.add(str(metadata.get("source_ref", "")))
                if metadata.get("target_type") == "Decision":
                    decision_refs.add(str(metadata.get("target_ref", "")))

    beliefs: dict[str, dict[str, Any]] = {}
    for claim_id in sorted(claims):
        claim = claims[claim_id]
        beliefs[claim_id] = {
            "state": str(claim.get("current_state", "")),
            "state_history": [str(item) for item in claim.get("state_history", [])],
            "proposed_event_id": str(claim.get("proposed_event_id", "")),
            "evidence_refs": sorted(claim_evidence.get(claim_id, set())),
            "source_snapshot_refs": sorted(claim_snapshots.get(claim_id, set())),
        }

    dependency_impacts: list[dict[str, Any]] = []
    disagreements: list[dict[str, Any]] = []
    for relation_id in sorted(relations):
        relation = relations[relation_id]
        relation_type = str(relation.get("relation_type", ""))
        relation_state = str(relation.get("current_state", ""))
        metadata = relation_metadata.get(relation_id, {})
        source_ref = str(relation.get("source_ref", metadata.get("source_ref", "")))
        target_ref = str(relation.get("target_ref", metadata.get("target_ref", "")))

        if relation_type in _DEPENDENCY_RELATION_TYPES and relation_state == "active":
            premise = beliefs.get(target_ref)
            premise_state = str(premise.get("state", "")) if premise else None
            if premise_state in NONCURRENT_STATES:
                dependent = beliefs.get(source_ref)
                source_type = metadata.get("source_type")
                dependent_type = (
                    str(source_type)
                    if source_type
                    else ("Claim" if dependent is not None else "Unknown")
                )
                target_type = metadata.get("target_type")
                dependency_impacts.append(
                    {
                        "relation_id": relation_id,
                        "relation_type": relation_type,
                        "relation_state": relation_state,
                        "dependent_ref": source_ref,
                        "dependent_type": dependent_type,
                        "dependent_state": (
                            str(dependent.get("state", "")) if dependent is not None else None
                        ),
                        "premise_ref": target_ref,
                        "premise_type": str(target_type) if target_type else "Claim",
                        "premise_state": premise_state,
                        "ontology_ref": (
                            str(metadata["ontology_ref"])
                            if metadata.get("ontology_ref")
                            else None
                        ),
                        "impact": "at_risk_due_to_noncurrent_premise",
                    }
                )

        if (
            relation_type in _DISAGREEMENT_RELATION_TYPES
            and relation_state not in {"invalidated", "superseded"}
        ):
            disagreements.append(
                {
                    "relation_id": relation_id,
                    "relation_type": relation_type,
                    "state": relation_state,
                    "source_ref": source_ref,
                    "target_ref": target_ref,
                    "ontology_ref": (
                        str(metadata["ontology_ref"])
                        if metadata.get("ontology_ref")
                        else None
                    ),
                    "evidence_refs": sorted(
                        str(ref)
                        for ref in next(
                            (
                                event.get("evidence_refs", [])
                                for event in event_list
                                if event.get("event_type") == "relation.proposed"
                                and isinstance(event.get("payload"), Mapping)
                                and str(event["payload"].get("relation_id", "")) == relation_id
                            ),
                            [],
                        )
                    ),
                }
            )

    return {
        "event_count": len(event_list),
        "claim_count": len(claims),
        "decision_count": len({ref for ref in decision_refs if ref}),
        "relation_count": len(relations),
        "beliefs": beliefs,
        "position_changes": position_changes,
        "dependency_impacts": dependency_impacts,
        "disagreements": disagreements,
        "ontology_refs": sorted(ontology_refs),
    }


def _position_change_checks(
    expected: Iterable[PositionChangeExpectation],
    observed: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    observations = [dict(item) for item in observed]
    checks: list[dict[str, Any]] = []
    for item in expected:
        match = next(
            (
                observation
                for observation in observations
                if observation.get("subject_id") == item.subject_id
                and observation.get("event_id") == item.event_id
            ),
            None,
        )
        passed = bool(
            match
            and match.get("to_state") == item.to_state
            and set(match.get("evidence_refs", [])) == set(item.evidence_refs)
            and set(match.get("caused_by_event_ids", [])) == set(item.caused_by_event_ids)
        )
        checks.append(
            {
                "subject_id": item.subject_id,
                "event_id": item.event_id,
                "expected_to_state": item.to_state,
                "observed_to_state": match.get("to_state") if match else None,
                "passed": passed,
            }
        )
    return checks


def _dependency_impact_checks(
    expected: Iterable[DependencyImpactExpectation],
    observed: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    observations = [dict(item) for item in observed]
    checks: list[dict[str, Any]] = []
    for item in expected:
        match = next(
            (
                observation
                for observation in observations
                if observation.get("relation_id") == item.relation_id
                and observation.get("dependent_ref") == item.dependent_ref
                and observation.get("premise_ref") == item.premise_ref
            ),
            None,
        )
        passed = bool(match and match.get("premise_state") == item.premise_state)
        checks.append(
            {
                "relation_id": item.relation_id,
                "dependent_ref": item.dependent_ref,
                "premise_ref": item.premise_ref,
                "expected_premise_state": item.premise_state,
                "observed_premise_state": match.get("premise_state") if match else None,
                "passed": passed,
            }
        )
    return checks


def _disagreement_checks(
    expected: Iterable[DisagreementExpectation],
    observed: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    observations = [dict(item) for item in observed]
    checks: list[dict[str, Any]] = []
    for item in expected:
        match = next(
            (
                observation
                for observation in observations
                if observation.get("relation_id") == item.relation_id
            ),
            None,
        )
        passed = bool(
            match
            and match.get("relation_type") == item.relation_type
            and match.get("source_ref") == item.source_ref
            and match.get("target_ref") == item.target_ref
        )
        checks.append(
            {
                "relation_id": item.relation_id,
                "expected_relation_type": item.relation_type,
                "observed_relation_type": match.get("relation_type") if match else None,
                "passed": passed,
            }
        )
    return checks


def _query_stability(phase_results: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    repeated: dict[str, list[dict[str, Any]]] = {}
    for phase in phase_results:
        for observation in phase.get("queries", []):
            repeated.setdefault(str(observation["case_id"]), []).append(dict(observation))
    return {
        case_id: {
            "observations": len(observations),
            "all_full_recall": all(float(item["recall_at_k"]) == 1.0 for item in observations),
            "no_current_state_leakage": all(
                not item["stale_before_current_relevant"] for item in observations
            ),
        }
        for case_id, observations in sorted(repeated.items())
        if len(observations) > 1
    }


def run_longitudinal_epistemic_benchmark(
    pack_roots: Iterable[Path],
    *,
    schemas_root: Path,
    phases: Iterable[LongitudinalPhase],
    benchmark_id: str = "longitudinal-epistemic-integrity-v1",
) -> dict[str, Any]:
    """Answer #111 longitudinal questions from durable replay, not retrieval authority.

    The benchmark deliberately remains a read/rebuild workload. It reconstructs each
    phase from local durable pack files, rebuilds the replaceable projection twice to
    check deterministic equivalence, derives causal/dependency/disagreement facts from
    the cutoff event set, and measures retrieval latency only after that local rebuild.
    It does not authorize or require a transaction-store/database rewrite.
    """

    roots = [Path(root) for root in pack_roots]
    phase_list = list(phases)
    if not roots or not phase_list:
        raise ValueError("longitudinal benchmark requires pack roots and phases")

    phase_results: list[dict[str, Any]] = []
    previous_beliefs: dict[str, dict[str, Any]] | None = None

    for phase in phase_list:
        build_started = time.perf_counter()
        documents = retrieval_documents_from_pack_fixtures(
            roots,
            schemas_root=schemas_root,
            as_of_recorded_at=phase.as_of_recorded_at,
        )
        projection_build_ms = (time.perf_counter() - build_started) * 1000.0

        rebuild_started = time.perf_counter()
        rebuilt_documents = retrieval_documents_from_pack_fixtures(
            roots,
            schemas_root=schemas_root,
            as_of_recorded_at=phase.as_of_recorded_at,
        )
        projection_rebuild_ms = (time.perf_counter() - rebuild_started) * 1000.0
        rebuild_equivalent = documents == rebuilt_documents

        events = _load_cutoff_events(
            roots,
            as_of_recorded_at=phase.as_of_recorded_at,
        )
        facts = _epistemic_facts(events, documents)
        documents_by_id = _documents_by_id(documents)
        state_checks = _state_checks(phase.expected_states, documents_by_id)

        retriever = RerankedRetriever(
            BM25Retriever(documents),
            LifecycleIntentReranker(),
            candidate_multiplier=4,
            version="longitudinal-baseline-v1",
        )
        query_observations = [_query_observation(retriever, case) for case in phase.queries]
        query_latency_ms = sum(float(item["latency_ms"]) for item in query_observations)

        position_checks = _position_change_checks(
            phase.expected_position_changes,
            facts["position_changes"],
        )
        dependency_checks = _dependency_impact_checks(
            phase.expected_dependency_impacts,
            facts["dependency_impacts"],
        )
        disagreement_checks = _disagreement_checks(
            phase.expected_disagreements,
            facts["disagreements"],
        )

        transition: dict[str, Any] | None = None
        if previous_beliefs is not None:
            changes: list[dict[str, Any]] = []
            current_beliefs = facts["beliefs"]
            for identifier in sorted(set(previous_beliefs) | set(current_beliefs)):
                before = previous_beliefs.get(identifier)
                after = current_beliefs.get(identifier)
                before_state = before.get("state") if before else None
                after_state = after.get("state") if after else None
                if before_state != after_state:
                    changes.append(
                        {
                            "id": identifier,
                            "before_state": before_state,
                            "after_state": after_state,
                        }
                    )
            transition = {"belief_state_changes": changes}

        phase_passed = (
            rebuild_equivalent
            and all(check["passed"] for check in state_checks)
            and all(item["passed"] for item in query_observations)
            and all(check["passed"] for check in position_checks)
            and all(check["passed"] for check in dependency_checks)
            and all(check["passed"] for check in disagreement_checks)
        )
        phase_result = {
            "phase_id": phase.phase_id,
            "as_of_recorded_at": phase.as_of_recorded_at,
            "event_count": facts["event_count"],
            "claim_count": facts["claim_count"],
            "decision_count": facts["decision_count"],
            "relation_count": facts["relation_count"],
            "document_count": len(documents),
            "projection_build_ms": projection_build_ms,
            "projection_rebuild_ms": projection_rebuild_ms,
            "query_latency_ms": query_latency_ms,
            "rebuild_equivalent": rebuild_equivalent,
            "ontology_refs_observed": facts["ontology_refs"],
            "beliefs": facts["beliefs"],
            "position_changes": facts["position_changes"],
            "dependency_impacts": facts["dependency_impacts"],
            "disagreements": facts["disagreements"],
            "state_checks": state_checks,
            "position_change_checks": position_checks,
            "dependency_impact_checks": dependency_checks,
            "disagreement_checks": disagreement_checks,
            "queries": query_observations,
            "transition_from_previous": transition,
            "passed": phase_passed,
        }
        phase_results.append(phase_result)
        previous_beliefs = facts["beliefs"]

    stability = _query_stability(phase_results)
    scale = {
        "max_event_count": max(int(phase["event_count"]) for phase in phase_results),
        "max_claim_count": max(int(phase["claim_count"]) for phase in phase_results),
        "max_decision_count": max(int(phase["decision_count"]) for phase in phase_results),
        "max_relation_count": max(int(phase["relation_count"]) for phase in phase_results),
    }
    passed = all(bool(phase["passed"]) for phase in phase_results) and all(
        bool(item["all_full_recall"]) and bool(item["no_current_state_leakage"])
        for item in stability.values()
    )

    return {
        "schema_version": "fossil.longitudinal-benchmark.v1",
        "benchmark_id": benchmark_id,
        "projection": "durable-event-replay->in-memory-bm25+lifecycle-intent-reranker",
        "authority_rule": "durable event replay determines epistemic state; retrieval is observational",
        "measurement_boundary": {
            "canonical_source": "local durable pack replay",
            "remote_canonical_object_scans_during_query": 0,
        },
        "phase_count": len(phase_results),
        "phases": phase_results,
        "historical_answer_stability": stability,
        "scale": scale,
        "passed": passed,
    }


__all__ = [
    "DependencyImpactExpectation",
    "DisagreementExpectation",
    "LongitudinalPhase",
    "NONCURRENT_STATES",
    "PositionChangeExpectation",
    "TemporalPhase",
    "TemporalQueryCase",
    "run_longitudinal_epistemic_benchmark",
    "run_temporal_evolution_benchmark",
]
