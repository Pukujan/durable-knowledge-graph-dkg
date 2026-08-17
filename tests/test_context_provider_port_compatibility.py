from __future__ import annotations

import inspect

import fossil_core.contracts as legacy_contracts
import fossil_core.ports as ports
from fossil_core.ports.cognitive_service import VersionedCognitiveService
from fossil_core.ports.context_provider import ContextProvider


def test_context_provider_port_is_canonical_and_legacy_contract_preserves_identity():
    assert legacy_contracts.ContextProvider is ContextProvider
    assert ports.ContextProvider is ContextProvider
    assert VersionedCognitiveService in ContextProvider.__mro__


def test_context_provider_build_contract_is_unchanged():
    signature = inspect.signature(ContextProvider.build_context)
    parameters = list(signature.parameters.values())

    assert [parameter.name for parameter in parameters] == ["self", "request"]
    assert parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_legacy_contracts_namespace_remains_frozen_after_context_provider_extraction():
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
