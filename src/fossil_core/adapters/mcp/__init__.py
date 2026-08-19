from __future__ import annotations

from typing import Any, Mapping

from fossil_core.ports.capability import CapabilityError


__all__ = ["ThinMCPAdapter"]


class ThinMCPAdapter:
    """MCP-shaped dictionary adapter over :class:`CorpusService`.

    No MCP SDK types appear in the domain service. Replacing this adapter does not
    change durable schemas or corpus semantics.
    """

    TOOL_NAMES = (
        "fossil.search",
        "fossil.read",
        "fossil.lineage",
        "fossil.propose",
        "fossil.validate",
        "fossil.commit",
        "fossil.manage",
    )

    def __init__(
        self,
        *,
        service: CorpusService,
        access: PackAccess,
        context: AgentContext,
    ):
        self.service = service
        self.access = access
        self.context = context

    def list_tools(self) -> list[str]:
        return list(self.TOOL_NAMES)

    def invoke(self, tool_name: str, arguments: Mapping[str, Any]) -> Any:
        args = dict(arguments)
        if tool_name == "fossil.search":
            return self.service.search(
                str(args["query"]),
                access=self.access,
                context=self.context,
                limit=int(args.get("limit", 20)),
            )
        if tool_name == "fossil.read":
            return self.service.read(
                str(args["event_id"]), access=self.access, context=self.context
            )
        if tool_name == "fossil.lineage":
            return self.service.lineage(
                str(args["conversation_id"]),
                access=self.access,
                context=self.context,
                node_id=args.get("node_id"),
            )
        if tool_name == "fossil.propose":
            return self.service.propose(
                event_type=str(args["event_type"]),
                pack_id=str(args["pack_id"]),
                subject_refs=list(args["subject_refs"]),
                payload=dict(args["payload"]),
                occurred_at=str(args["occurred_at"]),
                recorded_at=str(args["recorded_at"]),
                idempotency_key=str(args["idempotency_key"]),
                evidence_refs=list(args.get("evidence_refs", [])),
                source_snapshot_refs=list(args.get("source_snapshot_refs", [])),
                caused_by_event_ids=list(args.get("caused_by_event_ids", [])),
                correlation_id=args.get("correlation_id"),
                provenance=dict(args.get("provenance", {})),
                access=self.access,
                context=self.context,
            )
        if tool_name == "fossil.validate":
            return self.service.validate(
                dict(args["event"]), access=self.access, context=self.context
            )
        if tool_name == "fossil.commit":
            return self.service.commit(
                dict(args["event"]), access=self.access, context=self.context
            )
        if tool_name == "fossil.manage":
            return self.service.manage(str(args["action"]), context=self.context)
        raise CapabilityError(
            f"tool {tool_name!r} is not in the FOSSIL agent capability surface"
        )
