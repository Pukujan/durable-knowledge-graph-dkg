"""Compatibility imports for the canonical filesystem artifact adapter.

New code should import the concrete filesystem implementation from
``fossil_core.adapters.filesystem``. Existing callers can continue using this
module during the bounded package migration.
"""

from .adapters.filesystem.artifact_store import (
    ArtifactIntegrityError,
    ArtifactRedactedError,
    ArtifactStore,
)

__all__ = ["ArtifactIntegrityError", "ArtifactRedactedError", "ArtifactStore"]
