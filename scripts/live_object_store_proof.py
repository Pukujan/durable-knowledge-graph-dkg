from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from fossil_core.artifact_store import ArtifactRedactedError
from fossil_core.event_store import (
    DurableEventStore,
    EventRedactedError,
    IdempotencyConflict,
)
from fossil_core.projection.migration import SemanticSnapshot
from fossil_core.s3_storage import (
    RemoteObjectConflict,
    RemoteStoreUnavailable,
    S3ArtifactStore,
    S3DurableEventStore,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/events/v1.schema.json"
PACK_ID = "pack_269099f7b2ba43b7a99b9427d64092de"
WRITER_RECEIPT = "proof-receipts/writer-receipt.json"
REBUILD_RECEIPT = "proof-receipts/rebuild-receipt.json"


class _CountingBody:
    def __init__(self, body: Any, owner: "CountingClient") -> None:
        self._body = body
        self._owner = owner

    def read(self, *args: Any, **kwargs: Any) -> bytes:
        data = self._body.read(*args, **kwargs)
        self._owner.bytes_read += len(data)
        return data

    def __getattr__(self, name: str) -> Any:
        return getattr(self._body, name)


class CountingClient:
    """Small metrics proxy around a real boto3 S3 client.

    It records only operation names and byte counts. Request parameters,
    authorization headers, endpoints, and credentials are never serialized.
    """

    def __init__(self, client: Any) -> None:
        self._client = client
        self.requests: Counter[str] = Counter()
        self.bytes_written = 0
        self.bytes_read = 0

    def __getattr__(self, name: str) -> Any:
        target = getattr(self._client, name)
        if not callable(target):
            return target

        def call(*args: Any, **kwargs: Any) -> Any:
            self.requests[name] += 1
            if name == "put_object":
                body = kwargs.get("Body", b"")
                if isinstance(body, str):
                    self.bytes_written += len(body.encode("utf-8"))
                elif isinstance(body, (bytes, bytearray, memoryview)):
                    self.bytes_written += len(body)
            result = target(*args, **kwargs)
            if name == "get_object" and isinstance(result, dict):
                body = result.get("Body")
                if hasattr(body, "read"):
                    result = dict(result)
                    result["Body"] = _CountingBody(body, self)
            return result

        return call

    def metrics(self) -> dict[str, Any]:
        return {
            "request_count": sum(self.requests.values()),
            "requests_by_operation": dict(sorted(self.requests.items())),
            "bytes_written": self.bytes_written,
            "bytes_read": self.bytes_read,
        }


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"BLOCKED_CREDENTIAL: required configuration {name} is empty")
    return value


def _prefix() -> str:
    value = _required("FOSSIL_PROOF_PREFIX").strip("/")
    if not value.startswith("fossil-live-proof/") or ".." in value:
        raise RuntimeError("proof prefix must stay under fossil-live-proof/")
    return value


def _event(number: int) -> dict[str, Any]:
    return {
        "schema_version": "dkg.event.v1",
        "event_type": "claim.proposed",
        "occurred_at": f"2026-08-15T17:0{number}:00Z",
        "recorded_at": f"2026-08-15T17:1{number}:00Z",
        "pack_id": PACK_ID,
        "actor": {"actor_type": "system", "actor_id": "object-store-live"},
        "subject_refs": [f"clm_object_store_live_{number}"],
        "idempotency_key": f"object-store-live-{number}",
        "payload": {"claim_text": f"OBJECT_STORE_LIVE canonical fixture {number}"},
    }


def _new_raw_client(*, endpoint: str, region: str, dead: bool = False) -> Any:
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url="http://127.0.0.1:1" if dead else endpoint,
        region_name=region,
        config=Config(
            connect_timeout=1 if dead else 10,
            read_timeout=1 if dead else 30,
            retries={"max_attempts": 0},
        ),
    )


def _stores() -> tuple[CountingClient, S3ArtifactStore, S3DurableEventStore]:
    endpoint = _required("OBJECT_STORE_ENDPOINT")
    bucket = _required("OBJECT_STORE_BUCKET")
    region = os.environ.get("OBJECT_STORE_REGION", "auto") or "auto"
    client = CountingClient(_new_raw_client(endpoint=endpoint, region=region))
    artifacts = S3ArtifactStore(bucket=bucket, prefix=_prefix(), client=client)
    events = S3DurableEventStore(
        bucket=bucket,
        schema_path=SCHEMA,
        prefix=_prefix(),
        client=client,
    )
    return client, artifacts, events


def _canonical(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def _assert_receipt_safe(encoded: bytes) -> None:
    text = encoded.decode("utf-8")
    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        value = os.environ.get(name, "")
        if value and value in text:
            raise RuntimeError(f"credential material leaked into proof receipt via {name}")


def _publish_receipt(events: S3DurableEventStore, relative: str, receipt: dict[str, Any]) -> None:
    encoded = _canonical(receipt)
    _assert_receipt_safe(encoded)
    events.backend.put_immutable(relative, encoded)


def _write_local_receipt(receipt: dict[str, Any]) -> None:
    path = Path(_required("FOSSIL_PROOF_RECEIPT_PATH"))
    encoded = _canonical(receipt)
    _assert_receipt_safe(encoded)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)


def _assert_raises(exc_type: type[BaseException], func: Any, message: str) -> None:
    try:
        func()
    except exc_type:
        return
    raise RuntimeError(message)


def write_phase() -> None:
    started = time.monotonic()
    bucket = _required("OBJECT_STORE_BUCKET")
    software_commit = _required("FOSSIL_SOFTWARE_COMMIT")
    client, artifacts, events = _stores()

    client.head_bucket(Bucket=bucket)

    artifact_payload = b"FOSSIL OBJECT_STORE_LIVE canonical artifact v1\n"
    artifact = artifacts.put_bytes(artifact_payload, media_type="text/plain")
    if artifacts.put_bytes(artifact_payload, media_type="text/plain") != artifact:
        raise RuntimeError("byte-identical artifact replay changed the canonical manifest")
    if artifacts.read_bytes(artifact["artifact_id"]) != artifact_payload:
        raise RuntimeError("canonical artifact bytes did not round-trip")
    if artifacts.verify(artifact["artifact_id"]) is not True:
        raise RuntimeError("canonical artifact verification did not pass")

    conflict_key = "proof-controls/immutable-conflict.bin"
    artifacts.backend.put_immutable(conflict_key, b"stable-v1")
    _assert_raises(
        RemoteObjectConflict,
        lambda: artifacts.backend.put_immutable(conflict_key, b"stable-v2"),
        "stable-key conflicting bytes did not fail closed",
    )

    redacted_artifact = artifacts.put_bytes(
        b"FOSSIL OBJECT_STORE_LIVE redactable artifact\n",
        media_type="text/plain",
    )
    artifact_tombstone_before_delete = {"passed": False}
    artifact_delete = artifacts.backend.delete

    def checked_artifact_delete(relative: str) -> None:
        tombstone_key = artifacts._redaction_key(redacted_artifact["artifact_id"])
        if not artifacts.backend.exists(tombstone_key):
            raise RuntimeError("artifact tombstone was not durable before sensitive delete")
        artifact_tombstone_before_delete["passed"] = True
        artifact_delete(relative)

    artifacts.backend.delete = checked_artifact_delete  # type: ignore[method-assign]
    artifacts.redact(
        redacted_artifact["artifact_id"],
        reason="OBJECT_STORE_LIVE privacy proof",
        authority="object-store-live",
        redacted_at="2026-08-15T17:30:00Z",
        request_ref="OBJECT_STORE_LIVE",
    )
    if not artifact_tombstone_before_delete["passed"]:
        raise RuntimeError("artifact tombstone-before-delete observation did not pass")
    _assert_raises(
        ArtifactRedactedError,
        lambda: artifacts.put_bytes(
            b"FOSSIL OBJECT_STORE_LIVE redactable artifact\n",
            media_type="text/plain",
        ),
        "redacted artifact identity was republished",
    )

    first = events.commit(_event(1))
    second = events.commit(_event(2))
    if events.commit(_event(2)) != second:
        raise RuntimeError("byte-identical event replay changed canonical event")

    conflicting = deepcopy(_event(2))
    conflicting["payload"]["claim_text"] = "conflicting content under stable identity"
    _assert_raises(
        IdempotencyConflict,
        lambda: events.commit(conflicting),
        "stable event identity accepted conflicting content",
    )

    event_tombstone_before_delete = {"passed": False}
    event_delete = events.backend.delete

    def checked_event_delete(relative: str) -> None:
        if not events.backend.exists(events._redaction_key(first["event_id"])):
            raise RuntimeError("event tombstone was not durable before event delete")
        event_tombstone_before_delete["passed"] = True
        event_delete(relative)

    events.backend.delete = checked_event_delete  # type: ignore[method-assign]
    events.redact(
        first["event_id"],
        reason="OBJECT_STORE_LIVE redaction proof",
        authority="object-store-live",
        redacted_at="2026-08-15T17:31:00Z",
        request_ref="OBJECT_STORE_LIVE",
    )
    if not event_tombstone_before_delete["passed"]:
        raise RuntimeError("event tombstone-before-delete observation did not pass")
    _assert_raises(
        EventRedactedError,
        lambda: events.commit(_event(1)),
        "redacted event identity was republished",
    )

    remaining = list(events.iter_events())
    if [item["event_id"] for item in remaining] != [second["event_id"]]:
        raise RuntimeError("canonical remote enumeration retained unexpected event identities")
    expected_digest = SemanticSnapshot.from_events(remaining).digest()

    region = os.environ.get("OBJECT_STORE_REGION", "auto") or "auto"
    dead_client = _new_raw_client(
        endpoint=_required("OBJECT_STORE_ENDPOINT"),
        region=region,
        dead=True,
    )
    unavailable = S3DurableEventStore(
        bucket=bucket,
        schema_path=SCHEMA,
        prefix=f"{_prefix()}/negative-control",
        client=dead_client,
    )
    _assert_raises(
        RemoteStoreUnavailable,
        lambda: unavailable.commit(_event(3)),
        "dead endpoint was normalized into durable success",
    )

    receipt = {
        "schema": "fossil.object-store-live.writer.v1",
        "status": "PASS",
        "software_commit": software_commit,
        "bucket": bucket,
        "proof_prefix": _prefix(),
        "artifact_id": artifact["artifact_id"],
        "redacted_artifact_id": redacted_artifact["artifact_id"],
        "redacted_event_id": first["event_id"],
        "remaining_event_ids": [second["event_id"]],
        "expected_snapshot_digest": expected_digest,
        "tombstone_before_delete": {
            "artifact": True,
            "event": True,
        },
        "negative_controls": {
            "immutable_conflict": "PASS",
            "event_conflict": "PASS",
            "dead_endpoint_fail_closed": "PASS",
            "redacted_republication_blocked": "PASS",
        },
        "metrics": {
            **client.metrics(),
            "elapsed_ms": round((time.monotonic() - started) * 1000),
        },
    }
    _publish_receipt(events, WRITER_RECEIPT, receipt)
    _write_local_receipt(receipt)
    print(
        "OBJECT_STORE_LIVE writer PASS "
        f"sha={software_commit} prefix={_prefix()} digest={expected_digest} "
        f"requests={receipt['metrics']['request_count']}"
    )


def _rebuild_once() -> tuple[str, list[str], dict[str, Any]]:
    client, _artifacts, events = _stores()
    remote_events = list(events.iter_events())
    expected_second = events.prepare(_event(2))
    expected_ids = [expected_second["event_id"]]
    actual_ids = [item["event_id"] for item in remote_events]
    if actual_ids != expected_ids:
        raise RuntimeError(
            f"empty-runner remote enumeration mismatch: expected {expected_ids}, got {actual_ids}"
        )

    redacted_id = events.prepare(_event(1))["event_id"]
    if not events.is_redacted(redacted_id):
        raise RuntimeError("redaction tombstone missing on empty-runner rebuild")
    _assert_raises(
        EventRedactedError,
        lambda: events.get(redacted_id),
        "redacted event resurrected during empty-runner rebuild",
    )

    with tempfile.TemporaryDirectory(prefix="fossil-object-store-live-") as temp:
        local = DurableEventStore(Path(temp) / "events", SCHEMA)
        if list(local.iter_events()):
            raise RuntimeError("fresh local rebuild directory was not empty")
        for event in remote_events:
            local.commit(event)
        digest = SemanticSnapshot.from_events(list(local.iter_events())).digest()

    return digest, actual_ids, client.metrics()


def rebuild_phase() -> None:
    started = time.monotonic()
    software_commit = _required("FOSSIL_SOFTWARE_COMMIT")
    client, _artifacts, events = _stores()
    writer = json.loads(events.backend.read(WRITER_RECEIPT).decode("utf-8"))
    if writer.get("status") != "PASS" or writer.get("software_commit") != software_commit:
        raise RuntimeError("writer receipt is absent, stale, or not PASS")

    first_digest, first_ids, first_metrics = _rebuild_once()
    second_digest, second_ids, second_metrics = _rebuild_once()
    expected = str(writer["expected_snapshot_digest"])
    if first_digest != expected or second_digest != expected:
        raise RuntimeError("fresh rebuild semantic digest does not match writer durable truth")
    if first_ids != second_ids:
        raise RuntimeError("second fresh rebuild produced different event identities")

    receipt = {
        "schema": "fossil.object-store-live.rebuild.v1",
        "status": "PASS",
        "software_commit": software_commit,
        "bucket": _required("OBJECT_STORE_BUCKET"),
        "proof_prefix": _prefix(),
        "writer_snapshot_digest": expected,
        "first_rebuild_digest": first_digest,
        "second_rebuild_digest": second_digest,
        "event_ids": first_ids,
        "redaction_non_resurrection": "PASS",
        "restartability": "PASS",
        "metrics": {
            "receipt_read_client": client.metrics(),
            "first_rebuild": first_metrics,
            "second_rebuild": second_metrics,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
        },
    }
    _publish_receipt(events, REBUILD_RECEIPT, receipt)
    _write_local_receipt(receipt)
    print(
        "OBJECT_STORE_LIVE rebuild PASS "
        f"sha={software_commit} prefix={_prefix()} digest={expected}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="FOSSIL live object-store durability proof")
    parser.add_argument("phase", choices=("write", "rebuild"))
    args = parser.parse_args()
    if args.phase == "write":
        write_phase()
    else:
        rebuild_phase()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
