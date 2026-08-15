from pathlib import Path

import pytest

from fossil_core.pack import KnowledgePackValidator, PackAccess, PackBoundaryError

ROOT = Path(__file__).parents[1]


def test_example_packs_validate():
    validator = KnowledgePackValidator(ROOT / "schemas/knowledge-pack/v1.schema.json")
    common = validator.load_and_validate(ROOT / "examples/packs/common/manifest.json")
    project = validator.load_and_validate(ROOT / "examples/packs/plugin-harness/manifest.json")
    validator.validate_set([common, project])

    assert common["pack_id"] in project["read_mounts"]
    assert project["write_targets"] == [project["pack_id"]]

    access = PackAccess.from_manifest(project)
    access.require_read(common["pack_id"])
    access.require_write(project["pack_id"])
    with pytest.raises(PackBoundaryError):
        access.require_write(common["pack_id"])


def test_required_dependency_must_be_available():
    validator = KnowledgePackValidator(ROOT / "schemas/knowledge-pack/v1.schema.json")
    project = validator.load_and_validate(ROOT / "examples/packs/plugin-harness/manifest.json")
    with pytest.raises(PackBoundaryError):
        validator.validate_set([project])
