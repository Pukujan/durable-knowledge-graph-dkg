from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from openapi_spec_validator import validate_spec
from starlette.testclient import TestClient

from fossil_core.runtime.chatgpt_action_server import (
    ChatGPTActionServerSettings,
    build_chatgpt_action_adapter,
    create_chatgpt_action_app_from_settings,
)


TOKEN = "holdout-token-0123456789abcdef-0123456789"
PUBLIC_ORIGIN = "https://fossil-action.holdout.invalid"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def make_settings(tmp_path: Path, *, max_bytes: int = 65536) -> ChatGPTActionServerSettings:
    data_root = tmp_path / "fossil-data"
    events = data_root / "canonical" / "events"
    events.mkdir(parents=True, exist_ok=True)
    return ChatGPTActionServerSettings(
        repository_root=repo_root(),
        data_root=data_root,
        pack_manifest_path=Path("examples/packs/common/manifest.json"),
        bearer_token=TOKEN,
        max_request_body_size=max_bytes,
        public_base_url=PUBLIC_ORIGIN,
    )


def auth() -> dict[str, str]:
    return {"authorization": f"Bearer {TOKEN}"}


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"authorization": ""},
        {"authorization": "Basic abc"},
        {"authorization": "Bearer"},
        {"authorization": "Bearer wrong"},
        {"authorization": f"Bearer {TOKEN} "},
        {"authorization": f"Bearer {TOKEN.upper()}"},
    ],
)
def test_holdout_malformed_auth_fails_closed(tmp_path: Path, headers: dict[str, str]) -> None:
    app = create_chatgpt_action_app_from_settings(make_settings(tmp_path))
    with TestClient(app) as client:
        response = client.post("/actions/search", headers=headers, json={"query": "x"})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_holdout_duplicate_authorization_header_fails_closed(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(make_settings(tmp_path))
    with TestClient(app) as client:
        response = client.post(
            "/actions/search",
            headers=[
                ("authorization", f"Bearer {TOKEN}"),
                ("authorization", "Bearer attacker"),
                ("content-type", "application/json"),
            ],
            content=b'{"query":"x"}',
        )
    assert response.status_code == 401


def test_holdout_forged_forwarded_headers_cannot_rewrite_schema(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(make_settings(tmp_path))
    forged = {
        "forwarded": "proto=http;host=attacker.invalid",
        "x-forwarded-proto": "http",
        "x-forwarded-host": "attacker.invalid",
        "x-forwarded-port": "80",
        "host": "internal.invalid:8787",
    }
    with TestClient(app, base_url="http://internal.invalid:8787") as client:
        schema = client.get("/openapi.json", headers=forged).json()
    assert schema["servers"] == [{"url": PUBLIC_ORIGIN}]


def test_holdout_openapi_is_valid_and_custom_gpt_bounded(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(make_settings(tmp_path))
    with TestClient(app) as client:
        response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    validate_spec(schema)
    assert schema["openapi"].startswith("3.1.")
    assert isinstance(schema["components"]["schemas"], dict)
    assert set(schema["components"]["schemas"]) >= {
        "ErrorDetail",
        "ErrorEnvelope",
        "FossilRecord",
        "LineageResponse",
        "CapabilitiesResponse",
    }
    assert set(schema["paths"]) == {
        "/actions/search",
        "/actions/read",
        "/actions/lineage",
        "/actions/capabilities",
    }
    operation_ids = [
        operation["operationId"]
        for path in schema["paths"].values()
        for operation in path.values()
    ]
    assert len(operation_ids) == len(set(operation_ids)) == 4
    assert schema["components"]["securitySchemes"]["BearerAuth"]["scheme"] == "bearer"

    props = schema["components"]["schemas"]["FossilRecord"]["properties"]
    assert {"event_id", "pack_id", "event_type", "recorded_at", "payload"} <= set(props)
    capability_props = schema["components"]["schemas"]["CapabilitiesResponse"]["properties"]
    assert capability_props["durable_writes_exposed"]["const"] is False
    assert capability_props["mcp_exposed"]["const"] is False

    serialized = json.dumps(schema).lower()
    for forbidden in (
        '"/mcp"',
        '"/ingest"',
        '"/actions/propose"',
        '"/actions/validate"',
        '"/actions/commit"',
        '"/actions/redact"',
        "neo4j",
        "graph mutation endpoint",
        TOKEN.lower(),
    ):
        assert forbidden not in serialized


def test_holdout_oversized_payloads_fail_before_service(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(make_settings(tmp_path, max_bytes=64))
    with TestClient(app) as client:
        actual = client.post(
            "/actions/search",
            headers=auth(),
            content=json.dumps({"query": "x" * 100}).encode(),
        )
        declared = client.post(
            "/actions/search",
            headers={**auth(), "content-type": "application/json", "content-length": "9999"},
            content=b'{"query":"x"}',
        )
    assert actual.status_code == 413
    assert declared.status_code == 413


def test_holdout_unknown_and_prohibited_paths_are_not_routable(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(make_settings(tmp_path))
    prohibited = [
        "/mcp",
        "/ingest",
        "/actions/propose",
        "/actions/validate",
        "/actions/commit",
        "/actions/redact",
        "/neo4j",
        "/graph",
        "/filesystem",
        "/admin",
        "/unknown",
    ]
    with TestClient(app) as client:
        for path in prohibited:
            assert client.get(path, headers=auth()).status_code == 404, path
            assert client.post(path, headers=auth(), json={}).status_code == 404, path


def test_holdout_unsupported_methods_return_405(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(make_settings(tmp_path))
    with TestClient(app) as client:
        assert client.post("/openapi.json").status_code == 405
        assert client.get("/actions/search", headers=auth()).status_code == 405
        assert client.get("/actions/read", headers=auth()).status_code == 405
        assert client.get("/actions/lineage", headers=auth()).status_code == 405
        assert client.post("/actions/capabilities", headers=auth(), json={}).status_code == 405


def test_holdout_path_traversal_event_ids_are_rejected(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(make_settings(tmp_path))
    malicious = [
        "../../../../etc/passwd",
        "evt_../../../../etc/passwd",
        "evt_................",
        "evt_abcdefghijklmnop/../../secret",
        "C:\\Windows\\System32\\drivers\\etc\\hosts",
    ]
    with TestClient(app) as client:
        for event_id in malicious:
            response = client.post(
                "/actions/read", headers=auth(), json={"event_id": event_id}
            )
            assert response.status_code == 400, event_id


def test_holdout_read_only_store_has_no_mutation_surface_and_boots_without_write(tmp_path: Path) -> None:
    configured = make_settings(tmp_path)
    events = configured.data_root / "canonical" / "events"
    os.chmod(events, 0o555)
    try:
        adapter = build_chatgpt_action_adapter(configured)
        for forbidden in ("commit", "prepare", "validate", "redact", "put", "delete"):
            assert not hasattr(adapter.service.event_store, forbidden)
        app = create_chatgpt_action_app_from_settings(configured)
        with TestClient(app) as client:
            response = client.post("/actions/search", headers=auth(), json={"query": "empty"})
        assert response.status_code == 200
        assert response.json() == []
    finally:
        os.chmod(events, 0o755)


def test_holdout_validation_rejects_ambiguous_limits_and_non_object_json(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(make_settings(tmp_path))
    with TestClient(app) as client:
        for limit in (True, False, 0, -1, 101, "5", 1.5):
            response = client.post(
                "/actions/search", headers=auth(), json={"query": "x", "limit": limit}
            )
            assert response.status_code == 400, repr(limit)
        non_object = client.post(
            "/actions/search",
            headers={**auth(), "content-type": "application/json"},
            content=b'["x"]',
        )
    assert non_object.status_code == 400


def test_holdout_secret_never_appears_in_public_or_error_responses(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(make_settings(tmp_path))
    with TestClient(app) as client:
        responses = [
            client.get("/openapi.json"),
            client.get("/actions/capabilities", headers=auth()),
            client.post("/actions/search", json={"query": "x"}),
            client.post("/actions/search", headers=auth(), content=b"not-json"),
        ]
    for response in responses:
        assert TOKEN not in response.text
