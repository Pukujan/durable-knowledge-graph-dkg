from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from fossil_core.application.ingest.pack_validation import KnowledgePackValidator
from fossil_core.domain.packset import PackSetLockError, packset_lock_digest, validate_packset_lock


ROOT = Path(__file__).resolve().parents[1]
PACK_SCHEMA = ROOT / "schemas/knowledge-pack/v1.schema.json"

COMMON = "pack_0000000000000101"
PROJECT = "pack_0000000000000102"
EXTRA_A = "pack_0000000000000103"
EXTRA_B = "pack_0000000000000104"


def dep(pack_id: str, *, required: bool) -> dict:
    return {"pack_id": pack_id, "required": required, "reason": "adversarial fixture"}


def manifest(pack_id: str, kind: str, dependencies: list[dict] | None = None) -> dict:
    deps = list(dependencies or [])
    return {
        "contract_version": "dkg.pack.v1",
        "pack_id": pack_id,
        "name": f"{kind}-{pack_id}",
        "kind": kind,
        "schema_version": "dkg.event.v1",
        "dependencies": deps,
        "read_mounts": sorted({pack_id, *(item["pack_id"] for item in deps if item["required"])}),
        "write_targets": [pack_id],
        "event_roots": ["events/"],
        "artifact_manifests": [],
    }


def validator() -> KnowledgePackValidator:
    return KnowledgePackValidator(PACK_SCHEMA)


def test_mounted_optional_dependency_is_a_resolved_required_false_edge():
    common = manifest(COMMON, "common")
    project = manifest(PROJECT, "project", [dep(COMMON, required=False)])

    lock = validator().build_packset_lock(
        [project, common],
        {PROJECT: "project-rev", COMMON: "common-rev"},
    )

    project_record = next(item for item in lock["packs"] if item["pack_id"] == PROJECT)
    assert project_record["dependencies"] == [
        {"pack_id": COMMON, "required": False}
    ]


def test_lock_validator_rejects_noncanonical_extra_fields_without_relying_on_schema_callers():
    common = manifest(COMMON, "common")
    lock = validator().build_packset_lock([common], {COMMON: "common-rev"})
    lock["packs"][0]["provider_native_location"] = "s3://must-not-be-semantic-identity"

    with pytest.raises(PackSetLockError, match="pack record fields"):
        validate_packset_lock(lock, {COMMON: common})


def test_lock_validator_rejects_noncanonical_dependency_shape():
    common = manifest(COMMON, "common")
    project = manifest(PROJECT, "project", [dep(COMMON, required=False)])
    lock = validator().build_packset_lock(
        [project, common],
        {PROJECT: "project-rev", COMMON: "common-rev"},
    )
    project_record = next(item for item in lock["packs"] if item["pack_id"] == PROJECT)
    project_record["dependencies"][0]["reason"] = "not part of lock edge contract"

    with pytest.raises(PackSetLockError, match="dependency fields"):
        validate_packset_lock(lock, {COMMON: common, PROJECT: project})


def test_replay_validation_ignores_unmounted_catalog_cycles():
    common = manifest(COMMON, "common")
    lock = validator().build_packset_lock([common], {COMMON: "common-rev"})
    extra_a = manifest(EXTRA_A, "personal", [dep(EXTRA_B, required=True)])
    extra_b = manifest(EXTRA_B, "experimental", [dep(EXTRA_A, required=True)])

    validator().validate_packset_lock(lock, [common, extra_a, extra_b])


def test_lock_digest_changes_when_exact_revision_changes_but_digest_never_enters_content():
    common = manifest(COMMON, "common")
    first = validator().build_packset_lock([common], {COMMON: "rev-a"})
    second = validator().build_packset_lock([deepcopy(common)], {COMMON: "rev-b"})

    assert "lock_digest" not in first
    assert "lock_digest" not in second
    assert packset_lock_digest(first) != packset_lock_digest(second)
