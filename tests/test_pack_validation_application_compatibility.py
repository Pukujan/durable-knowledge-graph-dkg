from __future__ import annotations

import inspect
from pathlib import Path

import fossil_core
import fossil_core.application.ingest as canonical_ingest
import fossil_core.domain.pack as canonical_pack
import fossil_core.pack as legacy_pack


ROOT = Path(__file__).resolve().parents[1]


def test_pack_legacy_namespace_and_object_identity_are_frozen():
    assert not hasattr(legacy_pack, "__all__")
    assert {name for name in vars(legacy_pack) if not name.startswith("_")} == {
        "Any",
        "Draft202012Validator",
        "FormatChecker",
        "Iterable",
        "KnowledgePackValidator",
        "PackAccess",
        "PackBoundaryError",
        "Path",
        "annotations",
        "dataclass",
        "json",
    }

    assert legacy_pack.KnowledgePackValidator is canonical_ingest.KnowledgePackValidator
    assert fossil_core.KnowledgePackValidator is canonical_ingest.KnowledgePackValidator
    assert legacy_pack.PackAccess is canonical_pack.PackAccess
    assert legacy_pack.PackBoundaryError is canonical_pack.PackBoundaryError


def test_pack_validator_call_signatures_are_unchanged():
    validator = canonical_ingest.KnowledgePackValidator

    init_parameters = list(inspect.signature(validator.__init__).parameters.values())
    assert [parameter.name for parameter in init_parameters] == ["self", "schema_path"]

    validate_parameters = list(inspect.signature(validator.validate).parameters.values())
    assert [parameter.name for parameter in validate_parameters] == ["self", "manifest"]

    set_parameters = list(inspect.signature(validator.validate_set).parameters.values())
    assert [parameter.name for parameter in set_parameters] == ["self", "manifests"]

    load_parameters = list(inspect.signature(validator.load_and_validate).parameters.values())
    assert [parameter.name for parameter in load_parameters] == ["self", "path"]


def test_canonical_and_legacy_pack_validation_behavior_match():
    schema = ROOT / "schemas/knowledge-pack/v1.schema.json"
    common_path = ROOT / "examples/packs/common/manifest.json"
    project_path = ROOT / "examples/packs/plugin-harness/manifest.json"

    canonical = canonical_ingest.KnowledgePackValidator(schema)
    legacy = legacy_pack.KnowledgePackValidator(schema)

    canonical_common = canonical.load_and_validate(common_path)
    canonical_project = canonical.load_and_validate(project_path)
    legacy_common = legacy.load_and_validate(common_path)
    legacy_project = legacy.load_and_validate(project_path)

    assert canonical_common == legacy_common
    assert canonical_project == legacy_project
    assert canonical.validate_set([canonical_common, canonical_project]) == legacy.validate_set(
        [legacy_common, legacy_project]
    )
