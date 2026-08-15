from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest

from fossil_core.artifact_store import ArtifactIntegrityError, ArtifactRedactedError
from fossil_core.event_store import DurableEventStore, IdempotencyConflict
from fossil_core.projection.migration import SemanticSnapshot
from fossil_core.s3_storage import RemoteStoreUnavailable, S3ArtifactStore, S3DurableEventStore


ROOT = Path(__file__).parents[1]
SCHEMA = ROOT / "schemas/events/v1.schema.json"
WORKFLOW = ROOT / ".github/workflows/s3-service-fixture.yml"
PACK = "pack_269099f7b2ba43b7a99b9427d64092de"


def _event(number: int) -> dict:
    return {
        "schema_version": "dkg.event.v1",
        "event_type": "claim.proposed",
        "occurred_at": f"2026-08-15T11:0{number}:00Z",
        "recorded_at": f"2026-08-15T11:1{number}:00Z",
        "pack_id": PACK,
        "actor": {"actor_type": "system", "actor_id": "s3-service-fixture"},
        "subject_refs": [f"clm_s3_service_{number}"],
        "idempotency_key": f"s3-service-fixture-{number}",
        "payload": {"claim_text": f"real S3-compatible fixture {number}"},
    }


def test_real_s3_service_fixture_workflow_is_fail_closed_and_exact_head() -> None:
    assert WORKFLOW.exists(), "real S3-compatible service fixture workflow is required"
    workflow = WORKFLOW.read_text(encoding="utf-8")
    required = [
        "quay.io/minio/minio",
        'server /data --console-address ":9001"',
        "/minio/health/ready",
        "python -m pip install -e '.[test,s3]'",
        "python -m pytest -q tests/test_s3_service_fixture.py",
        "FOSSIL_S3_TEST_ENDPOINT: http://127.0.0.1:9000",
        "ref: ${{ github.event.pull_request.head.sha || github.sha }}",
        "git rev-parse HEAD",
    ]
    for needle in required:
        assert needle in workflow, f"missing hosted service-fixture contract: {needle}"


def test_real_s3_service_preserves_canonical_semantics(tmp_path: Path) -> None:
    endpoint = os.environ.get("FOSSIL_S3_TEST_ENDPOINT")
    if not endpoint:
        pytest.skip("requires explicit local S3-compatible service endpoint")

    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError

    region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    access_key = os.environ["AWS_ACCESS_KEY_ID"]
    secret_key = os.environ["AWS_SECRET_ACCESS_KEY"]
    config = Config(
        s3={"addressing_style": "path"},
        connect_timeout=2,
        read_timeout=2,
        retries={"max_attempts": 0},
    )
    raw = boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=config,
    )

    bucket = f"fossil-fixture-{uuid4().hex[:12]}"
    prefix = f"proof/{uuid4().hex}"
    raw.create_bucket(Bucket=bucket)
    raw.head_bucket(Bucket=bucket)

    artifacts = S3ArtifactStore(
        bucket=bucket,
        prefix=prefix,
        endpoint_url=endpoint,
        region_name=region,
    )
    events = S3DurableEventStore(
        bucket=bucket,
        schema_path=SCHEMA,
        prefix=prefix,
        endpoint_url=endpoint,
        region_name=region,
    )

    manifest = artifacts.put_bytes(b"canonical service bytes", media_type="text/plain")
    assert artifacts.put_bytes(b"canonical service bytes", media_type="text/plain") == manifest
    assert artifacts.read_bytes(manifest["artifact_id"]) == b"canonical service bytes"
    assert artifacts.verify(manifest["artifact_id"]) is True

    digest = manifest["content_hash"]["digest"]
    raw.put_object(
        Bucket=bucket,
        Key=artifacts.backend.key(artifacts._blob_key(digest)),
        Body=b"corrupted remote bytes",
    )
    with pytest.raises(ArtifactIntegrityError, match="verification failed"):
        artifacts.verify(manifest["artifact_id"])

    redact_manifest = artifacts.put_bytes(b"redact me", media_type="text/plain")
    observed = {"tombstone_before_delete": False}
    original_delete = artifacts.backend.delete

    def checked_delete(relative: str) -> None:
        raw.head_object(
            Bucket=bucket,
            Key=artifacts.backend.key(
                artifacts._redaction_key(redact_manifest["artifact_id"])
            ),
        )
        observed["tombstone_before_delete"] = True
        original_delete(relative)

    artifacts.backend.delete = checked_delete  # type: ignore[method-assign]
    artifacts.redact(
        redact_manifest["artifact_id"],
        reason="privacy fixture",
        authority="test",
        redacted_at="2026-08-15T11:30:00Z",
        request_ref="service-fixture-redaction",
    )
    assert observed["tombstone_before_delete"] is True
    assert artifacts.is_redacted(redact_manifest["artifact_id"])
    with pytest.raises(ArtifactRedactedError):
        artifacts.put_bytes(b"redact me", media_type="text/plain")

    first = events.commit(_event(1))
    second = events.commit(_event(2))
    assert events.commit(_event(1)) == first

    conflicting = deepcopy(_event(1))
    conflicting["payload"]["claim_text"] = "different bytes under stable identity"
    with pytest.raises(IdempotencyConflict, match="different content"):
        events.commit(conflicting)

    expected = SemanticSnapshot.from_events([first, second])

    restarted = S3DurableEventStore(
        bucket=bucket,
        schema_path=SCHEMA,
        prefix=prefix,
        endpoint_url=endpoint,
        region_name=region,
    )
    restarted_events = list(restarted.iter_events())
    assert {item["event_id"] for item in restarted_events} == {
        first["event_id"],
        second["event_id"],
    }

    restored = DurableEventStore(tmp_path / "restored-events", SCHEMA)
    assert list(restored.iter_events()) == []
    for remote_event in restarted_events:
        restored.commit(remote_event)
    assert SemanticSnapshot.from_events(list(restored.iter_events())) == expected

    dead_client = boto3.client(
        "s3",
        endpoint_url="http://127.0.0.1:1",
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=config,
    )
    unavailable = S3DurableEventStore(
        bucket=bucket,
        schema_path=SCHEMA,
        prefix=f"{prefix}/outage",
        client=dead_client,
    )
    with pytest.raises(RemoteStoreUnavailable, match="durable object"):
        unavailable.commit(_event(3))

    try:
        raw.head_object(Bucket=bucket, Key="definitely-missing")
    except ClientError as exc:
        assert str(exc.response.get("Error", {}).get("Code")) in {"404", "NoSuchKey", "NotFound"}
    else:  # pragma: no cover
        raise AssertionError("missing object unexpectedly resolved")
