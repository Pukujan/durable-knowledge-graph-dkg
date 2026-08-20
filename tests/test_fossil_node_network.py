from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path
from types import SimpleNamespace

from mcp import Client
from mcp.server.transport_security import TransportSecuritySettings
from starlette.testclient import TestClient

from fossil_core.adapters.mcp import ThinMCPAdapter
from fossil_core.adapters.mcp.server import build_mcp_server
from fossil_core.agent import AgentContext
from fossil_core.runtime import FilesystemNodeConfig, compose_filesystem_node
from fossil_core.runtime.network import NodeReadinessProbe, create_node_network_app


COMMON = "pack_269099f7b2ba43b7a99b9427d64092de"
EXPECTED_TOOLS = (
    "fossil.search",
    "fossil.read",
    "fossil.lineage",
    "fossil.propose",
    "fossil.validate",
    "fossil.commit",
    "fossil.manage",
)


def root() -> Path:
    return Path(__file__).resolve().parents[1]


class FakeGraphiti:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def build_indices_and_constraints(self) -> None:
        return None

    async def add_episode(self, **kwargs):
        event_id = str(json.loads(kwargs["episode_body"])["event_id"])
        self.calls.append(event_id)
        return SimpleNamespace(episode=SimpleNamespace(uuid=f"episode-{event_id}"))

    async def remove_episode(self, episode_uuid: str) -> None:
        return None

    async def close(self) -> None:
        return None


class FakeLineage:
    def current_conclusions(self):
        return [{"node_id": "lin_current", "kind": "conclusion"}]

    def historical_nodes(self):
        return [{"node_id": "lin_history", "kind": "claim"}]

    def node(self, node_id: str):
        return {"node_id": node_id, "kind": "conclusion"}

    def citations(self, node_id: str):
        return [{"span_id": "span_fixture", "text": "fixture evidence"}]

    def opposing_positions(self, node_id: str):
        return []


def config(tmp_path: Path):
    return FilesystemNodeConfig(
        repository_root=root(),
        data_root=tmp_path / "node-data",
        pack_manifest_path=root() / "examples" / "packs" / "common" / "manifest.json",
        projection_build_id="node-02-test",
        projection_build_manifest={
            "graphiti_version": "0.29.3",
            "neo4j_version": "test",
            "model_id": "test-model",
            "ontology_version": "1.0.0",
            "software_commit": "test",
        },
        poll_interval_seconds=0.01,
    )


def compose(tmp_path: Path):
    return compose_filesystem_node(
        config(tmp_path),
        graphiti_client=FakeGraphiti(),
        episode_type_json="json",
    )


def agent_context() -> AgentContext:
    return AgentContext(
        actor_id="node-02-fixture",
        model_id="fixture-model-v2",
        harness_version="fixture-harness-v2",
        skill_id="skill_research-ingestion",
        skill_version="1.1.0",
    )


def read_context() -> AgentContext:
    return AgentContext(
        actor_id="node-02-reader",
        model_id="fixture-model-v2",
        harness_version="fixture-harness-v2",
        skill_id="skill_corpus-search",
        skill_version="1.0.0",
    )


def adapter(node, *, context: AgentContext | None = None) -> ThinMCPAdapter:
    return ThinMCPAdapter(
        service=node.corpus_service,
        access=node.pack_access,
        context=context or agent_context(),
    )


def _tool_error_text(result) -> str:
    return "\n".join(getattr(block, "text", "") for block in result.content)


def test_mcp_server_preserves_frozen_tools_and_corpus_semantics(tmp_path: Path):
    node = compose(tmp_path)
    node.corpus_service.lineages["conv_node_02"] = (COMMON, FakeLineage())
    write_server = build_mcp_server(adapter(node, context=agent_context()))
    read_server = build_mcp_server(adapter(node, context=read_context()))

    async def scenario() -> None:
        async with Client(write_server) as client:
            listing = await client.list_tools()
            assert tuple(tool.name for tool in listing.tools) == EXPECTED_TOOLS

            proposed = await client.call_tool(
                "fossil.propose",
                {
                    "event_type": "claim.proposed",
                    "pack_id": COMMON,
                    "subject_refs": ["clm_node_02_mcp"],
                    "payload": {"claim_text": "NODE-02 MCP routes through CorpusService."},
                    "occurred_at": "2026-08-20T04:05:00Z",
                    "recorded_at": "2026-08-20T04:05:00Z",
                    "idempotency_key": "node-02-mcp-propose-v1",
                },
            )
            assert proposed.is_error is False
            event = proposed.structured_content
            assert event is not None
            assert event["actor"] == agent_context().durable_actor()

            validated = await client.call_tool("fossil.validate", {"event": event})
            assert validated.is_error is False
            assert validated.structured_content == event

            committed = await client.call_tool("fossil.commit", {"event": event})
            assert committed.is_error is False
            committed_event = committed.structured_content
            assert committed_event is not None

        async with Client(read_server) as client:
            listing = await client.list_tools()
            assert tuple(tool.name for tool in listing.tools) == EXPECTED_TOOLS

            searched = await client.call_tool(
                "fossil.search", {"query": "NODE-02 MCP", "limit": 10}
            )
            assert searched.is_error is False
            assert any(
                item["event_id"] == committed_event["event_id"]
                for item in searched.structured_content["result"]
            )

            read = await client.call_tool(
                "fossil.read", {"event_id": committed_event["event_id"]}
            )
            assert read.is_error is False
            assert read.structured_content["event_id"] == committed_event["event_id"]

            lineage = await client.call_tool(
                "fossil.lineage", {"conversation_id": "conv_node_02"}
            )
            assert lineage.is_error is False
            assert lineage.structured_content["conversation_id"] == "conv_node_02"

    asyncio.run(scenario())


def test_mcp_server_fails_closed_on_pack_scope_and_graph_escape(tmp_path: Path):
    server = build_mcp_server(adapter(compose(tmp_path)))

    async def scenario() -> None:
        async with Client(server) as client:
            denied = await client.call_tool(
                "fossil.propose",
                {
                    "event_type": "claim.proposed",
                    "pack_id": "pack_forbidden_node_02",
                    "subject_refs": ["clm_forbidden"],
                    "payload": {"claim_text": "must not cross pack boundary"},
                    "occurred_at": "2026-08-20T04:06:00Z",
                    "recorded_at": "2026-08-20T04:06:00Z",
                    "idempotency_key": "node-02-forbidden-v1",
                },
            )
            assert denied.is_error is True
            assert "unauthorized_pack" in _tool_error_text(denied)

            graph_escape = await client.call_tool(
                "neo4j.cypher", {"query": "MATCH (n) DETACH DELETE n"}
            )
            assert graph_escape.is_error is True
            assert "Unknown tool" in _tool_error_text(graph_escape)

    asyncio.run(scenario())


def test_streamable_http_transport_and_health_readiness_are_independent(tmp_path: Path):
    node = compose(tmp_path)

    async def projection_down() -> None:
        raise RuntimeError("neo4j unavailable")

    app = create_node_network_app(
        node,
        context=agent_context(),
        readiness_probe=NodeReadinessProbe(node, projection_check=projection_down),
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        ),
    )

    with TestClient(app, base_url="http://localhost") as client:
        health = client.get("/healthz")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        ready = client.get("/readyz")
        assert ready.status_code == 503
        assert ready.json()["status"] == "not_ready"
        assert ready.json()["durable_truth"] == "available"
        assert ready.json()["canonical"]["status"] == "available"
        assert ready.json()["projection"]["status"] == "unavailable"
        assert ready.json()["projection"]["reason"] == "projection_unavailable"

        envelope = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {
                "_meta": {
                    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                    "io.modelcontextprotocol/clientInfo": {
                        "name": "fossil-node-02-test",
                        "version": "1",
                    },
                    "io.modelcontextprotocol/clientCapabilities": {},
                }
            },
        }
        response = client.post(
            "/mcp",
            headers={
                "content-type": "application/json",
                "accept": "application/json, text/event-stream",
                "mcp-protocol-version": "2026-07-28",
                "mcp-method": "tools/list",
            },
            json=envelope,
        )
        assert response.status_code == 200
        tool_names = [tool["name"] for tool in response.json()["result"]["tools"]]
        assert tuple(tool_names) == EXPECTED_TOOLS


def test_reviewed_http_ingest_is_durable_before_projection(tmp_path: Path):
    node = compose(tmp_path)
    app = create_node_network_app(
        node,
        context=agent_context(),
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        ),
    )
    evidence = b"Reviewed evidence says canonical events survive projection outages.\n"
    payload = {
        "pack_id": COMMON,
        "source": {
            "data_b64": base64.b64encode(evidence).decode("ascii"),
            "source_kind": "research",
            "source_role": "primary",
            "locator": {"identifier": "node-02-reviewed-http-fixture"},
            "retrieved_at": "2026-08-20T04:07:00Z",
            "published_at": "2026-08-20T04:06:00Z",
            "media_type": "text/plain",
            "quality": {
                "authority": 0.8,
                "directness": 1.0,
                "independence": 0.7,
                "reproducibility": 0.9,
                "timeliness": 1.0,
                "notes": "reviewed NODE-02 fixture",
            },
        },
        "claims": [
            {
                "subject_ref": "clm_node_02_reviewed_ingest",
                "claim_text": "Canonical events survive projection outages.",
                "reason": "reviewed NODE-02 transport fixture",
            }
        ],
        "review_ref": "review:node-02:http-ingest",
        "occurred_at": "2026-08-20T04:07:01Z",
        "recorded_at": "2026-08-20T04:07:02Z",
        "correlation_id": "node-02-reviewed-http-v1",
    }

    with TestClient(app, base_url="http://localhost") as client:
        response = client.post("/ingest", json=payload)
        assert response.status_code == 201
        receipt = response.json()

    assert receipt["status"] == "proposed"
    assert receipt["pack_id"] == COMMON
    assert receipt["source"]["preserved"] is True
    assert node.artifact_store.read_bytes(receipt["source"]["artifact_id"]) == evidence
    event_id = receipt["proposal_event_ids"][0]
    event = node.event_store.get(event_id)
    assert event["evidence_refs"] == [receipt["source"]["artifact_id"]]
    assert event["source_snapshot_refs"] == [receipt["source"]["snapshot_id"]]
    assert event["actor"] == agent_context().durable_actor()
    assert node.projection.ledger.is_applied(event_id) is False

    cycle = asyncio.run(node.projector.run_once_async())
    assert cycle.applied == 1
    assert node.projection.ledger.is_applied(event_id) is True


def test_reviewed_http_ingest_rejects_pack_spoofing_and_invalid_payload(tmp_path: Path):
    node = compose(tmp_path)
    app = create_node_network_app(
        node,
        context=agent_context(),
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        ),
    )

    with TestClient(app, base_url="http://localhost") as client:
        denied = client.post(
            "/ingest",
            json={
                "pack_id": "pack_forbidden_node_02",
                "source": {},
                "claims": [],
                "review_ref": "review:denied",
                "occurred_at": "2026-08-20T04:08:00Z",
                "recorded_at": "2026-08-20T04:08:00Z",
                "correlation_id": "node-02-denied",
            },
        )
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "unauthorized_pack"

        invalid = client.post("/ingest", content=b"not-json")
        assert invalid.status_code == 400
        assert invalid.json()["error"]["code"] == "invalid_json"

    assert list(node.event_store.iter_events()) == []
