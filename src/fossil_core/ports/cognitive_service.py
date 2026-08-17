from __future__ import annotations

from typing import Any, Protocol


class VersionedCognitiveService(Protocol):
    """Every replaceable cognitive service must expose durable provenance metadata."""

    def metadata(self) -> dict[str, Any]: ...


__all__ = ["VersionedCognitiveService"]
