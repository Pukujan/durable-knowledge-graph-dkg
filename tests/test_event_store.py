from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import ValidationError

from fossil_core.event_store import DurableEventStore, IdempotencyConflict


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
