from __future__ import annotations

import json
from typing import Any, Iterable, Mapping

from .services import EmbeddingRetriever, ServiceMetadata


class SemanticEmbeddingRetriever(EmbeddingRetriever):
    """EmbeddingRetriever with full embedding-runtime provenance in benchmark metadata."""

    def __init__(
        self,
        documents: Iterable[Mapping[str, Any]],
        embedder: Any,
        *,
        version: str = "1",
    ) -> None:
        super().__init__(documents, embedder, version=version)

    def metadata(self) -> dict[str, Any]:
        embedder = dict(self.embedder.metadata())
        embedder_runtime = dict(embedder.get("runtime", {}))
        return ServiceMetadata(
            kind="retriever",
            provider=str(embedder.get("provider", "unknown")),
            provider_version=str(embedder.get("provider_version", "unknown")),
            implementation="semantic-in-memory-cosine",
            implementation_version=self.version,
            model_id=str(embedder.get("model_id")) if embedder.get("model_id") else None,
            local=bool(embedder.get("local", True)),
            estimated_cost_per_call_usd=float(
                embedder.get("estimated_cost_per_call_usd", 0.0)
            ),
            runtime={
                "embedding_implementation": str(embedder.get("implementation", "unknown")),
                "embedding_implementation_version": str(
                    embedder.get("implementation_version", "unknown")
                ),
                "embedding_runtime": json.dumps(
                    embedder_runtime,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            },
        ).as_dict()
