from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker

from .lifecycle import CLAIM_STATES, RELATION_STATES
from .ontology import (
    CORE_ONTOLOGY_REF,
    ENTITY_TYPES,
    RELATION_TYPES,
    EndpointTypeResolver,
    OntologyConstraintError,
    validate_relation_endpoints,
    validate_resolved_relation_endpoints,
)
from .promotion import (
    PROMOTION_CONTRACT_VERSION,
    PromotionSourceError,
    PromotionSourceResolver,
    validate_promotion_source,
)


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
    ontology_constraints: Mapping[str, Any] | None
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
    additional_properties: bool = True,
    schema_version: int = 1,
) -> dict[str, Any]:
    """Return the registry-owned payload contract for one event type.

    Step 1 intentionally preserves already-written dkg.event.v1 payload
    extensions. Required semantic fields are explicit, while unknown fields in
    a registered payload remain forward-compatible until a later payload
    version intentionally closes them.
    """

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": (
            "https://pukujan.github.io/fossil-core/schemas/event-types/"
            f"{event_type}/v{schema_version}.schema.json"
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
    ontology_constraints: Mapping[str, Any] | None = None,
    property_ids: tuple[str, ...],
    oracle_ids: tuple[str, ...] = ("tests/test_event_contracts.py",),
    contract_version: int = 1,
) -> EventTypeContract:
    return EventTypeContract(
        event_type=event_type,
        contract_version=f"dkg.event-contract.{event_type}.v{contract_version}",
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
_ENTITY_TYPE = {"type": "string", "enum": sorted(ENTITY_TYPES)}
_PACK_ID = {"type": "string", "pattern": "^pack_[A-Za-z0-9_-]{16,}$"}
_RELATION_ENDPOINT_REQUIRED = (
    "ontology_ref",
    "relation_type",
    "source_ref",
    "source_type",
    "target_ref",
    "target_type",
)
_RELATION_ENDPOINT_PROPERTIES: Mapping[str, Any] = {
    "ontology_ref": _string(),
    "relation_type": _RELATION_TYPE,
    "source_ref": _string(),
    "source_type": _ENTITY_TYPE,
    "target_ref": _string(),
    "target_type": _ENTITY_TYPE,
}
_RELATION_ONTOLOGY_CONSTRAINTS: Mapping[str, Any] = {
    "ontology_ref": CORE_ONTOLOGY_REF,
    "relation_type_field": "relation_type",
    "source_ref_field": "source_ref",
    "source_type_field": "source_type",
    "target_ref_field": "target_ref",
    "target_type_field": "target_type",
}


EVENT_TYPE_CONTRACTS: Mapping[str, EventTypeContract] = {
    "claim.proposed": _contract(
        "claim.proposed",
        commit_eligibility="proposal_only",
        payload_schema=_payload_schema(
            "claim.proposed",
            required=("claim_text",),
            properties={
                # Empty text is historically valid at the storage-contract layer.
                # Meaningfulness belongs to review/ingest policy, not identity storage.
                "claim_text": _string(min_length=0),
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
                "citation": {"type": "object"},
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
                "citation": {"type": "object"},
            },
        ),
        property_ids=(
            "FOSSIL-PROP-HISTORY-001",
            "FOSSIL-PROP-LIFECYCLE-DEPENDENCY-001",
        ),
    ),
    "relation.proposed": _contract(
        "relation.proposed",
        commit_eligibility="proposal_only",
        payload_schema=_payload_schema(
            "relation.proposed",
            required=("relation_id", "relation_type", "source_ref", "target_ref"),
            properties={
                "relation_id": _string(),
                **_RELATION_ENDPOINT_PROPERTIES,
                "state": _RELATION_STATE,
            },
        ),
        ontology_constraints=_RELATION_ONTOLOGY_CONSTRAINTS,
        property_ids=("FOSSIL-PROP-HISTORY-001", "FOSSIL-PROP-LIFECYCLE-DEPENDENCY-001"),
        oracle_ids=(
            "tests/test_event_contracts.py",
            "tests/test_ontology_contracts.py",
            "tests/test_relation_acceptance.py",
        ),
    ),
    "relation.state_changed": _contract(
        "relation.state_changed",
        commit_eligibility="accepted",
        payload_schema=_payload_schema(
            "relation.state_changed",
            required=("relation_id", "to_state", *_RELATION_ENDPOINT_REQUIRED),
            properties={
                "relation_id": _string(),
                "from_state": _RELATION_STATE,
                "to_state": _RELATION_STATE,
                **_RELATION_ENDPOINT_PROPERTIES,
            },
        ),
        ontology_constraints=_RELATION_ONTOLOGY_CONSTRAINTS,
        property_ids=("FOSSIL-PROP-HISTORY-001", "FOSSIL-PROP-LIFECYCLE-DEPENDENCY-001"),
        oracle_ids=("tests/test_relation_acceptance.py", "tests/test_ontology_contracts.py"),
    ),
    "relation.superseded": _contract(
        "relation.superseded",
        commit_eligibility="accepted",
        payload_schema=_payload_schema(
            "relation.superseded",
            required=("relation_id", *_RELATION_ENDPOINT_REQUIRED),
            properties={
                "relation_id": _string(),
                "from_state": _RELATION_STATE,
                **_RELATION_ENDPOINT_PROPERTIES,
            },
        ),
        ontology_constraints=_RELATION_ONTOLOGY_CONSTRAINTS,
        property_ids=("FOSSIL-PROP-HISTORY-001", "FOSSIL-PROP-LIFECYCLE-DEPENDENCY-001"),
        oracle_ids=("tests/test_relation_acceptance.py", "tests/test_ontology_contracts.py"),
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
        contract_version=2,
        payload_schema=_payload_schema(
            "knowledge.promoted",
            schema_version=2,
            required=(
                "contract_version",
                "source_pack_id",
                "source_pack_revision",
                "source_event_id",
                "target_pack_id",
                "reason",
            ),
            properties={
                "contract_version": {"const": PROMOTION_CONTRACT_VERSION},
                "source_pack_id": _PACK_ID,
                "source_pack_revision": _string(),
                "source_event_id": _string(),
                "target_pack_id": _PACK_ID,
                "reason": _string(min_length=0),
            },
        ),
        evidence_policy=EvidencePolicy(
            evidence_refs="required",
            required_provenance_fields=("method",),
        ),
        property_ids=("FOSSIL-PROP-PROMOTION-001", "FOSSIL-PROP-PROVENANCE-001"),
        oracle_ids=("tests/test_event_contracts.py", "tests/test_promotion_source_pin.py"),
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
                "lineage_id": _string(),
            },
        ),
        evidence_policy=EvidencePolicy(evidence_refs="required"),
        property_ids=("FOSSIL-PROP-PROVENANCE-001",),
    ),
    "review.completed": _contract(
        "review.completed",
        commit_eligibility="accepted",
        payload_schema=_payload_schema(
            "review.completed",
            required=("decision",),
            properties={"decision": _string()},
        ),
        evidence_policy=EvidencePolicy(required_provenance_fields=("method",)),
        property_ids=("FOSSIL-PROP-PROVENANCE-001", "FOSSIL-PROP-HISTORY-001"),
        oracle_ids=(
            "tests/test_event_contracts.py",
            "tests/test_cognitive_services_benchmark.py",
        ),
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


def _validate_relation_semantics(
    event_type: str,
    payload: Mapping[str, Any],
    *,
    endpoint_type_resolver: EndpointTypeResolver | None,
) -> None:
    if event_type == "relation.proposed":
        if payload.get("state", "proposed") != "proposed":
            raise EventContractError(
                "relation.proposed must remain proposed; use an accepted relation state transition"
            )

        optional_endpoint_fields = ("ontology_ref", "source_type", "target_type")
        if not any(field in payload for field in optional_endpoint_fields):
            return
        missing = [field for field in optional_endpoint_fields if not payload.get(field)]
        if missing:
            raise EventContractError(
                "relation.proposed ontology metadata must be complete when supplied: "
                + ", ".join(missing)
            )
        try:
            validate_relation_endpoints(
                relation_type=str(payload["relation_type"]),
                source_type=str(payload["source_type"]),
                target_type=str(payload["target_type"]),
                ontology_ref=str(payload["ontology_ref"]),
            )
        except OntologyConstraintError as exc:
            raise EventContractError(str(exc)) from exc
        return

    try:
        validate_resolved_relation_endpoints(
            relation_type=str(payload["relation_type"]),
            source_ref=str(payload["source_ref"]),
            source_type=str(payload["source_type"]),
            target_ref=str(payload["target_ref"]),
            target_type=str(payload["target_type"]),
            ontology_ref=str(payload["ontology_ref"]),
            resolver=endpoint_type_resolver,
        )
    except OntologyConstraintError as exc:
        raise EventContractError(str(exc)) from exc


def validate_event_for_commit(
    event: Mapping[str, Any],
    *,
    endpoint_type_resolver: EndpointTypeResolver | None = None,
    promotion_source_resolver: PromotionSourceResolver | None = None,
) -> EventTypeContract:
    """Validate one prepared event against the versioned acceptance registry.

    The event envelope's optional ``payload_schema`` field is preserved as
    historical/external metadata. It cannot override this registry: payload
    validation always uses the registered contract below. Accepted relation
    events additionally require an independently configured endpoint resolver;
    self-declared endpoint kinds are never sufficient for acceptance. Accepted
    promotions likewise require an independently configured exact-source resolver.
    """

    contract = event_contract(str(event.get("event_type", "")))
    Draft202012Validator(
        dict(contract.payload_schema),
        format_checker=FormatChecker(),
    ).validate(event.get("payload"))

    payload = event.get("payload")
    if contract.ontology_constraints is not None and isinstance(payload, Mapping):
        _validate_relation_semantics(
            contract.event_type,
            payload,
            endpoint_type_resolver=endpoint_type_resolver,
        )

    if contract.event_type == "knowledge.promoted":
        try:
            validate_promotion_source(event, resolver=promotion_source_resolver)
        except PromotionSourceError as exc:
            raise EventContractError(str(exc)) from exc

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
