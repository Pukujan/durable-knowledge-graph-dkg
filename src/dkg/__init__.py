"""DEPRECATED compatibility shim for the legacy `dkg` package.

The canonical package is now ``fossil_core``. This shim exists only so that
existing third-party imports that still say ``import dkg`` or ``from dkg import
...`` continue to resolve during the migration window.

It is TEMPORARY. It will be removed once all first-party and downstream code has
migrated to ``fossil_core``. Do NOT add new implementation under ``dkg``; add new
code to ``fossil_core`` and re-export it here only if a stable legacy symbol must
keep working.

Deprecation: importing this module emits a :class:`DeprecationWarning`.
"""

import warnings

from fossil_core import (
    ArtifactIntegrityError,
    ArtifactStore,
    DurableEventStore,
    IdempotencyConflict,
    KnowledgeState,
    LifecycleError,
    RelationRecord,
    KnowledgePackValidator,
    PackAccess,
    PackBoundaryError,
    build_promotion_event,
)

__all__ = [
    "ArtifactIntegrityError",
    "ArtifactStore",
    "DurableEventStore",
    "IdempotencyConflict",
    "KnowledgeState",
    "LifecycleError",
    "RelationRecord",
    "KnowledgePackValidator",
    "PackAccess",
    "PackBoundaryError",
    "build_promotion_event",
]

warnings.warn(
    "The legacy `dkg` package is deprecated; migrate to `fossil_core`. "
    "`dkg` will be removed in a future release (removal note: Issue #82).",
    DeprecationWarning,
    stacklevel=2,
)