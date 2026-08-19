from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from fossil_core.artifact_store import (
    ArtifactIntegrityError,
    ArtifactRedactedError,
    ArtifactStore,
)


def test_constructor_creates_stable_nested_store_layout_and_reopens(tmp_path: Path):
    root = tmp_path / "nested" / "durable" / "objects"
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


def test_canonical_bytes_are_stable_compact_sorted_utf8_json():
    assert ArtifactStore._canonical({"z": "café", "a": [2, 1]}) == (
        '{"a":[2,1],"z":"café"}\n'.encode("utf-8")
    )


def test_artifact_store_is_content_addressed_and_verifiable(tmp_path: Path):
    store = ArtifactStore(tmp_path / "objects")
    data = b"hello durable evidence"
    digest = hashlib.sha256(data).hexdigest()
    first = store.put_bytes(data, media_type="text/plain")
    second = store.put_bytes(data, media_type="text/plain")
    artifact_id = f"art_{digest[:32]}"

    assert first == second == {
        "artifact_id": artifact_id,
        "content_hash": {"algorithm": "sha256", "digest": digest},
        "byte_size": len(data),
        "media_type": "text/plain",
    }
    assert store._blob_path(digest) == store.blobs / digest[:2] / digest
    assert store._manifest_path(artifact_id) == (
        store.manifests / artifact_id.removeprefix("art_")[:2] / f"{artifact_id}.json"
    )
    assert store._manifest_path(artifact_id).read_bytes() == ArtifactStore._canonical(first)
    assert store.read_bytes(artifact_id) == data
    assert store.verify(artifact_id)


def test_put_bytes_default_media_type_is_durable(tmp_path: Path):
    store = ArtifactStore(tmp_path / "objects")
    manifest = store.put_bytes(b"default media type")
    assert manifest["media_type"] == "application/octet-stream"
    assert store.get_manifest(manifest["artifact_id"]) == manifest


def test_put_file_reads_exact_bytes_and_forwards_media_type(tmp_path: Path):
    store = ArtifactStore(tmp_path / "objects")
    source = tmp_path / "source.bin"
    source.write_bytes(b"file-backed evidence\x00\xff")

    manifest = store.put_file(source, media_type="application/x-fossil-fixture")

    assert manifest["media_type"] == "application/x-fossil-fixture"
    assert manifest["byte_size"] == len(source.read_bytes())
    assert store.read_bytes(manifest["artifact_id"]) == source.read_bytes()

    default_source = tmp_path / "default.bin"
    default_source.write_bytes(b"different bytes for default media")
    default_manifest = store.put_file(default_source)
    assert default_manifest["media_type"] == "application/octet-stream"


def test_existing_corrupted_blob_is_rejected_on_idempotent_retry(tmp_path: Path):
    store = ArtifactStore(tmp_path / "objects")
    data = b"immutable blob"
    manifest = store.put_bytes(data)
    digest = manifest["content_hash"]["digest"]
    store._blob_path(digest).write_bytes(b"corrupted blob")

    with pytest.raises(ArtifactIntegrityError):
        store.put_bytes(data)


def test_same_content_cannot_change_manifest_metadata(tmp_path: Path):
    store = ArtifactStore(tmp_path / "objects")
    data = b"same identity means same manifest"
    store.put_bytes(data, media_type="text/plain")

    with pytest.raises(ArtifactIntegrityError):
        store.put_bytes(data, media_type="application/octet-stream")


def test_get_redaction_returns_none_when_no_tombstone_exists(tmp_path: Path):
    store = ArtifactStore(tmp_path / "objects")
    assert store.get_redaction("art_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa") is None


def test_artifact_tamper_is_detected_when_digest_alone_changes(tmp_path: Path):
    store = ArtifactStore(tmp_path / "objects")
    manifest = store.put_bytes(b"abc")
    digest = manifest["content_hash"]["digest"]
    store._blob_path(digest).write_bytes(b"xyz")

    with pytest.raises(ArtifactIntegrityError):
        store.verify(manifest["artifact_id"])


def test_artifact_tamper_is_detected_when_size_alone_changes(tmp_path: Path):
    store = ArtifactStore(tmp_path / "objects")
    manifest = store.put_bytes(b"size-fixture")
    changed = dict(manifest)
    changed["byte_size"] = manifest["byte_size"] + 1
    store._manifest_path(manifest["artifact_id"]).write_bytes(
        ArtifactStore._canonical(changed)
    )

    with pytest.raises(ArtifactIntegrityError):
        store.verify(manifest["artifact_id"])


@pytest.mark.parametrize("missing", ["reason", "authority", "redacted_at"])
def test_redaction_requires_complete_authorization_metadata(tmp_path: Path, missing: str):
    store = ArtifactStore(tmp_path / "objects")
    manifest = store.put_bytes(b"authorized redaction")
    kwargs = {
        "reason": "privacy erasure request",
        "authority": "fixture-data-controller",
        "redacted_at": "2026-08-19T06:35:00Z",
        "request_ref": "erase-required-fields",
    }
    kwargs[missing] = ""

    with pytest.raises(ValueError):
        store.redact(manifest["artifact_id"], **kwargs)

    assert store.read_bytes(manifest["artifact_id"]) == b"authorized redaction"
    assert store.get_redaction(manifest["artifact_id"]) is None


def test_redaction_publishes_exact_tombstone_before_removing_blob_and_blocks_resurrection(
    tmp_path: Path,
):
    store = ArtifactStore(tmp_path / "objects")
    data = b"sensitive artifact payload"
    manifest = store.put_bytes(data, media_type="text/plain")
    artifact_id = manifest["artifact_id"]
    digest = manifest["content_hash"]["digest"]
    blob_path = store._blob_path(digest)
    suffix = artifact_id.removeprefix("art_")
    expected_path = store.redactions / suffix[:2] / f"{artifact_id}.json"
    expected = {
        "artifact_id": artifact_id,
        "redacted_at": "2026-08-19T06:36:00Z",
        "reason": "privacy deletion",
        "authority": "fixture-privacy-officer",
        "request_ref": "erase-36",
        "content_hash": manifest["content_hash"],
        "byte_size": len(data),
        "media_type": "text/plain",
    }

    tombstone = store.redact(
        artifact_id,
        reason=expected["reason"],
        authority=expected["authority"],
        redacted_at=expected["redacted_at"],
        request_ref=expected["request_ref"],
    )

    assert tombstone == expected
    assert store._redaction_path(artifact_id) == expected_path
    assert expected_path.read_bytes() == ArtifactStore._canonical(expected)
    assert not blob_path.exists()
    assert store.is_redacted(artifact_id)
    assert store.get_redaction(artifact_id) == expected
    with pytest.raises(ArtifactRedactedError):
        store.read_bytes(artifact_id)
    with pytest.raises(ArtifactRedactedError):
        store.put_bytes(data, media_type="text/plain")


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("reason", "different reason"),
        ("authority", "different-authority"),
        ("redacted_at", "2026-08-19T06:37:01Z"),
        ("request_ref", "different-request"),
    ],
)
def test_redaction_is_idempotent_but_conflicting_metadata_is_rejected(
    tmp_path: Path, field: str, replacement: str
):
    store = ArtifactStore(tmp_path / "objects")
    artifact_id = store.put_bytes(b"redaction conflict fixture")["artifact_id"]
    kwargs = {
        "reason": "legal deletion",
        "authority": "privacy-officer",
        "redacted_at": "2026-08-19T06:37:00Z",
        "request_ref": "legal-37",
    }
    first = store.redact(artifact_id, **kwargs)
    assert store.redact(artifact_id, **kwargs) == first

    conflicting = dict(kwargs)
    conflicting[field] = replacement
    with pytest.raises(ArtifactIntegrityError):
        store.redact(artifact_id, **conflicting)


def test_manifest_file_is_canonical_json(tmp_path: Path):
    store = ArtifactStore(tmp_path / "objects")
    manifest = store.put_bytes("café".encode("utf-8"), media_type="text/plain")
    raw = store._manifest_path(manifest["artifact_id"]).read_bytes()

    assert raw == ArtifactStore._canonical(manifest)
    assert json.loads(raw.decode("utf-8")) == manifest
