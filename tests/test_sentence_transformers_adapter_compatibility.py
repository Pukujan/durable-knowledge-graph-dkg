from __future__ import annotations

import inspect

import fossil_core.adapters.vector.sentence_transformers as canonical_runtime
import fossil_core.real_retrieval as legacy_retrieval


EXPECTED_LEGACY_IMPLICIT_NAMESPACE = {
    "Any",
    "DEFAULT_BGE_MODEL",
    "DEFAULT_BGE_REVISION",
    "DEFAULT_CROSS_ENCODER_MODEL",
    "DEFAULT_CROSS_ENCODER_REVISION",
    "LifecycleIntentReranker",
    "OptionalRetrievalDependencyUnavailable",
    "ReciprocalRankFusionRetriever",
    "RerankedRetriever",
    "SentenceTransformerCrossEncoderReranker",
    "SentenceTransformerEmbeddingProvider",
    "Sequence",
    "ServiceMetadata",
    "annotations",
    "copy",
    "importlib",
    "json",
    "tokenize",
}

MOVED_SYMBOLS = (
    "DEFAULT_BGE_MODEL",
    "DEFAULT_BGE_REVISION",
    "DEFAULT_CROSS_ENCODER_MODEL",
    "DEFAULT_CROSS_ENCODER_REVISION",
    "OptionalRetrievalDependencyUnavailable",
    "SentenceTransformerEmbeddingProvider",
    "SentenceTransformerCrossEncoderReranker",
)


class FakeEncoder:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], dict]] = []

    def encode(self, texts, **kwargs):
        self.calls.append((list(texts), dict(kwargs)))
        return [[1, 0.5], [2, 0.25]]


class FakeCrossEncoder:
    def __init__(self) -> None:
        self.calls: list[tuple[list[tuple[str, str]], dict]] = []

    def predict(self, pairs, **kwargs):
        self.calls.append((list(pairs), dict(kwargs)))
        return [0.25, 1.75]


def test_real_retrieval_legacy_namespace_and_moved_object_identity_are_frozen():
    assert not hasattr(legacy_retrieval, "__all__")
    assert {
        name for name in vars(legacy_retrieval) if not name.startswith("_")
    } == EXPECTED_LEGACY_IMPLICIT_NAMESPACE

    for name in MOVED_SYMBOLS:
        assert getattr(legacy_retrieval, name) is getattr(canonical_runtime, name)
    assert legacy_retrieval._installed_version is canonical_runtime._installed_version


def test_sentence_transformer_adapter_constructor_shapes_are_frozen():
    embedding_parameters = list(
        inspect.signature(canonical_runtime.SentenceTransformerEmbeddingProvider).parameters.values()
    )
    assert [parameter.name for parameter in embedding_parameters] == [
        "model_name",
        "revision",
        "device",
        "normalize_embeddings",
        "model",
        "provider_version",
        "implementation_version",
    ]
    assert all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in embedding_parameters)

    reranker_parameters = list(
        inspect.signature(canonical_runtime.SentenceTransformerCrossEncoderReranker).parameters.values()
    )
    assert [parameter.name for parameter in reranker_parameters] == [
        "model_name",
        "revision",
        "device",
        "batch_size",
        "max_length",
        "model",
        "provider_version",
        "implementation_version",
    ]
    assert all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in reranker_parameters)


def test_injected_embedding_and_reranking_behavior_matches_legacy_path():
    encoder = FakeEncoder()
    provider = legacy_retrieval.SentenceTransformerEmbeddingProvider(
        model=encoder,
        provider_version="test-runtime",
        device="cpu",
    )
    assert type(provider) is canonical_runtime.SentenceTransformerEmbeddingProvider
    assert provider.embed(["alpha", "beta"]) == [[1.0, 0.5], [2.0, 0.25]]
    assert provider.metadata()["runtime"]["model_revision"] == canonical_runtime.DEFAULT_BGE_REVISION
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

    cross_encoder = FakeCrossEncoder()
    reranker = legacy_retrieval.SentenceTransformerCrossEncoderReranker(
        model=cross_encoder,
        provider_version="test-runtime",
        batch_size=8,
    )
    candidates = [
        {"id": "alpha", "text": "alpha", "retrieval": {"rank": 1}},
        {"id": "beta", "text": "beta", "retrieval": {"rank": 2}},
    ]
    result = reranker.rerank("query", candidates, limit=2)
    assert [item["id"] for item in result] == ["beta", "alpha"]
    assert result[0]["rerank"]["service"]["runtime"]["score_authority"] == "candidate-ordering-only"
    assert "rerank" not in candidates[0]
    assert cross_encoder.calls == [
        (
            [("query", "alpha"), ("query", "beta")],
            {
                "batch_size": 8,
                "show_progress_bar": False,
                "convert_to_numpy": True,
            },
        )
    ]
