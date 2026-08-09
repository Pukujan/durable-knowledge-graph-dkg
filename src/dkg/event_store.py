from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Iterator

from jsonschema import Draft202012Validator, FormatChecker

from .ids import deterministic_event_id, new_id
from .io import publish_immutable


class IdempotencyConflict(RuntimeError):
    pass


class DurableEventStore:
    """Immutable filesystem event store with atomic publication.

    Accepted knowledge history is durable without requiring a graph database.
    One event is one JSON file; JSONL is reserved for import/export.
    """

    def __init__(self, root: Path, schema_path: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(schema, format_checker=FormatChecker())

    def _event_path(self, event_id: str) -> Path:
        suffix = event_id.removeprefix("evt_")
        return self.root / suffix[:2] / f"{event_id}.json"

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

    def commit(self, event: dict[str, Any]) -> dict[str, Any]:
        candidate = self.prepare(event)
        path = self._event_path(candidate["event_id"])
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
        return json.loads(self._event_path(event_id).read_text(encoding="utf-8"))

    def iter_events(self) -> Iterator[dict[str, Any]]:
        for path in sorted(self.root.glob("*/*.json")):
            yield json.loads(path.read_text(encoding="utf-8"))
