from __future__ import annotations

from dkg.answer_eval import (
    AnswerReliabilityCase,
    DeterministicEvidenceAnswerService,
    evaluate_answer_candidate,
    run_answer_reliability_benchmark,
)

PACK = "pack_test_answer_reliability"


def _citation(identifier: str, *, start: int = 0) -> dict:
    return {
        "schema_version": "fossil.citation.v1",
        "citation_id": identifier,
        "snapshot_id": f"snap_{identifier}",
        "artifact_id": f"art_{identifier}",
        "byte_start": start,
        "byte_end": start + 20,
        "passage_hash": {"algorithm": "sha256", "digest": identifier[-1] * 64},
    }


def _claim(identifier: str, text: str, state: str, citation_id: str) -> dict:
    return {
        "id": identifier,
        "pack_id": PACK,
        "text": text,
        "document_type": "claim",
        "current_state": state,
        "state_history": [state],
        "citation": _citation(citation_id),
    }


def test_evaluator_accepts_exact_supported_answer_and_citation():
    document = _claim(
        "clm_durable",
        "Durable truth uses immutable evidence and append-only events.",
        "supported",
        "cite_durable",
    )
    case = AnswerReliabilityCase(
        case_id="current-durable",
        query="What is the current durable truth?",
        pack_ids=(PACK,),
        expected_outcome="answer",
        required_claim_ids=frozenset({"clm_durable"}),
        allowed_claim_ids=frozenset({"clm_durable"}),
        required_citation_ids=frozenset({"cite_durable"}),
    )
    result = evaluate_answer_candidate(
        {
            "outcome": "answer",
            "answer_text": document["text"],
            "claims": [
                {
                    "claim_id": document["id"],
                    "text": document["text"],
                    "citation": document["citation"],
                }
            ],
            "confidence": 0.95,
        },
        case=case,
        documents=[document],
    )

    assert result["case_correct"] is True
    assert result["citation_correct"] is True
    assert result["unsupported_claim_rate"] == 0.0
    assert result["completeness"] == 1.0


def test_evaluator_flags_wrong_citation_and_unsupported_claim():
    supported = _claim("clm_supported", "Supported claim.", "supported", "cite_supported")
    other = _claim("clm_other", "Other claim.", "supported", "cite_other")
    case = AnswerReliabilityCase(
        case_id="bad-answer",
        query="What is supported?",
        pack_ids=(PACK,),
        expected_outcome="answer",
        required_claim_ids=frozenset({"clm_supported"}),
        allowed_claim_ids=frozenset({"clm_supported"}),
        required_citation_ids=frozenset({"cite_supported"}),
    )
    result = evaluate_answer_candidate(
        {
            "outcome": "answer",
            "claims": [
                {
                    "claim_id": "clm_supported",
                    "text": supported["text"],
                    "citation": other["citation"],
                },
                {
                    "claim_id": "clm_other",
                    "text": other["text"],
                    "citation": other["citation"],
                },
            ],
            "confidence": 1.0,
        },
        case=case,
        documents=[supported, other],
    )

    assert result["case_correct"] is False
    assert result["citation_correct"] is False
    assert result["unsupported_claim_ids"] == ["clm_other"]
    assert result["unsupported_claim_rate"] == 0.5


def test_deterministic_answerer_emits_unresolved_and_conflicting_evidence():
    service = DeterministicEvidenceAnswerService()
    stale = _claim(
        "clm_stale",
        "The first SQLite prototype is the canonical architecture implementation.",
        "stale_pending_review",
        "cite_stale",
    )
    unresolved = service.run(
        {
            "query": "Is the first SQLite prototype the current canonical architecture implementation?",
            "context_items": [stale],
        }
    )["output"]
    assert unresolved["outcome"] == "current_state_unresolved"
    assert unresolved["claims"][0]["claim_id"] == "clm_stale"

    left = _claim("clm_blue", "Widget mode is blue.", "supported", "cite_blue")
    right = _claim("clm_not_blue", "Widget mode is not blue.", "supported", "cite_not_blue")
    contradiction = {
        "id": "rel_widget_conflict",
        "pack_id": PACK,
        "text": "Widget mode is blue. Relation: CONTRADICTS. Widget mode is not blue.",
        "document_type": "relation",
        "relation_type": "CONTRADICTS",
        "source_ref": "clm_blue",
        "target_ref": "clm_not_blue",
        "current_state": "active",
    }
    conflict = service.run(
        {
            "query": "What is the current widget mode blue?",
            "context_items": [left, right, contradiction],
        }
    )["output"]
    assert conflict["outcome"] == "conflicting_evidence"
    assert {item["claim_id"] for item in conflict["claims"]} == {
        "clm_blue",
        "clm_not_blue",
    }


def test_benchmark_scores_answer_abstention_conflict_and_calibration():
    durable = _claim(
        "clm_durable",
        "Durable truth uses immutable evidence and append-only events.",
        "supported",
        "cite_durable",
    )
    stale = _claim(
        "clm_stale",
        "The first SQLite prototype is the canonical architecture implementation.",
        "stale_pending_review",
        "cite_stale",
    )
    left = _claim("clm_blue", "Widget mode is blue.", "supported", "cite_blue")
    right = _claim("clm_not_blue", "Widget mode is not blue.", "supported", "cite_not_blue")
    contradiction = {
        "id": "rel_widget_conflict",
        "pack_id": PACK,
        "text": "Widget mode is blue. Relation: CONTRADICTS. Widget mode is not blue.",
        "document_type": "relation",
        "relation_type": "CONTRADICTS",
        "source_ref": "clm_blue",
        "target_ref": "clm_not_blue",
        "current_state": "active",
    }
    cases = [
        AnswerReliabilityCase(
            case_id="answer",
            query="What is the current durable truth using immutable evidence and append-only events?",
            pack_ids=(PACK,),
            expected_outcome="answer",
            required_claim_ids=frozenset({"clm_durable"}),
            allowed_claim_ids=frozenset({"clm_durable"}),
            required_citation_ids=frozenset({"cite_durable"}),
        ),
        AnswerReliabilityCase(
            case_id="unresolved",
            query="Is the first SQLite prototype the current canonical architecture implementation?",
            pack_ids=(PACK,),
            expected_outcome="current_state_unresolved",
            required_claim_ids=frozenset({"clm_stale"}),
            allowed_claim_ids=frozenset({"clm_stale"}),
            required_citation_ids=frozenset({"cite_stale"}),
        ),
        AnswerReliabilityCase(
            case_id="conflict",
            query="What is the current widget mode blue?",
            pack_ids=(PACK,),
            expected_outcome="conflicting_evidence",
            required_claim_ids=frozenset({"clm_blue", "clm_not_blue"}),
            allowed_claim_ids=frozenset({"clm_blue", "clm_not_blue"}),
            required_citation_ids=frozenset({"cite_blue", "cite_not_blue"}),
        ),
        AnswerReliabilityCase(
            case_id="insufficient",
            query="quasar zebrafish magnetotail authorization",
            pack_ids=(PACK,),
            expected_outcome="insufficient_evidence",
        ),
    ]

    report = run_answer_reliability_benchmark(
        DeterministicEvidenceAnswerService(),
        documents=[durable, stale, left, right, contradiction],
        cases=cases,
    )

    assert report["passed"] is True
    assert report["metrics"]["final_answer_correctness_rate"] == 1.0
    assert report["metrics"]["citation_correctness_rate"] == 1.0
    assert report["metrics"]["mean_unsupported_claim_rate"] == 0.0
    assert report["metrics"]["completeness_rate"] == 1.0
    assert report["metrics"]["contradiction_handling_rate"] == 1.0
    assert report["metrics"]["appropriate_abstention_rate"] == 1.0
    assert report["metrics"]["overabstention_rate"] == 0.0
    assert report["metrics"]["brier_score"] == 0.0
    assert report["metrics"]["high_confidence_error_rate"] == 0.0
