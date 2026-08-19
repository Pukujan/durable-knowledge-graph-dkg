from __future__ import annotations

from pathlib import Path

import pytest
from jsonschema import ValidationError

from fossil_core.adapters.s3.storage import S3DurableEventStore
from fossil_core.domain.event_contracts import (
    EVENT_TYPE_CONTRACTS,
    EVENT_TYPE_REGISTRY_VERSION,
    EventContractError,
)
from fossil_core.event_store import DurableEventStore


ROOT = Path(__file__).parents[1]
SCHEMA = ROOT / "schemas/events/v1.schema.json"
PACK = "pack_269099f7b2ba43b7a99b9427d64092de"

CURRENT_WRITE_EVENT_TYPES = {
    "claim.proposed",
    "claim.state_changed",
    "claim.superseded",
    "relation.proposed",
    "relation.state_changed",
    "relation.superseded",
    "source.stale",
    "source.retracted",
    "source.restored",
    "evidence.redacted",
    "knowledge.promoted",
    "conversation.ingested",
}


def event(
    event_type: str = "claim.proposed",
    *,
    payload: dict | None = None,
    evidence_refs: list[str] | None = None,
    source_snapshot_refs: list[str] | None = None,
    provenance: dict | None = None,
) -> dict:
    value = {
        "schema_version": "dkg.event.v1",
        "event_type": event_type,
        "occurred_at": "2026-08-19T15:45:00Z",
        "recorded_at": "2026-08-19T15:45:01Z",
        "pack_id": PACK,
        "actor": {"actor_type": "system", "actor_id": "event-contract-test"},
        "subject_refs": ["clm_event_contract_fixture"],
        "idempotency_key": f"event-contract:{event_type}",
        "payload": payload if payload is not None else {"claim_text": "proposal"},
    }
    if evidence_refs is not None:
        value["evidence_refs"] = evidence_refs
    if source_snapshot_refs is not None:
        value["source_snapshot_refs"] = source_snapshot_refs
    if provenance is not None:
        value["provenance"] = provenance
    return value


def test_registry_is_versioned_and_covers_the_characterized_write_vocabulary():
    assert EVENT_TYPE_REGISTRY_VERSION == "dkg.event-type-registry.v1"
    assert set(EVENT_TYPE_CONTRACTS) == CURRENT_WRITE_EVENT_TYPES

    for event_type, contract in EVENT_TYPE_CONTRACTS.items():
        assert contract.event_type == event_type
        assert contract.contract_version.endswith(".v1")
        assert contract.commit_eligibility in {"proposal_only", "accepted"}
        assert contract.payload_schema["$id"].endswith("v1.schema.json")
        assert contract.evidence_policy is not None
        assert contract.property_ids
        assert contract.oracle_ids

    assert EVENT_TYPE_CONTRACTS["claim.proposed"].commit_eligibility == "proposal_only"
    relation = EVENT_TYPE_CONTRACTS["relation.proposed"]
    assert relation.ontology_constraints == {
        "ontology_ref": "dkg.core@1.0.0",
        "relation_type_field": "relation_type",
        "source_ref_field": "source_ref",
        "target_ref_field": "target_ref",
    }


def test_prepare_keeps_unknown_proposals_cheap_but_acceptance_fails_closed(tmp_path):
    store = DurableEventStore(tmp_path / "events", SCHEMA)
    unknown = event("ontology.concept_split", payload={"concept_id": "concept_fixture"})

    prepared = store.prepare(unknown)
    assert prepared["event_type"] == "ontology.concept_split"
    assert list(store.iter_events()) == []

    with pytest.raises(EventContractError, match="unregistered event type"):
        store.validate(unknown)
    with pytest.raises(EventContractError, match="unregistered event type"):
        store.commit(unknown)
    assert list(store.iter_events()) == []


def test_s3_durable_commit_uses_the_same_fail_closed_acceptance_gate():
    store = S3DurableEventStore(
        bucket="event-contract-fixture",
        schema_path=SCHEMA,
        client=object(),
    )
    unknown = event("ontology.concept_split", payload={"concept_id": "concept_fixture"})

    assert store.prepare(unknown)["event_type"] == "ontology.concept_split"
    with pytest.raises(EventContractError, match="unregistered event type"):
        store.validate(unknown)
    with pytest.raises(EventContractError, match="unregistered event type"):
        store.commit(unknown)


def test_registered_payload_contract_rejects_semantically_empty_claim_before_write(tmp_path):
    store = DurableEventStore(tmp_path / "events", SCHEMA)
    bad = event("claim.proposed", payload={})

    with pytest.raises(ValidationError):
        store.validate(bad)
    with pytest.raises(ValidationError):
        store.commit(bad)
    assert list(store.iter_events()) == []


def test_promotion_evidence_policy_and_provenance_fail_closed(tmp_path):
    store = DurableEventStore(tmp_path / "events", SCHEMA)
    promotion = event(
        "knowledge.promoted",
        payload={
            "source_pack_id": "pack_f024177f89a5442db84171c3dd7f58e5",
            "target_pack_id": PACK,
            "reason": "reviewed reuse",
        },
        evidence_refs=[],
        provenance={"method": "explicit_cross_pack_promotion"},
    )

    with pytest.raises(EventContractError, match="evidence_refs"):
        store.commit(promotion)

    promotion["evidence_refs"] = ["art_promotion_evidence"]
    promotion.pop("provenance")
    with pytest.raises(EventContractError, match="provenance.method"):
        store.commit(promotion)


def test_source_lifecycle_requires_snapshot_reference_and_provenance(tmp_path):
    store = DurableEventStore(tmp_path / "events", SCHEMA)
    stale = event(
        "source.stale",
        payload={
            "snapshot_id": "snap_event_contract_fixture",
            "source_id": "src_event_contract_fixture",
            "reason": "upstream changed",
        },
        source_snapshot_refs=[],
        provenance={"method": "source_lifecycle"},
    )

    with pytest.raises(EventContractError, match="source_snapshot_refs"):
        store.commit(stale)


def test_registered_proposal_only_event_can_still_be_recorded_as_proposal(tmp_path):
    store = DurableEventStore(tmp_path / "events", SCHEMA)
    committed = store.commit(event())

    assert committed["event_type"] == "claim.proposed"
    assert EVENT_TYPE_CONTRACTS[committed["event_type"]].commit_eligibility == "proposal_only"


def test_historical_unknown_events_remain_replayable_without_silent_upgrade(tmp_path):
    store = DurableEventStore(tmp_path / "events", SCHEMA)
    historical = event("ontology.concept_split", payload={"concept_id": "concept_legacy"})
    historical.pop("idempotency_key")
    historical["event_id"] = "evt_legacy_event_contract_000001"
    path = store._event_path(historical["event_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(store._canonical(historical))

    assert store.get(historical["event_id"]) == historical
    assert list(store.iter_events()) == [historical]
