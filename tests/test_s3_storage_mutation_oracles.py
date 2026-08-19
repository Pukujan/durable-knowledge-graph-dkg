from __future__ import annotations

from pathlib import Path

import fossil_core.adapters.s3.storage as s3_storage
from fossil_core.s3_storage import S3ArtifactStore, S3DurableEventStore


ROOT = Path(__file__).parents[1]
SCHEMA = ROOT / "schemas/events/v1.schema.json"


def test_s3_store_default_prefixes_remain_empty():
    artifacts = S3ArtifactStore(bucket="fixture", client=object())
    events = S3DurableEventStore(
        bucket="fixture", schema_path=SCHEMA, client=object()
    )

    assert artifacts.backend.prefix == ""
    assert events.backend.prefix == ""


def test_backend_slash_normalization_does_not_strip_valid_x_characters():
    backend = s3_storage._S3ObjectBackend(
        bucket="fixture", prefix="XproofX", client=object()
    )

    assert backend.prefix == "XproofX"
    assert backend.key("X/item") == "XproofX/X/item"


def test_s3_artifact_put_file_preserves_default_media_type(monkeypatch, tmp_path: Path):
    source = tmp_path / "artifact.bin"
    source.write_bytes(b"default media")
    store = S3ArtifactStore(bucket="fixture", client=object())
    captured: dict[str, object] = {}

    def fake_put_bytes(data: bytes, *, media_type: str):
        captured.update(data=data, media_type=media_type)
        return {"media_type": media_type}

    monkeypatch.setattr(store, "put_bytes", fake_put_bytes)

    assert store.put_file(source) == {"media_type": "application/octet-stream"}
    assert captured == {
        "data": b"default media",
        "media_type": "application/octet-stream",
    }
