from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from fossil_core.adapters.filesystem.artifact_store import (
    ArtifactIntegrityError,
    ArtifactStore,
)


def test_artifact_store_layout_and_reopen_are_stable(tmp_path: Path) -> None:
    root = tmp_path / "nested" / "artifacts"
    store = ArtifactStore(root)

    assert store.root == root
    assert store.blobs == root / "blobs" / "sha256"
    assert store.manifests == root / "manifests"
    assert store.redactions == root / "redactions"
    assert store.blobs.is_dir()
    assert store.manifests.is_dir()
    assert store.redactions.is_dir()

    reopened = ArtifactStore(root)
    assert reopened.blobs == store.blobs
    assert reopened.manifests == store.manifests
    assert reopened.redactions == store.redactions


def test_artifact_paths_use_exact_two_character_shards(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")
    data = b"stable artifact shard fixture"
    digest = hashlib.sha256(data).hexdigest()
    artifact_id = f"art_{digest[:32]}"

    assert store._blob_path(digest) == store.blobs / digest[:2] / digest
    assert store._manifest_path(artifact_id) == (
        store.manifests / digest[:2] / f"{artifact_id}.json"
    )
    assert store._redaction_path(artifact_id) == (
        store.redactions / digest[:2] / f"{artifact_id}.json"
    )


def test_canonical_artifact_json_is_sorted_compact_utf8_with_trailing_newline() -> None:
    value = {"z": "π", "a": {"b": 2, "a": 1}}

    assert ArtifactStore._canonical(value) == (
        '{"a":{"a":1,"b":2},"z":"π"}\n'.encode("utf-8")
    )


def test_put_bytes_default_media_type_and_exact_manifest_bytes(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")
    data = b"default media type fixture"
    digest = hashlib.sha256(data).hexdigest()

    manifest = store.put_bytes(data)

    assert manifest == {
        "artifact_id": f"art_{digest[:32]}",
        "content_hash": {"algorithm": "sha256", "digest": digest},
        "byte_size": len(data),
        "media_type": "application/octet-stream",
    }
    assert store._manifest_path(manifest["artifact_id"]).read_bytes() == store._canonical(
        manifest
    )


def test_put_file_reads_exact_bytes_and_preserves_media_type(tmp_path: Path) -> None:
    source = tmp_path / "evidence.bin"
    source.write_bytes(b"\x00artifact-file\xff")
    store = ArtifactStore(tmp_path / "artifacts")

    manifest = store.put_file(source, media_type="application/x-fossil-fixture")

    assert manifest["content_hash"]["digest"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert manifest["byte_size"] == len(source.read_bytes())
    assert manifest["media_type"] == "application/x-fossil-fixture"
    assert store.read_bytes(manifest["artifact_id"]) == source.read_bytes()


def test_put_file_default_media_type_is_octet_stream(tmp_path: Path) -> None:
    source = tmp_path / "evidence.bin"
    source.write_bytes(b"artifact-file-default")
    store = ArtifactStore(tmp_path / "artifacts")

    assert store.put_file(source)["media_type"] == "application/octet-stream"


def test_reput_detects_corrupted_existing_blob(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")
    data = b"immutable artifact bytes"
    manifest = store.put_bytes(data)
    blob_path = store._blob_path(manifest["content_hash"]["digest"])
    blob_path.write_bytes(b"corrupted artifact byte")

    with pytest.raises(ArtifactIntegrityError, match="hash collision or corrupted blob"):
        store.put_bytes(data)


def test_reput_detects_conflicting_existing_manifest(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")
    data = b"immutable manifest fixture"
    manifest = store.put_bytes(data, media_type="text/plain")
    path = store._manifest_path(manifest["artifact_id"])
    conflicting = dict(manifest)
    conflicting["media_type"] = "application/json"
    path.write_text(json.dumps(conflicting), encoding="utf-8")

    with pytest.raises(ArtifactIntegrityError, match="manifest conflict"):
        store.put_bytes(data, media_type="text/plain")


def test_get_redaction_is_none_before_redaction(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")
    artifact_id = store.put_bytes(b"not redacted")["artifact_id"]

    assert store.is_redacted(artifact_id) is False
    assert store.get_redaction(artifact_id) is None


def test_verify_rejects_same_length_digest_corruption(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")
    manifest = store.put_bytes(b"abcdefgh")
    blob_path = store._blob_path(manifest["content_hash"]["digest"])
    blob_path.write_bytes(b"ABCDEFGH")

    with pytest.raises(ArtifactIntegrityError, match="artifact verification failed"):
        store.verify(manifest["artifact_id"])


def test_verify_rejects_size_mismatch_even_when_digest_matches(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")
    manifest = store.put_bytes(b"size integrity fixture")
    path = store._manifest_path(manifest["artifact_id"])
    tampered = dict(manifest)
    tampered["byte_size"] = manifest["byte_size"] + 1
    path.write_bytes(store._canonical(tampered))

    with pytest.raises(ArtifactIntegrityError, match="artifact verification failed"):
        store.verify(manifest["artifact_id"])


@pytest.mark.parametrize(
    ("reason", "authority", "redacted_at"),
    [
        ("", "privacy-officer", "2026-08-19T06:00:00Z"),
        ("privacy request", "", "2026-08-19T06:00:00Z"),
        ("privacy request", "privacy-officer", ""),
    ],
)
def test_redaction_rejects_each_missing_required_field(
    tmp_path: Path,
    reason: str,
    authority: str,
    redacted_at: str,
) -> None:
    store = ArtifactStore(tmp_path / "artifacts")
    artifact_id = store.put_bytes(b"redaction required field fixture")["artifact_id"]

    with pytest.raises(
        ValueError, match="redaction requires reason, authority, and redacted_at"
    ):
        store.redact(
            artifact_id,
            reason=reason,
            authority=authority,
            redacted_at=redacted_at,
        )


def test_redaction_tombstone_is_exact_canonical_record_and_blob_is_removed(
    tmp_path: Path,
) -> None:
    store = ArtifactStore(tmp_path / "artifacts")
    data = b"sensitive artifact fixture"
    manifest = store.put_bytes(data, media_type="text/plain")
    artifact_id = manifest["artifact_id"]

    record = store.redact(
        artifact_id,
        reason="privacy request",
        authority="privacy-officer",
        redacted_at="2026-08-19T06:00:00Z",
        request_ref="request-42",
    )

    assert record == {
        "artifact_id": artifact_id,
        "redacted_at": "2026-08-19T06:00:00Z",
        "reason": "privacy request",
        "authority": "privacy-officer",
        "request_ref": "request-42",
        "content_hash": manifest["content_hash"],
        "byte_size": len(data),
        "media_type": "text/plain",
    }
    assert store._redaction_path(artifact_id).read_bytes() == store._canonical(record)
    assert not store._blob_path(manifest["content_hash"]["digest"]).exists()
    assert store.get_redaction(artifact_id) == record


def test_redaction_rejects_conflicting_existing_tombstone(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")
    artifact_id = store.put_bytes(b"redaction conflict fixture")["artifact_id"]
    store.redact(
        artifact_id,
        reason="first reason",
        authority="privacy-officer",
        redacted_at="2026-08-19T06:00:00Z",
    )

    with pytest.raises(ArtifactIntegrityError, match="redaction tombstone conflict"):
        store.redact(
            artifact_id,
            reason="different reason",
            authority="privacy-officer",
            redacted_at="2026-08-19T06:00:00Z",
        )
