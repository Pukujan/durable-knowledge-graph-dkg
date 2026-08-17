from __future__ import annotations

import fossil_core.source as legacy_source
from fossil_core.domain.evidence import build_redaction_event


def test_redaction_event_factory_preserves_legacy_identity():
    assert legacy_source.build_redaction_event is build_redaction_event


def test_redaction_event_shape_is_unchanged():
    event = build_redaction_event(
        tombstone={
            "artifact_id": "artifact_123",
            "reason": "legal request",
            "authority": "owner",
            "request_ref": "request_456",
            "redacted_at": "2026-08-09T23:50:00Z",
        },
        pack_id="pack_789",
        actor={"actor_type": "system", "actor_id": "redaction-fixture"},
        occurred_at="2026-08-09T23:51:00Z",
        recorded_at="2026-08-09T23:52:00Z",
        idempotency_key="redaction-1",
        snapshot_ids=("snap_1", "snap_2"),
    )
    assert event == {
        "schema_version": "dkg.event.v1",
        "event_type": "evidence.redacted",
        "occurred_at": "2026-08-09T23:51:00Z",
        "recorded_at": "2026-08-09T23:52:00Z",
        "pack_id": "pack_789",
        "actor": {"actor_type": "system", "actor_id": "redaction-fixture"},
        "subject_refs": ["artifact_123", "snap_1", "snap_2"],
        "idempotency_key": "redaction-1",
        "payload": {
            "artifact_id": "artifact_123",
            "snapshot_ids": ["snap_1", "snap_2"],
            "reason": "legal request",
            "authority": "owner",
            "request_ref": "request_456",
            "redacted_at": "2026-08-09T23:50:00Z",
        },
        "provenance": {"method": "artifact_redaction_tombstone"},
    }


def test_redaction_event_preserves_optional_request_ref_default():
    event = build_redaction_event(
        tombstone={
            "artifact_id": "artifact_123",
            "reason": "policy",
            "authority": "owner",
            "redacted_at": "2026-08-09T23:50:00Z",
        },
        pack_id="pack_789",
        actor={"actor_type": "system", "actor_id": "redaction-fixture"},
        occurred_at="2026-08-09T23:51:00Z",
        recorded_at="2026-08-09T23:52:00Z",
        idempotency_key="redaction-2",
    )
    assert event["payload"]["request_ref"] is None
    assert event["payload"]["snapshot_ids"] == []
    assert event["subject_refs"] == ["artifact_123"]
