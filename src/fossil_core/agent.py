from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker

from fossil_core.event_store import DurableEventStore
from fossil_core.pack import PackAccess
from fossil_core.promotion import build_promotion_event


class CapabilityError(PermissionError):
    pass


class AgentProvenanceError(ValueError):
    pass


class SkillRegistry:
    """Discover small Skill manifests without eagerly loading methodology text."""

    def __init__(self, root: Path, schema_path: Path):
        self.root = Path(root)
        schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(schema, format_checker=FormatChecker())
        self._skills: dict[str, dict[str, Any]] = {}
        self._skill_dirs: dict[str, Path] = {}
        self._loaded_methodologies: set[str] = set()
        self._load_manifests()

    def _load_manifests(self) -> None:
        for path in sorted(self.root.glob("*/manifest.json")):
            manifest = json.loads(path.read_text(encoding="utf-8"))
            self.validator.validate(manifest)
            skill_id = manifest["skill_id"]
            if skill_id in self._skills:
                raise ValueError(f"duplicate skill_id: {skill_id}")
            methodology_path = path.parent / manifest["methodology_ref"]
            if not methodology_path.is_file():
                raise ValueError(f"missing methodology for {skill_id}: {methodology_path}")
            self._skills[skill_id] = manifest
            self._skill_dirs[skill_id] = path.parent

    def list_skills(self) -> list[dict[str, Any]]:
        """Return discovery metadata only; methodology stays unloaded."""

        return [copy.deepcopy(self._skills[key]) for key in sorted(self._skills)]

    def discover(self, query: str, *, capability: str | None = None) -> list[dict[str, Any]]:
        terms = [term for term in query.lower().split() if term]
        matches = []
        for manifest in self.list_skills():
            if capability and capability not in manifest["capabilities"]:
                continue
            haystack = " ".join(
                [manifest["name"], manifest["summary"], *manifest["triggers"]]
            ).lower()
            if not terms or any(term in haystack for term in terms):
                matches.append(manifest)
        return matches

    def get(self, skill_id: str) -> dict[str, Any]:
        if skill_id not in self._skills:
            raise KeyError(skill_id)
        return copy.deepcopy(self._skills[skill_id])

    def require_capability(self, skill_id: str, capability: str) -> dict[str, Any]:
        manifest = self.get(skill_id)
        if capability not in manifest["capabilities"]:
            raise CapabilityError(
                f"skill {skill_id} does not grant corpus capability {capability}"
            )
        return manifest

    def load_methodology(self, skill_id: str) -> str:
        """Explicit progressive-disclosure boundary for methodology instructions."""

        manifest = self.get(skill_id)
        path = self._skill_dirs[skill_id] / manifest["methodology_ref"]
        self._loaded_methodologies.add(skill_id)
        return path.read_text(encoding="utf-8")

    def methodology_loaded(self, skill_id: str) -> bool:
        return skill_id in self._loaded_methodologies


@dataclass(frozen=True)
class AgentContext:
    actor_id: str
    model_id: str
    harness_version: str
    skill_id: str
    skill_version: str

    def __post_init__(self) -> None:
        for name, value in (
            ("actor_id", self.actor_id),
            ("model_id", self.model_id),
            ("harness_version", self.harness_version),
            ("skill_id", self.skill_id),
            ("skill_version", self.skill_version),
        ):
            if not value:
                raise AgentProvenanceError(f"agent context requires {name}")

    def durable_actor(self) -> dict[str, Any]:
        return {
            "actor_type": "agent",
            "actor_id": self.actor_id,
            "model_id": self.model_id,
            "harness_version": self.harness_version,
            "skill_id": self.skill_id,
            "skill_version": self.skill_version,
        }


class CorpusService:
    """Protocol-independent safe domain boundary for agent-facing corpus work.

    This service has no Graphiti/Neo4j client and intentionally exposes no
    arbitrary projection/database mutation. Durable commit is the only normal
    knowledge mutation. Projection workers operate downstream of accepted events.
    """

    CAPABILITIES = ("search", "read", "lineage", "propose", "validate", "commit", "manage")

    def __init__(
        self,
        *,
        event_store: DurableEventStore,
        skills: SkillRegistry,
        lineages: Mapping[str, tuple[str, Any]] | None = None,
        service_version: str = "1",
    ):
        self.event_store = event_store
        self.skills = skills
        self.lineages = dict(lineages or {})
        self.service_version = service_version

    def _authorize(self, context: AgentContext, capability: str) -> dict[str, Any]:
        manifest = self.skills.require_capability(context.skill_id, capability)
        if manifest["version"] != context.skill_version:
            raise AgentProvenanceError(
                f"context skill version {context.skill_version} does not match "
                f"registered {manifest['version']}"
            )
        return manifest

    @staticmethod
    def _require_actor_match(event: Mapping[str, Any], context: AgentContext) -> None:
        if event.get("actor") != context.durable_actor():
            raise AgentProvenanceError(
                "agent event actor/model/harness/skill provenance does not match session context"
            )

    def search(
        self,
        query: str,
        *,
        access: PackAccess,
        context: AgentContext,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        self._authorize(context, "search")
        if limit < 1 or limit > 100:
            raise ValueError("search limit must be between 1 and 100")
        needle = query.lower().strip()
        results: list[dict[str, Any]] = []
        for event in self.event_store.iter_events():
            if event["pack_id"] not in access.read_mounts:
                continue
            serialized = json.dumps(event, sort_keys=True, ensure_ascii=False).lower()
            if needle and needle not in serialized:
                continue
            results.append(
                {
                    "event_id": event["event_id"],
                    "event_type": event["event_type"],
                    "pack_id": event["pack_id"],
                    "recorded_at": event["recorded_at"],
                    "subject_refs": list(event.get("subject_refs", [])),
                    "evidence_refs": list(event.get("evidence_refs", [])),
                    "source_snapshot_refs": list(event.get("source_snapshot_refs", [])),
                }
            )
            if len(results) >= limit:
                break
        return results

    def read(
        self,
        event_id: str,
        *,
        access: PackAccess,
        context: AgentContext,
    ) -> dict[str, Any]:
        self._authorize(context, "read")
        event = self.event_store.get(event_id)
        access.require_read(event["pack_id"])
        return event

    def lineage(
        self,
        conversation_id: str,
        *,
        access: PackAccess,
        context: AgentContext,
        node_id: str | None = None,
    ) -> dict[str, Any]:
        self._authorize(context, "lineage")
        if conversation_id not in self.lineages:
            raise KeyError(conversation_id)
        pack_id, lineage = self.lineages[conversation_id]
        access.require_read(pack_id)
        result: dict[str, Any] = {
            "conversation_id": conversation_id,
            "pack_id": pack_id,
            "current_conclusions": lineage.current_conclusions(),
            "historical_nodes": lineage.historical_nodes(),
        }
        if node_id is not None:
            result["node"] = lineage.node(node_id)
            result["citations"] = lineage.citations(node_id)
            result["opposing_positions"] = lineage.opposing_positions(node_id)
        return result

    def propose(
        self,
        *,
        event_type: str,
        pack_id: str,
        subject_refs: list[str],
        payload: dict[str, Any],
        occurred_at: str,
        recorded_at: str,
        idempotency_key: str,
        access: PackAccess,
        context: AgentContext,
        evidence_refs: list[str] | None = None,
        source_snapshot_refs: list[str] | None = None,
        caused_by_event_ids: list[str] | None = None,
        correlation_id: str | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._authorize(context, "propose")
        access.require_write(pack_id)
        merged_provenance = {
            "method": "agent_proposal",
            "prompt_or_policy_ref": f"{context.skill_id}@{context.skill_version}",
            **(provenance or {}),
        }
        event = {
            "schema_version": "dkg.event.v1",
            "event_type": event_type,
            "occurred_at": occurred_at,
            "recorded_at": recorded_at,
            "pack_id": pack_id,
            "actor": context.durable_actor(),
            "subject_refs": list(subject_refs),
            "caused_by_event_ids": list(caused_by_event_ids or []),
            "correlation_id": correlation_id,
            "idempotency_key": idempotency_key,
            "evidence_refs": list(evidence_refs or []),
            "source_snapshot_refs": list(source_snapshot_refs or []),
            "payload": copy.deepcopy(payload),
            "provenance": merged_provenance,
        }
        return self.event_store.prepare(event)

    def propose_promotion(
        self,
        *,
        source_pack_id: str,
        target_pack_id: str,
        subject_refs: list[str],
        occurred_at: str,
        recorded_at: str,
        idempotency_key: str,
        access: PackAccess,
        context: AgentContext,
        evidence_refs: list[str] | None = None,
        reason: str = "",
    ) -> dict[str, Any]:
        self._authorize(context, "propose")
        access.require_read(source_pack_id)
        access.require_write(target_pack_id)
        event = build_promotion_event(
            source_pack_id=source_pack_id,
            target_pack_id=target_pack_id,
            subject_refs=subject_refs,
            actor=context.durable_actor(),
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            idempotency_key=idempotency_key,
            evidence_refs=evidence_refs or [],
            reason=reason,
        )
        event["provenance"]["prompt_or_policy_ref"] = (
            f"{context.skill_id}@{context.skill_version}"
        )
        return self.event_store.prepare(event)

    def validate(
        self,
        event: dict[str, Any],
        *,
        access: PackAccess,
        context: AgentContext,
    ) -> dict[str, Any]:
        self._authorize(context, "validate")
        access.require_write(event["pack_id"])
        self._require_actor_match(event, context)
        return self.event_store.validate(event)

    def commit(
        self,
        event: dict[str, Any],
        *,
        access: PackAccess,
        context: AgentContext,
    ) -> dict[str, Any]:
        self._authorize(context, "commit")
        access.require_write(event["pack_id"])
        self._require_actor_match(event, context)
        return self.event_store.commit(event)

    def manage(
        self,
        action: str,
        *,
        context: AgentContext,
    ) -> dict[str, Any]:
        self._authorize(context, "manage")
        if action == "capabilities":
            return {
                "service_version": self.service_version,
                "capabilities": list(self.CAPABILITIES),
                "arbitrary_graph_mutation": False,
            }
        if action == "skills":
            return {"skills": self.skills.list_skills()}
        if action == "health":
            return {
                "status": "ok",
                "service_version": self.service_version,
                "event_store_root": str(self.event_store.root),
            }
        raise CapabilityError(f"unsupported management action: {action}")


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
