from __future__ import annotations

from typing import Protocol

from .cognitive_service import VersionedCognitiveService


class EmbeddingProvider(VersionedCognitiveService, Protocol):
    @property
    def model_id(self) -> str: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...


__all__ = ["EmbeddingProvider"]
