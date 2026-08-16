"""Compatibility imports for the canonical S3-compatible storage adapter.

New code should import concrete S3 implementations from ``fossil_core.adapters.s3``.
Existing callers can continue using this module during the bounded package
migration. Direct import of ``RemoteObjectConflict`` is preserved even though
it was not part of this module's historical ``__all__`` declaration.
"""

from .adapters.s3 import (
    RemoteObjectConflict,
    RemoteStoreUnavailable,
    S3ArtifactStore,
    S3DurableEventStore,
)

__all__ = [
    "RemoteStoreUnavailable",
    "S3ArtifactStore",
    "S3DurableEventStore",
]
