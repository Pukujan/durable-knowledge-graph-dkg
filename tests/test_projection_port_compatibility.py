from __future__ import annotations

import fossil_core.contracts as legacy_contracts
import fossil_core.ports as ports
from fossil_core.ports.projection import ProjectionAdapter, ProjectionReceipt
from fossil_core.projection.graphiti import GraphitiProjectionAdapter
from fossil_core.projection.null import NullProjection


def test_projection_port_is_canonical_and_legacy_contracts_preserve_identity():
    assert legacy_contracts.ProjectionReceipt is ProjectionReceipt
    assert legacy_contracts.ProjectionAdapter is ProjectionAdapter
    assert ports.ProjectionReceipt is ProjectionReceipt
    assert ports.ProjectionAdapter is ProjectionAdapter


def test_projection_receipt_shape_is_unchanged():
    receipt = ProjectionReceipt("graphiti-neo4j", "1", "evt_example", "applied")

    assert receipt.projection == "graphiti-neo4j"
    assert receipt.projection_version == "1"
    assert receipt.event_id == "evt_example"
    assert receipt.status == "applied"
    assert receipt.detail is None


def test_existing_projection_implementations_keep_expected_runtime_shape():
    projection = NullProjection()

    assert projection.name == "null"
    assert projection.version == "1"
    assert projection.apply_event({"event_id": "evt_example"}) == ProjectionReceipt(
        "null", "1", "evt_example", "applied"
    )
    assert hasattr(GraphitiProjectionAdapter, "apply_event")
    assert hasattr(GraphitiProjectionAdapter, "rebuild")
    assert hasattr(GraphitiProjectionAdapter, "health")


def test_legacy_contracts_implicit_surface_is_unchanged():
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
