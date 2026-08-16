from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Iterator

from jsonschema import Draft202012Validator, FormatChecker

from ...ids import deterministic_event_id, new_id
from ...io import publish_immutable


class IdempotencyConflict(RuntimeError):
    pass


class EventRedactedError(FileNotFoundError):
    pass


class EventRedactionConflict(RuntimeError):
    pass


class DurableEventStore:
    """Immutable filesystem event store with an exceptional redaction path.

    Normal accepted knowledge is append-only. Privacy/legal erasure is separate:
    a minimal immutable tombstone is published before the event bytes are removed.
    The stable event ID and canonical hash survive for audit, but sensitive payload,
    subjects, evidence refs, and provenance are not copied into the tombstone.
    """

    def __init__(self, root: Path, schema_path: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.redactions = self.root / "_redactions"
        self.redactions.mkdir(parents=True, exist_ok=True)
        schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(schema, format_checker=FormatChecker())

    def _event_path(self, event_id: str) -> Path:
        suffix = event_id.removeprefix("evt_")
        return self.root / suffix[:2] / f"{event_id}.json"

    def _redaction_path(self, event_id: str) -> Path:
        suffix = event_id.removeprefix("evt_")
        return self.redactions / suffix[:2] / f"{event_id}.json"

    @staticmethod
    def _canonical(event: dict[str, Any]) -> bytes:
        return (
            json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            + "\n"
        ).encode("utf-8")

    def prepare(self, event: dict[str, Any]) -> dict[str, Any]:
        """Assign durable identity and validate without publishing anything."""

        candidate = copy.deepcopy(event)
        pack_id = candidate.get("pack_id")
        idem = candidate.get("idempotency_key")

        if pack_id and idem:
            expected = deterministic_event_id(pack_id, idem)
            supplied = candidate.get("event_id")
            if supplied and supplied != expected:
                raise IdempotencyConflict(
                    "event_id does not match deterministic idempotency identity"
                )
            candidate["event_id"] = expected
        elif not candidate.get("event_id"):
            candidate["event_id"] = new_id("evt")

        self.validator.validate(candidate)
        return candidate

    def validate(self, event: dict[str, Any]) -> dict[str, Any]:
        """Public non-mutating validation path used by agent/API boundaries."""

        return self.prepare(event)

    def is_redacted(self, event_id: str) -> bool:
        return self._redaction_path(event_id).exists()

    def get_redaction(self, event_id: str) -> dict[str, Any] | None:
        path = self._redaction_path(event_id)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def iter_redactions(self) -> Iterator[dict[str, Any]]:
        """Iterate minimal event-erasure tombstones without exposing deleted payloads."""

        for path in sorted(self.redactions.glob("*/*.json")):
            yield json.loads(path.read_text(encoding="utf-8"))

    def commit(self, event: dict[str, Any]) -> dict[str, Any]:
        candidate = self.prepare(event)
        event_id = candidate["event_id"]
        if self.is_redacted(event_id):
            raise EventRedactedError(
                f"event {event_id} was redacted and cannot be republished under the same identity"
            )
        path = self._event_path(event_id)
        data = self._canonical(candidate)

        if publish_immutable(path, data):
            return candidate

        existing = json.loads(path.read_text(encoding="utf-8"))
        if self._canonical(existing) == data:
            return existing
        raise IdempotencyConflict(
            f"event {candidate['event_id']} already exists with different content"
        )

    def get(self, event_id: str) -> dict[str, Any]:
        if self.is_redacted(event_id):
            raise EventRedactedError(f"event {event_id} has been redacted")
        return json.loads(self._event_path(event_id).read_text(encoding="utf-8"))

    def redact(
        self,
        event_id: str,
        *,
        reason: str,
        authority: str,
        redacted_at: str,
        request_ref: str | None = None,
    ) -> dict[str, Any]:
        """Publish a minimal audit tombstone before physically deleting event bytes."""

        if not reason or not authority or not redacted_at:
            raise ValueError("event redaction requires reason, authority, and redacted_at")

        tombstone_path = self._redaction_path(event_id)
        if tombstone_path.exists():
            existing = json.loads(tombstone_path.read_text(encoding="utf-8"))
            requested = {
                "reason": reason,
                "authority": authority,
                "redacted_at": redacted_at,
                "request_ref": request_ref,
            }
            if any(existing.get(key) != value for key, value in requested.items()):
                raise EventRedactionConflict(
                    f"event {event_id} already has a different redaction tombstone"
                )
            return existing

        event_path = self._event_path(event_id)
        event = json.loads(event_path.read_text(encoding="utf-8"))
        canonical = self._canonical(event)
        tombstone = {
            "event_id": event_id,
            "pack_id": event["pack_id"],
            "event_type": event["event_type"],
            "recorded_at": event["recorded_at"],
            "canonical_hash": {
                "algorithm": "sha256",
                "digest": hashlib.sha256(canonical).hexdigest(),
            },
            "redacted_at": redacted_at,
            "reason": reason,
            "authority": authority,
            "request_ref": request_ref,
        }
        if not publish_immutable(tombstone_path, self._canonical(tombstone)):
            raise EventRedactionConflict(
                f"could not publish event redaction tombstone for {event_id}"
            )
        try:
            event_path.unlink()
        except FileNotFoundError:
            pass
        return tombstone

    def iter_events(self) -> Iterator[dict[str, Any]]:
        for path in sorted(self.root.glob("*/*.json")):
            yield json.loads(path.read_text(encoding="utf-8"))
