from __future__ import annotations

import inspect

import fossil_core.answer_eval as legacy_answer_eval
import fossil_core.application.evaluation.answer as canonical_answer_eval


EXPECTED_IMPLICIT_NAMESPACE = {
    "ANSWER_OUTCOMES",
    "AnswerReliabilityCase",
    "Any",
    "BM25Retriever",
    "CURRENT_STATES",
    "DeterministicEvidenceAnswerService",
    "HISTORICAL_STATES",
    "Iterable",
    "LIVE_CONFLICT_STATES",
    "LifecycleIntentReranker",
    "Mapping",
    "RerankedRetriever",
    "ServiceMetadata",
    "UNRESOLVED_STATES",
    "annotations",
    "build_answer_context",
    "dataclass",
    "evaluate_answer_candidate",
    "run_answer_reliability_benchmark",
    "time",
    "tokenize",
}


def test_answer_eval_legacy_namespace_and_moved_identity_are_frozen():
    assert not hasattr(legacy_answer_eval, "__all__")
    assert {
        name for name in vars(legacy_answer_eval) if not name.startswith("_")
    } == EXPECTED_IMPLICIT_NAMESPACE

    assert legacy_answer_eval.ANSWER_OUTCOMES is canonical_answer_eval.ANSWER_OUTCOMES
    assert legacy_answer_eval.AnswerReliabilityCase is canonical_answer_eval.AnswerReliabilityCase
    assert legacy_answer_eval.evaluate_answer_candidate is canonical_answer_eval.evaluate_answer_candidate
    assert legacy_answer_eval._CITATION_KEYS is canonical_answer_eval._CITATION_KEYS
    assert legacy_answer_eval._documents_by_id is canonical_answer_eval._documents_by_id
    assert legacy_answer_eval._canonical_citation is canonical_answer_eval._canonical_citation
    assert legacy_answer_eval._candidate_claims is canonical_answer_eval._candidate_claims


def test_answer_evaluation_call_shapes_are_unchanged():
    from_mapping = list(
        inspect.signature(canonical_answer_eval.AnswerReliabilityCase.from_mapping).parameters.values()
    )
    assert [parameter.name for parameter in from_mapping] == ["value"]

    evaluation = list(
        inspect.signature(canonical_answer_eval.evaluate_answer_candidate).parameters.values()
    )
    assert [parameter.name for parameter in evaluation] == ["candidate", "case", "documents"]
    assert evaluation[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert evaluation[1].kind is inspect.Parameter.KEYWORD_ONLY
    assert evaluation[2].kind is inspect.Parameter.KEYWORD_ONLY


def test_answer_candidate_evaluation_behavior_matches_legacy_path():
    citation = {
        "schema_version": "fossil.citation.v1",
        "citation_id": "cite_one",
        "snapshot_id": "snap_one",
        "artifact_id": "artifact_one",
        "byte_start": 0,
        "byte_end": 4,
        "passage_hash": {"algorithm": "sha256", "digest": "abc"},
    }
    documents = [
        {
            "id": "claim_one",
            "document_type": "claim",
            "text": "supported claim",
            "citation": citation,
        },
        {
            "id": "claim_forbidden",
            "document_type": "claim",
            "text": "forbidden claim",
            "citation": citation,
        },
    ]
    case = canonical_answer_eval.AnswerReliabilityCase(
        case_id="case_one",
        query="what is supported",
        pack_ids=("pack_one",),
        expected_outcome="answer",
        required_claim_ids=frozenset({"claim_one"}),
        allowed_claim_ids=frozenset({"claim_one"}),
        forbidden_claim_ids=frozenset({"claim_forbidden"}),
        required_citation_ids=frozenset({"cite_one"}),
    )
    candidate = {
        "outcome": "answer",
        "claims": [
            {
                "claim_id": "claim_one",
                "text": "supported claim",
                "citation": citation,
            }
        ],
        "confidence": 1.5,
    }

    canonical = canonical_answer_eval.evaluate_answer_candidate(
        candidate,
        case=case,
        documents=documents,
    )
    legacy = legacy_answer_eval.evaluate_answer_candidate(
        candidate,
        case=case,
        documents=documents,
    )
    assert legacy == canonical
    assert canonical["case_correct"] is True
    assert canonical["citation_correct"] is True
    assert canonical["completeness"] == 1.0
    assert canonical["unsupported_claim_rate"] == 0.0
    assert canonical["confidence"] == 1.0


def test_answer_candidate_failure_classification_is_preserved():
    documents = [
        {"id": "claim_one", "document_type": "claim", "text": "supported"},
        {"id": "claim_forbidden", "document_type": "claim", "text": "forbidden"},
    ]
    case = canonical_answer_eval.AnswerReliabilityCase(
        case_id="case_two",
        query="what is supported",
        pack_ids=("pack_one",),
        expected_outcome="answer",
        required_claim_ids=frozenset({"claim_one"}),
        allowed_claim_ids=frozenset({"claim_one"}),
        forbidden_claim_ids=frozenset({"claim_forbidden"}),
    )
    candidate = {
        "outcome": "insufficient_evidence",
        "claims": [{"claim_id": "claim_forbidden"}],
        "confidence": "not-a-number",
    }

    result = canonical_answer_eval.evaluate_answer_candidate(
        candidate,
        case=case,
        documents=documents,
    )
    assert result["case_correct"] is False
    assert result["outcome_match"] is False
    assert result["forbidden_claim_ids_present"] == ["claim_forbidden"]
    assert result["unsupported_claim_ids"] == ["claim_forbidden"]
    assert result["overabstention"] is True
    assert result["confidence"] == 0.0
