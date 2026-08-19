from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

from fossil_core.application.ingest.pack_validation import KnowledgePackValidator
from fossil_core.domain.pack import PackAccess, PackBoundaryError

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "knowledge-pack" / "v1.schema.json"
MAX_ID = (1 << 64) - 1


def pack_id(value: int) -> str:
    return f"pack_{value & MAX_ID:016x}"


def other_id(value: int) -> str:
    return pack_id(value ^ (1 << 63))


def manifest(
    identity: str,
    *,
    read_mounts: list[str] | None = None,
    write_targets: list[str] | None = None,
    dependencies: list[dict] | None = None,
    name: str = "property pack",
) -> dict:
    return {
        "contract_version": "dkg.pack.v1",
        "pack_id": identity,
        "name": name,
        "kind": "experimental",
        "schema_version": "dkg.event.v1",
        "dependencies": list(dependencies or []),
        "read_mounts": list(read_mounts if read_mounts is not None else [identity]),
        "write_targets": list(write_targets if write_targets is not None else [identity]),
        "event_roots": ["events/"],
        "artifact_manifests": [],
    }


@settings(max_examples=160, derandomize=True)
@given(
    read_values=st.sets(st.integers(min_value=0, max_value=MAX_ID), max_size=8),
    write_values=st.sets(st.integers(min_value=0, max_value=MAX_ID), max_size=8),
    candidate=st.integers(min_value=0, max_value=MAX_ID),
)
def test_pack_access_read_and_write_authority_is_exact_membership(
    read_values: set[int],
    write_values: set[int],
    candidate: int,
) -> None:
    reads = frozenset(pack_id(value) for value in read_values)
    writes = frozenset(pack_id(value) for value in write_values)
    access = PackAccess(pack_id="pack_property_owner_0001", read_mounts=reads, write_targets=writes)
    candidate_id = pack_id(candidate)

    if candidate_id in reads:
        access.require_read(candidate_id)
    else:
        with pytest.raises(PackBoundaryError, match="not mounted for reading"):
            access.require_read(candidate_id)

    if candidate_id in writes:
        access.require_write(candidate_id)
    else:
        with pytest.raises(PackBoundaryError, match="not an allowed write target"):
            access.require_write(candidate_id)


@settings(max_examples=120, derandomize=True)
@given(
    owner=st.integers(min_value=0, max_value=MAX_ID),
    extras=st.sets(st.integers(min_value=1, max_value=64), max_size=8),
)
def test_generated_valid_manifest_preserves_pack_access_and_subset_laws(
    owner: int,
    extras: set[int],
) -> None:
    identity = pack_id(owner)
    extra_ids = {pack_id(owner + delta) for delta in extras}
    reads = {identity, *extra_ids}
    writes = {identity, *(item for item in extra_ids if int(item.removeprefix("pack_"), 16) % 2 == 0)}
    required = [
        {"pack_id": item, "required": True, "reason": "generated required dependency"}
        for item in sorted(extra_ids)
        if int(item.removeprefix("pack_"), 16) % 3 == 0
    ]
    candidate = manifest(
        identity,
        read_mounts=sorted(reads),
        write_targets=sorted(writes),
        dependencies=required,
    )

    KnowledgePackValidator(SCHEMA).validate(candidate)
    access = PackAccess.from_manifest(candidate)

    assert access.pack_id == identity
    assert access.read_mounts == frozenset(reads)
    assert access.write_targets == frozenset(writes)
    assert access.write_targets <= access.read_mounts
    assert all(dep["pack_id"] in access.read_mounts for dep in required)


@settings(max_examples=80, derandomize=True)
@given(owner=st.integers(min_value=0, max_value=MAX_ID))
def test_pack_manifest_must_mount_itself_for_reading(owner: int) -> None:
    identity = pack_id(owner)
    candidate = manifest(identity, read_mounts=[other_id(owner)], write_targets=[])

    with pytest.raises(PackBoundaryError, match="read itself"):
        KnowledgePackValidator(SCHEMA).validate(candidate)


@settings(max_examples=80, derandomize=True)
@given(owner=st.integers(min_value=0, max_value=MAX_ID))
def test_pack_manifest_rejects_write_authority_outside_read_mounts(owner: int) -> None:
    identity = pack_id(owner)
    candidate = manifest(
        identity,
        read_mounts=[identity],
        write_targets=[other_id(owner)],
    )

    with pytest.raises(PackBoundaryError, match="write target must also be readable"):
        KnowledgePackValidator(SCHEMA).validate(candidate)


@settings(max_examples=80, derandomize=True)
@given(
    owner=st.integers(min_value=0, max_value=MAX_ID),
    required=st.booleans(),
)
def test_only_required_dependencies_must_be_mounted(owner: int, required: bool) -> None:
    identity = pack_id(owner)
    dependency = other_id(owner)
    candidate = manifest(
        identity,
        read_mounts=[identity],
        dependencies=[{"pack_id": dependency, "required": required}],
    )
    validator = KnowledgePackValidator(SCHEMA)

    if required:
        with pytest.raises(PackBoundaryError, match="required dependency"):
            validator.validate(candidate)
    else:
        validator.validate(candidate)


@settings(max_examples=80, derandomize=True)
@given(owner=st.integers(min_value=0, max_value=MAX_ID))
def test_required_dependency_must_be_available_in_validated_pack_set(owner: int) -> None:
    identity = pack_id(owner)
    dependency = other_id(owner)
    root = manifest(
        identity,
        read_mounts=[identity, dependency],
        dependencies=[{"pack_id": dependency, "required": True}],
    )
    dependency_manifest = manifest(dependency)
    validator = KnowledgePackValidator(SCHEMA)

    with pytest.raises(PackBoundaryError, match="is unavailable"):
        validator.validate_set([root])

    validated = validator.validate_set([root, dependency_manifest])
    assert set(validated) == {identity, dependency}


@settings(max_examples=80, derandomize=True)
@given(owner=st.integers(min_value=0, max_value=MAX_ID))
def test_pack_set_rejects_duplicate_stable_pack_identity(owner: int) -> None:
    identity = pack_id(owner)
    first = manifest(identity, name="first")
    duplicate = manifest(identity, name="duplicate")

    with pytest.raises(PackBoundaryError, match="duplicate pack_id"):
        KnowledgePackValidator(SCHEMA).validate_set([first, duplicate])
