from __future__ import annotations

import inspect

import fossil_core.contracts as legacy_contracts
import fossil_core.ports as ports
from fossil_core.ports.cognitive_service import VersionedCognitiveService
from fossil_core.ports.retriever import Retriever


def test_retriever_port_is_canonical_and_legacy_contract_preserves_identity():
    assert legacy_contracts.Retriever is Retriever
    assert ports.Retriever is Retriever
    assert VersionedCognitiveService in Retriever.__mro__


def test_retriever_search_contract_is_unchanged():
    signature = inspect.signature(Retriever.search)
    parameters = list(signature.parameters.values())

    assert [parameter.name for parameter in parameters] == [
        "self",
        "query",
        "pack_ids",
        "limit",
    ]
    assert parameters[2].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters[3].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters[3].default == 20


def test_legacy_contracts_namespace_remains_frozen_after_retriever_extraction():
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
