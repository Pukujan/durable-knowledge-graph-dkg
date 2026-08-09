from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .ids import deterministic_event_id, new_id


class IdempotencyConflict(RuntimeError):
    pass


class DurableEventStore:
    """Filesystem-first immutable event store.

    One accepted event is one immutable JSON file. JSONL is reserved for
    import/export, avoiding one shared append hotspot for concurrent agents.
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

    def commit(self, event: dict[str, Any]) -> dict[str, Any]:
        candidate = copy.deepcopy(event)
        pack_id = candidate.get("pack_id")
        idem = candidate.get("idempotency_key")

        if not candidate.get("event_id"):
            candidate["event_id"] = (
                deterministic_event_id(pack_id, idem)
                if pack_id and idem
                else new_id("evt")
            )

        self.validator.validate(candidate)
        path = self._event_path(candidate["event_id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self._canonical(candidate)

        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if self._canonical(existing) == data:
                return existing
            raise IdempotencyConflict(
                f"event {candidate['event_id']} already exists with different content"
            )

        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            try:
                path.unlink(missing_ok=True)
            finally:
                raise

        return candidate

    def get(self, event_id: str) -> dict[str, Any]:
        return json.loads(self._event_path(event_id).read_text(encoding="utf-8"))

    def iter_events(self):
        for path in sorted(self.root.glob("*/*.json")):
            yield json.loads(path.read_text(encoding="utf-8"))
