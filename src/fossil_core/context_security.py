from __future__ import annotations

import copy
import hashlib
from typing import Any, Iterable, Mapping


CONTEXT_SECURITY_RESOLVER = "fossil-untrusted-context-v1"
UNTRUSTED_SOURCE_DATA = "untrusted_source_data"

_CITATION_KEYS = (
    "schema_version",
    "citation_id",
    "snapshot_id",
    "artifact_id",
    "byte_start",
    "byte_end",
    "passage_hash",
)
_EXECUTABLE_FIELDS = frozenset(
    {
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
)
_ALLOWED_OUTPUT_FIELDS = frozenset({"outcome", "answer_text", "claims", "confidence"})
_ALLOWED_CLAIM_FIELDS = frozenset({"claim_id", "text", "citation"})


def _canonical_citation(value: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    return {key: copy.deepcopy(value.get(key)) for key in _CITATION_KEYS}


def _authority_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    """Fields that retrieved payloads are never allowed to authoritatively override."""

    return {
        "id": value.get("id"),
        "pack_id": value.get("pack_id"),
        "text": value.get("text"),
        "document_type": value.get("document_type"),
        "current_state": value.get("current_state"),
        "state_history": value.get("state_history"),
        "relation_type": value.get("relation_type"),
        "source_ref": value.get("source_ref"),
        "target_ref": value.get("target_ref"),
        "citation": _canonical_citation(value.get("citation")),
    }


def _untrusted_fingerprint(pack_id: str, text: str) -> str:
    payload = f"{pack_id}\x00{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def canonicalize_untrusted_context(
    context_items: Iterable[Mapping[str, Any]],
    *,
    documents: Iterable[Mapping[str, Any]],
    pack_ids: Iterable[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Resolve authority from mounted durable documents while preserving source text as data.

    Retrieved payloads are attacker-controlled inputs at this boundary. A stable ID may be
    used to resolve the corresponding mounted durable document, but retrieved lifecycle,
    relation, citation, text, and pack metadata never become authoritative merely because
    they were returned by a retriever.

    Unknown in-scope payloads remain available to a model as ``untrusted_context`` text.
    They are deliberately stripped of claim/relation/lifecycle/citation authority. Unknown
    out-of-scope payloads are dropped. Exact duplicate unknown passages are collapsed to
    reduce trivial ranking/context flooding without claiming a universal poisoning defense.
    """

    raw_items = [copy.deepcopy(dict(item)) for item in context_items]
    allowed_packs = {str(pack_id) for pack_id in pack_ids}
    durable_by_id = {
        str(document["id"]): copy.deepcopy(dict(document))
        for document in documents
        if document.get("id") is not None
    }

    secured: list[dict[str, Any]] = []
    seen_durable_ids: set[str] = set()
    seen_untrusted_fingerprints: set[str] = set()
    canonicalized_ids: list[str] = []
    mismatched_ids: list[str] = []
    demoted_ids: list[str] = []
    dropped_ids: list[str] = []
    deduplicated_ids: list[str] = []

    for raw in raw_items:
        identifier = str(raw.get("id", ""))
        claimed_pack_id = str(raw.get("pack_id", ""))
        durable = durable_by_id.get(identifier) if identifier else None

        if durable is not None:
            durable_pack_id = str(durable.get("pack_id", ""))
            if durable_pack_id not in allowed_packs:
                dropped_ids.append(identifier or "<missing-id>")
                continue
            if identifier in seen_durable_ids:
                deduplicated_ids.append(identifier)
                continue
            seen_durable_ids.add(identifier)

            mismatch = _authority_projection(raw) != _authority_projection(durable)
            if mismatch:
                mismatched_ids.append(identifier)
            canonicalized_ids.append(identifier)
            durable["context_security"] = {
                "resolver": CONTEXT_SECURITY_RESOLVER,
                "trust": UNTRUSTED_SOURCE_DATA,
                "authority": "durable_identity_resolved",
                "retrieved_payload_mismatch": mismatch,
            }
            secured.append(durable)
            continue

        if claimed_pack_id not in allowed_packs:
            dropped_ids.append(identifier or "<missing-id>")
            continue

        text = str(raw.get("text", ""))
        fingerprint = _untrusted_fingerprint(claimed_pack_id, text)
        if fingerprint in seen_untrusted_fingerprints:
            deduplicated_ids.append(identifier or f"sha256:{fingerprint[:16]}")
            continue
        seen_untrusted_fingerprints.add(fingerprint)

        if not identifier:
            identifier = f"untrusted_{fingerprint[:24]}"
        demoted_ids.append(identifier)
        secured.append(
            {
                "id": identifier,
                "pack_id": claimed_pack_id,
                "text": text,
                "document_type": "untrusted_context",
                "context_security": {
                    "resolver": CONTEXT_SECURITY_RESOLVER,
                    "trust": UNTRUSTED_SOURCE_DATA,
                    "authority": "unresolved_untrusted_payload",
                    "claimed_document_type": str(raw.get("document_type", "")),
                },
            }
        )

    diagnostics = {
        "resolver": CONTEXT_SECURITY_RESOLVER,
        "source_text_trust": UNTRUSTED_SOURCE_DATA,
        "allowed_pack_ids": sorted(allowed_packs),
        "input_item_count": len(raw_items),
        "forwarded_item_count": len(secured),
        "forwarded_item_ids": [
            str(item.get("id", "")) for item in secured if item.get("id")
        ],
        "forwarded_pack_ids": sorted(
            {str(item.get("pack_id", "")) for item in secured if item.get("pack_id")}
        ),
        "canonicalized_ids": canonicalized_ids,
        "retrieved_payload_mismatch_ids": mismatched_ids,
        "demoted_untrusted_ids": demoted_ids,
        "dropped_out_of_scope_ids": dropped_ids,
        "deduplicated_ids": deduplicated_ids,
    }
    return secured, diagnostics


def _durable_claim_payload(document: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "claim_id": str(document["id"]),
        "text": str(document.get("text", "")),
    }
    citation = _canonical_citation(document.get("citation"))
    if citation is not None:
        payload["citation"] = citation
    return payload


class UntrustedContextModelService:
    """Harden a ModelService against retrieved-text authority and executable-output escape.

    This wrapper is deliberately model/provider independent. It does not attempt to detect
    every malicious instruction in natural language. Instead it enforces structural trust
    boundaries around the model call:

    - retrieved payload metadata is resolved from mounted durable IDs;
    - unknown retrieved text is explicitly non-authoritative data;
    - out-of-scope packs are removed before the model sees context;
    - the answer surface is candidate-only and contains no executable tool/action fields;
    - emitted claim IDs are resolved back to mounted durable claim text/citation identity.

    A model can still be confused or induced to abstain. That residual risk belongs in the
    benchmark/report rather than being hidden behind a claim of universal poisoning defense.
    """

    def __init__(self, service: Any, *, documents: Iterable[Mapping[str, Any]]) -> None:
        self.service = service
        self.documents = [copy.deepcopy(dict(document)) for document in documents]

    def metadata(self) -> dict[str, Any]:
        metadata = copy.deepcopy(dict(self.service.metadata()))
        runtime = dict(metadata.get("runtime", {}))
        runtime["context_security_resolver"] = CONTEXT_SECURITY_RESOLVER
        runtime["retrieved_source_text_trust"] = UNTRUSTED_SOURCE_DATA
        runtime["answer_tool_execution"] = "disabled"
        metadata["runtime"] = runtime
        return metadata

    def run(self, task: dict[str, Any]) -> dict[str, Any]:
        request = copy.deepcopy(task)
        pack_ids = [str(item) for item in request.get("pack_ids", [])]
        secured_items, diagnostics = canonicalize_untrusted_context(
            request.get("context_items", []),
            documents=self.documents,
            pack_ids=pack_ids,
        )
        request["context_items"] = secured_items
        request["context_security"] = {
            "resolver": CONTEXT_SECURITY_RESOLVER,
            "retrieved_source_text": UNTRUSTED_SOURCE_DATA,
            "retrieved_text_can_issue_policy": False,
            "model_can_execute_tools": False,
            "durable_claim_resolution_required": True,
        }
        for key in _EXECUTABLE_FIELDS:
            request.pop(key, None)

        raw_response = copy.deepcopy(dict(self.service.run(request)))
        blocked_response_fields = sorted(
            key for key in raw_response if key in _EXECUTABLE_FIELDS
        )
        for key in blocked_response_fields:
            raw_response.pop(key, None)

        raw_output_value = raw_response.get("output", {})
        raw_output = dict(raw_output_value) if isinstance(raw_output_value, Mapping) else {}
        blocked_output_fields = sorted(
            key for key in raw_output if key not in _ALLOWED_OUTPUT_FIELDS
        )
        output = {
            key: copy.deepcopy(value)
            for key, value in raw_output.items()
            if key in _ALLOWED_OUTPUT_FIELDS
        }

        allowed_packs = set(pack_ids)
        durable_claims = {
            str(document["id"]): document
            for document in self.documents
            if str(document.get("pack_id", "")) in allowed_packs
            and str(document.get("document_type", "")) == "claim"
        }
        raw_claims = output.get("claims", [])
        claim_values = raw_claims if isinstance(raw_claims, list) else []
        canonical_claims: list[dict[str, Any]] = []
        invalid_claim_ids: list[str] = []
        blocked_claim_fields: dict[str, list[str]] = {}

        for claim_value in claim_values:
            claim = dict(claim_value) if isinstance(claim_value, Mapping) else {}
            identifier = str(claim.get("claim_id", ""))
            if not identifier or identifier not in durable_claims:
                invalid_claim_ids.append(identifier or "<missing-id>")
                continue
            extras = sorted(key for key in claim if key not in _ALLOWED_CLAIM_FIELDS)
            if extras:
                blocked_claim_fields[identifier] = extras
            canonical_claims.append(_durable_claim_payload(durable_claims[identifier]))

        output["claims"] = canonical_claims
        if invalid_claim_ids:
            output = {
                "outcome": "insufficient_evidence",
                "answer_text": "Insufficient evidence.",
                "claims": [],
                "confidence": 1.0,
            }

        raw_response["output"] = output
        raw_response["authority"] = "candidate_only"
        raw_response["service"] = self.metadata()
        raw_response["context_security"] = {
            **diagnostics,
            "blocked_response_fields": blocked_response_fields,
            "blocked_output_fields": blocked_output_fields,
            "blocked_claim_fields": blocked_claim_fields,
            "invalid_output_claim_ids": invalid_claim_ids,
        }
        return raw_response
