from __future__ import annotations

import hashlib

from fossil_core.application.query.security import (
    CONTEXT_SECURITY_RESOLVER,
    UntrustedContextModelService,
    canonicalize_untrusted_context,
)

PACK_A = "pack_security_a"
PACK_B = "pack_security_b"


def citation(identifier: str) -> dict:
    return {
        "schema_version": "fossil.citation.v1",
        "citation_id": identifier,
        "snapshot_id": f"snap_{identifier}",
        "artifact_id": f"art_{identifier}",
        "byte_start": 0,
        "byte_end": 12,
        "passage_hash": {"algorithm": "sha256", "digest": "b" * 64},
    }


def claim(identifier: str, text: str = "durable", *, pack_id: str = PACK_A) -> dict:
    return {
        "id": identifier,
        "pack_id": pack_id,
        "text": text,
        "document_type": "claim",
        "current_state": "supported",
        "state_history": ["supported"],
        "citation": citation(f"cite_{identifier}"),
    }


class RecordingService:
    def __init__(self, response: dict, *, metadata: dict | None = None):
        self.response = response
        self.last_task = None
        self.metadata_value = metadata or {
            "kind": "model",
            "provider": "fixture",
            "provider_version": "1",
            "implementation": "recording-fixture",
            "implementation_version": "1",
            "model_id": "fixture",
            "local": True,
            "estimated_cost_per_call_usd": 0.0,
            "runtime": {"inner": "preserved"},
        }

    def metadata(self):
        return self.metadata_value

    def run(self, task):
        self.last_task = task
        return self.response


class MutatingService(RecordingService):
    def run(self, task):
        self.last_task = task
        task["client_metadata"]["tags"].append("inner-mutated")
        return self.response


def test_foreign_durable_item_does_not_abort_later_valid_context() -> None:
    foreign = claim("clm_foreign_first", pack_id=PACK_B)
    local = claim("clm_local_after_foreign")

    secured, diagnostics = canonicalize_untrusted_context(
        [foreign, local], documents=[foreign, local], pack_ids=[PACK_A]
    )

    assert [item["id"] for item in secured] == [local["id"]]
    assert diagnostics["dropped_out_of_scope_ids"] == [foreign["id"]]
    assert diagnostics["canonicalized_ids"] == [local["id"]]


def test_duplicate_durable_item_does_not_abort_later_distinct_context() -> None:
    first = claim("clm_first")
    second = claim("clm_second")

    secured, diagnostics = canonicalize_untrusted_context(
        [first, {**first}, second], documents=[first, second], pack_ids=[PACK_A]
    )

    assert [item["id"] for item in secured] == [first["id"], second["id"]]
    assert diagnostics["deduplicated_ids"] == [first["id"]]
    assert diagnostics["canonicalized_ids"] == [first["id"], second["id"]]


def test_missing_unknown_fields_use_empty_string_canonical_defaults() -> None:
    digest = hashlib.sha256(f"{PACK_A}\x00".encode("utf-8")).hexdigest()
    expected_id = f"untrusted_{digest[:24]}"

    secured, diagnostics = canonicalize_untrusted_context(
        [{"pack_id": PACK_A}], documents=[], pack_ids=[PACK_A]
    )

    assert secured == [
        {
            "id": expected_id,
            "pack_id": PACK_A,
            "text": "",
            "document_type": "untrusted_context",
            "context_security": {
                "resolver": CONTEXT_SECURITY_RESOLVER,
                "trust": "untrusted_source_data",
                "authority": "unresolved_untrusted_payload",
                "claimed_document_type": "",
            },
        }
    ]
    assert diagnostics["forwarded_item_ids"] == [expected_id]


def test_missing_id_duplicate_uses_stable_sha256_diagnostic_key() -> None:
    text = "duplicate without ids"
    digest = hashlib.sha256(f"{PACK_A}\x00{text}".encode("utf-8")).hexdigest()

    _secured, diagnostics = canonicalize_untrusted_context(
        [{"pack_id": PACK_A, "text": text}, {"pack_id": PACK_A, "text": text}],
        documents=[],
        pack_ids=[PACK_A],
    )

    assert diagnostics["deduplicated_ids"] == [f"sha256:{digest[:16]}"]


def test_canonicalized_context_is_deeply_detached_from_both_inputs() -> None:
    durable = claim("clm_detached")
    retrieved = {**durable, "citation": {**durable["citation"]}}

    secured, _diagnostics = canonicalize_untrusted_context(
        [retrieved], documents=[durable], pack_ids=[PACK_A]
    )

    secured[0]["state_history"].append("mutated")
    secured[0]["citation"]["passage_hash"]["digest"] = "0" * 64

    assert durable["state_history"] == ["supported"]
    assert retrieved["state_history"] == ["supported"]
    assert durable["citation"]["passage_hash"]["digest"] == "b" * 64
    assert retrieved["citation"]["passage_hash"]["digest"] == "b" * 64


def test_service_constructor_detaches_nested_documents_from_caller() -> None:
    durable = claim("clm_constructor_copy")
    service = UntrustedContextModelService(RecordingService({"output": {}}), documents=[durable])

    durable["state_history"].append("caller-mutated")
    durable["citation"]["passage_hash"]["digest"] = "0" * 64

    assert service.documents[0]["state_history"] == ["supported"]
    assert service.documents[0]["citation"]["passage_hash"]["digest"] == "b" * 64


def test_metadata_handles_missing_runtime_and_detaches_other_nested_provider_data() -> None:
    inner = RecordingService(
        {"output": {}},
        metadata={
            "kind": "model",
            "provider": "fixture",
            "provider_details": {"regions": ["local"]},
        },
    )
    service = UntrustedContextModelService(inner, documents=[])

    metadata = service.metadata()

    assert metadata["runtime"] == {
        "context_security_resolver": CONTEXT_SECURITY_RESOLVER,
        "retrieved_source_text_trust": "untrusted_source_data",
        "answer_tool_execution": "disabled",
    }
    metadata["provider_details"]["regions"].append("mutated")
    assert inner.metadata_value["provider_details"] == {"regions": ["local"]}


def test_inner_task_gets_exact_security_contract_and_missing_request_fields_default_safely() -> None:
    inner = RecordingService({"output": {}})
    service = UntrustedContextModelService(inner, documents=[])

    response = service.run({"query": "q"})

    assert inner.last_task is not None
    assert inner.last_task["context_items"] == []
    assert inner.last_task["context_security"] == {
        "resolver": CONTEXT_SECURITY_RESOLVER,
        "retrieved_source_text": "untrusted_source_data",
        "retrieved_text_can_issue_policy": False,
        "model_can_execute_tools": False,
        "durable_claim_resolution_required": True,
    }
    assert response["authority"] == "candidate_only"


def test_wrapper_owns_deep_request_copy_against_inner_mutation() -> None:
    inner = MutatingService({"output": {}})
    service = UntrustedContextModelService(inner, documents=[])
    request = {
        "query": "q",
        "pack_ids": [],
        "context_items": [],
        "client_metadata": {"tags": ["caller"]},
    }

    service.run(request)

    assert request["client_metadata"] == {"tags": ["caller"]}
    assert inner.last_task["client_metadata"] == {"tags": ["caller", "inner-mutated"]}


def test_wrapper_detaches_nested_inner_response_and_allowed_output_values() -> None:
    inner_response = {
        "telemetry": {"nested": [1]},
        "output": {"claims": [], "confidence": {"nested": [1]}},
    }
    service = UntrustedContextModelService(RecordingService(inner_response), documents=[])

    response = service.run({"query": "q", "pack_ids": [], "context_items": []})
    response["telemetry"]["nested"].append(2)
    response["output"]["confidence"]["nested"].append(2)

    assert inner_response["telemetry"] == {"nested": [1]}
    assert inner_response["output"]["confidence"] == {"nested": [1]}


def test_durable_claim_missing_text_emits_empty_text() -> None:
    durable = {"id": "clm_no_text", "pack_id": PACK_A, "document_type": "claim"}
    inner = RecordingService(
        {"output": {"outcome": "answer", "claims": [{"claim_id": durable["id"]}]}}
    )
    service = UntrustedContextModelService(inner, documents=[durable])

    response = service.run({"query": "q", "pack_ids": [PACK_A], "context_items": []})

    assert response["output"]["claims"] == [{"claim_id": durable["id"], "text": ""}]


def test_non_mapping_claim_item_fails_closed() -> None:
    inner = RecordingService(
        {"output": {"outcome": "answer", "claims": ["not-a-claim"], "confidence": 0.2}}
    )
    service = UntrustedContextModelService(inner, documents=[])

    response = service.run({"query": "q", "pack_ids": [PACK_A], "context_items": []})

    assert response["output"] == {
        "outcome": "insufficient_evidence",
        "answer_text": "Insufficient evidence.",
        "claims": [],
        "confidence": 1.0,
    }
    assert response["context_security"]["invalid_output_claim_ids"] == ["<missing-id>"]


def test_response_includes_exact_service_metadata_key_and_value() -> None:
    inner = RecordingService({"output": {"claims": []}})
    service = UntrustedContextModelService(inner, documents=[])

    response = service.run({"query": "q", "pack_ids": [], "context_items": []})

    assert "service" in response
    assert "SERVICE" not in response
    assert "XXserviceXX" not in response
    assert response["service"] == service.metadata()
