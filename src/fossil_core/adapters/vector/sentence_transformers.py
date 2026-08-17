from __future__ import annotations

import copy
import importlib.metadata
from typing import Any

from ...services import ServiceMetadata


DEFAULT_BGE_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_BGE_REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
DEFAULT_CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L6-v2"
DEFAULT_CROSS_ENCODER_REVISION = "ce0834f22110de6d9222af7a7a03628121708969"


def _installed_version(package: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return "unavailable"


class OptionalRetrievalDependencyUnavailable(RuntimeError):
    """Raised when an explicitly requested real retrieval runtime is unavailable."""


class SentenceTransformerEmbeddingProvider:
    """Revision-pinned local sentence-transformer embedding provider.

    The model object can be injected for deterministic contract tests. Normal
    runtime construction imports Sentence Transformers lazily so the core
    package does not acquire a mandatory ML/runtime dependency.
    """

    def __init__(
        self,
        *,
        model_name: str = DEFAULT_BGE_MODEL,
        revision: str = DEFAULT_BGE_REVISION,
        device: str = "cpu",
        normalize_embeddings: bool = True,
        model: Any | None = None,
        provider_version: str | None = None,
        implementation_version: str = "1",
    ) -> None:
        if not model_name or not revision or not device:
            raise ValueError("semantic embedding provider requires model, revision, and device")
        self.model_name = model_name
        self.revision = revision
        self.device = device
        self.normalize_embeddings = bool(normalize_embeddings)
        self.implementation_version = implementation_version

        if provider_version is None:
            try:
                provider_version = importlib.metadata.version("sentence-transformers")
            except importlib.metadata.PackageNotFoundError:
                if model is None:
                    raise OptionalRetrievalDependencyUnavailable(
                        "Sentence Transformers is unavailable; install fossil-core[semantic] "
                        "or inject a compatible model object"
                    ) from None
                provider_version = "injected-runtime"
        self.provider_version = provider_version
        self.torch_version = _installed_version("torch")
        self.transformers_version = _installed_version("transformers")

        if model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise OptionalRetrievalDependencyUnavailable(
                    "Sentence Transformers is unavailable; install fossil-core[semantic]"
                ) from None
            model = SentenceTransformer(
                self.model_name,
                revision=self.revision,
                device=self.device,
            )
        self._model = model

    @property
    def model_id(self) -> str:
        return f"{self.model_name}@{self.revision}"

    def metadata(self) -> dict[str, Any]:
        return ServiceMetadata(
            kind="embedding",
            provider="sentence-transformers",
            provider_version=self.provider_version,
            implementation="sentence-transformer-encode",
            implementation_version=self.implementation_version,
            model_id=self.model_id,
            local=True,
            estimated_cost_per_call_usd=0.0,
            runtime={
                "device": self.device,
                "model_revision": self.revision,
                "normalize_embeddings": str(self.normalize_embeddings).lower(),
                "torch_version": self.torch_version,
                "transformers_version": self.transformers_version,
            },
        ).as_dict()

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._model.encode(
            list(texts),
            normalize_embeddings=self.normalize_embeddings,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return [[float(value) for value in vector] for vector in vectors]


class SentenceTransformerCrossEncoderReranker:
    """Revision-pinned local pairwise reranker behind the FOSSIL Reranker contract.

    Cross-encoder scores only reorder candidate documents. They never become
    durable truth, lifecycle state, citation authority, or commit authority.
    The model object can be injected so the normal contract suite remains
    independent of optional ML/runtime downloads.
    """

    def __init__(
        self,
        *,
        model_name: str = DEFAULT_CROSS_ENCODER_MODEL,
        revision: str = DEFAULT_CROSS_ENCODER_REVISION,
        device: str = "cpu",
        batch_size: int = 32,
        max_length: int | None = None,
        model: Any | None = None,
        provider_version: str | None = None,
        implementation_version: str = "1",
    ) -> None:
        if not model_name or not revision or not device:
            raise ValueError("cross-encoder reranker requires model, revision, and device")
        if batch_size < 1:
            raise ValueError("cross-encoder batch size must be positive")
        if max_length is not None and max_length < 1:
            raise ValueError("cross-encoder max_length must be positive when set")
        self.model_name = model_name
        self.revision = revision
        self.device = device
        self.batch_size = int(batch_size)
        self.max_length = int(max_length) if max_length is not None else None
        self.implementation_version = implementation_version

        if provider_version is None:
            try:
                provider_version = importlib.metadata.version("sentence-transformers")
            except importlib.metadata.PackageNotFoundError:
                if model is None:
                    raise OptionalRetrievalDependencyUnavailable(
                        "Sentence Transformers is unavailable; install fossil-core[semantic] "
                        "or inject a compatible cross-encoder model object"
                    ) from None
                provider_version = "injected-runtime"
        self.provider_version = provider_version
        self.torch_version = _installed_version("torch")
        self.transformers_version = _installed_version("transformers")

        if model is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError:
                raise OptionalRetrievalDependencyUnavailable(
                    "Sentence Transformers is unavailable; install fossil-core[semantic]"
                ) from None
            kwargs: dict[str, Any] = {
                "revision": self.revision,
                "device": self.device,
            }
            if self.max_length is not None:
                kwargs["max_length"] = self.max_length
            model = CrossEncoder(self.model_name, **kwargs)
        self._model = model

    @property
    def model_id(self) -> str:
        return f"{self.model_name}@{self.revision}"

    def metadata(self) -> dict[str, Any]:
        return ServiceMetadata(
            kind="reranker",
            provider="sentence-transformers",
            provider_version=self.provider_version,
            implementation="cross-encoder-pairwise-reranker",
            implementation_version=self.implementation_version,
            model_id=self.model_id,
            local=True,
            estimated_cost_per_call_usd=0.0,
            runtime={
                "batch_size": str(self.batch_size),
                "device": self.device,
                "max_length": str(self.max_length) if self.max_length is not None else "model-default",
                "model_revision": self.revision,
                "score_authority": "candidate-ordering-only",
                "torch_version": self.torch_version,
                "transformers_version": self.transformers_version,
            },
        ).as_dict()

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        if not candidates:
            return []
        pairs = [(str(query), str(candidate.get("text", ""))) for candidate in candidates]
        raw_scores = self._model.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        scores = [float(value) for value in raw_scores]
        if len(scores) != len(candidates):
            raise ValueError("cross-encoder returned a score count that does not match candidates")

        service = self.metadata()
        scored: list[tuple[float, int, str, dict[str, Any]]] = []
        for fallback_rank, (candidate, score) in enumerate(zip(candidates, scores, strict=True), start=1):
            retrieval = dict(candidate.get("retrieval", {}))
            base_rank = int(retrieval.get("rank", fallback_rank))
            result = copy.deepcopy(candidate)
            result["rerank"] = {
                "base_rank": base_rank,
                "score": score,
                "service": service,
            }
            scored.append((score, base_rank, str(candidate.get("id", "")), result))
        scored.sort(key=lambda item: (-item[0], item[1], item[2]))
        return [item[3] for item in scored[:limit]]
