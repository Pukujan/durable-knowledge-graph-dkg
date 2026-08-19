from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import ValidationError

from fossil_core.domain.event_contracts import EventContractError
from fossil_core.event_store import DurableEventStore, IdempotencyConflict
from fossil_core.ids import deterministic_event_id


ROOT = Path(__file__).parents[1]
SCHEMA = ROOT / "schemas/events/v1.schema.json"
SOURCE = "clm_event_store_source_000001"
TARGET = "clm_event_store_target_000001"
PROMOTION_SOURCE_PACK = "pack_f024177f89a5442db84171c3dd7f58e5"
PROMOTION_TARGET_PACK = "pack_269099f7b2ba43b7a99b9427d64092de"
PROMOTION_SOURCE_REVISION = "git:source@aaaaaaaa"
PROMOTION_SOURCE_EVENT = "evt_event_store_promotion_source_0001"
PROMOTION_SUBJECT = "clm_event_store_promotion_subject_0001"


def event():
    return {
        "schema_version": "dkg.event.v1",
        "event_type": "claim.proposed",
        "occurred_at": "2026-08-09T17:21:00Z",
        "recorded_at": "2026-08-09T17:21:01Z",
        "pack_id": "pack_269099f7b2ba43b7a99b9427d64092de",
        "actor": {"actor_type": "human", "actor_id": "user"},
        "subject_refs": ["clm_example_0000000000000001"],
        "idempotency_key": "conversation-1-turn-1-claim-1",
        "evidence_refs": ["span_example_0000000000000001"],
        "payload": {"claim_text": "Evidence should survive projection replacement."},
    }


def accepted_relation(*, source_type: str = "Claim") -> dict:
    return {
        "schema_version": "dkg.event.v1",
        "event_type": "relation.state_changed",
        "occurred_at": "2026-08-19T16:25:00Z",
        "recorded_at": "2026-08-19T16:25:01Z",
        "pack_id": "pack_269099f7b2ba43b7a99b9427d64092de",
        "actor": {"actor_type": "system", "actor_id": "event-store-oracle"},
        "subject_refs": ["rel_event_store_000001"],
        "idempotency_key": "event-store:accepted-relation",
        "payload": {
            "relation_id": "rel_event_store_000001",
            "from_state": "proposed",
            "to_state": "active",
            "ontology_ref": "dkg.core@1.0.0",
            "relation_type": "DEPENDS_ON",
            "source_ref": SOURCE,
            "source_type": source_type,
            "target_ref": TARGET,
            "target_type": "Claim",
        },
        "provenance": {"method": "event-store-oracle"},
    }


def promotion_event() -> dict:
    return {
        "schema_version": "dkg.event.v1",
        "event_type": "knowledge.promoted",
        "occurred_at": "2026-08-19T16:30:00Z",
        "recorded_at": "2026-08-19T16:30:01Z",
        "pack_id": PROMOTION_TARGET_PACK,
        "actor": {"actor_type": "system", "actor_id": "event-store-oracle"},
        "subject_refs": [PROMOTION_SUBJECT],
        "idempotency_key": "event-store:pinned-promotion",
        "evidence_refs": ["art_event_store_promotion_evidence"],
        "payload": {
            "contract_version": "dkg.promotion.v2",
            "source_pack_id": PROMOTION_SOURCE_PACK,
            "source_pack_revision": PROMOTION_SOURCE_REVISION,
            "source_event_id": PROMOTION_SOURCE_EVENT,
            "target_pack_id": PROMOTION_TARGET_PACK,
            "reason": "reviewed reusable knowledge",
        },
        "provenance": {"method": "explicit_cross_pack_promotion"},
    }


def test_constructor_creates_nested_store_and_stable_redaction_namespace(tmp_path):
    root = tmp_path / "nested" / "durable" / "events"
    first = DurableEventStore(root, SCHEMA)

    assert first.root == root
    assert root.is_dir()
    assert first.redactions == root / "_redactions"
    assert first.redactions.is_dir()
    assert first.endpoint_type_resolver is None
    assert first.promotion_source_resolver is None

    reopened = DurableEventStore(root, SCHEMA)
    assert reopened.root == root
    assert reopened.redactions == root / "_redactions"


def test_constructor_preserves_exact_endpoint_resolver_identity(tmp_path):
    resolver = {SOURCE: "Claim", TARGET: "Claim"}.get
    store = DurableEventStore(
        tmp_path / "events",
        SCHEMA,
        endpoint_type_resolver=resolver,
    )

    assert store.endpoint_type_resolver is resolver


def test_promotion_source_resolver_is_retained_and_forwarded_by_validate_and_commit(tmp_path):
    calls: list[tuple[str, str, str]] = []

    def resolver(pack_id: str, revision: str, event_id: str):
        calls.append((pack_id, revision, event_id))
        return {
            "event_id": PROMOTION_SOURCE_EVENT,
            "pack_id": PROMOTION_SOURCE_PACK,
            "subject_refs": [PROMOTION_SUBJECT],
        }

    store = DurableEventStore(
        tmp_path / "events",
        SCHEMA,
        promotion_source_resolver=resolver,
    )
    assert store.promotion_source_resolver is resolver

    validated = store.validate(promotion_event())
    assert validated["event_type"] == "knowledge.promoted"
    assert calls == [
        (PROMOTION_SOURCE_PACK, PROMOTION_SOURCE_REVISION, PROMOTION_SOURCE_EVENT)
    ]

    calls.clear()
    committed = store.commit(promotion_event())
    assert committed["event_type"] == "knowledge.promoted"
    assert calls == [
        (PROMOTION_SOURCE_PACK, PROMOTION_SOURCE_REVISION, PROMOTION_SOURCE_EVENT)
    ]


def test_validate_is_non_mutating_and_assigns_deterministic_identity(tmp_path):
    store = DurableEventStore(tmp_path / "events", SCHEMA)
    candidate = event()
    original = deepcopy(candidate)

    validated = store.validate(candidate)

    assert candidate == original
    assert validated is not candidate
    assert validated["payload"] is not candidate["payload"]
    assert validated["event_id"] == deterministic_event_id(
        candidate["pack_id"], candidate["idempotency_key"]
    )
    assert list(store.iter_events()) == []


def test_validate_forwards_endpoint_resolver_to_acceptance_gate(tmp_path):
    resolver = {SOURCE: "Claim", TARGET: "Claim"}.get
    store = DurableEventStore(
        tmp_path / "events",
        SCHEMA,
        endpoint_type_resolver=resolver,
    )

    validated = store.validate(accepted_relation())
    assert validated["payload"]["source_type"] == "Claim"

    with pytest.raises(EventContractError, match="source_type.*does not match resolved"):
        store.validate(accepted_relation(source_type="Concept"))


def test_commit_forwards_endpoint_resolver_before_write(tmp_path):
    resolver = {SOURCE: "Claim", TARGET: "Claim"}.get
    store = DurableEventStore(
        tmp_path / "events",
        SCHEMA,
        endpoint_type_resolver=resolver,
    )

    with pytest.raises(EventContractError, match="source_type.*does not match resolved"):
        store.commit(accepted_relation(source_type="Concept"))
    assert list(store.iter_events()) == []


def test_validate_enforces_schema_date_time_formats(tmp_path):
    store = DurableEventStore(tmp_path / "events", SCHEMA)
    candidate = event()
    candidate["occurred_at"] = "not-a-date-time"

    with pytest.raises(ValidationError):
        store.validate(candidate)


def test_prepare_without_idempotency_preserves_explicit_event_identity(tmp_path):
    store = DurableEventStore(tmp_path / "events", SCHEMA)
    candidate = event()
    candidate.pop("idempotency_key")
    candidate["event_id"] = "evt_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

    prepared = store.prepare(candidate)

    assert prepared["event_id"] == candidate["event_id"]


def test_prepare_without_idempotency_assigns_valid_fresh_identity(tmp_path):
    store = DurableEventStore(tmp_path / "events", SCHEMA)
    candidate = event()
    candidate.pop("idempotency_key")

    prepared = store.prepare(candidate)

    assert prepared["event_id"].startswith("evt_")
    assert len(prepared["event_id"]) >= len("evt_") + 16


def test_prepare_accepts_matching_deterministic_event_identity(tmp_path):
    store = DurableEventStore(tmp_path / "events", SCHEMA)
    candidate = event()
    expected = deterministic_event_id(candidate["pack_id"], candidate["idempotency_key"])
    candidate["event_id"] = expected

    assert store.prepare(candidate)["event_id"] == expected


def test_canonical_bytes_are_stable_compact_utf8_json():
    assert DurableEventStore._canonical({"z": "café", "a": [2, 1]}) == (
        '{"a":[2,1],"z":"café"}\n'.encode("utf-8")
    )


def test_commit_uses_stable_two_character_shard_and_canonical_bytes(tmp_path):
    root = tmp_path / "events"
    store = DurableEventStore(root, SCHEMA)
    committed = store.commit(event())
    event_id = committed["event_id"]
    suffix = event_id.removeprefix("evt_")
    expected_path = root / suffix[:2] / f"{event_id}.json"

    assert store._event_path(event_id) == expected_path
    assert expected_path.read_bytes() == DurableEventStore._canonical(committed)


def test_commit_is_immutable_and_retry_is_idempotent(tmp_path):
    store = DurableEventStore(tmp_path / "events", SCHEMA)
    first = store.commit(event())
    second = store.commit(event())
    assert first == second
    assert len(list(store.iter_events())) == 1


def test_same_idempotency_key_cannot_change_history(tmp_path):
    store = DurableEventStore(tmp_path / "events", SCHEMA)
    original = event()
    store.commit(original)
    changed = deepcopy(original)
    changed["payload"]["claim_text"] = "Changed after commit"
    with pytest.raises(IdempotencyConflict):
        store.commit(changed)


def test_supplied_event_id_must_match_idempotency_identity(tmp_path):
    store = DurableEventStore(tmp_path / "events", SCHEMA)
    bad = event()
    bad["event_id"] = "evt_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    with pytest.raises(IdempotencyConflict):
        store.commit(bad)


def test_invalid_event_rejected_before_write(tmp_path):
    store = DurableEventStore(tmp_path / "events", SCHEMA)
    bad = event()
    del bad["pack_id"]
    with pytest.raises(ValidationError):
        store.commit(bad)
    assert list(store.iter_events()) == []


def test_unknown_event_type_is_prepare_only_and_fails_validate_and_commit(tmp_path):
    store = DurableEventStore(tmp_path / "events", SCHEMA)
    unknown = event()
    unknown["event_type"] = "ontology.concept_split"

    assert store.prepare(unknown)["event_type"] == "ontology.concept_split"
    with pytest.raises(EventContractError, match="unregistered event type"):
        store.validate(unknown)
    with pytest.raises(EventContractError, match="unregistered event type"):
        store.commit(unknown)
    assert list(store.iter_events()) == []
