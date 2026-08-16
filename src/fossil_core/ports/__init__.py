"""Provider-neutral interfaces for FOSSIL capabilities."""

from .artifact_store import ArtifactStorePort
from .event_store import EventStorePort

__all__ = ["ArtifactStorePort", "EventStorePort"]
