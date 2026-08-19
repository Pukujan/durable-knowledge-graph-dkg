from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Iterator

from jsonschema import Draft202012Validator, FormatChecker

from ...artifact_store import ArtifactIntegrityError, ArtifactRedactedError
from ...domain.event_contracts import validate_event_for_commit
from ...domain.ontology import EndpointTypeResolver
from ...domain.promotion import PromotionSourceResolver
from ...event_store import (
    EventRedactedError,
    EventRedactionConflict,
    IdempotencyConflict,
)
from ...ids import deterministic_event_id, new_id


class RemoteStoreUnavailable(RuntimeError):
    """A remote operation could not establish durable storage semantics."""


class RemoteObjectConflict(RuntimeError):
    """A stable object key already exists with different canonical bytes."""


def _error_code(exc: BaseException) -> str | None:
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return None
    error = response.get("Error")
    if not isinstance(error, dict):
        return None
    code = error.get("Code")
    return str(code) if code is not None else None


def _default_s3_client(*, endpoint_url: str | None, region_name: str | None):
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover - exercised only with real runtime config
        raise RuntimeError(
            "S3 runtime client requires the optional 's3' dependency: "
            "install fossil-core[s3]"
        ) from exc

    options: dict[str, Any] = {}
    if endpoint_url:
        options["endpoint_url"] = endpoint_url
    if region_name:
        options["region_name"] = region_name
    return boto3.client("s3", **options)


class _S3ObjectBackend:
    """Minimal immutable byte-object surface shared by the domain adapters.

    The adapter intentionally relies only on ordinary S3-compatible operations.
    Conditional `If-None-Match: *` writes enforce a fail-closed immutable key
    contract. Provider credentials are left to the standard client credential
    chain and are never accepted or recorded as FOSSIL data.
    """

    _NOT_FOUND = {"404", "NoSuchKey", "NotFound", "NoSuchObject"}
    _PRECONDITION = {"412", "PreconditionFailed", "ConditionalRequestConflict"}

    def __init__(
        self,
        *,
        bucket: str,
        prefix: str = "",
        client: Any | None = None,
        endpoint_url: str | None = None,
        region_name: str | None = None,
    ):
        if not bucket or not bucket.strip():
            raise ValueError("S3 bucket is required")
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.client = client or _default_s3_client(
            endpoint_url=endpoint_url,
            region_name=region_name,
        )

    def key(self, relative: str) -> str:
        relative = relative.lstrip("/")
        return f"{self.prefix}/{relative}" if self.prefix else relative

    def read(self, relative: str) -> bytes:
        key = self.key(relative)
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            body = response["Body"]
            return body.read() if hasattr(body, "read") else bytes(body)
        except Exception as exc:
            if _error_code(exc) in self._NOT_FOUND:
                raise FileNotFoundError(key) from exc
            raise RemoteStoreUnavailable(
                f"durable object read failed for {relative}"
            ) from exc

    def exists(self, relative: str) -> bool:
        key = self.key(relative)
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception as exc:
            if _error_code(exc) in self._NOT_FOUND:
                return False
            raise RemoteStoreUnavailable(
                f"durable object existence check failed for {relative}"
            ) from exc

    def put_immutable(self, relative: str, data: bytes) -> bool:
        """Create an object once; return False only for byte-identical replay."""

        key = self.key(relative)
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                IfNoneMatch="*",
            )
            return True
        except Exception as exc:
            if _error_code(exc) not in self._PRECONDITION:
                raise RemoteStoreUnavailable(
                    f"durable object write failed for {relative}"
                ) from exc

        existing = self.read(relative)
        if existing == data:
            return False
        raise RemoteObjectConflict(
            f"stable object key already exists with different content: {relative}"
        )

    def delete(self, relative: str) -> None:
        key = self.key(relative)
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except Exception as exc:
            raise RemoteStoreUnavailable(
                f"durable object delete failed for {relative}"
            ) from exc

    def iter_keys(self, relative_prefix: str) -> Iterator[str]:
        full_prefix = self.key(relative_prefix)
        token: str | None = None
        while True:
            params: dict[str, Any] = {
                "Bucket": self.bucket,
                "Prefix": full_prefix,
            }
            if token:
                params["ContinuationToken"] = token
            try:
                response = self.client.list_objects_v2(**params)
            except Exception as exc:
                raise RemoteStoreUnavailable(
                    f"durable object enumeration failed for {relative_prefix}"
                ) from exc

            for item in response.get("Contents", []):
                key = str(item["Key"])
                if self.prefix:
                    prefix = f"{self.prefix}/"
                    if not key.startswith(prefix):
                        continue
                    key = key[len(prefix) :]
                yield key

            if not response.get("IsTruncated"):
                return
            token = response.get("NextContinuationToken")
            if not token:
                raise RemoteStoreUnavailable(
                    f"durable object enumeration truncated without continuation token: {relative_prefix}"
                )


class S3ArtifactStore:
    """S3-compatible implementation of the FOSSIL artifact-store contract."""

    def __init__(
        self,
        *,
        bucket: str,
        prefix: str = "",
        client: Any | None = None,
        endpoint_url: str | None = None,
        region_name: str | None = None,
    ):
        self.backend = _S3ObjectBackend(
            bucket=bucket,
            prefix=prefix,
            client=client,
            endpoint_url=endpoint_url,
            region_name=region_name,
        )

    @staticmethod
    def _canonical(value: dict[str, Any]) -> bytes:
        return (
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            + "\n"
        ).encode("utf-8")

    @staticmethod
    def artifact_id_for_digest(digest: str) -> str:
        return f"art_{digest[:32]}"

    @staticmethod
    def _blob_key(digest: str) -> str:
        return f"canonical/artifacts/blobs/sha256/{digest[:2]}/{digest}"

    @staticmethod
    def _manifest_key(artifact_id: str) -> str:
        suffix = artifact_id.removeprefix("art_")
        return f"canonical/artifacts/manifests/{suffix[:2]}/{artifact_id}.json"

    @staticmethod
    def _redaction_key(artifact_id: str) -> str:
        suffix = artifact_id.removeprefix("art_")
        return f"canonical/redactions/artifacts/{suffix[:2]}/{artifact_id}.json"

    def put_bytes(
        self,
        data: bytes,
        *,
        media_type: str = "application/octet-stream",
    ) -> dict[str, Any]:
        digest = hashlib.sha256(data).hexdigest()
        artifact_id = self.artifact_id_for_digest(digest)
        if self.is_redacted(artifact_id):
            raise ArtifactRedactedError(
                f"artifact {artifact_id} was redacted and cannot be republished under the same content identity"
            )

        manifest = {
            "artifact_id": artifact_id,
            "content_hash": {"algorithm": "sha256", "digest": digest},
            "byte_size": len(data),
            "media_type": media_type,
        }
        try:
            self.backend.put_immutable(self._blob_key(digest), data)
        except RemoteObjectConflict as exc:
            raise ArtifactIntegrityError(
                f"hash collision or corrupted blob for {artifact_id}"
            ) from exc

        encoded = self._canonical(manifest)
        try:
            self.backend.put_immutable(self._manifest_key(artifact_id), encoded)
        except RemoteObjectConflict as exc:
            raise ArtifactIntegrityError(f"manifest conflict for {artifact_id}") from exc
        return manifest

    def put_file(
        self,
        path: Path,
        *,
        media_type: str = "application/octet-stream",
    ) -> dict[str, Any]:
        return self.put_bytes(Path(path).read_bytes(), media_type=media_type)

    def get_manifest(self, artifact_id: str) -> dict[str, Any]:
        try:
            return json.loads(self.backend.read(self._manifest_key(artifact_id)).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ArtifactIntegrityError(f"invalid manifest for {artifact_id}") from exc

    def is_redacted(self, artifact_id: str) -> bool:
        return self.backend.exists(self._redaction_key(artifact_id))

    def get_redaction(self, artifact_id: str) -> dict[str, Any] | None:
        key = self._redaction_key(artifact_id)
        if not self.backend.exists(key):
            return None
        try:
            return json.loads(self.backend.read(key).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ArtifactIntegrityError(
                f"invalid redaction tombstone for {artifact_id}"
            ) from exc

    def read_bytes(self, artifact_id: str) -> bytes:
        if self.is_redacted(artifact_id):
            raise ArtifactRedactedError(f"artifact {artifact_id} has been redacted")
        manifest = self.get_manifest(artifact_id)
        return self.backend.read(self._blob_key(manifest["content_hash"]["digest"]))

    def verify(self, artifact_id: str) -> bool:
        manifest = self.get_manifest(artifact_id)
        data = self.read_bytes(artifact_id)
        digest = hashlib.sha256(data).hexdigest()
        if digest != manifest["content_hash"]["digest"] or len(data) != manifest["byte_size"]:
            raise ArtifactIntegrityError(f"artifact verification failed for {artifact_id}")
        return True

    def redact(
        self,
        artifact_id: str,
        *,
        reason: str,
        authority: str,
        redacted_at: str,
        request_ref: str | None = None,
    ) -> dict[str, Any]:
        if not reason or not authority or not redacted_at:
            raise ValueError("redaction requires reason, authority, and redacted_at")
        manifest = self.get_manifest(artifact_id)
        record = {
            "artifact_id": artifact_id,
            "redacted_at": redacted_at,
            "reason": reason,
            "authority": authority,
            "request_ref": request_ref,
            "content_hash": manifest["content_hash"],
            "byte_size": manifest["byte_size"],
            "media_type": manifest["media_type"],
        }
        encoded = self._canonical(record)
        try:
            self.backend.put_immutable(self._redaction_key(artifact_id), encoded)
        except RemoteObjectConflict as exc:
            raise ArtifactIntegrityError(
                f"redaction tombstone conflict for {artifact_id}"
            ) from exc

        self.backend.delete(self._blob_key(manifest["content_hash"]["digest"]))
        return record


class S3DurableEventStore:
    """S3-compatible immutable event store with explicit redaction semantics."""

    def __init__(
        self,
        *,
        bucket: str,
        schema_path: Path,
        prefix: str = "",
        client: Any | None = None,
        endpoint_url: str | None = None,
        region_name: str | None = None,
        endpoint_type_resolver: EndpointTypeResolver | None = None,
        promotion_source_resolver: PromotionSourceResolver | None = None,
    ):
        self.backend = _S3ObjectBackend(
            bucket=bucket,
            prefix=prefix,
            client=client,
            endpoint_url=endpoint_url,
            region_name=region_name,
        )
        schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(schema, format_checker=FormatChecker())
        self.endpoint_type_resolver = endpoint_type_resolver
        self.promotion_source_resolver = promotion_source_resolver

    @staticmethod
    def _canonical(event: dict[str, Any]) -> bytes:
        return (
            json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            + "\n"
        ).encode("utf-8")

    @staticmethod
    def _event_key(event_id: str) -> str:
        suffix = event_id.removeprefix("evt_")
        return f"canonical/events/{suffix[:2]}/{event_id}.json"

    @staticmethod
    def _redaction_key(event_id: str) -> str:
        suffix = event_id.removeprefix("evt_")
        return f"canonical/redactions/events/{suffix[:2]}/{event_id}.json"

    def prepare(self, event: dict[str, Any]) -> dict[str, Any]:
        candidate = copy.deepcopy(event)
        pack_id = candidate.get("pack_id")
        idem = candidate.get("idempotency_key")
        if pack_id and idem:
            expected = deterministic_event_id(pack_id, idem)
            supplied = candidate.get("event_id")
            if supplied and supplied != expected:
                raise IdempotencyConflict(
                    "event_id does not match deterministic idempotency identity"
                )
            candidate["event_id"] = expected
        elif not candidate.get("event_id"):
            candidate["event_id"] = new_id("evt")
        self.validator.validate(candidate)
        return candidate

    def validate(self, event: dict[str, Any]) -> dict[str, Any]:
        candidate = self.prepare(event)
        validate_event_for_commit(
            candidate,
            endpoint_type_resolver=self.endpoint_type_resolver,
            promotion_source_resolver=self.promotion_source_resolver,
        )
        return candidate

    def is_redacted(self, event_id: str) -> bool:
        return self.backend.exists(self._redaction_key(event_id))

    def get_redaction(self, event_id: str) -> dict[str, Any] | None:
        key = self._redaction_key(event_id)
        if not self.backend.exists(key):
            return None
        return json.loads(self.backend.read(key).decode("utf-8"))

    def iter_redactions(self) -> Iterator[dict[str, Any]]:
        keys = sorted(
            key
            for key in self.backend.iter_keys("canonical/redactions/events/")
            if key.endswith(".json")
        )
        for key in keys:
            yield json.loads(self.backend.read(key).decode("utf-8"))

    def commit(self, event: dict[str, Any]) -> dict[str, Any]:
        candidate = self.prepare(event)
        validate_event_for_commit(
            candidate,
            endpoint_type_resolver=self.endpoint_type_resolver,
            promotion_source_resolver=self.promotion_source_resolver,
        )
        event_id = candidate["event_id"]
        if self.is_redacted(event_id):
            raise EventRedactedError(
                f"event {event_id} was redacted and cannot be republished under the same identity"
            )
        data = self._canonical(candidate)
        try:
            self.backend.put_immutable(self._event_key(event_id), data)
        except RemoteObjectConflict as exc:
            raise IdempotencyConflict(
                f"event {event_id} already exists with different content"
            ) from exc
        return candidate

    def get(self, event_id: str) -> dict[str, Any]:
        if self.is_redacted(event_id):
            raise EventRedactedError(f"event {event_id} has been redacted")
        return json.loads(self.backend.read(self._event_key(event_id)).decode("utf-8"))

    def redact(
        self,
        event_id: str,
        *,
        reason: str,
        authority: str,
        redacted_at: str,
        request_ref: str | None = None,
    ) -> dict[str, Any]:
        if not reason or not authority or not redacted_at:
            raise ValueError("event redaction requires reason, authority, and redacted_at")

        existing = self.get_redaction(event_id)
        if existing is not None:
            requested = {
                "reason": reason,
                "authority": authority,
                "redacted_at": redacted_at,
                "request_ref": request_ref,
            }
            if any(existing.get(key) != value for key, value in requested.items()):
                raise EventRedactionConflict(
                    f"event {event_id} already has a different redaction tombstone"
                )
            return existing

        event = self.get(event_id)
        canonical = self._canonical(event)
        tombstone = {
            "event_id": event_id,
            "pack_id": event["pack_id"],
            "event_type": event["event_type"],
            "recorded_at": event["recorded_at"],
            "canonical_hash": {
                "algorithm": "sha256",
                "digest": hashlib.sha256(canonical).hexdigest(),
            },
            "redacted_at": redacted_at,
            "reason": reason,
            "authority": authority,
            "request_ref": request_ref,
        }
        try:
            self.backend.put_immutable(
                self._redaction_key(event_id), self._canonical(tombstone)
            )
        except RemoteObjectConflict as exc:
            raise EventRedactionConflict(
                f"could not publish event redaction tombstone for {event_id}"
            ) from exc

        self.backend.delete(self._event_key(event_id))
        return tombstone

    def iter_events(self) -> Iterator[dict[str, Any]]:
        keys = sorted(
            key
            for key in self.backend.iter_keys("canonical/events/")
            if key.endswith(".json")
        )
        for key in keys:
            yield json.loads(self.backend.read(key).decode("utf-8"))


__all__ = [
    "RemoteStoreUnavailable",
    "S3ArtifactStore",
    "S3DurableEventStore",
]
