"""Compatibility imports for the canonical lifecycle domain model.

New code should import lifecycle semantics from ``fossil_core.domain.lifecycle``.
This module intentionally preserves the historical implicit star-import names
while existing callers migrate; no runtime deprecation warning is added here.
"""

from dataclasses import dataclass, field
from typing import Any, Iterable

from .domain.lifecycle import (
    CLAIM_STATES,
    RELATION_STATES,
    RELATION_TYPES,
    KnowledgeState,
    LifecycleError,
    RelationRecord,
)
