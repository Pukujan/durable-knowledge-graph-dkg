from __future__ import annotations

from typing import Any, Iterable, Mapping


def build_redaction_event(
    *,
    tombstone: Mapping[str, Any],
    pack_id: str,
    actor: Mapping[str, Any],
    occurred_at: str,
    recorded_at: str,
    idempotency_key: str,
    snapshot_ids: Iterable[str] = (),
) -> dict[str, Any]:
    return {
        "schema_version": "dkg.event.v1",
        "event_type": "evidence.redacted",
        "occurred_at": occurred_at,
        "recorded_at": recorded_at,
        "pack_id": pack_id,
        "actor": dict(actor),
        "subject_refs": [str(tombstone["artifact_id"]), *list(snapshot_ids)],
        "idempotency_key": idempotency_key,
        "payload": {
            "artifact_id": tombstone["artifact_id"],
            "snapshot_ids": list(snapshot_ids),
            "reason": tombstone["reason"],
            "authority": tombstone["authority"],
            "request_ref": tombstone.get("request_ref"),
            "redacted_at": tombstone["redacted_at"],
        },
        "provenance": {"method": "artifact_redaction_tombstone"},
    }


__all__ = ["build_redaction_event"]
