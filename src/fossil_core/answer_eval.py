from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .application.evaluation.answer import (
    ANSWER_OUTCOMES,
    AnswerReliabilityCase,
    _CITATION_KEYS,
    _candidate_claims,
    _canonical_citation,
    _documents_by_id,
    evaluate_answer_candidate,
)
from .real_retrieval import LifecycleIntentReranker, RerankedRetriever
from .services import BM25Retriever, ServiceMetadata, tokenize

CURRENT_STATES = frozenset({"supported", "open"})
HISTORICAL_STATES = frozenset(
    {"superseded", "rejected", "retracted", "stale_pending_review", "disputed"}
)
UNRESOLVED_STATES = frozenset({"disputed", "stale_pending_review"})
LIVE_CONFLICT_STATES = frozenset({"supported", "open", "disputed"})


def _claim_payload(document: Mapping[str, Any]) -> dict[str, Any]:
    payload = {
        "claim_id": str(document["id"]),
        "text": str(document.get("text", "")),
    }
    citation = _canonical_citation(document.get("citation"))
    if citation is not None:
        payload["citation"] = citation
    return payload


class DeterministicEvidenceAnswerService:
    """Provider-independent answer baseline that can only emit retrieved durable claims.

    It is intentionally conservative. It copies claim text/citation identity from validated
    retrieval documents, respects lifecycle state, and abstains instead of inventing prose.
    """

    def __init__(self, *, version: str = "1") -> None:
        self.version = version

    def metadata(self) -> dict[str, Any]:
        return ServiceMetadata(
            kind="model",
            provider="fossil",
            provider_version="1",
            implementation="deterministic-evidence-answerer",
            implementation_version=self.version,
            model_id=None,
            local=True,
            estimated_cost_per_call_usd=0.0,
            runtime={"authority": "durable-context-only"},
        ).as_dict()

    @staticmethod
    def _overlap(query: str, document: Mapping[str, Any]) -> float:
        query_terms = set(tokenize(query))
        if not query_terms:
            return 0.0
        document_terms = set(tokenize(str(document.get("text", ""))))
        return len(query_terms & document_terms) / len(query_terms)

    def run(self, task: dict[str, Any]) -> dict[str, Any]:
        query = str(task["query"])
        items = [dict(item) for item in task.get("context_items", [])]
        claim_items = [
            item for item in items if str(item.get("document_type", "")) == "claim"
        ]
        if not claim_items:
            return {
                "output": {
                    "outcome": "insufficient_evidence",
                    "answer_text": "Insufficient evidence.",
                    "claims": [],
                    "confidence": 1.0,
                },
                "authority": "candidate_only",
                "service": self.metadata(),
            }

        ranked_claims = sorted(
            enumerate(claim_items),
            key=lambda pair: (
                -self._overlap(query, pair[1]),
                pair[0],
                str(pair[1].get("id", "")),
            ),
        )
        top_overlap = self._overlap(query, ranked_claims[0][1])
        topical = [
            item
            for _, item in ranked_claims
            if abs(self._overlap(query, item) - top_overlap) < 1e-12
        ]
        topical_by_id = {str(item["id"]): item for item in topical}

        relations = [
            item
            for item in items
            if str(item.get("document_type", "")) == "relation"
            and str(item.get("relation_type", "")) == "CONTRADICTS"
            and str(item.get("current_state", "")) == "active"
        ]
        for relation in relations:
            source = topical_by_id.get(str(relation.get("source_ref", "")))
            target = topical_by_id.get(str(relation.get("target_ref", "")))
            if not source or not target:
                continue
            source_state = str(source.get("current_state", ""))
            target_state = str(target.get("current_state", ""))
            if source_state in LIVE_CONFLICT_STATES and target_state in LIVE_CONFLICT_STATES:
                evidence = [_claim_payload(source), _claim_payload(target)]
                evidence.sort(key=lambda item: str(item["claim_id"]))
                return {
                    "output": {
                        "outcome": "conflicting_evidence",
                        "answer_text": "Conflicting evidence remains unresolved.",
                        "claims": evidence,
                        "confidence": 1.0,
                    },
                    "authority": "candidate_only",
                    "service": self.metadata(),
                }

        intent = LifecycleIntentReranker.intent_for_query(query)
        if intent == "historical":
            historical = [
                item
                for item in topical
                if str(item.get("current_state", "")) in HISTORICAL_STATES
            ]
            if historical:
                chosen = historical[0]
                return {
                    "output": {
                        "outcome": "answer",
                        "answer_text": str(chosen.get("text", "")),
                        "claims": [_claim_payload(chosen)],
                        "confidence": 1.0,
                    },
                    "authority": "candidate_only",
                    "service": self.metadata(),
                }

        current = [
            item for item in topical if str(item.get("current_state", "")) in CURRENT_STATES
        ]
        if current:
            chosen = current[0]
            return {
                "output": {
                    "outcome": "answer",
                    "answer_text": str(chosen.get("text", "")),
                    "claims": [_claim_payload(chosen)],
                    "confidence": 1.0,
                },
                "authority": "candidate_only",
                "service": self.metadata(),
            }

        unresolved = [
            item
            for item in topical
            if str(item.get("current_state", "")) in UNRESOLVED_STATES
        ]
        if unresolved:
            chosen = unresolved[0]
            return {
                "output": {
                    "outcome": "current_state_unresolved",
                    "answer_text": "Current state unresolved.",
                    "claims": [_claim_payload(chosen)],
                    "confidence": 1.0,
                },
                "authority": "candidate_only",
                "service": self.metadata(),
            }

        return {
            "output": {
                "outcome": "insufficient_evidence",
                "answer_text": "Insufficient evidence.",
                "claims": [],
                "confidence": 1.0,
            },
            "authority": "candidate_only",
            "service": self.metadata(),
        }


def build_answer_context(
    documents: Iterable[Mapping[str, Any]],
    case: AnswerReliabilityCase,
) -> list[dict[str, Any]]:
    document_list = [dict(document) for document in documents]
    base = BM25Retriever(document_list)
    retriever = RerankedRetriever(
        base,
        LifecycleIntentReranker(),
        candidate_multiplier=4,
        version="answer-reliability-baseline-v1",
    )
    return retriever.search(
        case.query,
        pack_ids=list(case.pack_ids),
        limit=case.limit,
    )


def run_answer_reliability_benchmark(
    service: Any,
    *,
    documents: Iterable[Mapping[str, Any]],
    cases: Iterable[AnswerReliabilityCase],
    benchmark_id: str = "post-gate2-answer-reliability-v1",
) -> dict[str, Any]:
    document_list = [dict(document) for document in documents]
    case_list = list(cases)
    if not document_list or not case_list:
        raise ValueError("answer reliability benchmark requires documents and cases")

    service_metadata = dict(service.metadata())
    observations: list[dict[str, Any]] = []
    latencies_ms: list[float] = []

    for case in case_list:
        context_items = build_answer_context(document_list, case)
        started = time.perf_counter()
        response = dict(
            service.run(
                {
                    "query": case.query,
                    "pack_ids": list(case.pack_ids),
                    "context_items": context_items,
                    "response_contract": {
                        "outcomes": sorted(ANSWER_OUTCOMES),
                        "claims": "structured claim_id/text/citation assertions",
                        "confidence": "0..1 confidence in the emitted outcome",
                    },
                }
            )
        )
        latency_ms = (time.perf_counter() - started) * 1000.0
        latencies_ms.append(latency_ms)
        candidate = dict(response.get("output", {}))
        evaluation = evaluate_answer_candidate(
            candidate,
            case=case,
            documents=document_list,
        )
        observations.append(
            {
                **evaluation,
                "query": case.query,
                "context_ids": [str(item["id"]) for item in context_items],
                "answer_text": str(candidate.get("answer_text", "")),
                "latency_ms": latency_ms,
                "authority": response.get("authority"),
                "service": dict(response.get("service", service_metadata)),
            }
        )

    count = len(observations)
    abstention_cases = [
        item for item in observations if item["expected_outcome"] != "answer"
    ]
    conflict_cases = [
        item
        for item in observations
        if item["expected_outcome"] == "conflicting_evidence"
    ]
    exact_citations = [bool(item["citation_correct"]) for item in observations]
    brier = sum(
        (
            float(item["confidence"])
            - (1.0 if bool(item["case_correct"]) else 0.0)
        )
        ** 2
        for item in observations
    ) / count
    high_confidence_errors = [
        item
        for item in observations
        if float(item["confidence"]) >= 0.8 and not bool(item["case_correct"])
    ]
    cost_per_call = float(service_metadata.get("estimated_cost_per_call_usd", 0.0))

    metrics = {
        "final_answer_correctness_rate": sum(
            bool(item["case_correct"]) for item in observations
        )
        / count,
        "outcome_accuracy": sum(bool(item["outcome_match"]) for item in observations)
        / count,
        "citation_correctness_rate": sum(exact_citations) / count,
        "mean_unsupported_claim_rate": sum(
            float(item["unsupported_claim_rate"]) for item in observations
        )
        / count,
        "completeness_rate": sum(
            float(item["completeness"]) == 1.0 for item in observations
        )
        / count,
        "contradiction_handling_rate": (
            sum(bool(item["contradiction_handled"]) for item in conflict_cases)
            / len(conflict_cases)
            if conflict_cases
            else None
        ),
        "appropriate_abstention_rate": (
            sum(bool(item["appropriate_abstention"]) for item in abstention_cases)
            / len(abstention_cases)
            if abstention_cases
            else None
        ),
        "overabstention_rate": sum(bool(item["overabstention"]) for item in observations)
        / count,
        "brier_score": brier,
        "high_confidence_error_rate": len(high_confidence_errors) / count,
        "mean_latency_ms": sum(latencies_ms) / count,
        "estimated_cost_usd": cost_per_call * count,
    }

    return {
        "schema_version": "fossil.answer-reliability-benchmark.v1",
        "benchmark_id": benchmark_id,
        "authority_rule": "durable evidence/lifecycle/citation identity outranks model confidence",
        "service": service_metadata,
        "case_count": count,
        "metrics": metrics,
        "observations": observations,
        "passed": all(bool(item["case_correct"]) for item in observations),
    }
