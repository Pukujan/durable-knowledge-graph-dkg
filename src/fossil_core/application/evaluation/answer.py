from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


ANSWER_OUTCOMES = frozenset(
    {"answer", "insufficient_evidence", "conflicting_evidence", "current_state_unresolved"}
)
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
