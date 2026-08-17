from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .ports.cognitive_service import VersionedCognitiveService
from .ports.projection import ProjectionAdapter, ProjectionReceipt


class Retriever(VersionedCognitiveService, Protocol):
    def search(
        self,
        query: str,
        *,
        pack_ids: list[str],
        limit: int = 20,
    ) -> list[dict[str, Any]]: ...


class EmbeddingProvider(VersionedCognitiveService, Protocol):
    @property
    def model_id(self) -> str: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class Reranker(VersionedCognitiveService, Protocol):
    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        *,
        limit: int,
    ) -> list[dict[str, Any]]: ...


class ContextProvider(VersionedCognitiveService, Protocol):
    def build_context(self, request: dict[str, Any]) -> dict[str, Any]: ...


class ModelService(VersionedCognitiveService, Protocol):
    def run(self, task: dict[str, Any]) -> dict[str, Any]: ...


class VerificationService(VersionedCognitiveService, Protocol):
    def verify(self, proposal: dict[str, Any]) -> dict[str, Any]: ...
