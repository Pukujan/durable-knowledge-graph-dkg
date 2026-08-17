from __future__ import annotations

from typing import Any, Protocol

from .cognitive_service import VersionedCognitiveService


class ModelService(VersionedCognitiveService, Protocol):
    def run(self, task: dict[str, Any]) -> dict[str, Any]: ...


__all__ = ["ModelService"]
