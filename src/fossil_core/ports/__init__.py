"""Provider-neutral interfaces for FOSSIL capabilities."""

from .artifact_store import ArtifactStorePort
from .cognitive_service import VersionedCognitiveService
from .event_store import EventStorePort
from .projection import ProjectionAdapter, ProjectionReceipt
from .retriever import Retriever

__all__ = [
    "ArtifactStorePort",
    "EventStorePort",
    "ProjectionReceipt",
    "ProjectionAdapter",
    "VersionedCognitiveService",
    "Retriever",
]
