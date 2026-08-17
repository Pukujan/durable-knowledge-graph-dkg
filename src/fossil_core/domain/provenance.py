from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class SourceStatus:
    snapshot_id: str
    state: str
    reason: str | None
    last_event_id: str


class SourceLifecycleState:
    """Replay explicit source staleness/retraction/restoration events."""

    VALID = {"source.stale", "source.retracted", "source.restored"}

    def __init__(self) -> None:
        self.statuses: dict[str, SourceStatus] = {}

    @classmethod
    def replay(cls, events: Iterable[Mapping[str, Any]]) -> "SourceLifecycleState":
        state = cls()
        for event in sorted(
            (event for event in events if event.get("event_type") in cls.VALID),
            key=lambda event: (str(event["recorded_at"]), str(event["event_id"])),
        ):
            snapshot_id = str(event["payload"]["snapshot_id"])
            event_type = str(event["event_type"])
            new_state = {
                "source.stale": "stale",
                "source.retracted": "retracted",
                "source.restored": "active",
            }[event_type]
            state.statuses[snapshot_id] = SourceStatus(
                snapshot_id=snapshot_id,
                state=new_state,
                reason=event["payload"].get("reason"),
                last_event_id=str(event["event_id"]),
            )
        return state

    def status(self, snapshot_id: str) -> str:
        return self.statuses.get(
            snapshot_id, SourceStatus(snapshot_id, "active", None, "")
        ).state


def build_source_state_event(
    *,
    event_type: str,
    snapshot_id: str,
    source_id: str,
    pack_id: str,
    actor: Mapping[str, Any],
    occurred_at: str,
    recorded_at: str,
    idempotency_key: str,
    reason: str,
) -> dict[str, Any]:
    if event_type not in SourceLifecycleState.VALID:
        raise ValueError(f"unsupported source lifecycle event: {event_type}")
    return {
        "schema_version": "dkg.event.v1",
        "event_type": event_type,
        "occurred_at": occurred_at,
        "recorded_at": recorded_at,
        "pack_id": pack_id,
        "actor": dict(actor),
        "subject_refs": [snapshot_id, source_id],
        "idempotency_key": idempotency_key,
        "source_snapshot_refs": [snapshot_id],
        "payload": {
            "snapshot_id": snapshot_id,
            "source_id": source_id,
            "reason": reason,
        },
        "provenance": {"method": "source_lifecycle"},
    }


__all__ = ["SourceStatus", "SourceLifecycleState", "build_source_state_event"]
