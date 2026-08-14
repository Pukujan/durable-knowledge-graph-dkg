from __future__ import annotations

import importlib.metadata
import json

import pytest

from fossil_core.real_retrieval import (
    DEFAULT_BGE_MODEL,
    DEFAULT_BGE_REVISION,
    DEFAULT_CROSS_ENCODER_MODEL,
    DEFAULT_CROSS_ENCODER_REVISION,
    LifecycleIntentReranker,
    OptionalRetrievalDependencyUnavailable,
    ReciprocalRankFusionRetriever,
    RerankedRetriever,
    SentenceTransformerCrossEncoderReranker,
    SentenceTransformerEmbeddingProvider,
)
from fossil_core.semantic_retriever import SemanticEmbeddingRetriever


PACK = "pack_f024177f89a5442db84171c3dd7f58e5"
OTHER_PACK = "pack_269099f7b2ba43b7a99b9427d64092de"


class FakeEncoder:
    def __init__(self) -> None:
        self.calls = []

    def encode(self, texts, **kwargs):
        self.calls.append((list(texts), dict(kwargs)))
        return [[float(index + 1), 0.5] for index, _ in enumerate(texts)]


class FakeCrossEncoder:
    def __init__(self, scores: list[float]) -> None:
        self.scores = list(scores)
        self.calls = []

    def predict(self, pairs, **kwargs):
        self.calls.append((list(pairs), dict(kwargs)))
        return list(self.scores)


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


def test_cross_encoder_reranker_preserves_exact_identity_and_pairwise_predict_options():
    model = FakeCrossEncoder([0.25, 1.75, 1.75])
    reranker = SentenceTransformerCrossEncoderReranker(
        model=model,
        provider_version="5.2.2",
        device="cpu",
        batch_size=8,
        max_length=256,
    )
    candidates = [
        {**doc("alpha", rank=1), "retrieval": {"rank": 1, "score": 3.0}},
        {**doc("beta", rank=2), "retrieval": {"rank": 2, "score": 2.0}},
        {**doc("gamma", rank=3), "retrieval": {"rank": 3, "score": 1.0}},
    ]

    results = reranker.rerank("which candidate", candidates, limit=3)
    metadata = reranker.metadata()

    assert [item["id"] for item in results] == ["beta", "gamma", "alpha"]
    assert results[0]["rerank"]["score"] == 1.75
    assert results[0]["rerank"]["base_rank"] == 2
    assert results[0]["rerank"]["service"]["model_id"] == (
        f"{DEFAULT_CROSS_ENCODER_MODEL}@{DEFAULT_CROSS_ENCODER_REVISION}"
    )
    assert "rerank" not in candidates[0]
    assert metadata["kind"] == "reranker"
    assert metadata["provider"] == "sentence-transformers"
    assert metadata["provider_version"] == "5.2.2"
    assert metadata["implementation"] == "cross-encoder-pairwise-reranker"
    assert metadata["model_id"] == (
        f"{DEFAULT_CROSS_ENCODER_MODEL}@{DEFAULT_CROSS_ENCODER_REVISION}"
    )
    assert metadata["runtime"]["model_revision"] == DEFAULT_CROSS_ENCODER_REVISION
    assert metadata["runtime"]["score_authority"] == "candidate-ordering-only"
    assert model.calls == [
        (
            [
                ("which candidate", "alpha"),
                ("which candidate", "beta"),
                ("which candidate", "gamma"),
            ],
            {
                "batch_size": 8,
                "show_progress_bar": False,
                "convert_to_numpy": True,
            },
        )
    ]


def test_cross_encoder_reranker_fails_on_invalid_score_count():
    reranker = SentenceTransformerCrossEncoderReranker(
        model=FakeCrossEncoder([1.0]),
        provider_version="5.2.2",
    )
    candidates = [
        {**doc("alpha", rank=1), "retrieval": {"rank": 1}},
        {**doc("beta", rank=2), "retrieval": {"rank": 2}},
    ]

    with pytest.raises(ValueError, match="score count"):
        reranker.rerank("query", candidates, limit=2)


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


def test_cross_encoder_reranker_fails_cleanly_when_optional_runtime_is_unavailable(monkeypatch):
    def missing(_name: str):
        raise importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(importlib.metadata, "version", missing)
    with pytest.raises(OptionalRetrievalDependencyUnavailable, match=r"fossil-core\[semantic\]"):
        SentenceTransformerCrossEncoderReranker(model=None)


def test_rrf_fuses_distinct_retrievers_and_preserves_pack_filtering_and_component_provenance():
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
    service = results[0]["retrieval"]["service"]
    components = json.loads(service["runtime"]["components"])

    assert [item["id"] for item in results] == ["beta", "alpha", "gamma"]
    assert all(item["pack_id"] == PACK for item in results)
    assert lexical.requested_limits == [9]
    assert semantic.requested_limits == [9]
    assert service["implementation"] == "reciprocal-rank-fusion"
    assert service["model_id"] == "semantic-model@revision"
    assert len(results[0]["retrieval"]["components"]) == 2
    assert {component["implementation"] for component in components} == {"lexical", "semantic"}
    assert any(component["model_id"] == "semantic-model@revision" for component in components)


def test_lifecycle_intent_uses_explicit_temporal_cues_instead_of_ambiguous_words():
    assert (
        LifecycleIntentReranker.intent_for_query(
            "Was graph database canonical storage retained as the accepted conclusion?"
        )
        == "neutral"
    )
    assert (
        LifecycleIntentReranker.intent_for_query(
            "What happens after the premise is superseded?"
        )
        == "historical"
    )
    assert (
        LifecycleIntentReranker.intent_for_query(
            "What is the current accepted architecture after reconsideration?"
        )
        == "current"
    )


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


def test_lifecycle_reranker_uses_text_fit_to_break_same_state_current_candidates():
    reranker = LifecycleIntentReranker(lexical_weight=0.75)
    candidates = [
        {
            "id": "unrelated_supported",
            "pack_id": PACK,
            "text": "fresh projection replay order",
            "current_state": "supported",
            "retrieval": {"rank": 1},
        },
        {
            "id": "current_architecture",
            "pack_id": PACK,
            "text": "current accepted durable architecture",
            "current_state": "supported",
            "retrieval": {"rank": 2},
        },
    ]

    reranked = reranker.rerank(
        "current accepted durable architecture",
        candidates,
        limit=2,
    )

    assert [item["id"] for item in reranked] == ["current_architecture", "unrelated_supported"]
    assert reranked[0]["rerank"]["lexical_bonus"] > reranked[1]["rerank"]["lexical_bonus"]


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


def test_reranked_retriever_exposes_same_retriever_contract_and_full_base_provenance():
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
    service = results[0]["retrieval"]["service"]
    base_service = json.loads(service["runtime"]["base_service"])
    reranker_service = json.loads(service["runtime"]["reranker_service"])

    assert base.requested_limits == [8]
    assert [item["id"] for item in results][0] == "current"
    assert results[0]["retrieval"]["rank"] == 1
    assert service["implementation"] == "reranked-retriever"
    assert service["model_id"] == "dense@revision"
    assert base_service["implementation"] == "base"
    assert reranker_service["implementation"] == "lifecycle-intent-reranker"
    assert results[0]["base_retrieval"]["service"]["implementation"] == "base"
    assert results[0]["rerank"]["service"]["implementation"] == "lifecycle-intent-reranker"


def test_reranked_retriever_surfaces_cross_encoder_service_identity():
    base = FakeRetriever(
        "base",
        [doc("alpha", rank=1), doc("beta", rank=2)],
        model_id="dense@revision",
    )
    reranker = SentenceTransformerCrossEncoderReranker(
        model=FakeCrossEncoder([0.1, 0.9]),
        provider_version="5.2.2",
    )
    retriever = RerankedRetriever(
        base,
        reranker,
        candidate_multiplier=2,
        version="cross-encoder-fixture",
    )

    results = retriever.search("query", pack_ids=[PACK], limit=2)
    metadata = retriever.metadata()
    reranker_metadata = json.loads(metadata["runtime"]["reranker_service"])

    assert [item["id"] for item in results] == ["beta", "alpha"]
    assert reranker_metadata["model_id"] == (
        f"{DEFAULT_CROSS_ENCODER_MODEL}@{DEFAULT_CROSS_ENCODER_REVISION}"
    )
    assert results[0]["rerank"]["service"]["implementation"] == (
        "cross-encoder-pairwise-reranker"
    )
