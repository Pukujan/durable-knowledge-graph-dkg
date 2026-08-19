from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker

from .lifecycle import CLAIM_STATES, RELATION_STATES, RELATION_TYPES


EVENT_TYPE_REGISTRY_VERSION = "dkg.event-type-registry.v1"


class EventContractError(ValueError):
    """An event cannot cross the durable acceptance boundary under the registry."""


@dataclass(frozen=True)
class EvidencePolicy:
    evidence_refs: str = "optional"
    source_snapshot_refs: str = "optional"
    required_provenance_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        allowed = {"optional", "required"}
        if self.evidence_refs not in allowed:
            raise ValueError(f"unsupported evidence_refs policy: {self.evidence_refs}")
        if self.source_snapshot_refs not in allowed:
            raise ValueError(
                f"unsupported source_snapshot_refs policy: {self.source_snapshot_refs}"
            )


@dataclass(frozen=True)
class EventTypeContract:
    event_type: str
    contract_version: str
    commit_eligibility: str
    payload_schema: Mapping[str, Any]
    evidence_policy: EvidencePolicy
    ontology_constraints: Mapping[str, str] | None
    property_ids: tuple[str, ...]
    oracle_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.commit_eligibility not in {"proposal_only", "accepted"}:
            raise ValueError(
                f"unsupported commit eligibility for {self.event_type}: "
                f"{self.commit_eligibility}"
            )


def _payload_schema(
    event_type: str,
    *,
    required: tuple[str, ...],
    properties: Mapping[str, Any],
    additional_properties: bool = False,
) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": (
            "https://pukujan.github.io/fossil-core/schemas/event-types/"
            f"{event_type}/v1.schema.json"
        ),
        "type": "object",
        "additionalProperties": additional_properties,
        "required": list(required),
        "properties": dict(properties),
    }


def _string(*, min_length: int = 1) -> dict[str, Any]:
    return {"type": "string", "minLength": min_length}


def _string_array(*, min_items: int = 0) -> dict[str, Any]:
    return {
        "type": "array",
        "minItems": min_items,
        "uniqueItems": True,
        "items": _string(),
    }


def _contract(
    event_type: str,
    *,
    commit_eligibility: str,
    payload_schema: Mapping[str, Any],
    evidence_policy: EvidencePolicy = EvidencePolicy(),
    ontology_constraints: Mapping[str, str] | None = None,
    property_ids: tuple[str, ...],
    oracle_ids: tuple[str, ...] = ("tests/test_event_contracts.py",),
) -> EventTypeContract:
    return EventTypeContract(
        event_type=event_type,
        contract_version=f"dkg.event-contract.{event_type}.v1",
        commit_eligibility=commit_eligibility,
        payload_schema=payload_schema,
        evidence_policy=evidence_policy,
        ontology_constraints=ontology_constraints,
        property_ids=property_ids,
        oracle_ids=oracle_ids,
    )


_CLAIM_STATE = {"type": "string", "enum": sorted(CLAIM_STATES)}
_RELATION_STATE = {"type": "string", "enum": sorted(RELATION_STATES)}
_RELATION_TYPE = {"type": "string", "enum": sorted(RELATION_TYPES)}
_PACK_ID = {"type": "string", "pattern": "^pack_[A-Za-z0-9_-]{16,}$"}


EVENT_TYPE_CONTRACTS: Mapping[str, EventTypeContract] = {
    "claim.proposed": _contract(
        "claim.proposed",
        commit_eligibility="proposal_only",
        payload_schema=_payload_schema(
            "claim.proposed",
            required=("claim_text",),
            properties={
                "claim_text": _string(),
                "citation": {"type": "object"},
            },
        ),
        property_ids=("FOSSIL-PROP-PROVENANCE-001", "FOSSIL-PROP-HISTORY-001"),
    ),
    "claim.state_changed": _contract(
        "claim.state_changed",
        commit_eligibility="accepted",
        payload_schema=_payload_schema(
            "claim.state_changed",
            required=("to_state",),
            properties={
                "from_state": _CLAIM_STATE,
                "to_state": _CLAIM_STATE,
            },
        ),
        property_ids=("FOSSIL-PROP-HISTORY-001",),
    ),
    "claim.superseded": _contract(
        "claim.superseded",
        commit_eligibility="accepted",
        payload_schema=_payload_schema(
            "claim.superseded",
            required=("superseded_by",),
            properties={
                "from_state": _CLAIM_STATE,
                "superseded_by": _string(),
            },
        ),
        property_ids=(
            "FOSSIL-PROP-HISTORY-001",
            "FOSSIL-PROP-LIFECYCLE-DEPENDENCY-001",
        ),
    ),
    "relation.proposed": _contract(
        "relation.proposed",
        commit_eligibility="accepted",
        payload_schema=_payload_schema(
            "relation.proposed",
            required=("relation_id", "relation_type", "source_ref", "target_ref"),
            properties={
                "relation_id": _string(),
                "relation_type": _RELATION_TYPE,
                "source_ref": _string(),
                "target_ref": _string(),
                "state": _RELATION_STATE,
            },
        ),
        ontology_constraints={
            "ontology_ref": "dkg.core@1.0.0",
            "relation_type_field": "relation_type",
            "source_ref_field": "source_ref",
            "target_ref_field": "target_ref",
        },
        property_ids=("FOSSIL-PROP-HISTORY-001",),
    ),
    "relation.state_changed": _contract(
        "relation.state_changed",
        commit_eligibility="accepted",
        payload_schema=_payload_schema(
            "relation.state_changed",
            required=("relation_id", "to_state"),
            properties={
                "relation_id": _string(),
                "from_state": _RELATION_STATE,
                "to_state": _RELATION_STATE,
            },
        ),
        property_ids=("FOSSIL-PROP-HISTORY-001",),
    ),
    "relation.superseded": _contract(
        "relation.superseded",
        commit_eligibility="accepted",
        payload_schema=_payload_schema(
            "relation.superseded",
            required=("relation_id",),
            properties={
                "relation_id": _string(),
                "from_state": _RELATION_STATE,
            },
        ),
        property_ids=("FOSSIL-PROP-HISTORY-001",),
    ),
    **{
        event_type: _contract(
            event_type,
            commit_eligibility="accepted",
            payload_schema=_payload_schema(
                event_type,
                required=("snapshot_id", "source_id", "reason"),
                properties={
                    "snapshot_id": _string(),
                    "source_id": _string(),
                    "reason": _string(min_length=0),
                },
            ),
            evidence_policy=EvidencePolicy(
                source_snapshot_refs="required",
                required_provenance_fields=("method",),
            ),
            property_ids=("FOSSIL-PROP-PROVENANCE-001",),
        )
        for event_type in ("source.stale", "source.retracted", "source.restored")
    },
    "evidence.redacted": _contract(
        "evidence.redacted",
        commit_eligibility="accepted",
        payload_schema=_payload_schema(
            "evidence.redacted",
            required=(
                "artifact_id",
                "snapshot_ids",
                "reason",
                "authority",
                "request_ref",
                "redacted_at",
            ),
            properties={
                "artifact_id": _string(),
                "snapshot_ids": _string_array(),
                "reason": _string(),
                "authority": _string(),
                "request_ref": {"type": ["string", "null"]},
                "redacted_at": {"type": "string", "format": "date-time"},
            },
        ),
        evidence_policy=EvidencePolicy(required_provenance_fields=("method",)),
        property_ids=(
            "FOSSIL-PROP-PROVENANCE-001",
            "FOSSIL-PROP-REDACTION-NONRESURRECTION-001",
        ),
    ),
    "knowledge.promoted": _contract(
        "knowledge.promoted",
        commit_eligibility="accepted",
        payload_schema=_payload_schema(
            "knowledge.promoted",
            required=("source_pack_id", "target_pack_id", "reason"),
            properties={
                "source_pack_id": _PACK_ID,
                "target_pack_id": _PACK_ID,
                "reason": _string(min_length=0),
            },
        ),
        evidence_policy=EvidencePolicy(
            evidence_refs="required",
            required_provenance_fields=("method",),
        ),
        property_ids=("FOSSIL-PROP-PROMOTION-001", "FOSSIL-PROP-PROVENANCE-001"),
    ),
    "conversation.ingested": _contract(
        "conversation.ingested",
        commit_eligibility="accepted",
        payload_schema=_payload_schema(
            "conversation.ingested",
            required=(
                "conversation_id",
                "source_status",
                "source_artifact_ids",
                "message_ids",
            ),
            properties={
                "conversation_id": _string(),
                "source_status": {
                    "type": "string",
                    "enum": ["verbatim", "reconstructed", "mixed"],
                },
                "source_artifact_ids": _string_array(min_items=1),
                "message_ids": _string_array(min_items=1),
            },
        ),
        evidence_policy=EvidencePolicy(evidence_refs="required"),
        property_ids=("FOSSIL-PROP-PROVENANCE-001",),
    ),
}


def event_contract(event_type: str) -> EventTypeContract:
    try:
        return EVENT_TYPE_CONTRACTS[event_type]
    except KeyError as exc:
        raise EventContractError(
            f"unregistered event type cannot cross durable acceptance boundary: {event_type}"
        ) from exc


def _require_nonempty_refs(event: Mapping[str, Any], field: str) -> None:
    refs = event.get(field)
    if not isinstance(refs, list) or not refs:
        raise EventContractError(
            f"event type {event.get('event_type')} requires non-empty {field}"
        )


def validate_event_for_commit(event: Mapping[str, Any]) -> EventTypeContract:
    """Validate one prepared event against the versioned acceptance registry.

    This function intentionally has no storage-provider, pack-session, agent,
    projection, or network dependencies. Envelope validation and stable identity
    assignment remain adapter responsibilities; pack/actor authority remains at
    the application boundary. The registry adds the event-type semantic gate that
    every durable adapter can share.
    """

    contract = event_contract(str(event.get("event_type", "")))
    supplied_payload_schema = event.get("payload_schema")
    expected_payload_schema = str(contract.payload_schema["$id"])
    if supplied_payload_schema is not None and supplied_payload_schema != expected_payload_schema:
        raise EventContractError(
            f"event type {contract.event_type} payload_schema does not match registered contract"
        )

    Draft202012Validator(
        dict(contract.payload_schema),
        format_checker=FormatChecker(),
    ).validate(event.get("payload"))

    policy = contract.evidence_policy
    if policy.evidence_refs == "required":
        _require_nonempty_refs(event, "evidence_refs")
    if policy.source_snapshot_refs == "required":
        _require_nonempty_refs(event, "source_snapshot_refs")

    provenance = event.get("provenance")
    for field in policy.required_provenance_fields:
        if not isinstance(provenance, Mapping) or not provenance.get(field):
            raise EventContractError(
                f"event type {contract.event_type} requires provenance.{field}"
            )

    return contract


__all__ = [
    "EVENT_TYPE_CONTRACTS",
    "EVENT_TYPE_REGISTRY_VERSION",
    "EvidencePolicy",
    "EventContractError",
    "EventTypeContract",
    "event_contract",
    "validate_event_for_commit",
]
