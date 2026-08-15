from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fossil_core.contracts import ProjectionReceipt
from fossil_core.projection.ledger import ProjectionLedger
from fossil_core.projection.migration import ordered_events


class GraphitiProjectionAdapter:
    """Graphiti/Neo4j materialized projection of already accepted DKG events."""

    name = "graphiti-neo4j"
    version = "1"

    def __init__(
        self,
        *,
        client: Any,
        ledger: ProjectionLedger,
        build_manifest: dict[str, Any],
        episode_type_json: Any,
        visibility_policy: Any | None = None,
    ):
        self.client = client
        self.ledger = ledger
        self.build_manifest = dict(build_manifest)
        self.episode_type_json = episode_type_json
        self.visibility_policy = visibility_policy

    @classmethod
    def from_environment(
        cls,
        *,
        ledger_root: Path,
        build_manifest: dict[str, Any],
        visibility_policy: Any | None = None,
    ) -> "GraphitiProjectionAdapter":
        from graphiti_core import Graphiti
        from graphiti_core.nodes import EpisodeType

        uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        user = os.environ.get("NEO4J_USER", "neo4j")
        password = os.environ["NEO4J_PASSWORD"]
        client = Graphiti(uri, user, password)
        return cls(
            client=client,
            ledger=ProjectionLedger(ledger_root, cls.name),
            build_manifest=build_manifest,
            episode_type_json=EpisodeType.json,
            visibility_policy=visibility_policy,
        )

    @staticmethod
    def namespace_for_pack(pack_id: str) -> str:
        """Stable logical pack ID is the first projection namespace."""
        return pack_id

    async def initialize_async(self) -> None:
        await self.client.build_indices_and_constraints()

    async def close_async(self) -> None:
        await self.client.close()

    def _event_visible(self, event: dict[str, Any]) -> bool:
        if self.visibility_policy is None:
            return True
        return bool(self.visibility_policy.event_visible(event))

    async def apply_event_async(self, event: dict[str, Any]) -> ProjectionReceipt:
        event_id = event["event_id"]
        group_id = self.namespace_for_pack(event["pack_id"])

        if self.ledger.is_redacted(event_id):
            return ProjectionReceipt(
                self.name,
                self.version,
                event_id,
                "skipped",
                "projection redacted",
            )

        if not self._event_visible(event):
            if self.ledger.is_applied(event_id):
                return await self.remove_event_async(
                    event_id,
                    reason="source/evidence redaction visibility policy",
                )
            self.ledger.record_redaction(
                event_id,
                {
                    "projection": self.name,
                    "projection_version": self.version,
                    "group_id": group_id,
                    "reason": "source/evidence redaction visibility policy",
                    "episode_uuid": None,
                    "build_manifest": self.build_manifest,
                },
            )
            return ProjectionReceipt(
                self.name,
                self.version,
                event_id,
                "redacted",
                "event excluded by redaction visibility policy",
            )

        if self.ledger.is_applied(event_id):
            return ProjectionReceipt(
                self.name,
                self.version,
                event_id,
                "skipped",
                "already applied",
            )

        try:
            reference_time = datetime.fromisoformat(
                event["occurred_at"].replace("Z", "+00:00")
            )
            result = await self.client.add_episode(
                name=f"dkg-event:{event_id}",
                episode_body=json.dumps(event, sort_keys=True, ensure_ascii=False),
                source=self.episode_type_json,
                source_description="DKG durable knowledge event",
                reference_time=reference_time,
                group_id=group_id,
            )
            episode = getattr(result, "episode", None)
            episode_uuid = getattr(episode, "uuid", None)
        except Exception as exc:
            self.ledger.record_failure(
                event_id,
                {
                    "projection": self.name,
                    "projection_version": self.version,
                    "group_id": group_id,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "build_manifest": self.build_manifest,
                },
            )
            return ProjectionReceipt(
                self.name,
                self.version,
                event_id,
                "failed",
                str(exc),
            )

        applied_record = {
            "projection": self.name,
            "projection_version": self.version,
            "group_id": group_id,
            "episode_name": f"dkg-event:{event_id}",
            "build_manifest": self.build_manifest,
        }
        if episode_uuid is not None:
            applied_record["episode_uuid"] = str(episode_uuid)
        self.ledger.record_applied(event_id, applied_record)
        return ProjectionReceipt(self.name, self.version, event_id, "applied")

    async def remove_event_async(
        self,
        event_id: str,
        *,
        reason: str = "redaction",
    ) -> ProjectionReceipt:
        """Purge an already-materialized Graphiti episode for exceptional redaction.

        Applied history remains immutable in the projection ledger. A separate
        redaction receipt records the active purge. Older applied records that do
        not contain a Graphiti episode UUID cannot be safely deleted in place and
        therefore require a redaction-aware rebuild instead of guessing by name.
        """

        if self.ledger.is_redacted(event_id):
            return ProjectionReceipt(
                self.name,
                self.version,
                event_id,
                "skipped",
                "projection already redacted",
            )

        applied = self.ledger.get_applied(event_id)
        if applied is None:
            self.ledger.record_redaction(
                event_id,
                {
                    "projection": self.name,
                    "projection_version": self.version,
                    "reason": reason,
                    "episode_uuid": None,
                    "build_manifest": self.build_manifest,
                },
            )
            return ProjectionReceipt(
                self.name,
                self.version,
                event_id,
                "redacted",
                "event was not materialized in this projection build",
            )

        episode_uuid = applied.get("episode_uuid")
        if not episode_uuid:
            detail = "episode UUID unavailable in applied record; redaction-aware rebuild required"
            self.ledger.record_failure(
                event_id,
                {
                    "projection": self.name,
                    "projection_version": self.version,
                    "group_id": applied.get("group_id"),
                    "error_type": "RedactionRebuildRequired",
                    "error": detail,
                    "build_manifest": self.build_manifest,
                },
            )
            return ProjectionReceipt(
                self.name,
                self.version,
                event_id,
                "failed",
                detail,
            )

        try:
            await self.client.remove_episode(str(episode_uuid))
        except Exception as exc:
            self.ledger.record_failure(
                event_id,
                {
                    "projection": self.name,
                    "projection_version": self.version,
                    "group_id": applied.get("group_id"),
                    "episode_uuid": str(episode_uuid),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "build_manifest": self.build_manifest,
                },
            )
            return ProjectionReceipt(
                self.name,
                self.version,
                event_id,
                "failed",
                str(exc),
            )

        self.ledger.record_redaction(
            event_id,
            {
                "projection": self.name,
                "projection_version": self.version,
                "group_id": applied.get("group_id"),
                "episode_uuid": str(episode_uuid),
                "reason": reason,
                "build_manifest": self.build_manifest,
            },
        )
        return ProjectionReceipt(
            self.name,
            self.version,
            event_id,
            "redacted",
            "Graphiti episode removed",
        )

    async def purge_redacted_async(self, *, events_root: Path) -> list[ProjectionReceipt]:
        """Remove already-applied events that are now hidden by source redaction policy."""

        if self.visibility_policy is None:
            return []
        events = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in Path(events_root).glob("*/*.json")
        ]
        receipts: list[ProjectionReceipt] = []
        for event in ordered_events(events):
            event_id = event["event_id"]
            if (
                not self._event_visible(event)
                and self.ledger.is_applied(event_id)
                and not self.ledger.is_redacted(event_id)
            ):
                receipts.append(
                    await self.remove_event_async(
                        event_id,
                        reason="source/evidence redaction visibility policy",
                    )
                )
        return receipts

    async def purge_event_redactions_async(self, *, event_store: Any) -> list[ProjectionReceipt]:
        """Recoverably purge active episodes whose durable event bytes were erased.

        Event redaction removes the canonical event file after publishing a minimal
        tombstone. This scan uses only those tombstones plus the build-scoped applied
        ledger, so cleanup remains possible after a crash between canonical erasure
        and projection purge. Fresh rebuilds cannot resurrect these events because
        their canonical event files no longer exist.
        """

        receipts: list[ProjectionReceipt] = []
        for tombstone in event_store.iter_redactions():
            event_id = str(tombstone["event_id"])
            if self.ledger.is_redacted(event_id):
                continue
            receipts.append(
                await self.remove_event_async(
                    event_id,
                    reason="durable event redaction tombstone",
                )
            )
        return receipts

    async def rebuild_async(self, *, events_root: Path) -> list[ProjectionReceipt]:
        """Replay durable events sequentially in corpus commit order.

        Graphiti recommends sequential episode ingestion. Filesystem hash paths are
        not temporal order, so rebuild uses ``recorded_at`` with ``event_id`` as a
        stable tie breaker. A configured visibility policy prevents redacted source
        material from being re-materialized during rebuild. Event-redacted records
        are absent from the canonical event source and therefore cannot resurrect.
        """

        events = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in Path(events_root).glob("*/*.json")
        ]
        receipts: list[ProjectionReceipt] = []
        for event in ordered_events(events):
            receipts.append(await self.apply_event_async(event))
        return receipts

    def apply_event(self, event: dict[str, Any]) -> ProjectionReceipt:
        return self._run(self.apply_event_async(event))

    def remove_event(self, event_id: str, *, reason: str = "redaction") -> ProjectionReceipt:
        return self._run(self.remove_event_async(event_id, reason=reason))

    def purge_redacted(self, *, events_root: Path) -> list[ProjectionReceipt]:
        return self._run(self.purge_redacted_async(events_root=events_root))

    def purge_event_redactions(self, *, event_store: Any) -> list[ProjectionReceipt]:
        return self._run(self.purge_event_redactions_async(event_store=event_store))

    def rebuild(self, *, events_root: Path) -> list[ProjectionReceipt]:
        return self._run(self.rebuild_async(events_root=events_root))

    def health(self) -> dict[str, Any]:
        return {
            "projection": self.name,
            "version": self.version,
            "status": "configured",
            "build_manifest": self.build_manifest,
            "redaction_policy": self.visibility_policy is not None,
        }

    @staticmethod
    def _run(awaitable):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(awaitable)
        raise RuntimeError(
            "sync projection API called inside an event loop; use the async method"
        )
