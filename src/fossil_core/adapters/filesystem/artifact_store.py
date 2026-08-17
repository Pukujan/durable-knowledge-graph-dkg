from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .io import publish_immutable


class ArtifactIntegrityError(RuntimeError):
    pass


class ArtifactRedactedError(FileNotFoundError):
    pass


class ArtifactStore:
    """Content-addressed evidence store with an exceptional redaction path.

    Ordinary writes are immutable. Redaction is intentionally separate: an
    immutable tombstone is published first, then the sensitive blob bytes are
    removed. Manifests/tombstones remain so historical references can explain
    why bytes are unavailable without retaining the redacted content.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.blobs = self.root / "blobs" / "sha256"
        self.manifests = self.root / "manifests"
        self.redactions = self.root / "redactions"
        self.blobs.mkdir(parents=True, exist_ok=True)
        self.manifests.mkdir(parents=True, exist_ok=True)
        self.redactions.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _canonical(value: dict[str, Any]) -> bytes:
        return (
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            + "\n"
        ).encode("utf-8")

    @staticmethod
    def artifact_id_for_digest(digest: str) -> str:
        return f"art_{digest[:32]}"

    def _blob_path(self, digest: str) -> Path:
        return self.blobs / digest[:2] / digest

    def _manifest_path(self, artifact_id: str) -> Path:
        suffix = artifact_id.removeprefix("art_")
        return self.manifests / suffix[:2] / f"{artifact_id}.json"

    def _redaction_path(self, artifact_id: str) -> Path:
        suffix = artifact_id.removeprefix("art_")
        return self.redactions / suffix[:2] / f"{artifact_id}.json"

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

        blob_path = self._blob_path(digest)
        if not publish_immutable(blob_path, data) and blob_path.read_bytes() != data:
            raise ArtifactIntegrityError(f"hash collision or corrupted blob for {artifact_id}")

        manifest_path = self._manifest_path(artifact_id)
        encoded = self._canonical(manifest)
        if not publish_immutable(manifest_path, encoded):
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            if self._canonical(existing) != encoded:
                raise ArtifactIntegrityError(f"manifest conflict for {artifact_id}")
        return manifest

    def put_file(
        self,
        path: Path,
        *,
        media_type: str = "application/octet-stream",
    ) -> dict[str, Any]:
        return self.put_bytes(Path(path).read_bytes(), media_type=media_type)

    def get_manifest(self, artifact_id: str) -> dict[str, Any]:
        return json.loads(self._manifest_path(artifact_id).read_text(encoding="utf-8"))

    def is_redacted(self, artifact_id: str) -> bool:
        return self._redaction_path(artifact_id).exists()

    def get_redaction(self, artifact_id: str) -> dict[str, Any] | None:
        path = self._redaction_path(artifact_id)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def read_bytes(self, artifact_id: str) -> bytes:
        if self.is_redacted(artifact_id):
            raise ArtifactRedactedError(f"artifact {artifact_id} has been redacted")
        manifest = self.get_manifest(artifact_id)
        return self._blob_path(manifest["content_hash"]["digest"]).read_bytes()

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
        """Publish a durable tombstone before physically removing blob bytes."""

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
        path = self._redaction_path(artifact_id)
        encoded = self._canonical(record)
        if not publish_immutable(path, encoded):
            existing = json.loads(path.read_text(encoding="utf-8"))
            if self._canonical(existing) != encoded:
                raise ArtifactIntegrityError(
                    f"redaction tombstone conflict for {artifact_id}"
                )
            record = existing

        blob_path = self._blob_path(manifest["content_hash"]["digest"])
        try:
            blob_path.unlink()
        except FileNotFoundError:
            pass
        return record
