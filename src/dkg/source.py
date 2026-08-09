from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator, FormatChecker

from dkg.artifact_store import ArtifactRedactedError, ArtifactStore
from dkg.io import publish_immutable


class SourceSnapshotConflict(RuntimeError):
    pass


class CitationIntegrityError(RuntimeError):
    pass


class CitationLaunderingError(ValueError):
    pass


def _canonical(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def _stable_id(prefix: str, *parts: str, length: int = 24) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:length]}"


class SourceSnapshotStore:
    """Immutable observations of mutable/remote/local source evidence."""

    def __init__(
        self,
        root: Path,
        artifact_store: ArtifactStore,
        snapshot_schema_path: Path,
        citation_schema_path: Path,
    ):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.artifact_store = artifact_store
        snapshot_schema = json.loads(Path(snapshot_schema_path).read_text(encoding="utf-8"))
        citation_schema = json.loads(Path(citation_schema_path).read_text(encoding="utf-8"))
        self.snapshot_validator = Draft202012Validator(
            snapshot_schema, format_checker=FormatChecker()
        )
        self.citation_validator = Draft202012Validator(
            citation_schema, format_checker=FormatChecker()
        )

    @staticmethod
    def source_id_for_locator(locator: Mapping[str, Any]) -> str:
        return _stable_id(
            "source",
            json.dumps(locator, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
            length=20,
        )

    def _snapshot_path(self, snapshot_id: str) -> Path:
        suffix = snapshot_id.removeprefix("snap_")
        return self.root / "snapshots" / suffix[:2] / f"{snapshot_id}.json"

    def put_snapshot(
        self,
        data: bytes,
        *,
        locator: Mapping[str, Any],
        retrieved_at: str,
        source_role: str,
        quality: Mapping[str, Any],
        published_at: str | None = None,
        version_metadata: Mapping[str, Any] | None = None,
        derivation: Mapping[str, Any] | None = None,
        media_type: str = "application/octet-stream",
        source_id: str | None = None,
    ) -> dict[str, Any]:
        artifact = self.artifact_store.put_bytes(data, media_type=media_type)
        source_id = source_id or self.source_id_for_locator(locator)
        version = {
            "etag": None,
            "last_modified": None,
            "version_id": None,
            "commit_sha": None,
            **dict(version_metadata or {}),
        }
        if source_role in {"derived", "reconstructed"}:
            if not derivation or not derivation.get("parent_snapshot_refs"):
                raise ValueError(
                    f"{source_role} snapshot requires explicit parent_snapshot_refs"
                )
            for parent_id in derivation["parent_snapshot_refs"]:
                self.get_snapshot(parent_id)
        elif derivation is not None:
            raise ValueError("primary/secondary/local snapshots must not claim derivation")

        snapshot_id = _stable_id(
            "snap",
            source_id,
            artifact["content_hash"]["digest"],
            retrieved_at,
            json.dumps(version, sort_keys=True, separators=(",", ":")),
        )
        snapshot = {
            "schema_version": "fossil.source-snapshot.v1",
            "snapshot_id": snapshot_id,
            "source_id": source_id,
            "source_role": source_role,
            "locator": {
                "url": locator.get("url"),
                "identifier": locator.get("identifier"),
                "repository_ref": locator.get("repository_ref"),
            },
            "retrieved_at": retrieved_at,
            "published_at": published_at,
            "artifact_id": artifact["artifact_id"],
            "content_hash": artifact["content_hash"],
            "version_metadata": version,
            "quality": copy.deepcopy(dict(quality)),
            "derivation": copy.deepcopy(dict(derivation)) if derivation else None,
        }
        self.snapshot_validator.validate(snapshot)
        path = self._snapshot_path(snapshot_id)
        encoded = _canonical(snapshot)
        if not publish_immutable(path, encoded):
            existing = json.loads(path.read_text(encoding="utf-8"))
            if _canonical(existing) != encoded:
                raise SourceSnapshotConflict(snapshot_id)
            return existing
        return snapshot

    def get_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        return json.loads(self._snapshot_path(snapshot_id).read_text(encoding="utf-8"))

    def iter_snapshots(self) -> Iterable[dict[str, Any]]:
        for path in sorted((self.root / "snapshots").glob("*/*.json")):
            yield json.loads(path.read_text(encoding="utf-8"))

    def versions(self, source_id: str) -> list[dict[str, Any]]:
        return sorted(
            [snapshot for snapshot in self.iter_snapshots() if snapshot["source_id"] == source_id],
            key=lambda snapshot: (snapshot["retrieved_at"], snapshot["snapshot_id"]),
        )

    def create_citation(
        self,
        snapshot_id: str,
        *,
        byte_start: int | None = None,
        byte_end: int | None = None,
    ) -> dict[str, Any]:
        snapshot = self.get_snapshot(snapshot_id)
        artifact_id = snapshot["artifact_id"]
        data = self.artifact_store.read_bytes(artifact_id)
        passage_hash = None
        if (byte_start is None) != (byte_end is None):
            raise ValueError("citation byte_start and byte_end must be supplied together")
        if byte_start is not None and byte_end is not None:
            if byte_start < 0 or byte_end <= byte_start or byte_end > len(data):
                raise ValueError("citation span is outside source artifact bounds")
            passage = data[byte_start:byte_end]
            passage_hash = {
                "algorithm": "sha256",
                "digest": hashlib.sha256(passage).hexdigest(),
            }
        citation_id = _stable_id(
            "cite",
            snapshot_id,
            artifact_id,
            str(byte_start),
            str(byte_end),
            passage_hash["digest"] if passage_hash else "whole-artifact",
        )
        citation = {
            "schema_version": "fossil.citation.v1",
            "citation_id": citation_id,
            "snapshot_id": snapshot_id,
            "artifact_id": artifact_id,
            "byte_start": byte_start,
            "byte_end": byte_end,
            "passage_hash": passage_hash,
        }
        self.citation_validator.validate(citation)
        return citation

    def resolve_citation(
        self,
        citation: Mapping[str, Any],
        *,
        allowed_source_roles: set[str] | None = None,
    ) -> dict[str, Any]:
        candidate = copy.deepcopy(dict(citation))
        self.citation_validator.validate(candidate)
        snapshot = self.get_snapshot(candidate["snapshot_id"])
        if snapshot["artifact_id"] != candidate["artifact_id"]:
            raise CitationIntegrityError(
                "citation artifact does not match the immutable source snapshot"
            )
        if allowed_source_roles is not None and snapshot["source_role"] not in allowed_source_roles:
            raise CitationLaunderingError(
                f"source role {snapshot['source_role']} cannot satisfy required roles "
                f"{sorted(allowed_source_roles)}"
            )
        data = self.artifact_store.read_bytes(candidate["artifact_id"])
        start = candidate["byte_start"]
        end = candidate["byte_end"]
        passage = data if start is None else data[int(start) : int(end)]
        if candidate["passage_hash"] is not None:
            digest = hashlib.sha256(passage).hexdigest()
            if digest != candidate["passage_hash"]["digest"]:
                raise CitationIntegrityError("citation passage hash does not match source bytes")
        return {
            "citation": candidate,
            "snapshot": snapshot,
            "bytes": passage,
            "text": self._decode_text(passage),
        }

    @staticmethod
    def _decode_text(data: bytes) -> str | None:
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return None

    def artifact_for_snapshot(self, snapshot_id: str) -> str:
        return str(self.get_snapshot(snapshot_id)["artifact_id"])

    def snapshot_is_redacted(self, snapshot_id: str) -> bool:
        return self.artifact_store.is_redacted(self.artifact_for_snapshot(snapshot_id))

    def export_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        snapshot = self.get_snapshot(snapshot_id)
        artifact_id = snapshot["artifact_id"]
        if self.artifact_store.is_redacted(artifact_id):
            return {
                "snapshot": snapshot,
                "content": None,
                "redacted": True,
                "redaction": self.artifact_store.get_redaction(artifact_id),
            }
        return {
            "snapshot": snapshot,
            "content": self.artifact_store.read_bytes(artifact_id),
            "redacted": False,
            "redaction": None,
        }


@dataclass(frozen=True)
class SourceStatus:
    snapshot_id: str
    state: str
    reason: str | None
    last_event_id: str


class SourceLifecycleState:
    """Replay explicit source staleness/retraction/restoration events."""

    VALID = {"source.stale", "source.retracted", "source.restored"}

    def __init__(self) -> None:
        self.statuses: dict[str, SourceStatus] = {}

    @classmethod
    def replay(cls, events: Iterable[Mapping[str, Any]]) -> "SourceLifecycleState":
        state = cls()
        for event in sorted(
            (event for event in events if event.get("event_type") in cls.VALID),
            key=lambda event: (str(event["recorded_at"]), str(event["event_id"])),
        ):
            snapshot_id = str(event["payload"]["snapshot_id"])
            event_type = str(event["event_type"])
            new_state = {
                "source.stale": "stale",
                "source.retracted": "retracted",
                "source.restored": "active",
            }[event_type]
            state.statuses[snapshot_id] = SourceStatus(
                snapshot_id=snapshot_id,
                state=new_state,
                reason=event["payload"].get("reason"),
                last_event_id=str(event["event_id"]),
            )
        return state

    def status(self, snapshot_id: str) -> str:
        return self.statuses.get(
            snapshot_id, SourceStatus(snapshot_id, "active", None, "")
        ).state


def build_source_state_event(
    *,
    event_type: str,
    snapshot_id: str,
    source_id: str,
    pack_id: str,
    actor: Mapping[str, Any],
    occurred_at: str,
    recorded_at: str,
    idempotency_key: str,
    reason: str,
) -> dict[str, Any]:
    if event_type not in SourceLifecycleState.VALID:
        raise ValueError(f"unsupported source lifecycle event: {event_type}")
    return {
        "schema_version": "dkg.event.v1",
        "event_type": event_type,
        "occurred_at": occurred_at,
        "recorded_at": recorded_at,
        "pack_id": pack_id,
        "actor": dict(actor),
        "subject_refs": [snapshot_id, source_id],
        "idempotency_key": idempotency_key,
        "source_snapshot_refs": [snapshot_id],
        "payload": {
            "snapshot_id": snapshot_id,
            "source_id": source_id,
            "reason": reason,
        },
        "provenance": {"method": "source_lifecycle"},
    }


class RedactionPolicy:
    """Shared visibility policy for exports and materialized projections."""

    def __init__(self, source_store: SourceSnapshotStore):
        self.source_store = source_store

    def event_visible(self, event: Mapping[str, Any]) -> bool:
        for artifact_id in event.get("evidence_refs", []):
            if self.source_store.artifact_store.is_redacted(str(artifact_id)):
                return False
        for snapshot_id in event.get("source_snapshot_refs", []):
            try:
                if self.source_store.snapshot_is_redacted(str(snapshot_id)):
                    return False
            except FileNotFoundError:
                # Unknown snapshot references are not silently treated as redacted;
                # snapshot integrity is validated separately by citation/source audit.
                continue
        return True

    def visible_events(self, events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        return [event for event in events if self.event_visible(event)]

    def export_event(self, event: Mapping[str, Any]) -> dict[str, Any] | None:
        return copy.deepcopy(dict(event)) if self.event_visible(event) else None


def build_redaction_event(
    *,
    tombstone: Mapping[str, Any],
    pack_id: str,
    actor: Mapping[str, Any],
    occurred_at: str,
    recorded_at: str,
    idempotency_key: str,
    snapshot_ids: Iterable[str] = (),
) -> dict[str, Any]:
    return {
        "schema_version": "dkg.event.v1",
        "event_type": "evidence.redacted",
        "occurred_at": occurred_at,
        "recorded_at": recorded_at,
        "pack_id": pack_id,
        "actor": dict(actor),
        "subject_refs": [str(tombstone["artifact_id"]), *list(snapshot_ids)],
        "idempotency_key": idempotency_key,
        "payload": {
            "artifact_id": tombstone["artifact_id"],
            "snapshot_ids": list(snapshot_ids),
            "reason": tombstone["reason"],
            "authority": tombstone["authority"],
            "request_ref": tombstone.get("request_ref"),
            "redacted_at": tombstone["redacted_at"],
        },
        "provenance": {"method": "artifact_redaction_tombstone"},
    }
