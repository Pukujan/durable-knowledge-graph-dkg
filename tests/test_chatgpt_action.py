from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from openapi_spec_validator import validate_spec
from starlette.testclient import TestClient

from fossil_core.agent import AgentContext
from fossil_core.runtime import FilesystemNodeConfig, compose_filesystem_node
from fossil_core.runtime.chatgpt_action import (
    chatgpt_action_openapi_schema,
    create_chatgpt_action_app,
)


COMMON = "pack_269099f7b2ba43b7a99b9427d64092de"
TOKEN = "test-chatgpt-action-token"
ACTION_PATHS = {
    "/actions/search",
    "/actions/read",
    "/actions/lineage",
    "/actions/capabilities",
}


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
        return [{"node_id": "ln_action_current", "kind": "conclusion"}]

    def historical_nodes(self):
        return [{"node_id": "ln_action_history", "kind": "claim"}]

    def node(self, node_id: str):
        return {"node_id": node_id, "kind": "conclusion"}

    def citations(self, node_id: str):
        return [
            {
                "span_id": "span_action",
                "artifact_id": "art_action",
                "evidence_status": "verbatim",
                "byte_start": 0,
                "byte_end": 16,
                "text": "fixture evidence",
            }
        ]

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


def action_app(tmp_path: Path, **kwargs):
    return create_chatgpt_action_app(
        compose(tmp_path),
        context=read_context(),
        bearer_token=TOKEN,
        **kwargs,
    )


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
    validated = node.corpus_service.validate(event, access=node.pack_access, context=context)
    return node.corpus_service.commit(validated, access=node.pack_access, context=context)


def test_openapi_is_valid_explicit_and_read_only():
    schema = chatgpt_action_openapi_schema(server_url="https://fossil.example.test/")
    validate_spec(schema)

    assert schema["openapi"].startswith("3.1.")
    assert schema["servers"] == [{"url": "https://fossil.example.test"}]
    assert schema["security"] == [{"BearerAuth": []}]
    assert schema["components"]["securitySchemes"]["BearerAuth"]["scheme"] == "bearer"
    assert set(schema["paths"]) == ACTION_PATHS

    component_schemas = schema["components"]["schemas"]
    assert isinstance(component_schemas, dict) and component_schemas
    for name in (
        "ErrorEnvelope",
        "SearchRequest",
        "ReadRequest",
        "LineageRequest",
        "SearchResult",
        "FossilEvent",
        "LineageNode",
        "Citation",
        "LineageResponse",
        "CapabilitiesResponse",
    ):
        assert name in component_schemas
        assert component_schemas[name]["type"] == "object"
        assert component_schemas[name].get("properties")

    operation_ids = {
        operation["operationId"]
        for path in schema["paths"].values()
        for operation in path.values()
    }
    assert operation_ids == {
        "fossilSearch",
        "fossilRead",
        "fossilLineage",
        "fossilActionCapabilities",
    }

    serialized = json.dumps(schema).lower()
    for forbidden in (
        "fossil.propose",
        "fossil.validate",
        "fossil.commit",
        '"/ingest"',
        '"/mcp"',
        '"/actions/propose"',
        '"/actions/commit"',
        "neo4j",
        "graph mutation",
        "bearer_token",
    ):
        assert forbidden not in serialized


def test_openapi_success_response_objects_resolve_to_declared_properties():
    schema = chatgpt_action_openapi_schema(server_url="https://fossil.example.test")
    components = schema["components"]["schemas"]

    for path_item in schema["paths"].values():
        operation = next(iter(path_item.values()))
        response_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
        if response_schema.get("type") == "array":
            response_schema = response_schema["items"]
        assert "$ref" in response_schema
        name = response_schema["$ref"].rsplit("/", 1)[-1]
        assert components[name].get("properties")


def test_action_app_authenticates_and_exposes_only_allowlisted_routes(tmp_path: Path):
    app = action_app(tmp_path)

    with TestClient(app, base_url="https://fossil.example.test") as client:
        schema = client.get("/openapi.json")
        assert schema.status_code == 200
        assert schema.json()["servers"] == [{"url": "https://fossil.example.test"}]

        denied = client.get("/actions/capabilities")
        assert denied.status_code == 401
        assert denied.headers["www-authenticate"] == "Bearer"

        wrong = client.get(
            "/actions/capabilities", headers={"authorization": "Bearer wrong-token"}
        )
        assert wrong.status_code == 401

        allowed = client.get("/actions/capabilities", headers=auth_headers())
        assert allowed.status_code == 200
        assert allowed.json() == {
            "service_version": "1",
            "action_capabilities": ["search", "read", "lineage"],
            "durable_writes_exposed": False,
            "ingestion_exposed": False,
            "mcp_exposed": False,
            "arbitrary_graph_mutation": False,
        }

        for path in (
            "/mcp",
            "/ingest",
            "/actions/propose",
            "/actions/validate",
            "/actions/commit",
            "/actions/redact",
            "/actions/write",
            "/actions/admin",
            "/neo4j",
            "/graph",
            "/filesystem",
            "/etc/passwd",
            "/unknown",
        ):
            response = client.post(path, headers=auth_headers(), json={})
            assert response.status_code == 404, path
            assert response.json()["error"]["code"] == "not_found"


def test_auth_header_is_unambiguous_and_token_exact(tmp_path: Path):
    app = action_app(tmp_path)
    cases = (
        None,
        "",
        TOKEN,
        f"Basic {TOKEN}",
        "Bearer",
        "Bearer ",
        f"Bearer {TOKEN} ",
        f"Bearer {TOKEN}\textra",
        f"Bearer {TOKEN} extra",
        "Bearer wrong",
    )
    with TestClient(app, base_url="https://fossil.example.test") as client:
        for value in cases:
            headers = {} if value is None else {"authorization": value}
            response = client.get("/actions/capabilities", headers=headers)
            assert response.status_code == 401, value

        lower_scheme = client.get(
            "/actions/capabilities",
            headers={"authorization": f"bearer {TOKEN}"},
        )
        assert lower_scheme.status_code == 200

        duplicated = client.get(
            "/actions/capabilities",
            headers=[
                ("authorization", f"Bearer {TOKEN}"),
                ("authorization", f"Bearer {TOKEN}"),
            ],
        )
        assert duplicated.status_code == 401


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
            json={"query": "ChatGPT Action requests", "limit": 10},
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
            json={"conversation_id": "conv_chatgpt_action", "node_id": "ln_action_current"},
        )
        assert lineage.status_code == 200
        assert lineage.json()["conversation_id"] == "conv_chatgpt_action"
        assert lineage.json()["node"]["node_id"] == "ln_action_current"

        missing = client.post(
            "/actions/read",
            headers=auth_headers(),
            json={"event_id": "evt_aaaaaaaaaaaaaaaa"},
        )
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "not_found"


def test_request_validation_rejects_mutation_smuggling_and_traversal(tmp_path: Path):
    app = action_app(tmp_path)
    with TestClient(app, base_url="https://fossil.example.test") as client:
        extra = client.post(
            "/actions/search",
            headers=auth_headers(),
            json={
                "query": "FOSSIL",
                "graph_query": "MATCH (n) DETACH DELETE n",
            },
        )
        assert extra.status_code == 400

        traversal = client.post(
            "/actions/read",
            headers=auth_headers(),
            json={"event_id": "../../etc/passwd"},
        )
        assert traversal.status_code == 400

        lineage_traversal = client.post(
            "/actions/lineage",
            headers=auth_headers(),
            json={"conversation_id": "../secret"},
        )
        assert lineage_traversal.status_code == 400

        for bad_limit in (True, "10", 0, -1, 101):
            response = client.post(
                "/actions/search",
                headers=auth_headers(),
                json={"query": "FOSSIL", "limit": bad_limit},
            )
            assert response.status_code == 400

        too_long = client.post(
            "/actions/search",
            headers=auth_headers(),
            json={"query": "x" * 8193},
        )
        assert too_long.status_code == 400


def test_request_size_json_and_method_validation_fail_closed(tmp_path: Path):
    app = action_app(tmp_path, max_request_body_size=64)

    with TestClient(app, base_url="https://fossil.example.test") as client:
        invalid = client.post(
            "/actions/search", headers=auth_headers(), content=b"not-json"
        )
        assert invalid.status_code == 400
        assert invalid.json()["error"]["code"] == "invalid_json"

        non_object = client.post(
            "/actions/search", headers=auth_headers(), json=["not", "object"]
        )
        assert non_object.status_code == 400

        too_large = client.post(
            "/actions/search",
            headers=auth_headers(),
            content=json.dumps({"query": "x" * 100}).encode("utf-8"),
        )
        assert too_large.status_code == 413

        assert client.post("/openapi.json", json={}).status_code == 405
        assert client.get("/actions/search", headers=auth_headers()).status_code == 405
        assert client.post(
            "/actions/capabilities", headers=auth_headers(), json={}
        ).status_code == 405


def test_errors_do_not_echo_internal_paths_or_secret(tmp_path: Path):
    app = action_app(tmp_path)
    with TestClient(app, base_url="https://fossil.example.test") as client:
        response = client.post(
            "/actions/read",
            headers=auth_headers(),
            json={"event_id": "evt_aaaaaaaaaaaaaaaa"},
        )
        body = response.text
        assert TOKEN not in body
        assert str(tmp_path) not in body
        assert "/var/lib/fossil" not in body


@pytest.mark.parametrize(
    "forbidden_fragment",
    ["secret", "token", "credential", "password"],
)
def test_openapi_contains_no_runtime_secret_values(forbidden_fragment: str):
    schema = json.dumps(
        chatgpt_action_openapi_schema(server_url="https://fossil.example.test")
    ).lower()
    assert TOKEN.lower() not in schema
    assert f"replace-with-a-{forbidden_fragment}" not in schema
