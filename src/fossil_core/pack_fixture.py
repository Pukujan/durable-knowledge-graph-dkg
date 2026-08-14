from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from .artifact_store import ArtifactStore
from .ids import deterministic_event_id
from .lifecycle import KnowledgeState
from .pack import KnowledgePackValidator, PackAccess, PackBoundaryError
from .source import SourceSnapshotStore, _stable_id


class PackFixtureIntegrityError(ValueError):
    """Raised when a durable pack fixture is internally inconsistent."""


@dataclass(frozen=True)
class PackFixtureAudit:
    pack_ids: tuple[str, ...]
    artifact_count: int
    snapshot_count: int
    event_count: int
    citation_count: int
    claim_count: int
    relation_count: int


@dataclass
class _PackContents:
    root: Path
    manifest: dict[str, Any]
    access: PackAccess
    artifacts: dict[str, dict[str, Any]]
    snapshots: dict[str, dict[str, Any]]
    events: list[dict[str, Any]]


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackFixtureIntegrityError(f"invalid JSON fixture {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PackFixtureIntegrityError(f"fixture must contain a JSON object: {path}")
    return value


def _validator(path: Path) -> Draft202012Validator:
    return Draft202012Validator(
        _load_json(path),
        format_checker=FormatChecker(),
    )


def _validate_schema(
    validator: Draft202012Validator,
    value: Mapping[str, Any],
    *,
    label: str,
) -> None:
    try:
        validator.validate(dict(value))
    except ValidationError as exc:
        raise PackFixtureIntegrityError(f"{label} failed schema validation: {exc.message}") from exc


def _artifact_manifest_shape(manifest: Mapping[str, Any], *, label: str) -> None:
    required = {"artifact_id", "content_hash", "byte_size", "media_type"}
    if set(manifest) != required:
        raise PackFixtureIntegrityError(
            f"{label} artifact manifest fields must be exactly {sorted(required)}"
        )
    content_hash = manifest["content_hash"]
    if not isinstance(content_hash, Mapping) or set(content_hash) != {"algorithm", "digest"}:
        raise PackFixtureIntegrityError(f"{label} has invalid content_hash")
    if content_hash["algorithm"] != "sha256":
        raise PackFixtureIntegrityError(f"{label} must use sha256")
    digest = str(content_hash["digest"])
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise PackFixtureIntegrityError(f"{label} has invalid sha256 digest")
    if not isinstance(manifest["byte_size"], int) or manifest["byte_size"] < 0:
        raise PackFixtureIntegrityError(f"{label} has invalid byte_size")
    if not isinstance(manifest["media_type"], str) or not manifest["media_type"]:
        raise PackFixtureIntegrityError(f"{label} has invalid media_type")


def _read_artifacts(root: Path, manifest: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    artifact_root = root / "artifacts"
    discovered: dict[str, dict[str, Any]] = {}
    for path in sorted((artifact_root / "manifests").glob("*/*.json")):
        item = _load_json(path)
        artifact_id = str(item.get("artifact_id", ""))
        _artifact_manifest_shape(item, label=str(path))
        digest = str(item["content_hash"]["digest"])
        expected_id = ArtifactStore.artifact_id_for_digest(digest)
        if artifact_id != expected_id:
            raise PackFixtureIntegrityError(
                f"artifact identity mismatch in {path}: expected {expected_id}, got {artifact_id}"
            )
        expected_path = artifact_root / "manifests" / artifact_id.removeprefix("art_")[:2] / f"{artifact_id}.json"
        if path != expected_path:
            raise PackFixtureIntegrityError(
                f"artifact manifest path does not match stable identity: {path}"
            )
        blob_path = artifact_root / "blobs" / "sha256" / digest[:2] / digest
        if not blob_path.is_file():
            raise PackFixtureIntegrityError(f"artifact blob is missing: {blob_path}")
        data = blob_path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise PackFixtureIntegrityError(f"artifact hash mismatch for {artifact_id}")
        if len(data) != int(item["byte_size"]):
            raise PackFixtureIntegrityError(f"artifact byte_size mismatch for {artifact_id}")
        if artifact_id in discovered:
            raise PackFixtureIntegrityError(f"duplicate artifact manifest: {artifact_id}")
        discovered[artifact_id] = item

    indexed: dict[str, dict[str, Any]] = {}
    for relative in manifest.get("artifact_manifests", []):
        index_path = root / str(relative)
        if not index_path.is_file():
            raise PackFixtureIntegrityError(f"artifact manifest index is missing: {index_path}")
        for number, line in enumerate(index_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise PackFixtureIntegrityError(
                    f"invalid artifact manifest JSONL at {index_path}:{number}"
                ) from exc
            if not isinstance(item, dict):
                raise PackFixtureIntegrityError(
                    f"artifact manifest JSONL entry must be an object at {index_path}:{number}"
                )
            _artifact_manifest_shape(item, label=f"{index_path}:{number}")
            artifact_id = str(item["artifact_id"])
            if artifact_id in indexed:
                raise PackFixtureIntegrityError(f"duplicate artifact index entry: {artifact_id}")
            indexed[artifact_id] = item

    if indexed != discovered:
        missing = sorted(set(discovered) - set(indexed))
        extra = sorted(set(indexed) - set(discovered))
        mismatched = sorted(
            artifact_id
            for artifact_id in set(indexed) & set(discovered)
            if indexed[artifact_id] != discovered[artifact_id]
        )
        raise PackFixtureIntegrityError(
            "artifact manifest index does not match immutable manifests "
            f"(missing={missing}, extra={extra}, mismatched={mismatched})"
        )
    return discovered


def _read_snapshots(
    root: Path,
    artifacts: Mapping[str, Mapping[str, Any]],
    snapshot_validator: Draft202012Validator,
) -> dict[str, dict[str, Any]]:
    snapshots: dict[str, dict[str, Any]] = {}
    snapshot_root = root / "sources" / "snapshots"
    for path in sorted(snapshot_root.glob("*/*.json")):
        snapshot = _load_json(path)
        _validate_schema(snapshot_validator, snapshot, label=str(path))
        snapshot_id = str(snapshot["snapshot_id"])
        expected_path = snapshot_root / snapshot_id.removeprefix("snap_")[:2] / f"{snapshot_id}.json"
        if path != expected_path:
            raise PackFixtureIntegrityError(
                f"source snapshot path does not match stable identity: {path}"
            )
        expected_source_id = SourceSnapshotStore.source_id_for_locator(snapshot["locator"])
        if snapshot["source_id"] != expected_source_id:
            raise PackFixtureIntegrityError(
                f"source_id does not match locator for {snapshot_id}"
            )
        artifact_id = str(snapshot["artifact_id"])
        if artifact_id not in artifacts:
            raise PackFixtureIntegrityError(
                f"source snapshot {snapshot_id} references non-local artifact {artifact_id}"
            )
        artifact = artifacts[artifact_id]
        if snapshot["content_hash"] != artifact["content_hash"]:
            raise PackFixtureIntegrityError(
                f"source snapshot content hash disagrees with artifact {artifact_id}"
            )
        version = {
            "etag": None,
            "last_modified": None,
            "version_id": None,
            "commit_sha": None,
            **dict(snapshot["version_metadata"]),
        }
        expected_snapshot_id = _stable_id(
            "snap",
            str(snapshot["source_id"]),
            str(snapshot["content_hash"]["digest"]),
            str(snapshot["retrieved_at"]),
            json.dumps(version, sort_keys=True, separators=(",", ":")),
        )
        if snapshot_id != expected_snapshot_id:
            raise PackFixtureIntegrityError(
                f"snapshot_id does not match immutable snapshot identity: {snapshot_id}"
            )
        role = str(snapshot["source_role"])
        derivation = snapshot["derivation"]
        if role in {"derived", "reconstructed"}:
            if not isinstance(derivation, Mapping) or not derivation.get("parent_snapshot_refs"):
                raise PackFixtureIntegrityError(
                    f"{role} snapshot requires parent_snapshot_refs: {snapshot_id}"
                )
        elif derivation is not None:
            raise PackFixtureIntegrityError(
                f"non-derived snapshot must not claim derivation: {snapshot_id}"
            )
        if snapshot_id in snapshots:
            raise PackFixtureIntegrityError(f"duplicate source snapshot: {snapshot_id}")
        snapshots[snapshot_id] = snapshot
    return snapshots


def _read_events(
    root: Path,
    manifest: Mapping[str, Any],
    event_validator: Draft202012Validator,
) -> list[dict[str, Any]]:
    pack_id = str(manifest["pack_id"])
    access = PackAccess.from_manifest(dict(manifest))
    events: list[dict[str, Any]] = []
    seen: set[str] = set()
    for relative in manifest["event_roots"]:
        event_root = root / str(relative)
        if not event_root.is_dir():
            raise PackFixtureIntegrityError(f"event root is missing: {event_root}")
        for path in sorted(event_root.glob("*/*.json")):
            event = _load_json(path)
            _validate_schema(event_validator, event, label=str(path))
            event_id = str(event["event_id"])
            if event_id in seen:
                raise PackFixtureIntegrityError(f"duplicate event_id in pack: {event_id}")
            seen.add(event_id)
            if event["pack_id"] != pack_id:
                raise PackFixtureIntegrityError(
                    f"event {event_id} belongs to {event['pack_id']} but is stored in {pack_id}"
                )
            try:
                access.require_write(pack_id)
            except PackBoundaryError as exc:
                raise PackFixtureIntegrityError(
                    f"pack {pack_id} contains events but cannot write itself"
                ) from exc
            idem = event.get("idempotency_key")
            if idem:
                expected = deterministic_event_id(pack_id, str(idem))
                if event_id != expected:
                    raise PackFixtureIntegrityError(
                        f"event_id does not match deterministic idempotency identity: {event_id}"
                    )
            expected_path = event_root / event_id.removeprefix("evt_")[:2] / f"{event_id}.json"
            if path != expected_path:
                raise PackFixtureIntegrityError(
                    f"event path does not match stable identity: {path}"
                )
            events.append(event)
    return events


def _owners(index: Mapping[str, set[str]], identifier: str, *, kind: str) -> set[str]:
    owners = index.get(identifier, set())
    if not owners:
        raise PackFixtureIntegrityError(f"unknown {kind} reference: {identifier}")
    return owners


def _require_readable_owner(
    *,
    access: PackAccess,
    owners: set[str],
    identifier: str,
    kind: str,
) -> str:
    readable = sorted(owners & set(access.read_mounts))
    if not readable:
        raise PackFixtureIntegrityError(
            f"{kind} {identifier} exists only in packs not mounted by {access.pack_id}: {sorted(owners)}"
        )
    return readable[0]


def _citation_bytes(
    citation: Mapping[str, Any],
    *,
    access: PackAccess,
    packs: Mapping[str, _PackContents],
    snapshot_owners: Mapping[str, set[str]],
    citation_validator: Draft202012Validator,
) -> bytes:
    _validate_schema(citation_validator, citation, label=f"citation {citation.get('citation_id')}")
    snapshot_id = str(citation["snapshot_id"])
    owner = _require_readable_owner(
        access=access,
        owners=_owners(snapshot_owners, snapshot_id, kind="source snapshot"),
        identifier=snapshot_id,
        kind="source snapshot",
    )
    snapshot = packs[owner].snapshots[snapshot_id]
    if snapshot["artifact_id"] != citation["artifact_id"]:
        raise PackFixtureIntegrityError(
            f"citation artifact does not match source snapshot: {citation['citation_id']}"
        )
    artifact_id = str(citation["artifact_id"])
    artifact = packs[owner].artifacts[artifact_id]
    digest = str(artifact["content_hash"]["digest"])
    data = (packs[owner].root / "artifacts" / "blobs" / "sha256" / digest[:2] / digest).read_bytes()
    start = citation["byte_start"]
    end = citation["byte_end"]
    if (start is None) != (end is None):
        raise PackFixtureIntegrityError(
            f"citation span must provide both endpoints: {citation['citation_id']}"
        )
    if start is None:
        passage = data
        passage_digest = "whole-artifact"
        if citation["passage_hash"] is not None:
            raise PackFixtureIntegrityError(
                f"whole-artifact citation must not include passage_hash: {citation['citation_id']}"
            )
    else:
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start or end > len(data):
            raise PackFixtureIntegrityError(
                f"citation span is outside source artifact bounds: {citation['citation_id']}"
            )
        passage = data[start:end]
        passage_digest = hashlib.sha256(passage).hexdigest()
        passage_hash = citation["passage_hash"]
        if not isinstance(passage_hash, Mapping) or passage_hash.get("digest") != passage_digest:
            raise PackFixtureIntegrityError(
                f"citation passage hash does not match source bytes: {citation['citation_id']}"
            )
    expected_id = _stable_id(
        "cite",
        snapshot_id,
        artifact_id,
        str(start),
        str(end),
        passage_digest,
    )
    if citation["citation_id"] != expected_id:
        raise PackFixtureIntegrityError(
            f"citation_id does not match immutable citation identity: {citation['citation_id']}"
        )
    return passage


def validate_pack_fixtures(
    pack_roots: Iterable[Path],
    *,
    schemas_root: Path,
) -> PackFixtureAudit:
    """Audit durable pack fixture repositories without mutating them.

    The audit verifies schema-valid pack/event/source/citation data, content-addressed
    artifact integrity, stable derived identities, mount-aware cross-pack references,
    and deterministic lifecycle replay. It is intentionally projection-independent.
    """

    roots = [Path(root) for root in pack_roots]
    if not roots:
        raise PackFixtureIntegrityError("at least one pack root is required")
    schemas_root = Path(schemas_root)
    pack_validator = KnowledgePackValidator(schemas_root / "knowledge-pack" / "v1.schema.json")
    event_validator = _validator(schemas_root / "events" / "v1.schema.json")
    snapshot_validator = _validator(schemas_root / "source-snapshot" / "v1.schema.json")
    citation_validator = _validator(schemas_root / "citation" / "v1.schema.json")

    manifest_by_root: dict[Path, dict[str, Any]] = {}
    for root in roots:
        manifest_path = root / "manifest.json"
        manifest_by_root[root] = _load_json(manifest_path)
    try:
        manifests = pack_validator.validate_set(manifest_by_root.values())
    except (ValidationError, PackBoundaryError) as exc:
        raise PackFixtureIntegrityError(f"knowledge-pack manifest set is invalid: {exc}") from exc

    root_by_pack = {
        str(manifest["pack_id"]): root
        for root, manifest in manifest_by_root.items()
    }
    if set(root_by_pack) != set(manifests):
        raise PackFixtureIntegrityError("pack roots must have unique pack IDs")

    packs: dict[str, _PackContents] = {}
    for pack_id, manifest in manifests.items():
        root = root_by_pack[pack_id]
        artifacts = _read_artifacts(root, manifest)
        snapshots = _read_snapshots(root, artifacts, snapshot_validator)
        events = _read_events(root, manifest, event_validator)
        packs[pack_id] = _PackContents(
            root=root,
            manifest=manifest,
            access=PackAccess.from_manifest(manifest),
            artifacts=artifacts,
            snapshots=snapshots,
            events=events,
        )

    artifact_owners: dict[str, set[str]] = {}
    snapshot_owners: dict[str, set[str]] = {}
    event_owners: dict[str, set[str]] = {}
    claim_owners: dict[str, set[str]] = {}
    relation_owners: dict[str, set[str]] = {}
    for pack_id, pack in packs.items():
        for artifact_id in pack.artifacts:
            artifact_owners.setdefault(artifact_id, set()).add(pack_id)
        for snapshot_id in pack.snapshots:
            snapshot_owners.setdefault(snapshot_id, set()).add(pack_id)
        for event in pack.events:
            event_id = str(event["event_id"])
            event_owners.setdefault(event_id, set()).add(pack_id)
            if event["event_type"] == "claim.proposed":
                claim_owners.setdefault(str(event["subject_refs"][0]), set()).add(pack_id)
            if event["event_type"] == "relation.proposed":
                relation_owners.setdefault(str(event["payload"]["relation_id"]), set()).add(pack_id)

    for kind, index in (("event", event_owners), ("claim", claim_owners), ("relation", relation_owners)):
        duplicates = sorted(identifier for identifier, owners in index.items() if len(owners) > 1)
        if duplicates:
            raise PackFixtureIntegrityError(f"globally duplicate {kind} IDs across packs: {duplicates}")

    citation_count = 0
    for pack_id, pack in packs.items():
        access = pack.access
        for snapshot_id, snapshot in pack.snapshots.items():
            derivation = snapshot.get("derivation")
            if not isinstance(derivation, Mapping):
                continue
            for parent_id in derivation.get("parent_snapshot_refs", []):
                _require_readable_owner(
                    access=access,
                    owners=_owners(snapshot_owners, str(parent_id), kind="parent source snapshot"),
                    identifier=str(parent_id),
                    kind="parent source snapshot",
                )

        for event in pack.events:
            for artifact_id in event.get("evidence_refs", []):
                _require_readable_owner(
                    access=access,
                    owners=_owners(artifact_owners, str(artifact_id), kind="artifact"),
                    identifier=str(artifact_id),
                    kind="artifact",
                )
            for snapshot_id in event.get("source_snapshot_refs", []):
                _require_readable_owner(
                    access=access,
                    owners=_owners(snapshot_owners, str(snapshot_id), kind="source snapshot"),
                    identifier=str(snapshot_id),
                    kind="source snapshot",
                )
            for caused_by in event.get("caused_by_event_ids", []):
                _require_readable_owner(
                    access=access,
                    owners=_owners(event_owners, str(caused_by), kind="causal event"),
                    identifier=str(caused_by),
                    kind="causal event",
                )

            citation = event.get("payload", {}).get("citation")
            if isinstance(citation, Mapping):
                _citation_bytes(
                    citation,
                    access=access,
                    packs=packs,
                    snapshot_owners=snapshot_owners,
                    citation_validator=citation_validator,
                )
                citation_count += 1

            if event["event_type"] == "relation.proposed":
                for side in ("source_ref", "target_ref"):
                    reference = str(event["payload"][side])
                    if not reference.startswith("clm_"):
                        continue
                    _require_readable_owner(
                        access=access,
                        owners=_owners(claim_owners, reference, kind="claim"),
                        identifier=reference,
                        kind="claim",
                    )

        ordered = sorted(pack.events, key=lambda event: (str(event["recorded_at"]), str(event["event_id"])))
        try:
            KnowledgeState.replay(ordered)
        except (KeyError, ValueError) as exc:
            raise PackFixtureIntegrityError(
                f"lifecycle replay failed for pack {pack_id}: {exc}"
            ) from exc

    return PackFixtureAudit(
        pack_ids=tuple(sorted(packs)),
        artifact_count=sum(len(pack.artifacts) for pack in packs.values()),
        snapshot_count=sum(len(pack.snapshots) for pack in packs.values()),
        event_count=sum(len(pack.events) for pack in packs.values()),
        citation_count=citation_count,
        claim_count=len(claim_owners),
        relation_count=len(relation_owners),
    )
