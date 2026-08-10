from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from dkg.answer_eval import DeterministicEvidenceAnswerService
from dkg.answer_pipeline import LineageResolvedModelService
from dkg.context_security import UntrustedContextModelService
from dkg.execution_receipt import (
    QUERY_EXECUTION_RECEIPT_AUTHORITY,
    build_query_execution_receipt,
    build_service_invocation,
    compare_query_execution_receipts,
    execute_query_with_receipt,
)
from dkg.services import ServiceMetadata

PACK = "pack_receipt_fixture"


def _citation(identifier: str) -> dict:
    return {
        "schema_version": "fossil.citation.v1",
        "citation_id": identifier,
        "snapshot_id": f"snap_{identifier}",
        "artifact_id": f"art_{identifier}",
        "byte_start": 0,
        "byte_end": 12,
        "passage_hash": {"algorithm": "sha256", "digest": "c" * 64},
    }


def _claim(identifier: str, text: str, state: str) -> dict:
    return {
        "id": identifier,
        "pack_id": PACK,
        "text": text,
        "document_type": "claim",
        "current_state": state,
        "state_history": [state],
        "citation": _citation(f"cite_{identifier}"),
    }


def _relation(identifier: str, source_ref: str, target_ref: str) -> dict:
    return {
        "id": identifier,
        "pack_id": PACK,
        "text": f"{source_ref}\nRelation: DEPENDS_ON\n{target_ref}",
        "document_type": "relation",
        "relation_type": "DEPENDS_ON",
        "source_ref": source_ref,
        "target_ref": target_ref,
        "current_state": "active",
        "state_history": ["active"],
    }


class StaticRetriever:
    def __init__(self, results):
        self.results = [dict(item) for item in results]

    def metadata(self):
        return ServiceMetadata(
            kind="retriever",
            provider="fixture",
            provider_version="1",
            implementation="static-retriever",
            implementation_version="1",
            local=True,
            estimated_cost_per_call_usd=0.0,
            runtime={"fixture": "receipt"},
        ).as_dict()

    def search(self, query, *, pack_ids, limit=20):
        assert pack_ids == [PACK]
        output = []
        for rank, item in enumerate(self.results[:limit], start=1):
            result = dict(item)
            result["retrieval"] = {
                "rank": rank,
                "score": 1.0 / rank,
                "service": self.metadata(),
            }
            output.append(result)
        return output


def _schema() -> dict:
    root = Path(__file__).resolve().parents[1]
    return json.loads(
        (root / "schemas" / "query-execution-receipt" / "v1.schema.json").read_text(
            encoding="utf-8"
        )
    )


def _validate(receipt: dict) -> None:
    validator = Draft202012Validator(_schema(), format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(receipt), key=lambda item: list(item.path))
    assert errors == []


def test_service_invocation_records_requested_actual_fallback_without_secrets():
    invocation = build_service_invocation(
        "model",
        {
            "kind": "model",
            "provider": "fallback-provider",
            "provider_version": "2",
            "implementation": "gateway-model",
            "implementation_version": "4",
            "model_id": "actual-model",
            "local": False,
            "estimated_cost_per_call_usd": 0.02,
            "runtime": {
                "region": "us-east",
                "api_key": "must-not-survive",
                "nested": {"authorization": "must-not-survive", "safe": "yes"},
            },
        },
        requested={"provider": "requested-provider", "model_id": "requested-model"},
        attempts=[
            {
                "provider": "requested-provider",
                "model_id": "requested-model",
                "outcome": "failed",
                "error_type": "TimeoutError",
                "secret": "must-not-survive",
            },
            {
                "provider": "fallback-provider",
                "model_id": "actual-model",
                "outcome": "success",
            },
        ],
        latency_ms=12.5,
    )

    assert invocation["requested"]["model_id"] == "requested-model"
    assert invocation["actual"]["model_id"] == "actual-model"
    assert invocation["fallback_used"] is True
    assert "api_key" not in invocation["actual"]["runtime"]
    assert "authorization" not in invocation["actual"]["runtime"]["nested"]
    assert invocation["actual"]["runtime"]["nested"]["safe"] == "yes"
    assert "secret" not in invocation["attempts"][0]


def test_execution_receipt_records_true_model_bound_lineage_context_and_exact_citation():
    premise = _claim(
        "clm_premise",
        "SQLite is the canonical corpus database.",
        "superseded",
    )
    dependent = _claim(
        "clm_dependent",
        "The first SQLite prototype is the canonical architecture implementation.",
        "stale_pending_review",
    )
    unrelated = _claim(
        "clm_unrelated",
        "Production RAG hardening preserves the durable core.",
        "supported",
    )
    relation = _relation("rel_depends", "clm_dependent", "clm_premise")
    documents = [premise, dependent, unrelated, relation]
    retriever = StaticRetriever([relation, unrelated])
    model = UntrustedContextModelService(
        LineageResolvedModelService(
            DeterministicEvidenceAnswerService(),
            documents=documents,
        ),
        documents=documents,
    )

    response, receipt = execute_query_with_receipt(
        query="Is the first SQLite prototype the current canonical architecture implementation?",
        pack_mounts={PACK: "rev_fixture_123"},
        query_pack_ids=[PACK],
        projection={
            "name": "fixture-retrieval-documents",
            "version": "1",
            "build_id": "build_fixture_001",
        },
        policy={
            "route_id": "receipt-fixture-route",
            "retrieval_policy_id": "d021-fixture",
            "mode": "test",
        },
        retriever=retriever,
        model_service=model,
        limit=2,
        trace_ref="trace://receipt-fixture/001",
        run_ref="test_execution_receipt",
    )

    assert response["output"]["outcome"] == "current_state_unresolved"
    assert receipt["authority"] == QUERY_EXECUTION_RECEIPT_AUTHORITY
    assert receipt["retrieval"]["candidate_count"] == 2
    assert [item["id"] for item in receipt["retrieval"]["candidates"]] == [
        "rel_depends",
        "clm_unrelated",
    ]
    assert [item["resolver"] for item in receipt["resolvers"]] == [
        "fossil-untrusted-context-v1",
        "fossil-lineage-context-v1",
    ]
    assert receipt["resolvers"][1]["added_ids"] == ["clm_dependent", "clm_premise"]
    assert receipt["context"]["item_ids"] == [
        "rel_depends",
        "clm_unrelated",
        "clm_dependent",
        "clm_premise",
    ]
    assert receipt["result"]["claim_ids"] == ["clm_dependent"]
    assert receipt["result"]["citation_ids"] == ["cite_clm_dependent"]
    assert receipt["result"]["abstained"] is True
    assert receipt["result"]["authority"] == "candidate_only"
    _validate(receipt)


def _minimal_receipt(*, revision: str, route_id: str = "route-a", recorded_at: str, latency: float):
    service = build_service_invocation(
        "retriever",
        ServiceMetadata(
            kind="retriever",
            provider="fixture",
            provider_version="1",
            implementation="static",
            implementation_version="1",
            local=True,
        ).as_dict(),
        latency_ms=1.0,
    )
    model = build_service_invocation(
        "model",
        ServiceMetadata(
            kind="model",
            provider="fixture",
            provider_version="1",
            implementation="deterministic",
            implementation_version="1",
            local=True,
        ).as_dict(),
        latency_ms=1.0,
    )
    candidate = _claim("clm_truth", "Durable truth remains durable.", "supported")
    candidate["retrieval"] = {"rank": 1, "score": 2.0}
    response = {
        "output": {
            "outcome": "answer",
            "claims": [
                {
                    "claim_id": "clm_truth",
                    "text": candidate["text"],
                    "citation": candidate["citation"],
                }
            ],
            "confidence": 1.0,
        },
        "authority": "candidate_only",
    }
    return build_query_execution_receipt(
        query="  What   is durable truth?  ",
        pack_mounts={PACK: revision},
        projection={"name": "fixture", "version": "1", "build_id": "build-1"},
        policy={"route_id": route_id, "retrieval_policy_id": "D021", "mode": "test"},
        services=[service, model],
        candidates=[candidate],
        response=response,
        trace_ref="trace://fixture",
        recorded_at=recorded_at,
        latency_ms=latency,
    )


def test_replay_comparison_separates_telemetry_from_execution_identity():
    before = _minimal_receipt(
        revision="rev-a",
        recorded_at="2026-08-10T20:00:00+00:00",
        latency=2.0,
    )
    after = _minimal_receipt(
        revision="rev-a",
        recorded_at="2026-08-10T20:01:00+00:00",
        latency=9.0,
    )

    comparison = compare_query_execution_receipts(before, after)
    assert before["query"]["normalized"] == "What is durable truth?"
    assert before["query"]["sha256"] == after["query"]["sha256"]
    assert before["execution_identity_sha256"] == after["execution_identity_sha256"]
    assert before["result_sha256"] == after["result_sha256"]
    assert comparison["changed_dimensions"] == []
    assert comparison["telemetry_changed"] is True
    assert comparison["execution_identity_match"] is True
    assert comparison["result_identity_match"] is True


def test_replay_comparison_surfaces_corpus_revision_and_route_changes():
    before = _minimal_receipt(
        revision="rev-a",
        route_id="route-a",
        recorded_at="2026-08-10T20:00:00+00:00",
        latency=2.0,
    )
    after = _minimal_receipt(
        revision="rev-b",
        route_id="route-b",
        recorded_at="2026-08-10T20:00:00+00:00",
        latency=2.0,
    )

    comparison = compare_query_execution_receipts(before, after)
    assert comparison["same_logical_query"] is True
    assert comparison["same_pack_ids"] is True
    assert comparison["same_corpus_revision"] is False
    assert comparison["corpus_revision_changed"] is True
    assert comparison["replay_comparable"] is True
    assert {"corpus", "policy"} <= set(comparison["changed_dimensions"])
    assert comparison["execution_identity_match"] is False
