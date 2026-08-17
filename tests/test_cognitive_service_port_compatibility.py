from __future__ import annotations

import fossil_core.contracts as legacy_contracts
import fossil_core.ports as ports
from fossil_core.ports.cognitive_service import VersionedCognitiveService


def test_cognitive_metadata_port_is_canonical_and_legacy_contract_preserves_identity():
    assert legacy_contracts.VersionedCognitiveService is VersionedCognitiveService
    assert ports.VersionedCognitiveService is VersionedCognitiveService


def test_remaining_cognitive_protocols_keep_canonical_metadata_base():
    for protocol in (
        legacy_contracts.Retriever,
        legacy_contracts.EmbeddingProvider,
        legacy_contracts.Reranker,
        legacy_contracts.ContextProvider,
        legacy_contracts.ModelService,
        legacy_contracts.VerificationService,
    ):
        assert VersionedCognitiveService in protocol.__mro__
        assert hasattr(protocol, "metadata")


def test_legacy_contracts_namespace_remains_frozen_after_metadata_extraction():
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
