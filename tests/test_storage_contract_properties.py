from __future__ import annotations

from copy import deepcopy
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from hypothesis import given, settings, strategies as st

from fossil_core.adapters.filesystem.artifact_store import ArtifactRedactedError, ArtifactStore
from fossil_core.adapters.filesystem.event_store import (
    DurableEventStore,
    EventRedactedError,
    IdempotencyConflict,
)
from fossil_core.adapters.s3.storage import S3ArtifactStore, S3DurableEventStore


ROOT = Path(__file__).parents[1]
SCHEMA = ROOT / "schemas/events/v1.schema.json"
PACK = "pack_269099f7b2ba43b7a99b9427d64092de"
IDEMPOTENCY_KEY = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-",
    min_size=1,
    max_size=48,
)
PAYLOAD_TEXT = st.text(max_size=128)
MEDIA_TYPE = st.sampled_from(
    [
        "application/octet-stream",
        "application/json",
        "text/plain",
        "text/markdown",
    ]
)


class FakeS3Error(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class FakeS3Client:
    """Deterministic in-memory S3 surface for secretless property tests."""

    def __init__(self):
        self.objects: dict[tuple[str, str], bytes] = {}

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        IfNoneMatch: str | None = None,
    ):
        slot = (Bucket, Key)
        if IfNoneMatch == "*" and slot in self.objects:
            raise FakeS3Error("PreconditionFailed")
        self.objects[slot] = bytes(Body)
        return {"ETag": "fixture"}

    def get_object(self, *, Bucket: str, Key: str):
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


def _event(*, idempotency_key: str, claim_text: str) -> dict:
    return {
        "schema_version": "dkg.event.v1",
        "event_type": "claim.proposed",
        "occurred_at": "2026-08-15T10:00:00Z",
        "recorded_at": "2026-08-15T10:01:00Z",
        "pack_id": PACK,
        "actor": {"actor_type": "system", "actor_id": "storage-contract-property"},
        "subject_refs": ["clm_storage_contract_property"],
        "idempotency_key": idempotency_key,
        "payload": {"claim_text": claim_text},
    }


def _stores(root: Path) -> tuple[DurableEventStore, S3DurableEventStore]:
    return (
        DurableEventStore(root / "events", SCHEMA),
        S3DurableEventStore(
            bucket="fixture",
            schema_path=SCHEMA,
            prefix="property",
            client=FakeS3Client(),
        ),
    )


@settings(max_examples=75, derandomize=True)
@given(keys=st.lists(IDEMPOTENCY_KEY, min_size=1, max_size=6, unique=True))
def test_filesystem_and_s3_event_commit_get_and_enumeration_are_equivalent(
    keys: list[str],
) -> None:
    with TemporaryDirectory() as directory:
        filesystem, remote = _stores(Path(directory))

        committed = []
        for key in keys:
            candidate = _event(idempotency_key=key, claim_text=f"payload:{key}")
            local_result = filesystem.commit(candidate)
            remote_result = remote.commit(candidate)
            assert local_result == remote_result
            committed.append(local_result)

        assert list(filesystem.iter_events()) == list(remote.iter_events())
        for item in committed:
            assert filesystem.get(item["event_id"]) == remote.get(item["event_id"]) == item


@settings(max_examples=75, derandomize=True)
@given(idempotency_key=IDEMPOTENCY_KEY, claim_text=PAYLOAD_TEXT)
def test_filesystem_and_s3_event_retry_and_conflict_are_equivalent(
    idempotency_key: str,
    claim_text: str,
) -> None:
    with TemporaryDirectory() as directory:
        filesystem, remote = _stores(Path(directory))
        candidate = _event(idempotency_key=idempotency_key, claim_text=claim_text)

        local_first = filesystem.commit(candidate)
        remote_first = remote.commit(candidate)
        assert local_first == remote_first
        assert filesystem.commit(candidate) == local_first
        assert remote.commit(candidate) == remote_first

        conflicting = deepcopy(candidate)
        conflicting["payload"]["claim_text"] = claim_text + "\nconflict"
        with pytest.raises(IdempotencyConflict):
            filesystem.commit(conflicting)
        with pytest.raises(IdempotencyConflict):
            remote.commit(conflicting)


@settings(max_examples=60, derandomize=True)
@given(idempotency_key=IDEMPOTENCY_KEY, claim_text=PAYLOAD_TEXT)
def test_filesystem_and_s3_event_redaction_and_nonresurrection_are_equivalent(
    idempotency_key: str,
    claim_text: str,
) -> None:
    with TemporaryDirectory() as directory:
        filesystem, remote = _stores(Path(directory))
        candidate = _event(idempotency_key=idempotency_key, claim_text=claim_text)
        committed = filesystem.commit(candidate)
        assert remote.commit(candidate) == committed

        redaction_args = {
            "reason": "property privacy request",
            "authority": "test",
            "redacted_at": "2026-08-15T10:30:00Z",
            "request_ref": "property-redaction",
        }
        local_tombstone = filesystem.redact(committed["event_id"], **redaction_args)
        remote_tombstone = remote.redact(committed["event_id"], **redaction_args)

        assert local_tombstone == remote_tombstone
        assert filesystem.get_redaction(committed["event_id"]) == remote.get_redaction(
            committed["event_id"]
        )
        assert list(filesystem.iter_redactions()) == list(remote.iter_redactions())
        assert filesystem.redact(committed["event_id"], **redaction_args) == local_tombstone
        assert remote.redact(committed["event_id"], **redaction_args) == remote_tombstone

        with pytest.raises(EventRedactedError):
            filesystem.get(committed["event_id"])
        with pytest.raises(EventRedactedError):
            remote.get(committed["event_id"])
        with pytest.raises(EventRedactedError):
            filesystem.commit(candidate)
        with pytest.raises(EventRedactedError):
            remote.commit(candidate)


@settings(max_examples=75, derandomize=True)
@given(data=st.binary(max_size=512), media_type=MEDIA_TYPE)
def test_filesystem_and_s3_artifact_immutability_and_redaction_are_equivalent(
    data: bytes,
    media_type: str,
) -> None:
    with TemporaryDirectory() as directory:
        filesystem = ArtifactStore(Path(directory) / "artifacts")
        remote = S3ArtifactStore(
            bucket="fixture",
            prefix="property-artifacts",
            client=FakeS3Client(),
        )

        local_manifest = filesystem.put_bytes(data, media_type=media_type)
        remote_manifest = remote.put_bytes(data, media_type=media_type)
        assert local_manifest == remote_manifest
        assert filesystem.put_bytes(data, media_type=media_type) == local_manifest
        assert remote.put_bytes(data, media_type=media_type) == remote_manifest
        assert filesystem.read_bytes(local_manifest["artifact_id"]) == data
        assert remote.read_bytes(remote_manifest["artifact_id"]) == data
        assert filesystem.verify(local_manifest["artifact_id"]) is True
        assert remote.verify(remote_manifest["artifact_id"]) is True

        redaction_args = {
            "reason": "property privacy request",
            "authority": "test",
            "redacted_at": "2026-08-15T10:31:00Z",
            "request_ref": "property-artifact-redaction",
        }
        local_redaction = filesystem.redact(local_manifest["artifact_id"], **redaction_args)
        remote_redaction = remote.redact(remote_manifest["artifact_id"], **redaction_args)
        assert local_redaction == remote_redaction
        assert filesystem.get_redaction(local_manifest["artifact_id"]) == remote.get_redaction(
            remote_manifest["artifact_id"]
        )

        with pytest.raises(ArtifactRedactedError):
            filesystem.read_bytes(local_manifest["artifact_id"])
        with pytest.raises(ArtifactRedactedError):
            remote.read_bytes(remote_manifest["artifact_id"])
        with pytest.raises(ArtifactRedactedError):
            filesystem.put_bytes(data, media_type=media_type)
        with pytest.raises(ArtifactRedactedError):
            remote.put_bytes(data, media_type=media_type)
