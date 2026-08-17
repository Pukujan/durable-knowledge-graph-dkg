from __future__ import annotations

from typing import Any, Protocol

from .cognitive_service import VersionedCognitiveService


class VerificationService(VersionedCognitiveService, Protocol):
    def verify(self, proposal: dict[str, Any]) -> dict[str, Any]: ...


__all__ = ["VerificationService"]
