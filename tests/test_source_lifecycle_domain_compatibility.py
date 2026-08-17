from __future__ import annotations

import fossil_core.source as legacy_source
from fossil_core.domain.provenance import (
    SourceLifecycleState,
    SourceStatus,
    build_source_state_event,
)


def _event(event_type: str, recorded_at: str, event_id: str) -> dict:
    return {
        **build_source_state_event(
            event_type=event_type,
            snapshot_id="snap_fixture",
            source_id="source_fixture",
            pack_id="pack_fixture",
            actor={"actor_type": "system", "actor_id": "fixture"},
            occurred_at=recorded_at,
            recorded_at=recorded_at,
            idempotency_key=f"fixture:{event_type}",
            reason=event_type,
        ),
        "event_id": event_id,
    }


def test_source_lifecycle_domain_preserves_legacy_identity():
    assert legacy_source.SourceStatus is SourceStatus
    assert legacy_source.SourceLifecycleState is SourceLifecycleState
    assert legacy_source.build_source_state_event is build_source_state_event


def test_source_state_event_shape_is_unchanged():
    event = build_source_state_event(
        event_type="source.retracted",
        snapshot_id="snap_123",
        source_id="source_456",
        pack_id="pack_789",
        actor={"actor_type": "system", "actor_id": "source-fixture"},
        occurred_at="2026-08-09T23:42:00Z",
        recorded_at="2026-08-09T23:43:00Z",
        idempotency_key="source-lifecycle-2",
        reason="upstream retraction",
    )
    assert event == {
        "schema_version": "dkg.event.v1",
        "event_type": "source.retracted",
        "occurred_at": "2026-08-09T23:42:00Z",
        "recorded_at": "2026-08-09T23:43:00Z",
        "pack_id": "pack_789",
        "actor": {"actor_type": "system", "actor_id": "source-fixture"},
        "subject_refs": ["snap_123", "source_456"],
        "idempotency_key": "source-lifecycle-2",
        "source_snapshot_refs": ["snap_123"],
        "payload": {
            "snapshot_id": "snap_123",
            "source_id": "source_456",
            "reason": "upstream retraction",
        },
        "provenance": {"method": "source_lifecycle"},
    }


def test_source_lifecycle_replay_order_and_default_active_are_unchanged():
    stale = _event("source.stale", "2026-08-09T23:41:00Z", "evt_1")
    retracted = _event("source.retracted", "2026-08-09T23:42:00Z", "evt_2")
    restored = _event("source.restored", "2026-08-09T23:43:00Z", "evt_3")

    state = SourceLifecycleState.replay([restored, stale, retracted])
    assert state.status("snap_fixture") == "active"
    assert state.statuses["snap_fixture"] == SourceStatus(
        snapshot_id="snap_fixture",
        state="active",
        reason="source.restored",
        last_event_id="evt_3",
    )
    assert state.status("snap_unknown") == "active"


def test_legacy_source_namespace_remains_frozen_after_domain_extraction():
    assert not hasattr(legacy_source, "__all__")
    public_names = sorted(
        name for name in vars(legacy_source) if not name.startswith("_")
    )
    assert public_names == [
        "Any",
        "ArtifactStore",
        "CitationIntegrityError",
        "CitationLaunderingError",
        "Draft202012Validator",
        "FormatChecker",
        "Iterable",
        "Mapping",
        "Path",
        "RedactionPolicy",
        "SourceLifecycleState",
        "SourceSnapshotConflict",
        "SourceSnapshotStore",
        "SourceStatus",
        "annotations",
        "build_redaction_event",
        "build_source_state_event",
        "copy",
        "dataclass",
        "hashlib",
        "json",
        "publish_immutable",
    ]
