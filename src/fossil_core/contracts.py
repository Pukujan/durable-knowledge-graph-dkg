from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .ports.cognitive_service import VersionedCognitiveService
from .ports.context_provider import ContextProvider
from .ports.embedding_provider import EmbeddingProvider
from .ports.projection import ProjectionAdapter, ProjectionReceipt
from .ports.retriever import Retriever


class Reranker(VersionedCognitiveService, Protocol):
    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        *,
        limit: int,
    ) -> list[dict[str, Any]]: ...


class ModelService(VersionedCognitiveService, Protocol):
    def run(self, task: dict[str, Any]) -> dict[str, Any]: ...


class VerificationService(VersionedCognitiveService, Protocol):
    def verify(self, proposal: dict[str, Any]) -> dict[str, Any]: ...
