from __future__ import annotations

from typing import Any, Iterator, Protocol, runtime_checkable


@runtime_checkable
class EventStorePort(Protocol):
    """Durable event semantics independent of a physical storage provider."""

    def prepare(self, event: dict[str, Any]) -> dict[str, Any]: ...

    def validate(self, event: dict[str, Any]) -> dict[str, Any]: ...

    def is_redacted(self, event_id: str) -> bool: ...

    def get_redaction(self, event_id: str) -> dict[str, Any] | None: ...

    def iter_redactions(self) -> Iterator[dict[str, Any]]: ...

    def commit(self, event: dict[str, Any]) -> dict[str, Any]: ...

    def get(self, event_id: str) -> dict[str, Any]: ...

    def redact(
        self,
        event_id: str,
        *,
        reason: str,
        authority: str,
        redacted_at: str,
        request_ref: str | None = None,
    ) -> dict[str, Any]: ...

    def iter_events(self) -> Iterator[dict[str, Any]]: ...
