from __future__ import annotations

import inspect

import fossil_core.contracts as legacy_contracts
import fossil_core.ports as ports
from fossil_core.ports.cognitive_service import VersionedCognitiveService
from fossil_core.ports.reranker import Reranker


def test_reranker_port_is_canonical_and_legacy_contract_preserves_identity():
    assert legacy_contracts.Reranker is Reranker
    assert ports.Reranker is Reranker
    assert VersionedCognitiveService in Reranker.__mro__


def test_reranker_contract_is_unchanged():
    signature = inspect.signature(Reranker.rerank)
    parameters = list(signature.parameters.values())
    assert [parameter.name for parameter in parameters] == [
        "self",
        "query",
        "candidates",
        "limit",
    ]
    assert parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert parameters[2].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert parameters[3].kind is inspect.Parameter.KEYWORD_ONLY


def test_legacy_contracts_namespace_remains_frozen_after_reranker_extraction():
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
