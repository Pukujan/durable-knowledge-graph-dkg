from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ArtifactStorePort(Protocol):
    """Durable artifact semantics independent of a physical storage provider."""

    def put_bytes(
        self,
        data: bytes,
        *,
        media_type: str = "application/octet-stream",
    ) -> dict[str, Any]: ...

    def put_file(
        self,
        path: Path,
        *,
        media_type: str = "application/octet-stream",
    ) -> dict[str, Any]: ...

    def get_manifest(self, artifact_id: str) -> dict[str, Any]: ...

    def is_redacted(self, artifact_id: str) -> bool: ...

    def get_redaction(self, artifact_id: str) -> dict[str, Any] | None: ...

    def read_bytes(self, artifact_id: str) -> bytes: ...

    def verify(self, artifact_id: str) -> bool: ...

    def redact(
        self,
        artifact_id: str,
        *,
        reason: str,
        authority: str,
        redacted_at: str,
        request_ref: str | None = None,
    ) -> dict[str, Any]: ...
