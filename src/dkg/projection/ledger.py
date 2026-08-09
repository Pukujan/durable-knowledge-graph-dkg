from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dkg.io import publish_immutable


class ProjectionLedger:
    """Local operational ledger for retryable projection work.

    Accepted knowledge remains in the durable event store. This ledger records
    only whether a replaceable projection has materialized an event and why a
    prior attempt failed.
    """

    def __init__(self, root: Path, projection_name: str):
        self.root = Path(root) / projection_name
        self.applied_root = self.root / "applied"
        self.failure_root = self.root / "failures"

    @staticmethod
    def _canonical(value: dict[str, Any]) -> bytes:
        return (
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            + "\n"
        ).encode("utf-8")

    def _applied_path(self, event_id: str) -> Path:
        suffix = event_id.removeprefix("evt_")
        return self.applied_root / suffix[:2] / f"{event_id}.json"

    def is_applied(self, event_id: str) -> bool:
        return self._applied_path(event_id).exists()

    def get_applied(self, event_id: str) -> dict[str, Any] | None:
        path = self._applied_path(event_id)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def record_applied(self, event_id: str, record: dict[str, Any]) -> dict[str, Any]:
        path = self._applied_path(event_id)
        payload = {"event_id": event_id, "status": "applied", **record}
        data = self._canonical(payload)
        if not publish_immutable(path, data):
            return json.loads(path.read_text(encoding="utf-8"))
        return payload

    def record_failure(self, event_id: str, record: dict[str, Any]) -> Path:
        attempt = uuid.uuid4().hex
        path = self.failure_root / event_id / f"{attempt}.json"
        payload = {
            "event_id": event_id,
            "status": "failed",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            **record,
        }
        publish_immutable(path, self._canonical(payload))
        return path
