from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fossil_core.io import publish_immutable


class ProjectionLedger:
    """Local operational ledger for retryable projection work.

    Accepted knowledge remains in the durable event store. This ledger records
    whether a replaceable projection build materialized an event, why attempts
    failed, and whether already-materialized content was later purged for an
    exceptional redaction.

    A destructive rebuild must use a fresh ``build_id`` (or a separate root).
    Reusing applied markers from a destroyed graph would incorrectly skip events
    and can yield an empty rebuild.
    """

    def __init__(self, root: Path, projection_name: str, build_id: str | None = None):
        self.projection_name = projection_name
        self.build_id = build_id
        projection_root = Path(root) / projection_name
        self.root = (
            projection_root
            if build_id is None
            else projection_root / "builds" / build_id
        )
        self.applied_root = self.root / "applied"
        self.failure_root = self.root / "failures"
        self.redaction_root = self.root / "redactions"

    @staticmethod
    def _canonical(value: dict[str, Any]) -> bytes:
        return (
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            + "\n"
        ).encode("utf-8")

    def _applied_path(self, event_id: str) -> Path:
        suffix = event_id.removeprefix("evt_")
        return self.applied_root / suffix[:2] / f"{event_id}.json"

    def _redaction_path(self, event_id: str) -> Path:
        suffix = event_id.removeprefix("evt_")
        return self.redaction_root / suffix[:2] / f"{event_id}.json"

    def is_applied(self, event_id: str) -> bool:
        return self._applied_path(event_id).exists()

    def get_applied(self, event_id: str) -> dict[str, Any] | None:
        path = self._applied_path(event_id)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def iter_applied(self) -> list[dict[str, Any]]:
        return [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(self.applied_root.glob("*/*.json"))
        ]

    def record_applied(self, event_id: str, record: dict[str, Any]) -> dict[str, Any]:
        path = self._applied_path(event_id)
        payload = {"event_id": event_id, "status": "applied", **record}
        if self.build_id is not None:
            payload["projection_build_id"] = self.build_id
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
        if self.build_id is not None:
            payload["projection_build_id"] = self.build_id
        publish_immutable(path, self._canonical(payload))
        return path

    def is_redacted(self, event_id: str) -> bool:
        return self._redaction_path(event_id).exists()

    def get_redaction(self, event_id: str) -> dict[str, Any] | None:
        path = self._redaction_path(event_id)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def record_redaction(self, event_id: str, record: dict[str, Any]) -> dict[str, Any]:
        path = self._redaction_path(event_id)
        payload = {
            "event_id": event_id,
            "status": "redacted",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            **record,
        }
        if self.build_id is not None:
            payload["projection_build_id"] = self.build_id
        encoded = self._canonical(payload)
        if not publish_immutable(path, encoded):
            existing = json.loads(path.read_text(encoding="utf-8"))
            if self._canonical(existing) != encoded:
                # recorded_at is intentionally generated only on first write; a
                # subsequent idempotent purge returns the existing record.
                return existing
            return existing
        return payload
