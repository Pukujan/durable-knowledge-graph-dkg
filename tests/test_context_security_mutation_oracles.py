from __future__ import annotations

import hashlib

import pytest

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


def claim(identifier: str, text: str, *, pack_id: str = PACK_A) -> dict:
    return {
        "id": identifier,
        "pack_id": pack_id,
        "text": text,
        "document_type": "claim",
        "current_state": "supported",
        "state_history": ["supported"],
        "citation": citation(f"cite_{identifier}"),
    }


@pytest.mark.parametrize(
    ("field", "spoofed_value"),
    [
        ("pack_id", PACK_B),
        ("text", "retrieved text must never replace durable text"),
        ("document_type", "claim"),
        ("current_state", "superseded"),
        ("state_history", ["proposed", "superseded"]),
        ("relation_type", "CONTRADICTS"),
        ("source_ref", "clm_forged_source"),
        ("target_ref", "clm_forged_target"),
        ("citation", citation("cite_forged_authority")),
    ],
)
def test_each_retrieved_authority_field_is_resolved_from_durable_truth(
    field: str, spoofed_value: object
) -> None:
    durable = {
        "id": "rel_authority_truth",
        "pack_id": PACK_A,
        "text": "durable relation text",
        "document_type": "relation",
        "current_state": "active",
        "state_history": ["active"],
        "relation_type": "DEPENDS_ON",
        "source_ref": "clm_source",
        "target_ref": "clm_target",
        "citation": citation("cite_authority_truth"),
    }
    retrieved = {**durable, field: spoofed_value}

    secured, diagnostics = canonicalize_untrusted_context(
        [retrieved], documents=[durable], pack_ids=[PACK_A]
    )

    assert len(secured) == 1
    assert secured[0][field] == durable[field]
    assert secured[0]["context_security"] == {
        "resolver": CONTEXT_SECURITY_RESOLVER,
        "trust": "untrusted_source_data",
        "authority": "durable_identity_resolved",
        "retrieved_payload_mismatch": True,
    }
    assert diagnostics["canonicalized_ids"] == [durable["id"]]
    assert diagnostics["retrieved_payload_mismatch_ids"] == [durable["id"]]


def test_exact_durable_payload_has_no_false_mismatch() -> None:
    durable = {
        "id": "rel_exact",
        "pack_id": PACK_A,
        "text": "exact durable relation",
        "document_type": "relation",
        "current_state": "active",
        "state_history": ["active"],
        "relation_type": "DEPENDS_ON",
        "source_ref": "clm_source",
        "target_ref": "clm_target",
        "citation": citation("cite_exact"),
    }

    secured, diagnostics = canonicalize_untrusted_context(
        [durable], documents=[durable], pack_ids=[PACK_A]
    )

    assert secured[0]["context_security"]["retrieved_payload_mismatch"] is False
    assert diagnostics["canonicalized_ids"] == ["rel_exact"]
    assert diagnostics["retrieved_payload_mismatch_ids"] == []


def test_unknown_context_uses_exact_fingerprint_and_complete_diagnostics() -> None:
    text = "unknown retrieved π text"
    digest = hashlib.sha256(f"{PACK_A}\x00{text}".encode("utf-8")).hexdigest()
    expected_id = f"untrusted_{digest[:24]}"

    secured, diagnostics = canonicalize_untrusted_context(
        [
            {"pack_id": PACK_A, "text": text, "document_type": "claim"},
            {"id": "duplicate_unknown", "pack_id": PACK_A, "text": text},
            {"id": "foreign_unknown", "pack_id": PACK_B, "text": text},
        ],
        documents=[],
        pack_ids=[PACK_A],
    )

    assert secured == [
        {
            "id": expected_id,
            "pack_id": PACK_A,
            "text": text,
            "document_type": "untrusted_context",
            "context_security": {
                "resolver": CONTEXT_SECURITY_RESOLVER,
                "trust": "untrusted_source_data",
                "authority": "unresolved_untrusted_payload",
                "claimed_document_type": "claim",
            },
        }
    ]
    assert diagnostics == {
        "resolver": CONTEXT_SECURITY_RESOLVER,
        "source_text_trust": "untrusted_source_data",
        "allowed_pack_ids": [PACK_A],
        "input_item_count": 3,
        "forwarded_item_count": 1,
        "forwarded_item_ids": [expected_id],
        "forwarded_pack_ids": [PACK_A],
        "canonicalized_ids": [],
        "retrieved_payload_mismatch_ids": [],
        "demoted_untrusted_ids": [expected_id],
        "dropped_out_of_scope_ids": ["foreign_unknown"],
        "deduplicated_ids": ["duplicate_unknown"],
    }


def test_duplicate_durable_identity_is_forwarded_once() -> None:
    durable = claim("clm_duplicate", "durable")

    secured, diagnostics = canonicalize_untrusted_context(
        [durable, {**durable}], documents=[durable], pack_ids=[PACK_A]
    )

    assert [item["id"] for item in secured] == ["clm_duplicate"]
    assert diagnostics["canonicalized_ids"] == ["clm_duplicate"]
    assert diagnostics["deduplicated_ids"] == ["clm_duplicate"]
    assert diagnostics["input_item_count"] == 2
    assert diagnostics["forwarded_item_count"] == 1


class RecordingService:
    def __init__(self, response: dict):
        self.response = response
        self.last_task = None
        self.metadata_value = {
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


def test_security_metadata_is_defensive_and_adds_exact_runtime_contract() -> None:
    inner = RecordingService({"output": {}})
    service = UntrustedContextModelService(inner, documents=[])

    metadata = service.metadata()

    assert metadata["runtime"] == {
        "inner": "preserved",
        "context_security_resolver": CONTEXT_SECURITY_RESOLVER,
        "retrieved_source_text_trust": "untrusted_source_data",
        "answer_tool_execution": "disabled",
    }
    metadata["runtime"]["inner"] = "mutated"
    assert inner.metadata_value["runtime"] == {"inner": "preserved"}


def test_model_boundary_strips_all_executable_and_unknown_fields() -> None:
    executable = {
        "actions",
        "commit",
        "commit_request",
        "commit_requests",
        "proposals",
        "requested_actions",
        "tool_call",
        "tool_calls",
        "tools",
    }
    durable = claim("clm_exec", "durable claim")
    raw_response = {key: {"malicious": True} for key in executable}
    raw_response["output"] = {
        "outcome": "answer",
        "answer_text": "durable claim",
        "claims": [{"claim_id": durable["id"], "forged": True}],
        "confidence": 0.75,
        **{key: {"malicious": True} for key in executable},
        "unknown_output_field": "drop me",
    }
    inner = RecordingService(raw_response)
    service = UntrustedContextModelService(inner, documents=[durable])
    request = {
        "query": "q",
        "pack_ids": [PACK_A],
        "context_items": [durable],
        **{key: {"malicious": True} for key in executable},
    }

    response = service.run(request)

    assert set(executable).isdisjoint(inner.last_task)
    assert set(executable).issubset(request)
    assert response["authority"] == "candidate_only"
    assert set(executable).isdisjoint(response)
    assert set(response["output"]) == {"outcome", "answer_text", "claims", "confidence"}
    assert response["output"]["claims"] == [
        {
            "claim_id": durable["id"],
            "text": durable["text"],
            "citation": durable["citation"],
        }
    ]
    assert response["context_security"]["blocked_response_fields"] == sorted(executable)
    assert set(response["context_security"]["blocked_output_fields"]) == executable | {
        "unknown_output_field"
    }
    assert response["context_security"]["blocked_claim_fields"] == {
        durable["id"]: ["forged"]
    }


@pytest.mark.parametrize("raw_output", ["not-a-mapping", 3, None, ["claims"]])
def test_non_mapping_model_output_is_contained(raw_output: object) -> None:
    service = UntrustedContextModelService(RecordingService({"output": raw_output}), documents=[])

    response = service.run({"query": "q", "pack_ids": [PACK_A], "context_items": []})

    assert response["output"] == {"claims": []}
    assert response["authority"] == "candidate_only"
    assert response["context_security"]["invalid_output_claim_ids"] == []


def test_non_list_claims_are_discarded() -> None:
    durable = claim("clm_local", "local")
    service = UntrustedContextModelService(
        RecordingService(
            {"output": {"outcome": "answer", "claims": {"claim_id": durable["id"]}}}
        ),
        documents=[durable],
    )

    response = service.run({"query": "q", "pack_ids": [PACK_A], "context_items": []})

    assert response["output"] == {"outcome": "answer", "claims": []}


def test_foreign_or_missing_model_claim_ids_fail_closed() -> None:
    local = claim("clm_local", "local")
    foreign = claim("clm_foreign", "foreign", pack_id=PACK_B)
    service = UntrustedContextModelService(
        RecordingService(
            {
                "output": {
                    "outcome": "answer",
                    "answer_text": "untrusted",
                    "claims": [{"claim_id": foreign["id"]}, {}],
                    "confidence": 0.25,
                }
            }
        ),
        documents=[local, foreign],
    )

    response = service.run({"query": "q", "pack_ids": [PACK_A], "context_items": []})

    assert response["output"] == {
        "outcome": "insufficient_evidence",
        "answer_text": "Insufficient evidence.",
        "claims": [],
        "confidence": 1.0,
    }
    assert response["context_security"]["invalid_output_claim_ids"] == [
        foreign["id"],
        "<missing-id>",
    ]


def test_emitted_claim_and_citation_are_canonical_and_detached() -> None:
    durable = claim("clm_citation", "durable claim")
    durable["citation"]["ignored_extra"] = {"nested": [1]}
    service = UntrustedContextModelService(
        RecordingService(
            {
                "output": {
                    "outcome": "answer",
                    "claims": [
                        {
                            "claim_id": durable["id"],
                            "text": "forged",
                            "citation": citation("forged"),
                        }
                    ],
                }
            }
        ),
        documents=[durable],
    )

    response = service.run(
        {"query": "q", "pack_ids": [PACK_A], "context_items": [durable]}
    )
    emitted = response["output"]["claims"][0]

    assert emitted["claim_id"] == durable["id"]
    assert emitted["text"] == durable["text"]
    assert set(emitted["citation"]) == {
        "schema_version",
        "citation_id",
        "snapshot_id",
        "artifact_id",
        "byte_start",
        "byte_end",
        "passage_hash",
    }
    assert "ignored_extra" not in emitted["citation"]
    emitted["citation"]["passage_hash"]["digest"] = "0" * 64
    assert service.documents[0]["citation"]["passage_hash"]["digest"] == "b" * 64
