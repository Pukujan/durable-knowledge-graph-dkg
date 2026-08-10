from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from dkg.event_store import (
    DurableEventStore,
    EventRedactedError,
    EventRedactionConflict,
)
from dkg.projection.graphiti import GraphitiProjectionAdapter
from dkg.projection.ledger import ProjectionLedger


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
    assert list(events.iter_redactions()) == [tombstone]
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


class FakeGraphitiEventRedaction:
    def __init__(self) -> None:
        self.add_calls: list[dict] = []
        self.remove_calls: list[str] = []

    async def add_episode(self, **kwargs):
        self.add_calls.append(kwargs)
        return SimpleNamespace(episode=SimpleNamespace(uuid="episode-event-redaction-001"))

    async def remove_episode(self, episode_uuid: str):
        self.remove_calls.append(episode_uuid)


async def _projection_tombstone_recovery(tmp_path: Path) -> None:
    events = store(tmp_path)
    committed = events.commit(event())
    event_id = committed["event_id"]
    client = FakeGraphitiEventRedaction()
    ledger = ProjectionLedger(
        tmp_path / "ledger", "graphiti-neo4j", build_id="active-event-redaction"
    )
    adapter = GraphitiProjectionAdapter(
        client=client,
        ledger=ledger,
        build_manifest={"projection_build_id": "active-event-redaction"},
        episode_type_json="json",
    )

    applied = await adapter.apply_event_async(committed)
    assert applied.status == "applied"
    assert ledger.get_applied(event_id)["episode_uuid"] == "episode-event-redaction-001"

    tombstone = events.redact(
        event_id,
        reason="event contains sensitive copied text",
        authority="privacy-officer",
        redacted_at="2026-08-10T00:43:00Z",
        request_ref="event-erase-43",
    )
    assert tombstone["event_id"] == event_id
    assert list(events.iter_events()) == []

    receipts = await adapter.purge_event_redactions_async(event_store=events)
    assert [receipt.status for receipt in receipts] == ["redacted"]
    assert client.remove_calls == ["episode-event-redaction-001"]
    assert ledger.is_redacted(event_id)
    assert ledger.get_applied(event_id) is not None

    # Simulate a fresh projection build after the canonical event bytes are gone.
    fresh_client = FakeGraphitiEventRedaction()
    fresh = GraphitiProjectionAdapter(
        client=fresh_client,
        ledger=ProjectionLedger(
            tmp_path / "ledger", "graphiti-neo4j", build_id="fresh-after-event-redaction"
        ),
        build_manifest={"projection_build_id": "fresh-after-event-redaction"},
        episode_type_json="json",
    )
    assert await fresh.rebuild_async(events_root=events.root) == []
    assert fresh_client.add_calls == []


def test_event_redaction_tombstone_recovers_active_projection_cleanup(tmp_path):
    asyncio.run(_projection_tombstone_recovery(tmp_path))
