from __future__ import annotations

import hashlib
import json
import sys
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import ValidationError

import fossil_core.adapters.s3.storage as s3_storage
from fossil_core.artifact_store import (
    ArtifactIntegrityError,
    ArtifactRedactedError,
    ArtifactStore,
)
from fossil_core.event_store import (
    DurableEventStore,
    EventRedactedError,
    EventRedactionConflict,
    IdempotencyConflict,
)
from fossil_core.ids import deterministic_event_id
from fossil_core.projection.migration import SemanticSnapshot
from fossil_core.s3_storage import (
    RemoteObjectConflict,
    RemoteStoreUnavailable,
    S3ArtifactStore,
    S3DurableEventStore,
)
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


class RawBodyS3Client(FakeS3Client):
    def get_object(self, *, Bucket: str, Key: str):
        try:
            data = self.objects[(Bucket, Key)]
        except KeyError as exc:
            raise FakeS3Error("NoSuchKey") from exc
        return {"Body": data, "ContentLength": len(data)}


class PaginatedS3Client(FakeS3Client):
    def __init__(self):
        super().__init__()
        self.list_calls: list[dict] = []

    def list_objects_v2(self, **params):
        self.list_calls.append(dict(params))
        if len(self.list_calls) == 1:
            assert params == {"Bucket": "fixture", "Prefix": "proof/canonical/events/"}
            return {
                "IsTruncated": True,
                "NextContinuationToken": "page-2",
                "Contents": [
                    {"Key": "outside/should-not-stop-page", "Size": 1},
                    {"Key": "proof/canonical/events/aa/evt_a.json", "Size": 1},
                ],
            }
        assert params == {
            "Bucket": "fixture",
            "Prefix": "proof/canonical/events/",
            "ContinuationToken": "page-2",
        }
        return {
            "IsTruncated": False,
            "Contents": [
                {"Key": "proof/canonical/events/bb/evt_b.json", "Size": 1},
            ],
        }


class EmptyListingS3Client(FakeS3Client):
    def list_objects_v2(self, **params):
        return {"IsTruncated": False}


class TruncatedListingS3Client(FakeS3Client):
    def list_objects_v2(self, **params):
        return {"IsTruncated": True, "Contents": []}


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


def test_error_code_is_fail_closed_for_missing_or_malformed_provider_metadata():
    assert s3_storage._error_code(RuntimeError("plain")) is None
    assert s3_storage._error_code(SimpleNamespace(response={"Error": {}})) is None
    assert s3_storage._error_code(FakeS3Error("NoSuchKey")) == "NoSuchKey"


def test_default_client_forwards_only_explicit_runtime_options(monkeypatch):
    calls: list[tuple[str, dict]] = []
    sentinel = object()
    fake_boto3 = SimpleNamespace(
        client=lambda service, **options: calls.append((service, options)) or sentinel
    )
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)

    assert (
        s3_storage._default_s3_client(
            endpoint_url="https://objects.invalid", region_name="test-region-1"
        )
        is sentinel
    )
    assert calls == [
        (
            "s3",
            {
                "endpoint_url": "https://objects.invalid",
                "region_name": "test-region-1",
            },
        )
    ]

    calls.clear()
    assert s3_storage._default_s3_client(endpoint_url=None, region_name=None) is sentinel
    assert calls == [("s3", {})]


def test_backend_validates_bucket_and_normalizes_prefix_and_keys():
    client = FakeS3Client()
    with pytest.raises(ValueError):
        s3_storage._S3ObjectBackend(bucket="   ", client=client)

    plain = s3_storage._S3ObjectBackend(bucket="fixture", client=client)
    assert plain.bucket == "fixture"
    assert plain.prefix == ""
    assert plain.key("/canonical/item") == "canonical/item"

    prefixed = s3_storage._S3ObjectBackend(
        bucket="fixture", prefix="//proof//", client=client
    )
    assert prefixed.prefix == "proof"
    assert prefixed.key("/canonical/item") == "proof/canonical/item"


def test_store_constructors_forward_prefix_endpoint_and_region(monkeypatch):
    calls: list[tuple[str | None, str | None]] = []
    clients = [FakeS3Client(), FakeS3Client()]

    def fake_default(*, endpoint_url, region_name):
        calls.append((endpoint_url, region_name))
        return clients[len(calls) - 1]

    monkeypatch.setattr(s3_storage, "_default_s3_client", fake_default)
    artifacts = S3ArtifactStore(
        bucket="fixture",
        prefix="//artifact-proof//",
        endpoint_url="https://artifacts.invalid",
        region_name="artifact-region",
    )
    events = S3DurableEventStore(
        bucket="fixture",
        schema_path=SCHEMA,
        prefix="//event-proof//",
        endpoint_url="https://events.invalid",
        region_name="event-region",
    )

    assert calls == [
        ("https://artifacts.invalid", "artifact-region"),
        ("https://events.invalid", "event-region"),
    ]
    assert artifacts.backend.prefix == "artifact-proof"
    assert events.backend.prefix == "event-proof"


def test_backend_reads_stream_and_raw_bytes_and_maps_provider_failures():
    stream_client = FakeS3Client()
    stream_client.objects[("fixture", "proof/item")] = b"stream"
    stream_backend = s3_storage._S3ObjectBackend(
        bucket="fixture", prefix="proof", client=stream_client
    )
    assert stream_backend.read("item") == b"stream"
    assert stream_backend.exists("item") is True
    assert stream_backend.exists("missing") is False
    with pytest.raises(FileNotFoundError):
        stream_backend.read("missing")

    raw_client = RawBodyS3Client()
    raw_client.objects[("fixture", "proof/item")] = b"raw"
    raw_backend = s3_storage._S3ObjectBackend(
        bucket="fixture", prefix="proof", client=raw_client
    )
    assert raw_backend.read("item") == b"raw"

    stream_client.fail_get = True
    with pytest.raises(RemoteStoreUnavailable):
        stream_backend.read("item")


def test_backend_immutable_write_result_conflict_and_delete_are_observable():
    client = FakeS3Client()
    backend = s3_storage._S3ObjectBackend(
        bucket="fixture", prefix="proof", client=client
    )

    assert backend.put_immutable("item", b"one") is True
    assert backend.put_immutable("item", b"one") is False
    with pytest.raises(RemoteObjectConflict):
        backend.put_immutable("item", b"different")

    assert ("fixture", "proof/item") in client.objects
    backend.delete("item")
    assert ("fixture", "proof/item") not in client.objects


def test_backend_pagination_preserves_prefix_and_continuation_contract():
    client = PaginatedS3Client()
    backend = s3_storage._S3ObjectBackend(
        bucket="fixture", prefix="proof", client=client
    )

    assert list(backend.iter_keys("canonical/events/")) == [
        "canonical/events/aa/evt_a.json",
        "canonical/events/bb/evt_b.json",
    ]
    assert len(client.list_calls) == 2


def test_backend_empty_listing_and_truncated_page_fail_closed():
    empty = s3_storage._S3ObjectBackend(
        bucket="fixture", prefix="proof", client=EmptyListingS3Client()
    )
    assert list(empty.iter_keys("canonical/events/")) == []

    truncated = s3_storage._S3ObjectBackend(
        bucket="fixture", prefix="proof", client=TruncatedListingS3Client()
    )
    with pytest.raises(RemoteStoreUnavailable):
        list(truncated.iter_keys("canonical/events/"))


def test_s3_artifact_canonical_identity_and_remote_layout_are_exact():
    assert S3ArtifactStore._canonical({"z": "café", "a": [2, 1]}) == (
        '{"a":[2,1],"z":"café"}\n'.encode("utf-8")
    )

    client = FakeS3Client()
    store = S3ArtifactStore(bucket="fixture", prefix="proof", client=client)
    data = b"artifact bytes"
    digest = hashlib.sha256(data).hexdigest()
    artifact_id = f"art_{digest[:32]}"
    manifest = store.put_bytes(data)

    assert manifest == {
        "artifact_id": artifact_id,
        "content_hash": {"algorithm": "sha256", "digest": digest},
        "byte_size": len(data),
        "media_type": "application/octet-stream",
    }
    blob_key = f"proof/canonical/artifacts/blobs/sha256/{digest[:2]}/{digest}"
    manifest_key = (
        f"proof/canonical/artifacts/manifests/{digest[:2]}/{artifact_id}.json"
    )
    assert client.objects[("fixture", blob_key)] == data
    assert client.objects[("fixture", manifest_key)] == S3ArtifactStore._canonical(
        manifest
    )


def test_s3_artifact_put_file_reads_exact_bytes_and_media_type(tmp_path: Path):
    source = tmp_path / "artifact.bin"
    source.write_bytes(b"file bytes")
    client = FakeS3Client()
    store = S3ArtifactStore(bucket="fixture", prefix="proof", client=client)

    manifest = store.put_file(source, media_type="application/x-fixture")

    assert manifest["media_type"] == "application/x-fixture"
    assert store.read_bytes(manifest["artifact_id"]) == b"file bytes"


def test_s3_artifact_store_preserves_immutable_verify_and_redaction_semantics():
    client = FakeS3Client()
    store = S3ArtifactStore(bucket="fixture", prefix="proof", client=client)

    manifest = store.put_bytes(b"canonical bytes", media_type="text/plain")
    assert store.put_bytes(b"canonical bytes", media_type="text/plain") == manifest
    assert store.read_bytes(manifest["artifact_id"]) == b"canonical bytes"
    assert store.verify(manifest["artifact_id"]) is True
    assert store.get_redaction(manifest["artifact_id"]) is None

    redaction = store.redact(
        manifest["artifact_id"],
        reason="privacy fixture",
        authority="test",
        redacted_at="2026-08-15T10:30:00Z",
        request_ref="fixture-redaction",
    )
    assert redaction == {
        "artifact_id": manifest["artifact_id"],
        "redacted_at": "2026-08-15T10:30:00Z",
        "reason": "privacy fixture",
        "authority": "test",
        "request_ref": "fixture-redaction",
        "content_hash": manifest["content_hash"],
        "byte_size": manifest["byte_size"],
        "media_type": manifest["media_type"],
    }
    assert store.get_redaction(manifest["artifact_id"]) == redaction
    assert store.is_redacted(manifest["artifact_id"])

    digest = manifest["content_hash"]["digest"]
    blob_key = f"proof/canonical/artifacts/blobs/sha256/{digest[:2]}/{digest}"
    suffix = manifest["artifact_id"].removeprefix("art_")
    redaction_key = (
        f"proof/canonical/redactions/artifacts/{suffix[:2]}/{manifest['artifact_id']}.json"
    )
    assert ("fixture", blob_key) not in client.objects
    assert client.objects[("fixture", redaction_key)] == S3ArtifactStore._canonical(
        redaction
    )

    with pytest.raises(ArtifactRedactedError):
        store.read_bytes(manifest["artifact_id"])
    with pytest.raises(ArtifactRedactedError):
        store.put_bytes(b"canonical bytes", media_type="text/plain")


@pytest.mark.parametrize("missing", ["reason", "authority", "redacted_at"])
def test_s3_artifact_redaction_requires_complete_authorization_metadata(missing):
    client = FakeS3Client()
    store = S3ArtifactStore(bucket="fixture", prefix="proof", client=client)
    manifest = store.put_bytes(b"required metadata")
    kwargs = {
        "reason": "privacy fixture",
        "authority": "test",
        "redacted_at": "2026-08-15T10:30:00Z",
        "request_ref": "required-fields",
    }
    kwargs[missing] = ""

    with pytest.raises(ValueError):
        store.redact(manifest["artifact_id"], **kwargs)

    assert store.read_bytes(manifest["artifact_id"]) == b"required metadata"
    assert store.get_redaction(manifest["artifact_id"]) is None


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("reason", "different reason"),
        ("authority", "different-authority"),
        ("redacted_at", "2026-08-15T10:30:01Z"),
        ("request_ref", "different-request"),
    ],
)
def test_s3_artifact_redaction_is_idempotent_but_conflicting_metadata_fails(
    field, replacement
):
    client = FakeS3Client()
    store = S3ArtifactStore(bucket="fixture", prefix="proof", client=client)
    artifact_id = store.put_bytes(b"conflict fixture")["artifact_id"]
    kwargs = {
        "reason": "privacy fixture",
        "authority": "test",
        "redacted_at": "2026-08-15T10:30:00Z",
        "request_ref": "fixture-redaction",
    }
    first = store.redact(artifact_id, **kwargs)
    assert store.redact(artifact_id, **kwargs) == first

    conflicting = dict(kwargs)
    conflicting[field] = replacement
    with pytest.raises(ArtifactIntegrityError):
        store.redact(artifact_id, **conflicting)


def test_s3_artifact_verify_detects_same_length_corrupted_remote_bytes():
    client = FakeS3Client()
    store = S3ArtifactStore(bucket="fixture", prefix="proof", client=client)
    manifest = store.put_bytes(b"canonical bytes")
    digest = manifest["content_hash"]["digest"]
    blob_key = next(
        key for bucket, key in client.objects if bucket == "fixture" and key.endswith(digest)
    )
    original = client.objects[("fixture", blob_key)]
    client.objects[("fixture", blob_key)] = b"x" * len(original)

    with pytest.raises(ArtifactIntegrityError, match="verification failed"):
        store.verify(manifest["artifact_id"])


def test_s3_event_canonical_keys_validation_and_identity_are_exact():
    assert S3DurableEventStore._canonical({"z": "café", "a": [2, 1]}) == (
        '{"a":[2,1],"z":"café"}\n'.encode("utf-8")
    )

    candidate = event(1)
    expected_id = deterministic_event_id(candidate["pack_id"], candidate["idempotency_key"])
    suffix = expected_id.removeprefix("evt_")
    assert S3DurableEventStore._event_key(expected_id) == (
        f"canonical/events/{suffix[:2]}/{expected_id}.json"
    )
    assert S3DurableEventStore._redaction_key(expected_id) == (
        f"canonical/redactions/events/{suffix[:2]}/{expected_id}.json"
    )

    client = FakeS3Client()
    store = S3DurableEventStore(
        bucket="fixture", schema_path=SCHEMA, prefix="proof", client=client
    )
    original = deepcopy(candidate)
    validated = store.validate(candidate)
    assert candidate == original
    assert validated is not candidate
    assert validated["payload"] is not candidate["payload"]
    assert validated["event_id"] == expected_id
    assert list(store.iter_events()) == []

    invalid = event(2)
    invalid["occurred_at"] = "not-a-date-time"
    with pytest.raises(ValidationError):
        store.validate(invalid)


def test_s3_event_prepare_covers_explicit_fresh_matching_and_conflicting_identity():
    client = FakeS3Client()
    store = S3DurableEventStore(
        bucket="fixture", schema_path=SCHEMA, prefix="proof", client=client
    )

    explicit = event(1)
    explicit.pop("idempotency_key")
    explicit["event_id"] = "evt_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    assert store.prepare(explicit)["event_id"] == explicit["event_id"]

    fresh = event(2)
    fresh.pop("idempotency_key")
    prepared = store.prepare(fresh)
    assert prepared["event_id"].startswith("evt_")
    assert len(prepared["event_id"]) >= len("evt_") + 16

    deterministic = event(3)
    expected = deterministic_event_id(
        deterministic["pack_id"], deterministic["idempotency_key"]
    )
    deterministic["event_id"] = expected
    assert store.prepare(deterministic)["event_id"] == expected

    conflicting = event(4)
    conflicting["event_id"] = "evt_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    with pytest.raises(IdempotencyConflict):
        store.prepare(conflicting)


def test_s3_event_store_is_idempotent_enumerable_and_conflict_fails_loudly():
    client = FakeS3Client()
    store = S3DurableEventStore(
        bucket="fixture", schema_path=SCHEMA, prefix="proof", client=client
    )
    assert store.get_redaction("evt_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa") is None

    first = store.commit(event(1))
    second = store.commit(event(2))
    assert store.commit(event(1)) == first
    assert [item["event_id"] for item in store.iter_events()] == sorted(
        [first["event_id"], second["event_id"]]
    )

    first_suffix = first["event_id"].removeprefix("evt_")
    first_key = f"proof/canonical/events/{first_suffix[:2]}/{first['event_id']}.json"
    assert client.objects[("fixture", first_key)] == S3DurableEventStore._canonical(first)

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
    expected_digest = hashlib.sha256(S3DurableEventStore._canonical(first)).hexdigest()
    assert tombstone == {
        "event_id": first["event_id"],
        "pack_id": PACK,
        "event_type": "claim.proposed",
        "recorded_at": first["recorded_at"],
        "canonical_hash": {"algorithm": "sha256", "digest": expected_digest},
        "redacted_at": "2026-08-15T10:31:00Z",
        "reason": "privacy fixture",
        "authority": "test",
        "request_ref": "fixture-redaction",
    }
    redaction_key = (
        f"proof/canonical/redactions/events/{first_suffix[:2]}/{first['event_id']}.json"
    )
    assert client.objects[("fixture", redaction_key)] == S3DurableEventStore._canonical(
        tombstone
    )
    assert ("fixture", first_key) not in client.objects
    assert store.get_redaction(first["event_id"]) == tombstone
    assert [item["event_id"] for item in store.iter_redactions()] == [first["event_id"]]
    with pytest.raises(EventRedactedError):
        store.get(first["event_id"])
    with pytest.raises(EventRedactedError):
        store.commit(first)


@pytest.mark.parametrize("missing", ["reason", "authority", "redacted_at"])
def test_s3_event_redaction_requires_complete_authorization_metadata(missing):
    client = FakeS3Client()
    store = S3DurableEventStore(
        bucket="fixture", schema_path=SCHEMA, prefix="proof", client=client
    )
    committed = store.commit(event(1))
    kwargs = {
        "reason": "privacy fixture",
        "authority": "test",
        "redacted_at": "2026-08-15T10:31:00Z",
        "request_ref": "required-fields",
    }
    kwargs[missing] = ""

    with pytest.raises(ValueError):
        store.redact(committed["event_id"], **kwargs)

    assert store.get(committed["event_id"]) == committed
    assert store.get_redaction(committed["event_id"]) is None


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("reason", "different reason"),
        ("authority", "different-authority"),
        ("redacted_at", "2026-08-15T10:31:01Z"),
        ("request_ref", "different-request"),
    ],
)
def test_s3_event_redaction_is_idempotent_but_any_conflicting_metadata_is_rejected(
    field, replacement
):
    client = FakeS3Client()
    store = S3DurableEventStore(
        bucket="fixture", schema_path=SCHEMA, prefix="proof", client=client
    )
    event_id = store.commit(event(1))["event_id"]
    kwargs = {
        "reason": "privacy fixture",
        "authority": "test",
        "redacted_at": "2026-08-15T10:31:00Z",
        "request_ref": "fixture-redaction",
    }
    first = store.redact(event_id, **kwargs)
    assert store.redact(event_id, **kwargs) == first

    conflicting = dict(kwargs)
    conflicting[field] = replacement
    with pytest.raises(EventRedactionConflict):
        store.redact(event_id, **conflicting)


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
