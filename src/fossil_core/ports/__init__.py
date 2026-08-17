"""Provider-neutral interfaces for FOSSIL capabilities."""

from .artifact_store import ArtifactStorePort
from .cognitive_service import VersionedCognitiveService
from .context_provider import ContextProvider
from .embedding_provider import EmbeddingProvider
from .event_store import EventStorePort
from .model_service import ModelService
from .projection import ProjectionAdapter, ProjectionReceipt
from .reranker import Reranker
from .retriever import Retriever

__all__ = [
    "ArtifactStorePort",
    "EventStorePort",
    "ProjectionReceipt",
    "ProjectionAdapter",
    "VersionedCognitiveService",
    "Retriever",
    "ContextProvider",
    "EmbeddingProvider",
    "Reranker",
    "ModelService",
]
