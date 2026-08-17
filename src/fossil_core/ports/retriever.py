from __future__ import annotations

from typing import Any, Protocol

from .cognitive_service import VersionedCognitiveService


class Retriever(VersionedCognitiveService, Protocol):
    def search(
        self,
        query: str,
        *,
        pack_ids: list[str],
        limit: int = 20,
    ) -> list[dict[str, Any]]: ...


__all__ = ["Retriever"]
