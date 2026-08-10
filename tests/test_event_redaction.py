from __future__ import annotations

from pathlib import Path

import pytest

from dkg.event_store import (
    DurableEventStore,
    EventRedactedError,
    EventRedactionConflict,
)


PACK_ID = "pack_269099f7b2ba43b7a99b9427d64092de"


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def store(tmp_path: Path) -> DurableEventStore:
    return DurableEventStore(
        tmp_path / "events",
        root() / "schemas" / "events" / "v1.schema.json",
    )


def event() -> dict:
    return {
        "schema_version": "dkg.event.v1",
        "event_type": "claim.proposed",
        "occurred_at": "2026-08-10T00:40:00Z",
        "recorded_at": "2026-08-10T00:40:00Z",
        "pack_id": PACK_ID,
        "actor": {"actor_type": "system", "actor_id": "event-redaction-fixture"},
        "subject_refs": ["clm_event_redaction_fixture"],
        "idempotency_key": "event-redaction-fixture-v1",
        "evidence_refs": ["art_sensitive_fixture"],
        "payload": {"claim_text": "sensitive event payload must be erasable"},
        "provenance": {"method": "event_redaction_fixture"},
    }


def test_event_redaction_tombstones_before_delete_and_blocks_resurrection(tmp_path):
    events = store(tmp_path)
    committed = events.commit(event())
    event_id = committed["event_id"]
    event_path = events._event_path(event_id)
    assert event_path.exists()
    assert events.get(event_id)["payload"]["claim_text"].startswith("sensitive")

    tombstone = events.redact(
        event_id,
        reason="privacy erasure request",
        authority="fixture-data-controller",
        redacted_at="2026-08-10T00:41:00Z",
        request_ref="erase-request-001",
    )

    assert tombstone["event_id"] == event_id
    assert tombstone["pack_id"] == PACK_ID
    assert tombstone["event_type"] == "claim.proposed"
    assert tombstone["canonical_hash"]["algorithm"] == "sha256"
    assert len(tombstone["canonical_hash"]["digest"]) == 64
    assert "payload" not in tombstone
    assert "subject_refs" not in tombstone
    assert "evidence_refs" not in tombstone
    assert "provenance" not in tombstone
    assert not event_path.exists()
    assert events.is_redacted(event_id)

    with pytest.raises(EventRedactedError, match="has been redacted"):
        events.get(event_id)
    with pytest.raises(EventRedactedError, match="cannot be republished"):
        events.commit(event())

    assert list(events.iter_events()) == []
    assert events.get_redaction(event_id) == tombstone


def test_event_redaction_is_idempotent_but_conflicting_tombstone_is_rejected(tmp_path):
    events = store(tmp_path)
    event_id = events.commit(event())["event_id"]
    kwargs = {
        "reason": "legal deletion",
        "authority": "privacy-officer",
        "redacted_at": "2026-08-10T00:42:00Z",
        "request_ref": "legal-42",
    }
    first = events.redact(event_id, **kwargs)
    assert events.redact(event_id, **kwargs) == first

    with pytest.raises(EventRedactionConflict, match="different redaction tombstone"):
        events.redact(
            event_id,
            reason="different reason",
            authority="privacy-officer",
            redacted_at="2026-08-10T00:42:00Z",
            request_ref="legal-42",
        )
