from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from fossil_core.artifact_store import ArtifactRedactedError
from fossil_core.s3_storage import S3ArtifactStore

import live_object_store_proof as base


CANONICAL_ARTIFACT_PAYLOAD = b"FOSSIL OBJECT_STORE_LIVE canonical artifact v1\n"
REDACTABLE_ARTIFACT_PAYLOAD = b"FOSSIL OBJECT_STORE_LIVE redactable artifact\n"
MEDIA_TYPE = "text/plain"


def _artifact_identity(data: bytes) -> tuple[str, str]:
    digest = hashlib.sha256(data).hexdigest()
    return S3ArtifactStore.artifact_id_for_digest(digest), digest


def _expected_manifest(artifact_id: str, digest: str, data: bytes) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "content_hash": {"algorithm": "sha256", "digest": digest},
        "byte_size": len(data),
        "media_type": MEDIA_TYPE,
    }


def _verify_artifacts_once(fixture_identity: str) -> tuple[dict[str, Any], dict[str, Any]]:
    client, artifacts, _events = base._stores()

    artifact_id, artifact_digest = _artifact_identity(CANONICAL_ARTIFACT_PAYLOAD)
    if artifact_id != fixture_identity:
        raise RuntimeError(
            f"fresh-runner fixture identity mismatch: expected {artifact_id}, got {fixture_identity}"
        )

    manifest = artifacts.get_manifest(artifact_id)
    expected_manifest = _expected_manifest(
        artifact_id,
        artifact_digest,
        CANONICAL_ARTIFACT_PAYLOAD,
    )
    if manifest != expected_manifest:
        raise RuntimeError("fresh-runner canonical artifact manifest does not match expected identity")
    if artifacts.read_bytes(artifact_id) != CANONICAL_ARTIFACT_PAYLOAD:
        raise RuntimeError("fresh-runner canonical artifact bytes do not match expected content")
    if artifacts.verify(artifact_id) is not True:
        raise RuntimeError("fresh-runner canonical artifact hash/size verification did not pass")

    redacted_artifact_id, redacted_digest = _artifact_identity(REDACTABLE_ARTIFACT_PAYLOAD)
    redacted_manifest = artifacts.get_manifest(redacted_artifact_id)
    expected_redacted_manifest = _expected_manifest(
        redacted_artifact_id,
        redacted_digest,
        REDACTABLE_ARTIFACT_PAYLOAD,
    )
    if redacted_manifest != expected_redacted_manifest:
        raise RuntimeError("fresh-runner redacted artifact manifest identity changed")
    if not artifacts.is_redacted(redacted_artifact_id):
        raise RuntimeError("fresh-runner redacted artifact tombstone is missing")

    tombstone = artifacts.get_redaction(redacted_artifact_id)
    if tombstone is None:
        raise RuntimeError("fresh-runner redacted artifact tombstone could not be reopened")
    for key, expected in {
        "artifact_id": redacted_artifact_id,
        "content_hash": {"algorithm": "sha256", "digest": redacted_digest},
        "byte_size": len(REDACTABLE_ARTIFACT_PAYLOAD),
        "media_type": MEDIA_TYPE,
    }.items():
        if tombstone.get(key) != expected:
            raise RuntimeError(f"fresh-runner redaction tombstone mismatch for {key}")

    if artifacts.backend.exists(artifacts._blob_key(redacted_digest)):
        raise RuntimeError("fresh-runner found redacted sensitive artifact bytes still present")
    base._assert_raises(
        ArtifactRedactedError,
        lambda: artifacts.read_bytes(redacted_artifact_id),
        "redacted artifact resurrected during fresh-runner read",
    )
    base._assert_raises(
        ArtifactRedactedError,
        lambda: artifacts.put_bytes(REDACTABLE_ARTIFACT_PAYLOAD, media_type=MEDIA_TYPE),
        "fresh runner was able to republish a redacted artifact identity",
    )

    proof = {
        "artifact_id": artifact_id,
        "artifact_sha256": artifact_digest,
        "artifact_byte_size": len(CANONICAL_ARTIFACT_PAYLOAD),
        "redacted_artifact_id": redacted_artifact_id,
        "artifact_exact_bytes_hash_identity": "PASS",
        "artifact_redaction_non_resurrection": "PASS",
    }
    return proof, client.metrics()


def rebuild_phase() -> None:
    started = time.monotonic()
    software_commit = base._required("FOSSIL_SOFTWARE_COMMIT")
    fixture_identity = base._required("FOSSIL_FIXTURE_IDENTITY")
    client, _artifacts, events = base._stores()

    writer = json.loads(events.backend.read(base.WRITER_RECEIPT).decode("utf-8"))
    if writer.get("status") != "PASS" or writer.get("software_commit") != software_commit:
        raise RuntimeError("writer receipt is absent, stale, or not PASS")
    if writer.get("proof_prefix") != base._prefix():
        raise RuntimeError("runner B proof prefix does not match the durable writer receipt")
    if writer.get("artifact_id") != fixture_identity:
        raise RuntimeError("runner B fixture identity does not match the durable writer receipt")

    expected_redacted_artifact_id, _ = _artifact_identity(REDACTABLE_ARTIFACT_PAYLOAD)
    if writer.get("redacted_artifact_id") != expected_redacted_artifact_id:
        raise RuntimeError("writer receipt redacted artifact identity is not the deterministic fixture")

    first_artifacts, first_artifact_metrics = _verify_artifacts_once(fixture_identity)
    first_digest, first_ids, first_event_metrics = base._rebuild_once()

    second_artifacts, second_artifact_metrics = _verify_artifacts_once(fixture_identity)
    second_digest, second_ids, second_event_metrics = base._rebuild_once()

    expected_digest = str(writer["expected_snapshot_digest"])
    if first_digest != expected_digest or second_digest != expected_digest:
        raise RuntimeError("fresh rebuild semantic digest does not match writer durable truth")
    if first_ids != second_ids:
        raise RuntimeError("second fresh rebuild produced different event identities")
    if first_ids != list(writer.get("remaining_event_ids", [])):
        raise RuntimeError("fresh-runner event identities do not match the durable writer receipt")
    if first_artifacts != second_artifacts:
        raise RuntimeError("second fresh rebuild produced different artifact proof results")

    receipt = {
        "schema": "fossil.object-store-live.rebuild.v2",
        "status": "PASS",
        "software_commit": software_commit,
        "bucket": base._required("OBJECT_STORE_BUCKET"),
        "proof_prefix": base._prefix(),
        "fixture_identity": fixture_identity,
        "writer_snapshot_digest": expected_digest,
        "first_rebuild_digest": first_digest,
        "second_rebuild_digest": second_digest,
        "event_ids": first_ids,
        "artifact_id": first_artifacts["artifact_id"],
        "redacted_artifact_id": first_artifacts["redacted_artifact_id"],
        "artifact_exact_bytes_hash_identity": "PASS",
        "artifact_rebuild_verification": "PASS",
        "redaction_non_resurrection": "PASS",
        "restartability": "PASS",
        "metrics": {
            "receipt_read_client": client.metrics(),
            "first_rebuild": {
                "artifact_remote": first_artifact_metrics,
                "event_remote_and_local": first_event_metrics,
            },
            "second_rebuild": {
                "artifact_remote": second_artifact_metrics,
                "event_remote_and_local": second_event_metrics,
            },
            "elapsed_ms": round((time.monotonic() - started) * 1000),
        },
    }
    base._publish_receipt(events, base.REBUILD_RECEIPT, receipt)
    base._write_local_receipt(receipt)
    print(
        "OBJECT_STORE_LIVE rebuild PASS "
        f"sha={software_commit} prefix={base._prefix()} "
        f"artifact={fixture_identity} digest={expected_digest}"
    )


def main() -> int:
    rebuild_phase()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
