from pathlib import Path

from dkg.pack import KnowledgePackValidator

ROOT = Path(__file__).parents[1]


def test_example_packs_validate():
    validator = KnowledgePackValidator(ROOT / "schemas/knowledge-pack/v1.schema.json")
    common = validator.load_and_validate(ROOT / "examples/packs/common/manifest.json")
    project = validator.load_and_validate(ROOT / "examples/packs/plugin-harness/manifest.json")
    assert common["pack_id"] in project["read_mounts"]
    assert project["write_targets"] == [project["pack_id"]]
