from __future__ import annotations

import importlib.metadata
import json

import pytest

from dkg.real_retrieval import (
    DEFAULT_BGE_MODEL,
    DEFAULT_BGE_REVISION,
    LifecycleIntentReranker,
    OptionalRetrievalDependencyUnavailable,
    ReciprocalRankFusionRetriever,
    RerankedRetriever,
    SentenceTransformerEmbeddingProvider,
)
from dkg.semantic_retriever import SemanticEmbeddingRetriever


PACK = "pack_f024177f89a5442db84171c3dd7f58e5"
OTHER_PACK = "pack_269099f7b2ba43b7a99b9427d64092de"


class FakeEncoder:
    def __init__(self) -> None:
        self.calls = []

    def encode(self, texts, **kwargs):
        self.calls.append((list(texts), dict(kwargs)))
        return [[float(index + 1), 0.5] for index, _ in enumerate(texts)]


class FakeRetriever:
    def __init__(self, name: str, results: list[dict], *, model_id: str | None = None):
        self.name = name
        self.results = results
        self.model_id = model_id
        self.requested_limits: list[int] = []

    def metadata(self):
        return {
            "kind": "retriever",
            "provider": "test",
            "provider_version": "1",
            "implementation": self.name,
            "implementation_version": "1",
            "model_id": self.model_id,
            "local": True,
            "estimated_cost_per_call_usd": 0.0,
            "runtime": {},
        }

    def search(self, query: str, *, pack_ids: list[str], limit: int = 20):
        self.requested_limits.append(limit)
        allowed = set(pack_ids)
        selected = [item for item in self.results if item["pack_id"] in allowed]
        output = []
        for fallback_rank, item in enumerate(selected[:limit], start=1):
            result = dict(item)
            result["retrieval"] = {
                "rank": int(item.get("rank", fallback_rank)),
                "score": float(item.get("score", 1.0 / fallback_rank)),
                "service": self.metadata(),
            }
            output.append(result)
        return output


def doc(identifier: str, *, rank: int, state: str = "supported", pack_id: str = PACK):
    return {
        "id": identifier,
        "pack_id": pack_id,
        "text": identifier.replace("_", " "),
        "current_state": state,
        "rank": rank,
    }


def test_sentence_transformer_provider_preserves_exact_runtime_identity_and_encode_options():
    encoder = FakeEncoder()
    provider = SentenceTransformerEmbeddingProvider(
        model=encoder,
        provider_version="5.2.2",
        device="cpu",
    )

    vectors = provider.embed(["alpha", "beta"])
    metadata = provider.metadata()

    assert vectors == [[1.0, 0.5], [2.0, 0.5]]
    assert provider.model_id == f"{DEFAULT_BGE_MODEL}@{DEFAULT_BGE_REVISION}"
    assert metadata["provider"] == "sentence-transformers"
    assert metadata["provider_version"] == "5.2.2"
    assert metadata["model_id"] == provider.model_id
    assert metadata["runtime"]["model_revision"] == DEFAULT_BGE_REVISION
    assert encoder.calls == [
        (
            ["alpha", "beta"],
            {
                "normalize_embeddings": True,
                "convert_to_numpy": True,
                "show_progress_bar": False,
            },
        )
    ]


def test_semantic_retriever_carries_embedding_provider_and_runtime_into_benchmark_metadata():
    provider = SentenceTransformerEmbeddingProvider(
        model=FakeEncoder(),
        provider_version="5.2.2",
        device="cpu",
    )
    retriever = SemanticEmbeddingRetriever(
        [{"id": "doc_a", "pack_id": PACK, "text": "alpha"}],
        provider,
        version="gate2",
    )

    metadata = retriever.metadata()
    runtime = json.loads(metadata["runtime"]["embedding_runtime"])

    assert metadata["provider"] == "sentence-transformers"
    assert metadata["provider_version"] == "5.2.2"
    assert metadata["implementation"] == "semantic-in-memory-cosine"
    assert metadata["model_id"] == f"{DEFAULT_BGE_MODEL}@{DEFAULT_BGE_REVISION}"
    assert runtime["model_revision"] == DEFAULT_BGE_REVISION
    assert runtime["device"] == "cpu"


def test_sentence_transformer_provider_fails_cleanly_when_optional_runtime_is_unavailable(monkeypatch):
    def missing(_name: str):
        raise importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(importlib.metadata, "version", missing)
    with pytest.raises(OptionalRetrievalDependencyUnavailable, match=r"fossil-core\[semantic\]"):
        SentenceTransformerEmbeddingProvider(model=None)


def test_rrf_fuses_distinct_retrievers_and_preserves_pack_filtering():
    lexical = FakeRetriever(
        "lexical",
        [
            doc("alpha", rank=1),
            doc("beta", rank=2),
            doc("other", rank=1, pack_id=OTHER_PACK),
        ],
    )
    semantic = FakeRetriever(
        "semantic",
        [doc("beta", rank=1), doc("gamma", rank=2)],
        model_id="semantic-model@revision",
    )
    hybrid = ReciprocalRankFusionRetriever(
        [lexical, semantic],
        rrf_k=60,
        candidate_multiplier=3,
        version="gate2",
    )

    results = hybrid.search("query", pack_ids=[PACK], limit=3)

    assert [item["id"] for item in results] == ["beta", "alpha", "gamma"]
    assert all(item["pack_id"] == PACK for item in results)
    assert lexical.requested_limits == [9]
    assert semantic.requested_limits == [9]
    assert results[0]["retrieval"]["service"]["implementation"] == "reciprocal-rank-fusion"
    assert results[0]["retrieval"]["service"]["model_id"] == "semantic-model@revision"
    assert len(results[0]["retrieval"]["components"]) == 2


def test_lifecycle_reranker_promotes_supported_current_state_over_stale_and_rejected_history():
    reranker = LifecycleIntentReranker()
    candidates = [
        {**doc("stale_sqlite", rank=1, state="stale_pending_review"), "retrieval": {"rank": 1}},
        {**doc("rejected_graph", rank=2, state="rejected"), "retrieval": {"rank": 2}},
        {**doc("current_architecture", rank=5, state="supported"), "retrieval": {"rank": 5}},
    ]

    reranked = reranker.rerank(
        "What is the current accepted architecture after reconsideration?",
        candidates,
        limit=3,
    )

    assert [item["id"] for item in reranked][0] == "current_architecture"
    assert reranked[0]["rerank"]["intent"] == "current"
    assert reranked[0]["rerank"]["lifecycle_adjustment"] > 0
    assert reranked[-1]["rerank"]["lifecycle_adjustment"] < 0


def test_lifecycle_reranker_preserves_historical_access_when_query_requests_former_state():
    reranker = LifecycleIntentReranker()
    candidates = [
        {**doc("current", rank=1, state="supported"), "retrieval": {"rank": 1}},
        {**doc("former", rank=3, state="superseded"), "retrieval": {"rank": 3}},
    ]

    reranked = reranker.rerank(
        "What former historical conclusion was superseded?",
        candidates,
        limit=2,
    )

    assert [item["id"] for item in reranked] == ["former", "current"]
    assert reranked[0]["rerank"]["intent"] == "historical"


def test_reranked_retriever_exposes_same_retriever_contract_and_uses_deeper_candidate_pool():
    base = FakeRetriever(
        "base",
        [
            doc("stale", rank=1, state="stale_pending_review"),
            doc("rejected", rank=2, state="rejected"),
            doc("current", rank=5, state="supported"),
        ],
        model_id="dense@revision",
    )
    retriever = RerankedRetriever(
        base,
        LifecycleIntentReranker(version="gate2"),
        candidate_multiplier=4,
        version="gate2",
    )

    results = retriever.search(
        "current accepted architecture",
        pack_ids=[PACK],
        limit=2,
    )

    assert base.requested_limits == [8]
    assert [item["id"] for item in results][0] == "current"
    assert results[0]["retrieval"]["rank"] == 1
    assert results[0]["retrieval"]["service"]["implementation"] == "reranked-retriever"
    assert results[0]["retrieval"]["service"]["model_id"] == "dense@revision"
    assert results[0]["base_retrieval"]["service"]["implementation"] == "base"
    assert results[0]["rerank"]["service"]["implementation"] == "lifecycle-intent-reranker"
