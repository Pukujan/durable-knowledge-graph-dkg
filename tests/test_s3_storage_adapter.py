from __future__ import annotations

from copy import deepcopy
from io import BytesIO
from pathlib import Path

import pytest

from fossil_core.artifact_store import (
    ArtifactIntegrityError,
    ArtifactRedactedError,
    ArtifactStore,
)
from fossil_core.event_store import DurableEventStore, EventRedactedError, IdempotencyConflict
from fossil_core.projection.migration import SemanticSnapshot
from fossil_core.s3_storage import RemoteStoreUnavailable, S3ArtifactStore, S3DurableEventStore
from fossil_core.storage_ports import ArtifactStorePort, EventStorePort


ROOT = Path(__file__).parents[1]
SCHEMA = ROOT / "schemas/events/v1.schema.json"
PACK = "pack_269099f7b2ba43b7a99b9427d64092de"


class FakeS3Error(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class FakeS3Client:
    """Small deterministic S3 surface for secretless contract tests."""

    def __init__(self):
        self.objects: dict[tuple[str, str], bytes] = {}
        self.fail_put = False
        self.fail_get = False

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, IfNoneMatch: str | None = None):
        if self.fail_put:
            raise TimeoutError("injected object-store outage")
        slot = (Bucket, Key)
        if IfNoneMatch == "*" and slot in self.objects:
            raise FakeS3Error("PreconditionFailed")
        self.objects[slot] = bytes(Body)
        return {"ETag": "fixture"}

    def get_object(self, *, Bucket: str, Key: str):
        if self.fail_get:
            raise TimeoutError("injected object-store outage")
        try:
            data = self.objects[(Bucket, Key)]
        except KeyError as exc:
            raise FakeS3Error("NoSuchKey") from exc
        return {"Body": BytesIO(data), "ContentLength": len(data)}

    def head_object(self, *, Bucket: str, Key: str):
        try:
            data = self.objects[(Bucket, Key)]
        except KeyError as exc:
            raise FakeS3Error("404") from exc
        return {"ContentLength": len(data)}

    def delete_object(self, *, Bucket: str, Key: str):
        self.objects.pop((Bucket, Key), None)
        return {}

    def list_objects_v2(
        self,
        *,
        Bucket: str,
        Prefix: str,
        ContinuationToken: str | None = None,
    ):
        del ContinuationToken
        keys = sorted(
            key for bucket, key in self.objects if bucket == Bucket and key.startswith(Prefix)
        )
        return {
            "IsTruncated": False,
            "Contents": [
                {"Key": key, "Size": len(self.objects[(Bucket, key)])} for key in keys
            ],
        }


def event(number: int) -> dict:
    return {
        "schema_version": "dkg.event.v1",
        "event_type": "claim.proposed",
        "occurred_at": f"2026-08-15T10:0{number}:00Z",
        "recorded_at": f"2026-08-15T10:1{number}:00Z",
        "pack_id": PACK,
        "actor": {"actor_type": "system", "actor_id": "s3-storage-fixture"},
        "subject_refs": [f"clm_s3_fixture_{number}"],
        "idempotency_key": f"s3-storage-fixture-{number}",
        "payload": {"claim_text": f"canonical remote fixture {number}"},
    }


def test_filesystem_reference_stores_satisfy_explicit_storage_ports(tmp_path: Path):
    assert isinstance(ArtifactStore(tmp_path / "artifacts"), ArtifactStorePort)
    assert isinstance(DurableEventStore(tmp_path / "events", SCHEMA), EventStorePort)


def test_s3_artifact_store_preserves_immutable_verify_and_redaction_semantics():
    client = FakeS3Client()
    store = S3ArtifactStore(bucket="fixture", prefix="proof", client=client)

    manifest = store.put_bytes(b"canonical bytes", media_type="text/plain")
    assert store.put_bytes(b"canonical bytes", media_type="text/plain") == manifest
    assert store.read_bytes(manifest["artifact_id"]) == b"canonical bytes"
    assert store.verify(manifest["artifact_id"]) is True

    redaction = store.redact(
        manifest["artifact_id"],
        reason="privacy fixture",
        authority="test",
        redacted_at="2026-08-15T10:30:00Z",
        request_ref="fixture-redaction",
    )
    assert redaction["artifact_id"] == manifest["artifact_id"]
    assert store.is_redacted(manifest["artifact_id"])
    with pytest.raises(ArtifactRedactedError):
        store.read_bytes(manifest["artifact_id"])
    with pytest.raises(ArtifactRedactedError):
        store.put_bytes(b"canonical bytes", media_type="text/plain")


def test_s3_artifact_verify_detects_corrupted_remote_bytes():
    client = FakeS3Client()
    store = S3ArtifactStore(bucket="fixture", prefix="proof", client=client)
    manifest = store.put_bytes(b"canonical bytes")
    digest = manifest["content_hash"]["digest"]
    blob_key = next(
        key for bucket, key in client.objects if bucket == "fixture" and key.endswith(digest)
    )
    client.objects[("fixture", blob_key)] = b"corrupted"

    with pytest.raises(ArtifactIntegrityError, match="verification failed"):
        store.verify(manifest["artifact_id"])


def test_s3_event_store_is_idempotent_enumerable_and_conflict_fails_loudly():
    client = FakeS3Client()
    store = S3DurableEventStore(
        bucket="fixture", schema_path=SCHEMA, prefix="proof", client=client
    )
    first = store.commit(event(1))
    second = store.commit(event(2))
    assert store.commit(event(1)) == first
    assert [item["event_id"] for item in store.iter_events()] == sorted(
        [first["event_id"], second["event_id"]]
    )

    conflicting = deepcopy(event(1))
    conflicting["payload"]["claim_text"] = "different bytes under stable identity"
    with pytest.raises(IdempotencyConflict, match="different content"):
        store.commit(conflicting)

    tombstone = store.redact(
        first["event_id"],
        reason="privacy fixture",
        authority="test",
        redacted_at="2026-08-15T10:31:00Z",
        request_ref="fixture-redaction",
    )
    assert tombstone["event_id"] == first["event_id"]
    assert [item["event_id"] for item in store.iter_redactions()] == [first["event_id"]]
    with pytest.raises(EventRedactedError):
        store.get(first["event_id"])


def test_s3_outage_cannot_be_reported_as_durable_commit_success():
    client = FakeS3Client()
    client.fail_put = True
    store = S3DurableEventStore(
        bucket="fixture", schema_path=SCHEMA, prefix="proof", client=client
    )

    with pytest.raises(RemoteStoreUnavailable, match="durable object write failed"):
        store.commit(event(1))
    assert client.objects == {}


def test_empty_local_store_reconstructs_semantics_from_remote_canonical_events(tmp_path: Path):
    client = FakeS3Client()
    remote = S3DurableEventStore(
        bucket="fixture", schema_path=SCHEMA, prefix="proof", client=client
    )
    committed = [remote.commit(event(1)), remote.commit(event(2))]
    expected = SemanticSnapshot.from_events(committed)

    # Simulate a fresh runner with no warm local event/projection state. Only the
    # remote canonical event enumeration is used to repopulate the reference store.
    restored = DurableEventStore(tmp_path / "restored-events", SCHEMA)
    assert list(restored.iter_events()) == []
    for remote_event in remote.iter_events():
        restored.commit(remote_event)

    assert SemanticSnapshot.from_events(list(restored.iter_events())) == expected
