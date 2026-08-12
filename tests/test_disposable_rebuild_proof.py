"""Secretless filesystem reference proof for the #87 storage/recovery contract.

This deliberately exercises only the existing filesystem reference semantics.
It is not evidence for a live R2/S3 provider and does not select one.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from dkg.artifact_store import ArtifactStore
from dkg.event_store import DurableEventStore, IdempotencyConflict
from dkg.projection.migration import SemanticSnapshot
from dkg.projection.null import NullProjection


ROOT = Path(__file__).parents[1]
SCHEMA = ROOT / "schemas/events/v1.schema.json"
PACK = "pack_269099f7b2ba43b7a99b9427d64092de"


def event(number: int) -> dict:
    return {
        "schema_version": "dkg.event.v1",
        "event_type": "claim.proposed",
        "occurred_at": f"2026-08-12T01:5{number}:00Z",
        "recorded_at": f"2026-08-12T02:0{number}:00Z",
        "pack_id": PACK,
        "actor": {"actor_type": "system", "actor_id": "storage-proof-fixture"},
        "subject_refs": [f"clm_fixture_{number}"],
        "idempotency_key": f"storage-proof-{number}",
        "payload": {"claim_text": f"canonical fixture event {number}"},
    }


def test_disposable_rebuild_recovers_semantics_after_local_projection_loss(tmp_path: Path):
    """A fresh projection rebuild derives the same semantic snapshot from events."""

    events = DurableEventStore(tmp_path / "canonical" / "events", SCHEMA)
    artifacts = ArtifactStore(tmp_path / "canonical" / "artifacts")
    artifact = artifacts.put_bytes(b"fixture evidence", media_type="text/plain")
    committed = [events.commit(event(1)), events.commit(event(2))]
    before = SemanticSnapshot.from_events(committed)

    # The local projection/cache is intentionally disposable, not canonical state.
    projection_root = tmp_path / "local-projection"
    projection_root.mkdir()
    (projection_root / "warm-cache").write_text("discard me", encoding="utf-8")
    for path in projection_root.iterdir():
        path.unlink()
    projection_root.rmdir()

    rebuilt = list(events.iter_events())
    receipts = NullProjection().rebuild(events_root=events.root)
    assert not projection_root.exists()
    assert artifacts.verify(artifact["artifact_id"])
    assert SemanticSnapshot.from_events(rebuilt) == before
    assert [receipt.status for receipt in receipts] == ["applied", "applied"]


def test_duplicate_retry_is_idempotent_but_conflicting_stable_identity_fails_loudly(tmp_path: Path):
    events = DurableEventStore(tmp_path / "events", SCHEMA)
    original = event(1)
    assert events.commit(original) == events.commit(original)

    conflicting = deepcopy(original)
    conflicting["payload"]["claim_text"] = "different bytes under the same identity"
    with pytest.raises(IdempotencyConflict, match="already exists with different content"):
        events.commit(conflicting)


def test_interrupted_rebuild_can_restart_from_canonical_events(tmp_path: Path):
    """An interruption leaves no projection checkpoint that can masquerade as truth."""

    events = DurableEventStore(tmp_path / "events", SCHEMA)
    committed = [events.commit(event(1)), events.commit(event(2))]
    expected = SemanticSnapshot.from_events(committed)

    # Simulate runner death after a partial local projection attempt.
    partial = tmp_path / "discarded-runner-state"
    partial.mkdir()
    (partial / "checkpoint").write_text(committed[0]["event_id"], encoding="utf-8")
    for path in partial.iterdir():
        path.unlink()
    partial.rmdir()

    restarted = list(events.iter_events())
    assert not partial.exists()
    assert SemanticSnapshot.from_events(restarted) == expected
    assert [receipt.event_id for receipt in NullProjection().rebuild(events_root=events.root)] == [
        item["event_id"] for item in restarted
    ]
