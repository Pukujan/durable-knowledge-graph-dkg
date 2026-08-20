from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from fossil_core.agent import AgentContext
from fossil_core.runtime import FilesystemNodeConfig, compose_filesystem_node


COMMON = "pack_269099f7b2ba43b7a99b9427d64092de"


def root() -> Path:
    return Path(__file__).resolve().parents[1]


class FakeGraphiti:
    def __init__(self) -> None:
        self.attempts: list[str] = []
        self.calls: list[str] = []
        self.fail_on: set[str] = set()
        self.initialized = 0
        self.closed = 0

    async def build_indices_and_constraints(self) -> None:
        self.initialized += 1

    async def add_episode(self, **kwargs):
        event_id = str(json.loads(kwargs["episode_body"])["event_id"])
        self.attempts.append(event_id)
        if event_id in self.fail_on:
            raise RuntimeError("temporary graph failure")
        self.calls.append(event_id)
        return SimpleNamespace(
            episode=SimpleNamespace(uuid=f"episode-{event_id}")
        )

    async def remove_episode(self, episode_uuid: str) -> None:
        return None

    async def close(self) -> None:
        self.closed += 1


def config(tmp_path: Path, *, build_id: str = "build-a", poll: float = 0.01):
    return FilesystemNodeConfig(
        repository_root=root(),
        data_root=tmp_path / "node-data",
        pack_manifest_path=root() / "examples" / "packs" / "common" / "manifest.json",
        projection_build_id=build_id,
        projection_build_manifest={
            "graphiti_version": "0.29.3",
            "neo4j_version": "test",
            "model_id": "test-model",
            "ontology_version": "1.0.0",
            "software_commit": "test",
        },
        poll_interval_seconds=poll,
    )


def compose(tmp_path: Path, client: FakeGraphiti, *, build_id: str = "build-a", poll: float = 0.01):
    return compose_filesystem_node(
        config(tmp_path, build_id=build_id, poll=poll),
        graphiti_client=client,
        episode_type_json="json",
    )


def agent_context() -> AgentContext:
    return AgentContext(
        actor_id="runtime-fixture",
        model_id="fixture-model-v1",
        harness_version="fixture-harness-v1",
        skill_id="skill_research-ingestion",
        skill_version="1.1.0",
    )


def commit_claim(
    node,
    *,
    key: str,
    subject: str,
    occurred_at: str,
    recorded_at: str,
):
    ctx = agent_context()
    proposal = node.corpus_service.propose(
        event_type="claim.proposed",
        pack_id=COMMON,
        subject_refs=[subject],
        payload={"claim_text": f"runtime claim {key}"},
        occurred_at=occurred_at,
        recorded_at=recorded_at,
        idempotency_key=key,
        access=node.pack_access,
        context=ctx,
    )
    return node.corpus_service.commit(
        proposal,
        access=node.pack_access,
        context=ctx,
    )


def test_node_composition_uses_one_canonical_writer_and_separates_operational_state(tmp_path):
    node = compose(tmp_path, FakeGraphiti())

    assert node.pack_access.pack_id == COMMON
    assert node.corpus_service.event_store is node.event_store
    assert node.reviewed_ingest.event_store is node.event_store
    assert node.reviewed_ingest.source_store is node.source_store
    assert node.projector.event_store is node.event_store
    assert node.projector.ledger is node.projection.ledger

    assert node.paths.artifacts_root == tmp_path / "node-data" / "canonical" / "artifacts"
    assert node.paths.sources_root == tmp_path / "node-data" / "canonical" / "sources"
    assert node.paths.events_root == tmp_path / "node-data" / "canonical" / "events"
    assert node.paths.projection_ledger_root == (
        tmp_path / "node-data" / "operational" / "projection-ledger"
    )


def test_projection_failure_does_not_rollback_durable_commit_and_restart_catches_up(tmp_path):
    client = FakeGraphiti()
    first = compose(tmp_path, client)
    event = commit_claim(
        first,
        key="runtime-restart-v1",
        subject="clm_runtime_restart_fixture",
        occurred_at="2026-08-20T03:30:00Z",
        recorded_at="2026-08-20T03:30:00Z",
    )

    client.fail_on.add(event["event_id"])
    failed_cycle = asyncio.run(first.projector.run_once_async())
    assert failed_cycle.failed == 1
    assert first.event_store.get(event["event_id"]) == event
    assert not first.projection.ledger.is_applied(event["event_id"])

    client.fail_on.clear()
    restarted = compose(tmp_path, client)
    catchup_cycle = asyncio.run(restarted.projector.run_once_async())
    assert catchup_cycle.applied == 1
    assert restarted.projection.ledger.is_applied(event["event_id"])
    assert client.calls == [event["event_id"]]

    restarted_again = compose(tmp_path, client)
    idempotent_cycle = asyncio.run(restarted_again.projector.run_once_async())
    assert idempotent_cycle.skipped == 1
    assert client.calls == [event["event_id"]]


def test_projector_preserves_commit_order_and_stops_cycle_at_first_failure(tmp_path):
    client = FakeGraphiti()
    node = compose(tmp_path, client)

    later = commit_claim(
        node,
        key="runtime-order-later-v1",
        subject="clm_runtime_order_later",
        occurred_at="2026-08-20T03:32:00Z",
        recorded_at="2026-08-20T03:32:00Z",
    )
    earlier = commit_claim(
        node,
        key="runtime-order-earlier-v1",
        subject="clm_runtime_order_earlier",
        occurred_at="2026-08-20T03:31:00Z",
        recorded_at="2026-08-20T03:31:00Z",
    )

    client.fail_on.add(earlier["event_id"])
    first_cycle = asyncio.run(node.projector.run_once_async())
    assert first_cycle.failed == 1
    assert client.attempts == [earlier["event_id"]]
    assert not node.projection.ledger.is_applied(later["event_id"])

    client.fail_on.clear()
    second_cycle = asyncio.run(node.projector.run_once_async())
    assert second_cycle.applied == 2
    assert client.attempts == [
        earlier["event_id"],
        earlier["event_id"],
        later["event_id"],
    ]


def test_fresh_projection_build_id_replays_without_stale_applied_markers(tmp_path):
    first_client = FakeGraphiti()
    first = compose(tmp_path, first_client, build_id="build-a")
    event = commit_claim(
        first,
        key="runtime-rebuild-v1",
        subject="clm_runtime_rebuild_fixture",
        occurred_at="2026-08-20T03:33:00Z",
        recorded_at="2026-08-20T03:33:00Z",
    )
    assert asyncio.run(first.projector.run_once_async()).applied == 1
    assert first_client.calls == [event["event_id"]]

    rebuilt_client = FakeGraphiti()
    rebuilt = compose(tmp_path, rebuilt_client, build_id="build-b")
    rebuild_cycle = asyncio.run(rebuilt.projector.run_once_async())

    assert rebuild_cycle.applied == 1
    assert rebuilt_client.calls == [event["event_id"]]
    assert first.projection.ledger.root != rebuilt.projection.ledger.root
    assert rebuilt.projection.ledger.is_applied(event["event_id"])


def test_projector_shutdown_is_bounded_by_stop_event_not_poll_interval(tmp_path):
    node = compose(tmp_path, FakeGraphiti(), poll=60.0)

    async def scenario() -> None:
        stop = asyncio.Event()
        task = asyncio.create_task(node.projector.run_forever(stop))
        await asyncio.sleep(0)
        stop.set()
        await asyncio.wait_for(task, timeout=0.2)

    asyncio.run(scenario())
