from __future__ import annotations

from typing import Any, Protocol

from .cognitive_service import VersionedCognitiveService


class ContextProvider(VersionedCognitiveService, Protocol):
    def build_context(self, request: dict[str, Any]) -> dict[str, Any]: ...


__all__ = ["ContextProvider"]
