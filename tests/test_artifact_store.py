from pathlib import Path

import pytest

from dkg.artifact_store import ArtifactIntegrityError, ArtifactStore


def test_artifact_store_is_content_addressed_and_verifiable(tmp_path: Path):
    store = ArtifactStore(tmp_path / "objects")
    first = store.put_bytes(b"hello durable evidence", media_type="text/plain")
    second = store.put_bytes(b"hello durable evidence", media_type="text/plain")

    assert first == second
    assert store.read_bytes(first["artifact_id"]) == b"hello durable evidence"
    assert store.verify(first["artifact_id"])


def test_artifact_tamper_is_detected(tmp_path: Path):
    store = ArtifactStore(tmp_path / "objects")
    manifest = store.put_bytes(b"abc")
    digest = manifest["content_hash"]["digest"]
    blob = store.blobs / digest[:2] / digest
    blob.write_bytes(b"tampered")

    with pytest.raises(ArtifactIntegrityError):
        store.verify(manifest["artifact_id"])
