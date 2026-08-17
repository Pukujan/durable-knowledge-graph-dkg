from __future__ import annotations

import inspect

import fossil_core.adapters.vector.semantic_retriever as canonical_semantic
import fossil_core.semantic_retriever as legacy_semantic


def test_semantic_retriever_legacy_namespace_and_identity_are_frozen():
    assert not hasattr(legacy_semantic, "__all__")
    assert {
        name for name in vars(legacy_semantic) if not name.startswith("_")
    } == {
        "Any",
        "EmbeddingRetriever",
        "Iterable",
        "Mapping",
        "SemanticEmbeddingRetriever",
        "ServiceMetadata",
        "annotations",
        "json",
    }

    assert (
        legacy_semantic.SemanticEmbeddingRetriever
        is canonical_semantic.SemanticEmbeddingRetriever
    )
    assert legacy_semantic.EmbeddingRetriever is canonical_semantic.EmbeddingRetriever
    assert legacy_semantic.ServiceMetadata is canonical_semantic.ServiceMetadata


def test_semantic_retriever_constructor_signature_is_unchanged():
    signature = inspect.signature(canonical_semantic.SemanticEmbeddingRetriever)
    parameters = list(signature.parameters.values())

    assert [parameter.name for parameter in parameters] == [
        "documents",
        "embedder",
        "version",
    ]
    assert parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert parameters[0].default is inspect.Parameter.empty
    assert parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert parameters[1].default is inspect.Parameter.empty
    assert parameters[2].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters[2].default == "1"
