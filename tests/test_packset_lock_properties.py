from __future__ import annotations

from itertools import permutations
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

from fossil_core.application.ingest.pack_validation import KnowledgePackValidator
from fossil_core.domain.pack import PackBoundaryError
from fossil_core.domain.packset import packset_lock_digest


ROOT = Path(__file__).resolve().parents[1]
PACK_SCHEMA = ROOT / "schemas/knowledge-pack/v1.schema.json"

COMMON = "pack_0000000000000011"
DOMAIN = "pack_0000000000000012"
PROJECT = "pack_0000000000000013"


def manifest(pack_id: str, *, kind: str, dependencies: list[dict] | None = None) -> dict:
    deps = list(dependencies or [])
    return {
        "contract_version": "dkg.pack.v1",
        "pack_id": pack_id,
        "name": f"{kind} generated fixture",
        "kind": kind,
        "schema_version": "dkg.event.v1",
        "dependencies": deps,
        "read_mounts": sorted({pack_id, *(dep["pack_id"] for dep in deps if dep["required"])}),
        "write_targets": [pack_id],
        "event_roots": ["events/"],
        "artifact_manifests": [],
    }


def validator() -> KnowledgePackValidator:
    return KnowledgePackValidator(PACK_SCHEMA)


@settings(max_examples=80, derandomize=True)
@given(
    common_revision=st.text(min_size=1, max_size=40).filter(lambda value: bool(value.strip())),
    domain_revision=st.text(min_size=1, max_size=40).filter(lambda value: bool(value.strip())),
    project_revision=st.text(min_size=1, max_size=40).filter(lambda value: bool(value.strip())),
)
def test_pack_input_order_never_changes_canonical_lock_or_digest(
    common_revision: str,
    domain_revision: str,
    project_revision: str,
) -> None:
    manifests = [
        manifest(COMMON, kind="common"),
        manifest(DOMAIN, kind="domain", dependencies=[{"pack_id": COMMON, "required": True}]),
        manifest(
            PROJECT,
            kind="project",
            dependencies=[
                {"pack_id": DOMAIN, "required": True},
                {"pack_id": COMMON, "required": False},
            ],
        ),
    ]
    revisions = {
        COMMON: common_revision,
        DOMAIN: domain_revision,
        PROJECT: project_revision,
    }

    locks = [validator().build_packset_lock(order, revisions) for order in permutations(manifests)]

    assert all(lock == locks[0] for lock in locks)
    assert all(packset_lock_digest(lock) == packset_lock_digest(locks[0]) for lock in locks)


@settings(max_examples=120, derandomize=True)
@given(
    source_kind=st.sampled_from(["common", "domain", "project"]),
    target_kind=st.sampled_from(["common", "domain", "project"]),
)
def test_standard_layer_dependency_is_allowed_exactly_when_target_is_upstream(
    source_kind: str,
    target_kind: str,
) -> None:
    source = "pack_0000000000000021"
    target = "pack_0000000000000022"
    manifests = [
        manifest(source, kind=source_kind, dependencies=[{"pack_id": target, "required": True}]),
        manifest(target, kind=target_kind),
    ]
    rank = {"common": 0, "domain": 1, "project": 2}

    if rank[target_kind] < rank[source_kind]:
        validator().validate_set(manifests)
    else:
        with pytest.raises(PackBoundaryError, match="dependency layer violation"):
            validator().validate_set(manifests)


@settings(max_examples=80, derandomize=True)
@given(revision=st.text(min_size=1, max_size=64).filter(lambda value: bool(value.strip())))
def test_exact_revision_is_preserved_opaquely_in_lock(revision: str) -> None:
    lock = validator().build_packset_lock(
        [manifest(COMMON, kind="common")],
        {COMMON: revision},
    )

    assert lock["packs"] == [
        {
            "pack_id": COMMON,
            "revision": revision,
            "manifest_digest": lock["packs"][0]["manifest_digest"],
            "dependencies": [],
        }
    ]
