from __future__ import annotations

from fossil_core.answer_eval import (
    AnswerReliabilityCase,
    DeterministicEvidenceAnswerService,
    run_answer_reliability_benchmark,
)
from fossil_core.answer_pipeline import LineageResolvedModelService, expand_context_with_lineage

PACK = "pack_lineage_answer"


def _citation(identifier: str) -> dict:
    return {
        "schema_version": "fossil.citation.v1",
        "citation_id": identifier,
        "snapshot_id": f"snap_{identifier}",
        "artifact_id": f"art_{identifier}",
        "byte_start": 0,
        "byte_end": 20,
        "passage_hash": {"algorithm": "sha256", "digest": "a" * 64},
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


def test_lineage_expansion_resolves_relation_endpoints_missing_from_top_k():
    premise = _claim(
        "clm_premise",
        "SQLite is the canonical corpus database.",
        "superseded",
        "cite_premise",
    )
    dependent = _claim(
        "clm_dependent",
        "The first SQLite prototype is the canonical architecture implementation.",
        "stale_pending_review",
        "cite_dependent",
    )
    unrelated = _claim(
        "clm_unrelated",
        "Production RAG hardening keeps the durable core.",
        "supported",
        "cite_unrelated",
    )
    relation = {
        "id": "rel_depends",
        "pack_id": PACK,
        "text": (
            "The first SQLite prototype is the canonical architecture implementation.\n"
            "Relation: DEPENDS_ON\nSQLite is the canonical corpus database."
        ),
        "document_type": "relation",
        "relation_type": "DEPENDS_ON",
        "source_ref": "clm_dependent",
        "target_ref": "clm_premise",
        "current_state": "active",
    }

    expanded = expand_context_with_lineage(
        [relation, unrelated],
        documents=[premise, dependent, unrelated, relation],
        pack_ids=[PACK],
    )

    assert [item["id"] for item in expanded] == [
        "rel_depends",
        "clm_unrelated",
        "clm_dependent",
        "clm_premise",
    ]
    assert expanded[2]["context_expansion"]["reason"] == "durable_relation_endpoint"


def test_lineage_resolved_service_recovers_stale_current_state_case():
    premise = _claim(
        "clm_premise",
        "SQLite is the canonical corpus database.",
        "superseded",
        "cite_premise",
    )
    dependent = _claim(
        "clm_dependent",
        "The first SQLite prototype is the canonical architecture implementation.",
        "stale_pending_review",
        "cite_dependent",
    )
    unrelated = _claim(
        "clm_unrelated",
        "Production RAG hardening keeps the durable core.",
        "supported",
        "cite_unrelated",
    )
    relation = {
        "id": "rel_depends",
        "pack_id": PACK,
        "text": (
            "The first SQLite prototype is the canonical architecture implementation.\n"
            "Relation: DEPENDS_ON\nSQLite is the canonical corpus database."
        ),
        "document_type": "relation",
        "relation_type": "DEPENDS_ON",
        "source_ref": "clm_dependent",
        "target_ref": "clm_premise",
        "current_state": "active",
    }
    documents = [premise, dependent, unrelated, relation]
    service = LineageResolvedModelService(
        DeterministicEvidenceAnswerService(),
        documents=documents,
    )
    case = AnswerReliabilityCase(
        case_id="stale-current",
        query="Is the first SQLite prototype the current canonical architecture implementation?",
        pack_ids=(PACK,),
        expected_outcome="current_state_unresolved",
        required_claim_ids=frozenset({"clm_dependent"}),
        allowed_claim_ids=frozenset({"clm_dependent"}),
        required_citation_ids=frozenset({"cite_dependent"}),
        limit=2,
    )

    report = run_answer_reliability_benchmark(
        service,
        documents=documents,
        cases=[case],
    )

    assert report["passed"] is True
    observation = report["observations"][0]
    assert observation["observed_outcome"] == "current_state_unresolved"
    assert observation["observed_claim_ids"] == ["clm_dependent"]
    assert report["service"]["runtime"]["lineage_context_resolver"] == (
        "fossil-lineage-context-v1"
    )
