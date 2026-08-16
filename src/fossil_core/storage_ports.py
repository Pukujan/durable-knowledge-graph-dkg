"""Compatibility aliases for the canonical :mod:`fossil_core.ports` interfaces.

New code should import storage contracts from ``fossil_core.ports`` or its
bounded modules. This module remains intentionally thin while existing callers
migrate; the exported objects are the canonical protocol classes themselves.
"""

from .ports import ArtifactStorePort, EventStorePort

__all__ = ["ArtifactStorePort", "EventStorePort"]
