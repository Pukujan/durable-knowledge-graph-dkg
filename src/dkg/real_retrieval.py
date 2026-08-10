from __future__ import annotations

import copy
import importlib.metadata
import json
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from .services import ServiceMetadata, tokenize


DEFAULT_BGE_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_BGE_REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"


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


class ReciprocalRankFusionRetriever:
    """Fuse materially different retrievers without changing document identity."""

    def __init__(
        self,
        retrievers: Sequence[Any],
        *,
        weights: Sequence[float] | None = None,
        rrf_k: int = 60,
        candidate_multiplier: int = 4,
        version: str = "1",
    ) -> None:
        self.retrievers = list(retrievers)
        if len(self.retrievers) < 2:
            raise ValueError("RRF hybrid requires at least two retrievers")
        if rrf_k < 1 or candidate_multiplier < 1:
            raise ValueError("RRF k and candidate multiplier must be positive")
        self.rrf_k = int(rrf_k)
        self.candidate_multiplier = int(candidate_multiplier)
        self.version = version
        self.weights = list(weights or [1.0] * len(self.retrievers))
        if len(self.weights) != len(self.retrievers) or any(weight <= 0 for weight in self.weights):
            raise ValueError("RRF weights must be positive and match retriever count")

    def _component_metadata(self) -> list[dict[str, Any]]:
        return [dict(retriever.metadata()) for retriever in self.retrievers]

    def metadata(self) -> dict[str, Any]:
        components = self._component_metadata()
        model_ids = sorted(
            {
                str(component["model_id"])
                for component in components
                if component.get("model_id")
            }
        )
        return ServiceMetadata(
            kind="retriever",
            provider="fossil",
            provider_version="1",
            implementation="reciprocal-rank-fusion",
            implementation_version=self.version,
            model_id="+".join(model_ids) if model_ids else None,
            local=all(bool(component.get("local", True)) for component in components),
            estimated_cost_per_call_usd=sum(
                float(component.get("estimated_cost_per_call_usd", 0.0))
                for component in components
            ),
            runtime={
                "candidate_multiplier": str(self.candidate_multiplier),
                "components": json.dumps(
                    [
                        {
                            "implementation": component.get("implementation"),
                            "model_id": component.get("model_id"),
                            "provider": component.get("provider"),
                        }
                        for component in components
                    ],
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                "rrf_k": str(self.rrf_k),
                "weights": json.dumps(self.weights, separators=(",", ":")),
            },
        ).as_dict()

    def search(
        self,
        query: str,
        *,
        pack_ids: list[str],
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        pool_limit = max(limit, limit * self.candidate_multiplier)
        fused_scores: dict[str, float] = {}
        documents: dict[str, dict[str, Any]] = {}
        component_ranks: dict[str, list[dict[str, Any]]] = {}

        for index, (retriever, weight) in enumerate(zip(self.retrievers, self.weights, strict=True)):
            metadata = dict(retriever.metadata())
            component_name = f"{index}:{metadata.get('implementation', 'retriever')}"
            results = retriever.search(query, pack_ids=pack_ids, limit=pool_limit)
            for fallback_rank, candidate in enumerate(results, start=1):
                identifier = str(candidate["id"])
                retrieval = dict(candidate.get("retrieval", {}))
                rank = int(retrieval.get("rank", fallback_rank))
                fused_scores[identifier] = fused_scores.get(identifier, 0.0) + (
                    float(weight) / (self.rrf_k + rank)
                )
                documents.setdefault(identifier, copy.deepcopy(dict(candidate)))
                component_ranks.setdefault(identifier, []).append(
                    {
                        "component": component_name,
                        "rank": rank,
                        "score": retrieval.get("score"),
                    }
                )

        ordered = sorted(fused_scores, key=lambda identifier: (-fused_scores[identifier], identifier))
        service = self.metadata()
        results: list[dict[str, Any]] = []
        for rank, identifier in enumerate(ordered[:limit], start=1):
            result = copy.deepcopy(documents[identifier])
            if "retrieval" in result:
                result["component_retrieval"] = result["retrieval"]
            result["retrieval"] = {
                "score": fused_scores[identifier],
                "rank": rank,
                "service": service,
                "components": sorted(component_ranks[identifier], key=lambda item: item["component"]),
            }
            results.append(result)
        return results


class LifecycleIntentReranker:
    """Use durable lifecycle metadata to distinguish current from historical intent."""

    CURRENT_CUES = frozenset(
        {
            "accepted",
            "active",
            "after",
            "current",
            "currently",
            "latest",
            "now",
            "present",
            "today",
        }
    )
    HISTORICAL_CUES = frozenset(
        {
            "before",
            "earlier",
            "former",
            "historical",
            "history",
            "old",
            "past",
            "previous",
            "rejected",
            "stale",
            "superseded",
        }
    )
    CURRENT_STATES = frozenset({"supported", "open", "active"})
    HISTORICAL_STATES = frozenset({"superseded", "rejected", "retracted", "invalidated"})
    STALE_STATES = frozenset({"stale_pending_review", "disputed"})

    def __init__(self, *, version: str = "1") -> None:
        self.version = version

    def metadata(self) -> dict[str, Any]:
        return ServiceMetadata(
            kind="reranker",
            provider="fossil",
            provider_version="1",
            implementation="lifecycle-intent-reranker",
            implementation_version=self.version,
            local=True,
            estimated_cost_per_call_usd=0.0,
            runtime={"policy": "query-intent+durable-current-state"},
        ).as_dict()

    @classmethod
    def intent_for_query(cls, query: str) -> str:
        terms = set(tokenize(query))
        current = bool(terms & cls.CURRENT_CUES)
        historical = bool(terms & cls.HISTORICAL_CUES)
        if current and historical:
            return "mixed"
        if current:
            return "current"
        if historical:
            return "historical"
        return "neutral"

    @classmethod
    def _lifecycle_adjustment(cls, intent: str, state: str | None) -> float:
        if not state:
            return 0.0
        if intent == "current":
            if state in cls.CURRENT_STATES:
                return 1.25
            if state in cls.HISTORICAL_STATES or state in cls.STALE_STATES:
                return -1.0
        elif intent == "historical":
            if state in cls.HISTORICAL_STATES:
                return 1.25
            if state in cls.STALE_STATES:
                return 0.9
            if state in cls.CURRENT_STATES:
                return 0.0
        elif intent == "mixed":
            if state in cls.CURRENT_STATES or state in cls.HISTORICAL_STATES:
                return 0.55
            if state in cls.STALE_STATES:
                return 0.2
        return 0.0

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        intent = self.intent_for_query(query)
        scored: list[tuple[float, str, dict[str, Any]]] = []
        for fallback_rank, candidate in enumerate(candidates, start=1):
            retrieval = dict(candidate.get("retrieval", {}))
            base_rank = int(retrieval.get("rank", fallback_rank))
            base_score = 1.0 / max(base_rank, 1)
            state_value = candidate.get("current_state")
            state = str(state_value) if state_value is not None else None
            lifecycle_adjustment = self._lifecycle_adjustment(intent, state)
            score = base_score + lifecycle_adjustment
            result = copy.deepcopy(candidate)
            result["rerank"] = {
                "base_rank": base_rank,
                "intent": intent,
                "lifecycle_adjustment": lifecycle_adjustment,
                "score": score,
                "state": state,
                "service": self.metadata(),
            }
            scored.append((score, str(candidate.get("id", "")), result))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [item[2] for item in scored[:limit]]


class RerankedRetriever:
    """Expose a Retriever contract over a candidate retriever + Reranker."""

    def __init__(
        self,
        retriever: Any,
        reranker: Any,
        *,
        candidate_multiplier: int = 4,
        version: str = "1",
    ) -> None:
        if candidate_multiplier < 1:
            raise ValueError("candidate multiplier must be positive")
        self.retriever = retriever
        self.reranker = reranker
        self.candidate_multiplier = int(candidate_multiplier)
        self.version = version

    def metadata(self) -> dict[str, Any]:
        base = dict(self.retriever.metadata())
        reranker = dict(self.reranker.metadata())
        return ServiceMetadata(
            kind="retriever",
            provider="fossil",
            provider_version="1",
            implementation="reranked-retriever",
            implementation_version=self.version,
            model_id=str(base.get("model_id")) if base.get("model_id") else None,
            local=bool(base.get("local", True)) and bool(reranker.get("local", True)),
            estimated_cost_per_call_usd=float(base.get("estimated_cost_per_call_usd", 0.0))
            + float(reranker.get("estimated_cost_per_call_usd", 0.0)),
            runtime={
                "base_implementation": str(base.get("implementation")),
                "candidate_multiplier": str(self.candidate_multiplier),
                "reranker": str(reranker.get("implementation")),
            },
        ).as_dict()

    def search(
        self,
        query: str,
        *,
        pack_ids: list[str],
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        candidates = self.retriever.search(
            query,
            pack_ids=pack_ids,
            limit=max(limit, limit * self.candidate_multiplier),
        )
        reranked = self.reranker.rerank(query, candidates, limit=limit)
        service = self.metadata()
        results: list[dict[str, Any]] = []
        for rank, candidate in enumerate(reranked, start=1):
            result = copy.deepcopy(candidate)
            if "retrieval" in result:
                result["base_retrieval"] = result["retrieval"]
            rerank = dict(result.get("rerank", {}))
            result["retrieval"] = {
                "score": float(rerank.get("score", 0.0)),
                "rank": rank,
                "service": service,
            }
            results.append(result)
        return results
