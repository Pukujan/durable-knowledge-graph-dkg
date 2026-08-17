from __future__ import annotations

import inspect

import fossil_core.contracts as legacy_contracts
import fossil_core.ports as ports
from fossil_core.ports.cognitive_service import VersionedCognitiveService
from fossil_core.ports.embedding_provider import EmbeddingProvider


def test_embedding_provider_port_is_canonical_and_legacy_contract_preserves_identity():
    assert legacy_contracts.EmbeddingProvider is EmbeddingProvider
    assert ports.EmbeddingProvider is EmbeddingProvider
    assert VersionedCognitiveService in EmbeddingProvider.__mro__


def test_embedding_provider_contract_is_unchanged():
    assert isinstance(EmbeddingProvider.model_id, property)
    model_id_signature = inspect.signature(EmbeddingProvider.model_id.fget)
    assert list(model_id_signature.parameters) == ["self"]

    embed_signature = inspect.signature(EmbeddingProvider.embed)
    parameters = list(embed_signature.parameters.values())
    assert [parameter.name for parameter in parameters] == ["self", "texts"]
    assert parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_legacy_contracts_namespace_remains_frozen_after_embedding_provider_extraction():
    assert not hasattr(legacy_contracts, "__all__")
    public_names = sorted(
        name for name in vars(legacy_contracts) if not name.startswith("_")
    )
    assert public_names == [
        "Any",
        "ContextProvider",
        "EmbeddingProvider",
        "ModelService",
        "Path",
        "ProjectionAdapter",
        "ProjectionReceipt",
        "Protocol",
        "Reranker",
        "Retriever",
        "VerificationService",
        "VersionedCognitiveService",
        "annotations",
        "dataclass",
    ]
