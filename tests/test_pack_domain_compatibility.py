from __future__ import annotations

import importlib

import fossil_core
import fossil_core.pack as legacy_pack
from fossil_core.application.ingest import KnowledgePackValidator
from fossil_core.domain.pack import PackAccess, PackBoundaryError


def test_pack_module_uses_canonical_domain_boundary_objects():
    assert legacy_pack.PackAccess is PackAccess
    assert legacy_pack.PackBoundaryError is PackBoundaryError
    assert not hasattr(legacy_pack, "__all__")


def test_package_root_pack_boundary_exports_alias_canonical_domain_objects():
    assert fossil_core.PackAccess is PackAccess
    assert fossil_core.PackBoundaryError is PackBoundaryError


def test_legacy_dkg_pack_boundary_exports_alias_canonical_domain_objects():
    dkg = importlib.import_module("dkg")

    assert dkg.PackAccess is PackAccess
    assert dkg.PackBoundaryError is PackBoundaryError


def test_json_schema_validator_stays_outside_pure_domain_boundary():
    assert legacy_pack.KnowledgePackValidator is KnowledgePackValidator
    assert fossil_core.KnowledgePackValidator is KnowledgePackValidator
    assert KnowledgePackValidator.__module__ == "fossil_core.application.ingest.pack_validation"
    assert not hasattr(importlib.import_module("fossil_core.domain.pack"), "KnowledgePackValidator")
