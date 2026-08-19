from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from .pack import PackBoundaryError


PACKSET_LOCK_CONTRACT_VERSION = "dkg.packset-lock.v1"
_STANDARD_LAYER_RANK = {"common": 0, "domain": 1, "project": 2}
_PACK_ID_RE = re.compile(r"^pack_[A-Za-z0-9_-]{16,}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_PACK_RECORD_FIELDS = {"pack_id", "revision", "manifest_digest", "dependencies"}
_DIGEST_FIELDS = {"algorithm", "digest"}
_DEPENDENCY_FIELDS = {"pack_id", "required"}


class PackSetLockError(PackBoundaryError):
    """A mounted pack revision set cannot satisfy the frozen lock contract."""


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def canonical_manifest_digest(manifest: Mapping[str, Any]) -> str:
    """Hash manifest meaning independently of JSON object key order/formatting."""

    return hashlib.sha256(_canonical_json_bytes(dict(manifest))).hexdigest()


def _dependencies_by_target(manifest: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    by_target: dict[str, dict[str, Any]] = {}
    for dependency in manifest.get("dependencies", []):
        target = str(dependency["pack_id"])
        if target in by_target:
            raise PackBoundaryError(
                f"duplicate dependency for pack {manifest['pack_id']}: {target}"
            )
        by_target[target] = dict(dependency)
    return by_target


def _resolved_dependencies(
    manifest: Mapping[str, Any], mounted_pack_ids: set[str]
) -> list[dict[str, Any]]:
    dependencies = _dependencies_by_target(manifest)
    return [
        {
            "pack_id": target,
            "required": bool(dependencies[target]["required"]),
        }
        for target in sorted(dependencies)
        if target in mounted_pack_ids
    ]


def validate_pack_dependency_graph(manifests: Mapping[str, Mapping[str, Any]]) -> None:
    """Enforce mounted dependency resolution, standard layering, and acyclicity.

    Optional dependencies that are not mounted are intentionally absent from the
    resolved graph. If an optional target *is* mounted, it is a real edge and is
    subject to the same layer and cycle laws as required dependencies.
    """

    mounted = set(manifests)
    adjacency: dict[str, tuple[str, ...]] = {}

    for pack_id in sorted(manifests):
        manifest = manifests[pack_id]
        if manifest.get("pack_id") != pack_id:
            raise PackBoundaryError(
                f"manifest identity mismatch: catalog key {pack_id} != manifest pack_id {manifest.get('pack_id')}"
            )
        dependencies = _dependencies_by_target(manifest)
        source_kind = str(manifest.get("kind", ""))
        resolved: list[str] = []
        for target in sorted(dependencies):
            dependency = dependencies[target]
            if target not in mounted:
                if bool(dependency["required"]):
                    raise PackBoundaryError(
                        f"required dependency {target} is unavailable"
                    )
                continue

            target_kind = str(manifests[target].get("kind", ""))
            if source_kind in _STANDARD_LAYER_RANK and target_kind in _STANDARD_LAYER_RANK:
                if _STANDARD_LAYER_RANK[target_kind] >= _STANDARD_LAYER_RANK[source_kind]:
                    raise PackBoundaryError(
                        "dependency layer violation: "
                        f"{pack_id} ({source_kind}) cannot depend on "
                        f"{target} ({target_kind}); standard dependencies must point "
                        "strictly upstream common <- domain <- project"
                    )
            resolved.append(target)
        adjacency[pack_id] = tuple(resolved)

    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(pack_id: str) -> None:
        status = state.get(pack_id, 0)
        if status == 2:
            return
        if status == 1:
            try:
                index = stack.index(pack_id)
            except ValueError:
                index = 0
            cycle = [*stack[index:], pack_id]
            raise PackBoundaryError("dependency cycle: " + " -> ".join(cycle))
        state[pack_id] = 1
        stack.append(pack_id)
        for target in adjacency[pack_id]:
            visit(target)
        stack.pop()
        state[pack_id] = 2

    for pack_id in sorted(adjacency):
        visit(pack_id)


def build_packset_lock(
    validated_manifests: Mapping[str, Mapping[str, Any]],
    revisions: Mapping[str, str],
) -> dict[str, Any]:
    """Build canonical portable lock content from validated manifests/revisions.

    The SHA-256 lock digest is deliberately not embedded here; callers compute it
    over this content with :func:`packset_lock_digest` to avoid self-reference.
    """

    manifests = {
        str(pack_id): dict(manifest)
        for pack_id, manifest in validated_manifests.items()
    }
    if not manifests:
        raise PackSetLockError("packset lock requires at least one mounted pack")
    validate_pack_dependency_graph(manifests)

    mounted = set(manifests)
    revision_ids = {str(pack_id) for pack_id in revisions}
    missing = sorted(mounted - revision_ids)
    if missing:
        raise PackSetLockError(f"missing exact revision for mounted pack(s): {missing}")
    extra = sorted(revision_ids - mounted)
    if extra:
        raise PackSetLockError(f"unresolved revision pack(s) are not mounted: {extra}")

    packs: list[dict[str, Any]] = []
    for pack_id in sorted(manifests):
        revision = revisions[pack_id]
        if not isinstance(revision, str) or not revision.strip():
            raise PackSetLockError(
                f"pack {pack_id} requires a non-empty exact revision"
            )
        manifest = manifests[pack_id]
        packs.append(
            {
                "pack_id": pack_id,
                "revision": revision,
                "manifest_digest": {
                    "algorithm": "sha256",
                    "digest": canonical_manifest_digest(manifest),
                },
                "dependencies": _resolved_dependencies(manifest, mounted),
            }
        )

    return {
        "contract_version": PACKSET_LOCK_CONTRACT_VERSION,
        "packs": packs,
    }


def _lock_records(lock: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if set(lock) != {"contract_version", "packs"}:
        raise PackSetLockError(
            "packset lock fields must be exactly contract_version and packs; "
            "lock digest is external"
        )
    if lock.get("contract_version") != PACKSET_LOCK_CONTRACT_VERSION:
        raise PackSetLockError(
            f"unsupported packset lock contract: {lock.get('contract_version')!r}"
        )
    packs = lock.get("packs")
    if not isinstance(packs, list) or not packs:
        raise PackSetLockError("packset lock requires at least one pack record")
    if not all(isinstance(item, Mapping) for item in packs):
        raise PackSetLockError("packset lock pack records must be objects")
    return list(packs)


def _validate_lock_record_shape(record: Mapping[str, Any]) -> None:
    if set(record) != _PACK_RECORD_FIELDS:
        raise PackSetLockError(
            "pack record fields must be exactly pack_id, revision, manifest_digest, dependencies"
        )

    pack_id = record.get("pack_id")
    if not isinstance(pack_id, str) or _PACK_ID_RE.fullmatch(pack_id) is None:
        raise PackSetLockError(f"invalid pack_id in packset lock: {pack_id!r}")
    revision = record.get("revision")
    if not isinstance(revision, str) or not revision.strip():
        raise PackSetLockError(f"pack {pack_id} requires a non-empty exact revision")

    digest = record.get("manifest_digest")
    if not isinstance(digest, Mapping) or set(digest) != _DIGEST_FIELDS:
        raise PackSetLockError(
            f"pack {pack_id} manifest digest fields must be exactly algorithm and digest"
        )
    if digest.get("algorithm") != "sha256" or not isinstance(digest.get("digest"), str):
        raise PackSetLockError(f"pack {pack_id} manifest digest must use sha256")
    if _HEX64_RE.fullmatch(str(digest["digest"])) is None:
        raise PackSetLockError(f"pack {pack_id} manifest digest must be 64 lowercase hex chars")

    dependencies = record.get("dependencies")
    if not isinstance(dependencies, list):
        raise PackSetLockError(f"pack {pack_id} dependencies must be a list")
    dependency_ids: list[str] = []
    for dependency in dependencies:
        if not isinstance(dependency, Mapping):
            raise PackSetLockError(f"pack {pack_id} dependency records must be objects")
        if set(dependency) != _DEPENDENCY_FIELDS:
            raise PackSetLockError(
                f"pack {pack_id} dependency fields must be exactly pack_id and required"
            )
        target = dependency.get("pack_id")
        if not isinstance(target, str) or _PACK_ID_RE.fullmatch(target) is None:
            raise PackSetLockError(
                f"pack {pack_id} has invalid dependency pack_id: {target!r}"
            )
        if not isinstance(dependency.get("required"), bool):
            raise PackSetLockError(
                f"pack {pack_id} dependency {target} required flag must be boolean"
            )
        if target in dependency_ids:
            raise PackSetLockError(f"duplicate dependency in lock for pack {pack_id}: {target}")
        dependency_ids.append(target)
    if dependency_ids != sorted(dependency_ids):
        raise PackSetLockError(f"pack {pack_id} dependencies must be sorted by pack_id")


def pack_revisions_from_lock(lock: Mapping[str, Any]) -> dict[str, str]:
    records = _lock_records(lock)
    by_pack: dict[str, str] = {}
    sequence: list[str] = []
    for record in records:
        _validate_lock_record_shape(record)
        pack_id = str(record["pack_id"])
        revision = str(record["revision"])
        if pack_id in by_pack:
            raise PackSetLockError(f"duplicate pack_id in packset lock: {pack_id}")
        by_pack[pack_id] = revision
        sequence.append(pack_id)
    if sequence != sorted(sequence):
        raise PackSetLockError("packset lock pack records must be sorted by pack_id")
    return by_pack


def validate_packset_lock(
    lock: Mapping[str, Any],
    manifests: Mapping[str, Mapping[str, Any]],
) -> None:
    """Validate lock content against the manifests available for replay.

    ``manifests`` may be a catalog superset. The mounted semantic input is exactly
    the pack IDs in the lock; required dependencies must resolve inside that set.
    """

    revisions = pack_revisions_from_lock(lock)
    records = _lock_records(lock)
    mounted = set(revisions)

    missing_manifests = sorted(pack_id for pack_id in mounted if pack_id not in manifests)
    if missing_manifests:
        raise PackSetLockError(
            f"unresolved referenced pack manifest(s): {missing_manifests}"
        )

    mounted_manifests = {pack_id: dict(manifests[pack_id]) for pack_id in mounted}
    validate_pack_dependency_graph(mounted_manifests)

    for record in records:
        pack_id = str(record["pack_id"])
        manifest = mounted_manifests[pack_id]
        dependencies = record["dependencies"]

        for dependency in dependencies:
            target = str(dependency["pack_id"])
            if target not in mounted:
                raise PackSetLockError(
                    f"unresolved referenced pack in lock dependency: {pack_id} -> {target}"
                )

        expected_dependencies = _resolved_dependencies(manifest, mounted)
        normalized_dependencies = [
            {
                "pack_id": str(item["pack_id"]),
                "required": item["required"],
            }
            for item in dependencies
        ]
        if normalized_dependencies != expected_dependencies:
            raise PackSetLockError(
                f"pack {pack_id} dependency metadata differs from validated manifest"
            )

        manifest_digest = record["manifest_digest"]
        expected_digest = canonical_manifest_digest(manifest)
        if manifest_digest["digest"] != expected_digest:
            raise PackSetLockError(
                f"pack {pack_id} manifest digest differs from validated manifest"
            )


def packset_lock_digest(lock: Mapping[str, Any]) -> str:
    """Return the external SHA-256 digest of canonical valid lock content."""

    pack_revisions_from_lock(lock)
    return hashlib.sha256(_canonical_json_bytes(dict(lock))).hexdigest()


__all__ = [
    "PACKSET_LOCK_CONTRACT_VERSION",
    "PackSetLockError",
    "build_packset_lock",
    "canonical_manifest_digest",
    "pack_revisions_from_lock",
    "packset_lock_digest",
    "validate_pack_dependency_graph",
    "validate_packset_lock",
]
