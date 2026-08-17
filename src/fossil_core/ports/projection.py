from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class ProjectionReceipt:
    projection: str
    projection_version: str
    event_id: str
    status: str
    detail: str | None = None


class ProjectionAdapter(Protocol):
    """Replaceable materialized view of durable knowledge."""

    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    def apply_event(self, event: dict[str, Any]) -> ProjectionReceipt: ...

    def rebuild(self, *, events_root: Path) -> list[ProjectionReceipt]: ...

    def health(self) -> dict[str, Any]: ...


__all__ = ["ProjectionReceipt", "ProjectionAdapter"]
