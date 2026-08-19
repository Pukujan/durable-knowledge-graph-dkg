from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from fossil_core.application.ingest.pack_validation import KnowledgePackValidator
from fossil_core.application.query.receipt import normalize_pack_mounts
from fossil_core.domain.pack import PackBoundaryError
from fossil_core.domain.packset import (
    PACKSET_LOCK_CONTRACT_VERSION,
    PackSetLockError,
    canonical_manifest_digest,
    pack_revisions_from_lock,
    packset_lock_digest,
    validate_packset_lock,
)


ROOT = Path(__file__).resolve().parents[1]
PACK_SCHEMA = ROOT / "schemas/knowledge-pack/v1.schema.json"
LOCK_SCHEMA = ROOT / "schemas/packset-lock/v1.schema.json"

COMMON = "pack_0000000000000001"
DOMAIN = "pack_0000000000000002"
PROJECT = "pack_0000000000000003"
OPTIONAL = "pack_0000000000000004"
PERSONAL_A = "pack_0000000000000005"
PERSONAL_B = "pack_0000000000000006"


def dependency(pack_id: str, *, required: bool = True) -> dict:
    return {
        "pack_id": pack_id,
        "required": required,
        "reason": "fixture dependency",
    }


def manifest(
    pack_id: str,
    *,
    kind: str,
    dependencies: list[dict] | None = None,
    name: str | None = None,
) -> dict:
    deps = list(dependencies or [])
    required_mounts = [item["pack_id"] for item in deps if item["required"]]
    return {
        "contract_version": "dkg.pack.v1",
        "pack_id": pack_id,
        "name": name or f"{kind} fixture",
        "kind": kind,
        "schema_version": "dkg.event.v1",
        "dependencies": deps,
        "read_mounts": sorted({pack_id, *required_mounts}),
        "write_targets": [pack_id],
        "event_roots": ["events/"],
        "artifact_manifests": [],
        "placement_hint": "unspecified",
        "projection_namespace": f"projection-{pack_id}",
    }


def validator() -> KnowledgePackValidator:
    return KnowledgePackValidator(PACK_SCHEMA)


def standard_manifests() -> list[dict]:
    common = manifest(COMMON, kind="common")
    domain = manifest(DOMAIN, kind="domain", dependencies=[dependency(COMMON)])
    project = manifest(
        PROJECT,
        kind="project",
        dependencies=[dependency(COMMON), dependency(DOMAIN)],
    )
    return [project, common, domain]


def standard_revisions() -> dict[str, str]:
    return {
        PROJECT: "git:project@cccccccc",
        COMMON: "git:common@aaaaaaaa",
        DOMAIN: "git:domain@bbbbbbbb",
    }


def test_build_lock_is_schema_valid_sorted_exact_and_digest_is_external():
    lock = validator().build_packset_lock(standard_manifests(), standard_revisions())

    schema = json.loads(LOCK_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(lock)
    assert lock["contract_version"] == PACKSET_LOCK_CONTRACT_VERSION
    assert [item["pack_id"] for item in lock["packs"]] == [COMMON, DOMAIN, PROJECT]
    assert "lock_digest" not in lock

    by_pack = {item["pack_id"]: item for item in lock["packs"]}
    assert by_pack[COMMON]["revision"] == "git:common@aaaaaaaa"
    assert by_pack[DOMAIN]["dependencies"] == [
        {"pack_id": COMMON, "required": True}
    ]
    assert by_pack[PROJECT]["dependencies"] == [
        {"pack_id": COMMON, "required": True},
        {"pack_id": DOMAIN, "required": True},
    ]
    for source in standard_manifests():
        record = by_pack[source["pack_id"]]
        assert record["manifest_digest"] == {
            "algorithm": "sha256",
            "digest": canonical_manifest_digest(source),
        }

    digest = packset_lock_digest(lock)
    assert len(digest) == 64
    assert all(ch in "0123456789abcdef" for ch in digest)


def test_lock_is_portable_across_input_order_paths_and_json_formatting(tmp_path):
    manifests = standard_manifests()
    compact_root = tmp_path / "compact"
    pretty_root = tmp_path / "moved" / "pretty"
    compact_root.mkdir(parents=True)
    pretty_root.mkdir(parents=True)

    compact_paths: list[Path] = []
    pretty_paths: list[Path] = []
    for index, item in enumerate(manifests):
        compact = compact_root / f"{index}.json"
        pretty = pretty_root / f"{index}.json"
        compact.write_text(json.dumps(item, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        pretty.write_text(json.dumps(dict(reversed(list(item.items()))), indent=4), encoding="utf-8")
        compact_paths.append(compact)
        pretty_paths.append(pretty)

    compact_manifests = [json.loads(path.read_text(encoding="utf-8")) for path in compact_paths]
    pretty_manifests = [json.loads(path.read_text(encoding="utf-8")) for path in reversed(pretty_paths)]
    left = validator().build_packset_lock(compact_manifests, standard_revisions())
    right = validator().build_packset_lock(pretty_manifests, standard_revisions())

    assert left == right
    assert packset_lock_digest(left) == packset_lock_digest(right)


def test_query_receipt_mounts_preserve_exact_lock_revisions():
    lock = validator().build_packset_lock(standard_manifests(), standard_revisions())

    assert normalize_pack_mounts(pack_revisions_from_lock(lock)) == [
        {"pack_id": COMMON, "revision": "git:common@aaaaaaaa"},
        {"pack_id": DOMAIN, "revision": "git:domain@bbbbbbbb"},
        {"pack_id": PROJECT, "revision": "git:project@cccccccc"},
    ]


def test_revision_set_must_match_mounted_pack_set_exactly():
    manifests = standard_manifests()
    revisions = standard_revisions()

    missing = dict(revisions)
    missing.pop(DOMAIN)
    with pytest.raises(PackSetLockError, match="missing exact revision"):
        validator().build_packset_lock(manifests, missing)

    extra = dict(revisions)
    extra[OPTIONAL] = "git:optional@dddddddd"
    with pytest.raises(PackSetLockError, match="unresolved revision pack"):
        validator().build_packset_lock(manifests, extra)

    blank = dict(revisions)
    blank[DOMAIN] = ""
    with pytest.raises(PackSetLockError, match="non-empty exact revision"):
        validator().build_packset_lock(manifests, blank)


def test_required_dependency_must_be_mounted_but_absent_optional_dependency_is_not_a_resolved_edge():
    required = manifest(DOMAIN, kind="domain", dependencies=[dependency(COMMON, required=True)])
    with pytest.raises(PackBoundaryError, match="required dependency.*unavailable"):
        validator().build_packset_lock([required], {DOMAIN: "rev-domain"})

    optional = manifest(DOMAIN, kind="domain", dependencies=[dependency(OPTIONAL, required=False)])
    lock = validator().build_packset_lock([optional], {DOMAIN: "rev-domain"})
    assert lock["packs"][0]["dependencies"] == []


def test_lock_validation_rejects_unresolved_dependency_edge_and_manifest_dependency_drift():
    manifests = standard_manifests()
    lock = validator().build_packset_lock(manifests, standard_revisions())

    unresolved = deepcopy(lock)
    unresolved["packs"][0]["dependencies"] = [
        {"pack_id": OPTIONAL, "required": False}
    ]
    with pytest.raises(PackSetLockError, match="unresolved referenced pack"):
        validate_packset_lock(unresolved, {item["pack_id"]: item for item in manifests})

    metadata_drift = deepcopy(lock)
    project = next(item for item in metadata_drift["packs"] if item["pack_id"] == PROJECT)
    project["dependencies"][0]["required"] = False
    with pytest.raises(PackSetLockError, match="dependency metadata differs"):
        validate_packset_lock(metadata_drift, {item["pack_id"]: item for item in manifests})


def test_lock_validation_rejects_manifest_drift_even_when_pack_id_and_revision_match():
    manifests = standard_manifests()
    lock = validator().build_packset_lock(manifests, standard_revisions())
    changed = deepcopy(manifests)
    changed[0]["name"] = "renamed project"

    with pytest.raises(PackSetLockError, match="manifest digest differs"):
        validate_packset_lock(lock, {item["pack_id"]: item for item in changed})


def test_lock_validation_rejects_duplicate_pack_identity_even_with_different_revisions():
    manifests = standard_manifests()
    lock = validator().build_packset_lock(manifests, standard_revisions())
    duplicate = deepcopy(lock)
    duplicate["packs"].append(deepcopy(duplicate["packs"][0]))
    duplicate["packs"][-1]["revision"] = "another-revision"

    with pytest.raises(PackSetLockError, match="duplicate pack_id"):
        validate_packset_lock(duplicate, {item["pack_id"]: item for item in manifests})


def test_standard_dependency_layers_are_strictly_upstream():
    common_to_domain = [
        manifest(COMMON, kind="common", dependencies=[dependency(DOMAIN)]),
        manifest(DOMAIN, kind="domain"),
    ]
    with pytest.raises(PackBoundaryError, match="dependency layer violation"):
        validator().validate_set(common_to_domain)

    domain_to_project = [
        manifest(DOMAIN, kind="domain", dependencies=[dependency(PROJECT)]),
        manifest(PROJECT, kind="project"),
    ]
    with pytest.raises(PackBoundaryError, match="dependency layer violation"):
        validator().validate_set(domain_to_project)

    project_to_project = [
        manifest(PROJECT, kind="project", dependencies=[dependency(OPTIONAL)]),
        manifest(OPTIONAL, kind="project"),
    ]
    with pytest.raises(PackBoundaryError, match="dependency layer violation"):
        validator().validate_set(project_to_project)

    validator().validate_set(standard_manifests())


def test_cycle_detection_applies_to_personal_and_experimental_packs_too():
    first = manifest(PERSONAL_A, kind="personal", dependencies=[dependency(PERSONAL_B)])
    second = manifest(PERSONAL_B, kind="experimental", dependencies=[dependency(PERSONAL_A)])

    with pytest.raises(PackBoundaryError, match="dependency cycle"):
        validator().validate_set([first, second])


def test_duplicate_dependency_metadata_for_one_target_is_rejected():
    candidate = manifest(
        PROJECT,
        kind="project",
        dependencies=[
            dependency(COMMON, required=True),
            dependency(COMMON, required=False),
        ],
    )
    common = manifest(COMMON, kind="common")

    with pytest.raises(PackBoundaryError, match="duplicate dependency"):
        validator().validate_set([candidate, common])
