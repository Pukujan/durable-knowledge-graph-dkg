from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .real_retrieval import LifecycleIntentReranker, RerankedRetriever
from .services import BM25Retriever, ServiceMetadata, tokenize

ANSWER_OUTCOMES = frozenset(
    {"answer", "insufficient_evidence", "conflicting_evidence", "current_state_unresolved"}
)
CURRENT_STATES = frozenset({"supported", "open"})
HISTORICAL_STATES = frozenset(
    {"superseded", "rejected", "retracted", "stale_pending_review", "disputed"}
)
UNRESOLVED_STATES = frozenset({"disputed", "stale_pending_review"})
LIVE_CONFLICT_STATES = frozenset({"supported", "open", "disputed"})
_CITATION_KEYS = (
    "schema_version",
    "citation_id",
    "snapshot_id",
    "artifact_id",
    "byte_start",
    "byte_end",
    "passage_hash",
)


@dataclass(frozen=True)
class AnswerReliabilityCase:
    case_id: str
    query: str
    pack_ids: tuple[str, ...]
    expected_outcome: str
    required_claim_ids: frozenset[str] = frozenset()
    allowed_claim_ids: frozenset[str] = frozenset()
    forbidden_claim_ids: frozenset[str] = frozenset()
    required_citation_ids: frozenset[str] = frozenset()
    category: str = "general"
    limit: int = 8

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "AnswerReliabilityCase":
        required = frozenset(str(item) for item in value.get("required_claim_ids", []))
        allowed_raw = value.get("allowed_claim_ids")
        allowed = (
            frozenset(str(item) for item in allowed_raw)
            if allowed_raw is not None
            else required
        )
        return cls(
            case_id=str(value["case_id"]),
            query=str(value["query"]),
            pack_ids=tuple(str(item) for item in value["pack_ids"]),
            expected_outcome=str(value["expected_outcome"]),
            required_claim_ids=required,
            allowed_claim_ids=allowed,
            forbidden_claim_ids=frozenset(
                str(item) for item in value.get("forbidden_claim_ids", [])
            ),
            required_citation_ids=frozenset(
                str(item) for item in value.get("required_citation_ids", [])
            ),
            category=str(value.get("category", "general")),
            limit=int(value.get("limit", 8)),
        )

    def __post_init__(self) -> None:
        if not self.case_id or not self.query or not self.pack_ids:
            raise ValueError("answer reliability cases require id/query/packs")
        if self.expected_outcome not in ANSWER_OUTCOMES:
            raise ValueError(f"invalid expected answer outcome: {self.expected_outcome}")
        if self.limit < 1:
            raise ValueError("answer reliability case limit must be positive")
        if self.expected_outcome == "answer" and not self.required_claim_ids:
            raise ValueError("answer cases require at least one required claim")


def _documents_by_id(documents: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(document["id"]): dict(document) for document in documents}


def _canonical_citation(value: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    return {key: value.get(key) for key in _CITATION_KEYS}


def _candidate_claims(candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = candidate.get("claims", [])
    if not isinstance(raw, list):
        return []
    return [dict(item) for item in raw if isinstance(item, Mapping)]


def _claim_payload(document: Mapping[str, Any]) -> dict[str, Any]:
    payload = {
        "claim_id": str(document["id"]),
        "text": str(document.get("text", "")),
    }
    citation = _canonical_citation(document.get("citation"))
    if citation is not None:
        payload["citation"] = citation
    return payload


def evaluate_answer_candidate(
    candidate: Mapping[str, Any],
    *,
    case: AnswerReliabilityCase,
    documents: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    document_by_id = _documents_by_id(documents)
    observed_outcome = str(candidate.get("outcome", "invalid"))
    claims = _candidate_claims(candidate)
    claim_ids = [str(item.get("claim_id", "")) for item in claims if item.get("claim_id")]
    claim_id_set = set(claim_ids)

    unsupported_ids = sorted(
        {
            identifier
            for identifier in claim_id_set
            if identifier not in case.allowed_claim_ids
            or identifier not in document_by_id
            or str(document_by_id[identifier].get("document_type", "")) != "claim"
        }
    )
    forbidden_present = sorted(claim_id_set & set(case.forbidden_claim_ids))
    required_present = set(case.required_claim_ids) <= claim_id_set
    completeness = (
        len(set(case.required_claim_ids) & claim_id_set) / len(case.required_claim_ids)
        if case.required_claim_ids
        else 1.0
    )

    citation_checks: list[dict[str, Any]] = []
    observed_citation_ids: set[str] = set()
    for claim in claims:
        identifier = str(claim.get("claim_id", ""))
        expected_document = document_by_id.get(identifier)
        expected = _canonical_citation(
            expected_document.get("citation") if expected_document else None
        )
        observed = _canonical_citation(claim.get("citation"))
        if observed and observed.get("citation_id"):
            observed_citation_ids.add(str(observed["citation_id"]))
        exact = expected is not None and observed == expected
        citation_checks.append(
            {
                "claim_id": identifier,
                "expected_citation_id": (
                    str(expected.get("citation_id")) if expected else None
                ),
                "observed_citation_id": (
                    str(observed.get("citation_id")) if observed else None
                ),
                "exact_match": exact,
            }
        )

    required_citations_present = set(case.required_citation_ids) <= observed_citation_ids
    citation_correct = all(item["exact_match"] for item in citation_checks) and (
        required_citations_present
    )
    if not claims and not case.required_citation_ids:
        citation_correct = True

    outcome_match = observed_outcome == case.expected_outcome
    contradiction_handled = (
        outcome_match and required_present and citation_correct
        if case.expected_outcome == "conflicting_evidence"
        else True
    )
    appropriate_abstention = (
        outcome_match if case.expected_outcome != "answer" else None
    )
    overabstention = case.expected_outcome == "answer" and observed_outcome != "answer"

    try:
        confidence = float(candidate.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    case_correct = (
        outcome_match
        and required_present
        and not unsupported_ids
        and not forbidden_present
        and citation_correct
        and contradiction_handled
    )
    unsupported_rate = len(unsupported_ids) / max(len(claim_id_set), 1)

    return {
        "case_id": case.case_id,
        "category": case.category,
        "expected_outcome": case.expected_outcome,
        "observed_outcome": observed_outcome,
        "outcome_match": outcome_match,
        "required_claim_ids": sorted(case.required_claim_ids),
        "observed_claim_ids": claim_ids,
        "unsupported_claim_ids": unsupported_ids,
        "unsupported_claim_rate": unsupported_rate,
        "forbidden_claim_ids_present": forbidden_present,
        "completeness": completeness,
        "citation_checks": citation_checks,
        "required_citation_ids": sorted(case.required_citation_ids),
        "required_citations_present": required_citations_present,
        "citation_correct": citation_correct,
        "contradiction_handled": contradiction_handled,
        "appropriate_abstention": appropriate_abstention,
        "overabstention": overabstention,
        "confidence": confidence,
        "case_correct": case_correct,
    }


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
