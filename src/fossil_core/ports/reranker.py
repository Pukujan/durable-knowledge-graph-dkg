from __future__ import annotations

from typing import Any, Protocol

from .cognitive_service import VersionedCognitiveService


class Reranker(VersionedCognitiveService, Protocol):
    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        *,
        limit: int,
    ) -> list[dict[str, Any]]: ...


__all__ = ["Reranker"]
