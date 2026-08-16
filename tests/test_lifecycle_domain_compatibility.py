from __future__ import annotations

import importlib

import fossil_core
import fossil_core.lifecycle as legacy_lifecycle
from fossil_core.domain.lifecycle import (
    CLAIM_STATES,
    RELATION_STATES,
    RELATION_TYPES,
    KnowledgeState,
    LifecycleError,
    RelationRecord,
)


def test_legacy_lifecycle_path_aliases_canonical_domain_objects():
    assert legacy_lifecycle.CLAIM_STATES is CLAIM_STATES
    assert legacy_lifecycle.RELATION_STATES is RELATION_STATES
    assert legacy_lifecycle.RELATION_TYPES is RELATION_TYPES
    assert legacy_lifecycle.KnowledgeState is KnowledgeState
    assert legacy_lifecycle.LifecycleError is LifecycleError
    assert legacy_lifecycle.RelationRecord is RelationRecord


def test_package_root_lifecycle_exports_alias_canonical_domain_objects():
    assert fossil_core.KnowledgeState is KnowledgeState
    assert fossil_core.LifecycleError is LifecycleError
    assert fossil_core.RelationRecord is RelationRecord


def test_legacy_dkg_lifecycle_exports_still_alias_canonical_domain_objects():
    dkg = importlib.import_module("dkg")

    assert dkg.KnowledgeState is KnowledgeState
    assert dkg.LifecycleError is LifecycleError
    assert dkg.RelationRecord is RelationRecord
