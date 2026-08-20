from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from starlette.testclient import TestClient

from fossil_core.agent import AgentContext
from fossil_core.runtime import FilesystemNodeConfig, compose_filesystem_node
from fossil_core.runtime.chatgpt_action import (
    chatgpt_action_openapi_schema,
    create_chatgpt_action_app,
)


COMMON = "pack_269099f7b2ba43b7a99b9427d64092de"
TOKEN = "test-chatgpt-action-token"


def root() -> Path:
    return Path(__file__).resolve().parents[1]


class FakeGraphiti:
    async def build_indices_and_constraints(self) -> None:
        return None

    async def add_episode(self, **kwargs):
        event_id = str(json.loads(kwargs["episode_body"])["event_id"])
        return SimpleNamespace(episode=SimpleNamespace(uuid=f"episode-{event_id}"))

    async def remove_episode(self, episode_uuid: str) -> None:
        return None

    async def close(self) -> None:
        return None


class FakeLineage:
    def current_conclusions(self):
        return [{"node_id": "lin_action_current", "kind": "conclusion"}]

    def historical_nodes(self):
        return [{"node_id": "lin_action_history", "kind": "claim"}]

    def node(self, node_id: str):
        return {"node_id": node_id, "kind": "conclusion"}

    def citations(self, node_id: str):
        return [{"span_id": "span_action", "text": "fixture evidence"}]

    def opposing_positions(self, node_id: str):
        return []


def config(tmp_path: Path) -> FilesystemNodeConfig:
    return FilesystemNodeConfig(
        repository_root=root(),
        data_root=tmp_path / "node-data",
        pack_manifest_path=root() / "examples" / "packs" / "common" / "manifest.json",
        projection_build_id="chatgpt-action-test",
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


def writer_context() -> AgentContext:
    return AgentContext(
        actor_id="chatgpt-action-writer-fixture",
        model_id="fixture-model-v2",
        harness_version="fixture-harness-v2",
        skill_id="skill_research-ingestion",
        skill_version="1.1.0",
    )


def read_context() -> AgentContext:
    return AgentContext(
        actor_id="chatgpt-action-reader-fixture",
        model_id="fixture-model-v2",
        harness_version="fixture-harness-v2",
        skill_id="skill_corpus-search",
        skill_version="1.0.0",
    )


def auth_headers() -> dict[str, str]:
    return {"authorization": f"Bearer {TOKEN}"}


def commit_fixture_event(node) -> dict:
    context = writer_context()
    event = node.corpus_service.propose(
        event_type="claim.proposed",
        pack_id=COMMON,
        subject_refs=["clm_chatgpt_action"],
        payload={"claim_text": "ChatGPT Action requests reuse the canonical corpus boundary."},
        occurred_at="2026-08-20T13:00:00Z",
        recorded_at="2026-08-20T13:00:00Z",
        idempotency_key="chatgpt-action-fixture-v1",
        access=node.pack_access,
        context=context,
    )
    validated = node.corpus_service.validate(
        event,
        access=node.pack_access,
        context=context,
    )
    return node.corpus_service.commit(
        validated,
        access=node.pack_access,
        context=context,
    )


def test_openapi_is_read_only_and_declares_bearer_auth():
    schema = chatgpt_action_openapi_schema(server_url="https://fossil.example.test/")

    assert schema["openapi"] == "3.1.0"
    assert schema["servers"] == [{"url": "https://fossil.example.test"}]
    assert schema["security"] == [{"BearerAuth": []}]
    assert schema["components"]["securitySchemes"]["BearerAuth"]["scheme"] == "bearer"
    assert set(schema["paths"]) == {
        "/actions/search",
        "/actions/read",
        "/actions/lineage",
        "/actions/capabilities",
    }
    serialized = json.dumps(schema)
    for forbidden in (
        "fossil.propose",
        "fossil.validate",
        "fossil.commit",
        "/ingest",
        "/mcp",
        "neo4j",
    ):
        assert forbidden not in serialized.lower()


def test_action_app_authenticates_and_does_not_publish_private_node_routes(tmp_path: Path):
    app = create_chatgpt_action_app(
        compose(tmp_path),
        context=read_context(),
        bearer_token=TOKEN,
    )

    with TestClient(app, base_url="https://fossil.example.test") as client:
        schema = client.get("/openapi.json")
        assert schema.status_code == 200
        assert schema.json()["servers"] == [{"url": "https://fossil.example.test"}]

        denied = client.get("/actions/capabilities")
        assert denied.status_code == 401
        assert denied.headers["www-authenticate"] == "Bearer"
        assert denied.json()["error"]["code"] == "unauthorized"

        wrong = client.get(
            "/actions/capabilities",
            headers={"authorization": "Bearer wrong-token"},
        )
        assert wrong.status_code == 401

        allowed = client.get("/actions/capabilities", headers=auth_headers())
        assert allowed.status_code == 200
        assert allowed.json()["action_capabilities"] == ["search", "read", "lineage"]
        assert allowed.json()["durable_writes_exposed"] is False
        assert allowed.json()["ingestion_exposed"] is False
        assert allowed.json()["mcp_exposed"] is False
        assert allowed.json()["arbitrary_graph_mutation"] is False

        assert client.get("/mcp", headers=auth_headers()).status_code == 404
        assert client.post("/ingest", headers=auth_headers(), json={}).status_code == 404
        assert client.post("/actions/commit", headers=auth_headers(), json={}).status_code == 404


def test_action_search_read_and_lineage_delegate_to_canonical_service(tmp_path: Path):
    node = compose(tmp_path)
    committed = commit_fixture_event(node)
    node.corpus_service.lineages["conv_chatgpt_action"] = (COMMON, FakeLineage())
    app = create_chatgpt_action_app(
        node,
        context=read_context(),
        bearer_token=TOKEN,
    )

    with TestClient(app, base_url="https://fossil.example.test") as client:
        searched = client.post(
            "/actions/search",
            headers=auth_headers(),
            json={
                "query": "ChatGPT Action requests",
                "limit": 10,
                "ignored_graph_escape": "MATCH (n) DETACH DELETE n",
            },
        )
        assert searched.status_code == 200
        assert any(item["event_id"] == committed["event_id"] for item in searched.json())

        read = client.post(
            "/actions/read",
            headers=auth_headers(),
            json={"event_id": committed["event_id"]},
        )
        assert read.status_code == 200
        assert read.json()["event_id"] == committed["event_id"]
        assert read.json()["pack_id"] == COMMON

        lineage = client.post(
            "/actions/lineage",
            headers=auth_headers(),
            json={
                "conversation_id": "conv_chatgpt_action",
                "node_id": "lin_action_current",
            },
        )
        assert lineage.status_code == 200
        assert lineage.json()["conversation_id"] == "conv_chatgpt_action"
        assert lineage.json()["node"]["node_id"] == "lin_action_current"

        missing = client.post(
            "/actions/read",
            headers=auth_headers(),
            json={"event_id": "evt_missing_chatgpt_action"},
        )
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "not_found"


def test_action_request_validation_fails_closed(tmp_path: Path):
    app = create_chatgpt_action_app(
        compose(tmp_path),
        context=read_context(),
        bearer_token=TOKEN,
        max_request_body_size=64,
    )

    with TestClient(app, base_url="https://fossil.example.test") as client:
        invalid = client.post(
            "/actions/search",
            headers=auth_headers(),
            content=b"not-json",
        )
        assert invalid.status_code == 400
        assert invalid.json()["error"]["code"] == "invalid_json"

        empty = client.post(
            "/actions/search",
            headers=auth_headers(),
            json={"query": ""},
        )
        assert empty.status_code == 400
        assert empty.json()["error"]["code"] == "invalid_request"

        too_large = client.post(
            "/actions/search",
            headers=auth_headers(),
            content=json.dumps({"query": "x" * 100}).encode("utf-8"),
        )
        assert too_large.status_code == 413
        assert too_large.json()["error"]["code"] == "request_too_large"
