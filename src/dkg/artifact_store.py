from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .io import publish_immutable


class ArtifactIntegrityError(RuntimeError):
    pass


class ArtifactStore:
    """Content-addressed immutable evidence store.

    The blob identity depends only on bytes. Source URL, filename, authorship,
    and other contextual provenance belong in durable knowledge events so the
    same evidence bytes can be observed in more than one context.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.blobs = self.root / "blobs" / "sha256"
        self.manifests = self.root / "manifests"
        self.blobs.mkdir(parents=True, exist_ok=True)
        self.manifests.mkdir(parents=True, exist_ok=True)

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

    def put_bytes(
        self,
        data: bytes,
        *,
        media_type: str = "application/octet-stream",
    ) -> dict[str, Any]:
        digest = hashlib.sha256(data).hexdigest()
        artifact_id = self.artifact_id_for_digest(digest)
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

    def read_bytes(self, artifact_id: str) -> bytes:
        manifest = self.get_manifest(artifact_id)
        return self._blob_path(manifest["content_hash"]["digest"]).read_bytes()

    def verify(self, artifact_id: str) -> bool:
        manifest = self.get_manifest(artifact_id)
        data = self.read_bytes(artifact_id)
        digest = hashlib.sha256(data).hexdigest()
        if digest != manifest["content_hash"]["digest"] or len(data) != manifest["byte_size"]:
            raise ArtifactIntegrityError(f"artifact verification failed for {artifact_id}")
        return True
