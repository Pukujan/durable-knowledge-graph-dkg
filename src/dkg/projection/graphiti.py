from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from dkg.contracts import ProjectionReceipt
from dkg.projection.ledger import ProjectionLedger
from dkg.projection.migration import ordered_events


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
    ):
        self.client = client
        self.ledger = ledger
        self.build_manifest = dict(build_manifest)
        self.episode_type_json = episode_type_json

    @classmethod
    def from_environment(
        cls,
        *,
        ledger_root: Path,
        build_manifest: dict[str, Any],
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
        )

    @staticmethod
    def namespace_for_pack(pack_id: str) -> str:
        """Stable logical pack ID is the first projection namespace."""
        return pack_id

    async def initialize_async(self) -> None:
        await self.client.build_indices_and_constraints()

    async def close_async(self) -> None:
        await self.client.close()

    async def apply_event_async(self, event: dict[str, Any]) -> ProjectionReceipt:
        event_id = event["event_id"]
        group_id = self.namespace_for_pack(event["pack_id"])
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
            await self.client.add_episode(
                name=f"dkg-event:{event_id}",
                episode_body=json.dumps(event, sort_keys=True, ensure_ascii=False),
                source=self.episode_type_json,
                source_description="DKG durable knowledge event",
                reference_time=reference_time,
                group_id=group_id,
            )
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

        self.ledger.record_applied(
            event_id,
            {
                "projection": self.name,
                "projection_version": self.version,
                "group_id": group_id,
                "episode_name": f"dkg-event:{event_id}",
                "build_manifest": self.build_manifest,
            },
        )
        return ProjectionReceipt(self.name, self.version, event_id, "applied")

    async def rebuild_async(self, *, events_root: Path) -> list[ProjectionReceipt]:
        """Replay durable events sequentially in corpus commit order.

        Graphiti recommends sequential episode ingestion. Filesystem hash paths are
        not temporal order, so rebuild uses ``recorded_at`` with ``event_id`` as a
        stable tie breaker.
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

    def rebuild(self, *, events_root: Path) -> list[ProjectionReceipt]:
        return self._run(self.rebuild_async(events_root=events_root))

    def health(self) -> dict[str, Any]:
        return {
            "projection": self.name,
            "version": self.version,
            "status": "configured",
            "build_manifest": self.build_manifest,
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
