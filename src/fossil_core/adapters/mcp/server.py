from __future__ import annotations

from typing import Any

from mcp.server import MCPServer

from fossil_core.domain.pack import PackBoundaryError
from fossil_core.ports.capability import CapabilityError

from . import ThinMCPAdapter


class FossilMCPToolError(RuntimeError):
    """Stable agent-visible MCP failure without exposing internal exceptions."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _mapped_error(exc: Exception) -> FossilMCPToolError:
    if isinstance(exc, PackBoundaryError):
        return FossilMCPToolError("unauthorized_pack", str(exc))
    if isinstance(exc, CapabilityError):
        return FossilMCPToolError("capability_denied", str(exc))
    if isinstance(exc, FileNotFoundError):
        return FossilMCPToolError("not_found", str(exc))
    if isinstance(exc, KeyError):
        detail = str(exc.args[0]) if exc.args else "resource not found"
        return FossilMCPToolError("not_found", detail)
    if isinstance(exc, (TypeError, ValueError)):
        return FossilMCPToolError("invalid_request", str(exc))
    if isinstance(exc, OSError):
        return FossilMCPToolError("canonical_store_unavailable", str(exc))
    return FossilMCPToolError("internal_error", "FOSSIL tool execution failed")


def _invoke(adapter: ThinMCPAdapter, tool_name: str, arguments: dict[str, Any]) -> Any:
    try:
        return adapter.invoke(tool_name, arguments)
    except FossilMCPToolError:
        raise
    except Exception as exc:
        raise _mapped_error(exc) from exc


def build_mcp_server(adapter: ThinMCPAdapter) -> MCPServer:
    """Expose the frozen ThinMCPAdapter capability surface as a real MCP server.

    The transport layer deliberately does not know Graphiti or Neo4j mutation APIs.
    Every tool delegates to ``ThinMCPAdapter.invoke`` so pack authorization,
    provenance checks, durable validation, and the canonical seven-tool allowlist
    remain the single source of truth.
    """

    server = MCPServer(
        name="fossil-core",
        version="0.1.0",
        instructions=(
            "FOSSIL durable corpus tools. Durable events are canonical; graph "
            "projections are rebuildable and cannot be mutated through this surface."
        ),
    )

    @server.tool(name="fossil.search")
    def fossil_search(query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search readable FOSSIL packs through the canonical corpus service."""

        return _invoke(adapter, "fossil.search", {"query": query, "limit": limit})

    @server.tool(name="fossil.read")
    def fossil_read(event_id: str) -> dict[str, Any]:
        """Read one durable event when its pack is mounted for the caller."""

        return _invoke(adapter, "fossil.read", {"event_id": event_id})

    @server.tool(name="fossil.lineage")
    def fossil_lineage(
        conversation_id: str, node_id: str | None = None
    ) -> dict[str, Any]:
        """Read conversation lineage through the pack-authorized corpus boundary."""

        arguments: dict[str, Any] = {"conversation_id": conversation_id}
        if node_id is not None:
            arguments["node_id"] = node_id
        return _invoke(adapter, "fossil.lineage", arguments)

    @server.tool(name="fossil.propose")
    def fossil_propose(
        event_type: str,
        pack_id: str,
        subject_refs: list[str],
        payload: dict[str, Any],
        occurred_at: str,
        recorded_at: str,
        idempotency_key: str,
        evidence_refs: list[str] | None = None,
        source_snapshot_refs: list[str] | None = None,
        caused_by_event_ids: list[str] | None = None,
        correlation_id: str | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Prepare a pack-authorized durable knowledge proposal."""

        return _invoke(
            adapter,
            "fossil.propose",
            {
                "event_type": event_type,
                "pack_id": pack_id,
                "subject_refs": subject_refs,
                "payload": payload,
                "occurred_at": occurred_at,
                "recorded_at": recorded_at,
                "idempotency_key": idempotency_key,
                "evidence_refs": evidence_refs,
                "source_snapshot_refs": source_snapshot_refs,
                "caused_by_event_ids": caused_by_event_ids,
                "correlation_id": correlation_id,
                "provenance": provenance,
            },
        )

    @server.tool(name="fossil.validate")
    def fossil_validate(event: dict[str, Any]) -> dict[str, Any]:
        """Validate a prepared event without committing it."""

        return _invoke(adapter, "fossil.validate", {"event": event})

    @server.tool(name="fossil.commit")
    def fossil_commit(event: dict[str, Any]) -> dict[str, Any]:
        """Commit a validated durable event through the canonical writer."""

        return _invoke(adapter, "fossil.commit", {"event": event})

    @server.tool(name="fossil.manage")
    def fossil_manage(action: str) -> dict[str, Any]:
        """Read the bounded management surface such as capabilities or health."""

        return _invoke(adapter, "fossil.manage", {"action": action})

    registered = tuple(tool.name for tool in server._tool_manager.list_tools())
    if registered != ThinMCPAdapter.TOOL_NAMES:
        raise RuntimeError(
            "network MCP tool surface drifted from ThinMCPAdapter allowlist: "
            f"{registered!r}"
        )
    return server


__all__ = ["FossilMCPToolError", "build_mcp_server"]
