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


class Retriever(Protocol):
    def search(self, query: str, *, pack_ids: list[str], limit: int = 20) -> list[dict[str, Any]]: ...


class EmbeddingProvider(Protocol):
    @property
    def model_id(self) -> str: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class Reranker(Protocol):
    def rerank(self, query: str, candidates: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]: ...


class ContextProvider(Protocol):
    def build_context(self, request: dict[str, Any]) -> dict[str, Any]: ...


class ModelService(Protocol):
    def run(self, task: dict[str, Any]) -> dict[str, Any]: ...


class VerificationService(Protocol):
    def verify(self, proposal: dict[str, Any]) -> dict[str, Any]: ...
