from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import ValidationError

from fossil_core.event_store import DurableEventStore, IdempotencyConflict
from fossil_core.ids import deterministic_event_id


ROOT = Path(__file__).parents[1]
SCHEMA = ROOT / "schemas/events/v1.schema.json"


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


def test_constructor_creates_nested_store_and_stable_redaction_namespace(tmp_path):
    root = tmp_path / "nested" / "durable" / "events"
    first = DurableEventStore(root, SCHEMA)

    assert first.root == root
    assert root.is_dir()
    assert first.redactions == root / "_redactions"
    assert first.redactions.is_dir()

    reopened = DurableEventStore(root, SCHEMA)
    assert reopened.root == root
    assert reopened.redactions == root / "_redactions"


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
