from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dkg.contracts import ProjectionReceipt


class NullProjection:
    """Test projection proving the durable layer can operate without a graph DB."""

    name = "null"
    version = "1"

    def apply_event(self, event: dict[str, Any]) -> ProjectionReceipt:
        return ProjectionReceipt(self.name, self.version, event["event_id"], "applied")

    def rebuild(self, *, events_root: Path) -> list[ProjectionReceipt]:
        receipts: list[ProjectionReceipt] = []
        for path in sorted(Path(events_root).glob("*/*.json")):
            event = json.loads(path.read_text(encoding="utf-8"))
            receipts.append(self.apply_event(event))
        return receipts

    def health(self) -> dict[str, Any]:
        return {"projection": self.name, "version": self.version, "status": "ok"}
