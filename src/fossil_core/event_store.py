"""Compatibility imports for the canonical filesystem event adapter.

New code should import the concrete filesystem implementation from
``fossil_core.adapters.filesystem``. Existing callers can continue using this
module during the bounded package migration.
"""

from .adapters.filesystem.event_store import (
    DurableEventStore,
    EventRedactedError,
    EventRedactionConflict,
    IdempotencyConflict,
)

__all__ = [
    "DurableEventStore",
    "EventRedactedError",
    "EventRedactionConflict",
    "IdempotencyConflict",
]
