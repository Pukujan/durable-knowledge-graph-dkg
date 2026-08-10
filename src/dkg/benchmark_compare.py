from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .benchmark import RetrievalBenchmarkCase
from .real_retrieval import LifecycleIntentReranker


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


def _documents_by_id(documents: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(document["id"]): dict(document) for document in documents}


def _cases_by_id(cases: Iterable[RetrievalBenchmarkCase]) -> dict[str, RetrievalBenchmarkCase]:
    return {case.case_id: case for case in cases}


def classify_retrieval_result(
    result: Mapping[str, Any],
    *,
    cases: Iterable[RetrievalBenchmarkCase],
    documents: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Classify benchmark observations without changing the benchmark contract."""

    case_by_id = _cases_by_id(cases)
    document_by_id = _documents_by_id(documents)
    counts = {
        "retrieval_miss": 0,
        "incomplete_multi_target_recall": 0,
        "bad_ranking": 0,
        "stale_superseded_leakage": 0,
        "pack_isolation_violation": 0,
    }
    examples: dict[str, list[dict[str, Any]]] = {key: [] for key in counts}

    for observation in result.get("observations", []):
        case_id = str(observation["case_id"])
        case = case_by_id[case_id]
        returned_ids = [str(identifier) for identifier in observation.get("returned_ids", [])]
        relevant = set(case.relevant_ids)

        if bool(observation.get("failed", False)):
            counts["retrieval_miss"] += 1
            examples["retrieval_miss"].append(
                {
                    "case_id": case_id,
                    "category": case.category,
                    "returned_ids": returned_ids,
                    "relevant_ids": sorted(relevant),
                }
            )

        recall = float(observation.get("recall_at_k", 0.0))
        if recall < 1.0:
            counts["incomplete_multi_target_recall"] += 1
            examples["incomplete_multi_target_recall"].append(
                {
                    "case_id": case_id,
                    "category": case.category,
                    "recall_at_k": recall,
                    "returned_ids": returned_ids,
                    "relevant_ids": sorted(relevant),
                }
            )

        reciprocal_rank = float(observation.get("reciprocal_rank", 0.0))
        if 0.0 < reciprocal_rank < 1.0:
            counts["bad_ranking"] += 1
            examples["bad_ranking"].append(
                {
                    "case_id": case_id,
                    "category": case.category,
                    "reciprocal_rank": reciprocal_rank,
                    "returned_ids": returned_ids,
                    "relevant_ids": sorted(relevant),
                }
            )

        isolation_violations = [
            identifier
            for identifier in returned_ids
            if identifier in document_by_id
            and str(document_by_id[identifier].get("pack_id")) not in set(case.pack_ids)
        ]
        if isolation_violations:
            counts["pack_isolation_violation"] += 1
            examples["pack_isolation_violation"].append(
                {
                    "case_id": case_id,
                    "allowed_pack_ids": list(case.pack_ids),
                    "violating_ids": isolation_violations,
                }
            )

        if LifecycleIntentReranker.intent_for_query(case.query) == "current":
            first_relevant_rank = next(
                (rank for rank, identifier in enumerate(returned_ids, start=1) if identifier in relevant),
                None,
            )
            leaked: list[dict[str, Any]] = []
            for rank, identifier in enumerate(returned_ids, start=1):
                if first_relevant_rank is not None and rank >= first_relevant_rank:
                    break
                document = document_by_id.get(identifier)
                state = str(document.get("current_state")) if document else ""
                if state in NONCURRENT_STATES:
                    leaked.append({"id": identifier, "rank": rank, "state": state})
            if first_relevant_rank is None:
                leaked = []
                for rank, identifier in enumerate(returned_ids, start=1):
                    document = document_by_id.get(identifier)
                    state = str(document.get("current_state")) if document else ""
                    if state in NONCURRENT_STATES:
                        leaked.append({"id": identifier, "rank": rank, "state": state})
            if leaked:
                counts["stale_superseded_leakage"] += 1
                examples["stale_superseded_leakage"].append(
                    {
                        "case_id": case_id,
                        "category": case.category,
                        "first_relevant_rank": first_relevant_rank,
                        "leaked": leaked,
                    }
                )

    return {
        "benchmark_id": result.get("benchmark_id"),
        "service": dict(result.get("service", {})),
        "counts": counts,
        "examples": examples,
        "unsupported_confidence_leakage": {
            "applicable": False,
            "observed": False,
            "reason": (
                "retrieval/context strategies return ranked corpus objects and do not emit "
                "candidate truth authority or truth-changing claims"
            ),
        },
    }


def classify_context_probe(probe: Mapping[str, Any]) -> dict[str, Any]:
    items = [dict(item) for item in probe.get("items", [])]
    truncated_ids = [
        str(item.get("id"))
        for item in items
        if bool(item.get("context_truncated", False))
    ]
    chars_used = int(probe.get("chars_used", 0))
    max_chars = int(probe.get("max_chars", 0))
    return {
        "chars_used": chars_used,
        "max_chars": max_chars,
        "item_ids": [str(item.get("id")) for item in items],
        "truncated_ids": truncated_ids,
        "context_truncation_or_overload": bool(truncated_ids) or (
            max_chars > 0 and chars_used >= max_chars
        ),
    }


def comparative_summary(
    results: Mapping[str, Mapping[str, Any]],
    *,
    cases: Iterable[RetrievalBenchmarkCase],
    documents: Iterable[Mapping[str, Any]],
    context_probes: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    case_list = list(cases)
    document_list = [dict(document) for document in documents]
    contexts = context_probes or {}
    services: dict[str, Any] = {}

    for name, result in results.items():
        services[name] = {
            "benchmark_id": result.get("benchmark_id"),
            "service": dict(result.get("service", {})),
            "metrics": dict(result.get("metrics", {})),
            "failure_taxonomy": classify_retrieval_result(
                result,
                cases=case_list,
                documents=document_list,
            ),
            "context_probe": (
                classify_context_probe(contexts[name]) if name in contexts else None
            ),
        }

    return {
        "schema_version": "fossil.gate2-comparison.v1",
        "case_count": len(case_list),
        "service_count": len(services),
        "services": services,
        "selection": {
            "selected": None,
            "reason": "comparison evidence only; policy selection belongs to Gate 2D / #37",
        },
    }
