from __future__ import annotations

import hashlib
import uuid


def new_id(prefix: str) -> str:
    """Create a corpus-owned globally unique ID.

    Storage-native IDs must never become durable identity.
    """
    return f"{prefix}_{uuid.uuid4().hex}"


def deterministic_event_id(pack_id: str, idempotency_key: str) -> str:
    """Map one logical retryable operation to one stable event ID."""
    digest = hashlib.sha256(f"{pack_id}\x00{idempotency_key}".encode("utf-8")).hexdigest()
    return f"evt_{digest[:32]}"
