from __future__ import annotations

import json
from pathlib import Path

import pytest
from openapi_spec_validator import validate_spec
from starlette.testclient import TestClient

from fossil_core.runtime.chatgpt_action_server import (
    ChatGPTActionServerSettings,
    create_chatgpt_action_app_from_settings,
)


TOKEN = "holdout-token-0123456789abcdef-0123456789"
PUBLIC_ORIGIN = "https://fossil-action.holdout.invalid"
COMMON = "pack_269099f7b2ba43b7a99b9427d64092de"
ACTION_PATHS = {
    "/actions/search",
    "/actions/read",
    "/actions/capabilities",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def make_settings(
    tmp_path: Path,
    *,
    max_bytes: int = 65536,
    public_base_url: str | None = PUBLIC_ORIGIN,
    trusted_proxy_cidrs: tuple[str, ...] = (),
) -> ChatGPTActionServerSettings:
    data_root = tmp_path / "fossil-data"
    (data_root / "canonical" / "events").mkdir(parents=True, exist_ok=True)
    return ChatGPTActionServerSettings(
        repository_root=repo_root(),
        data_root=data_root,
        pack_manifest_path=Path("examples/packs/common/manifest.json"),
        bearer_token=TOKEN,
        max_request_body_size=max_bytes,
        public_base_url=public_base_url,
        trusted_proxy_cidrs=trusted_proxy_cidrs,
    )


def auth() -> dict[str, str]:
    return {"authorization": f"Bearer {TOKEN}"}


def put_event(data_root: Path, event_id: str, marker: str) -> None:
    suffix = event_id.removeprefix("evt_")
    path = data_root / "canonical" / "events" / suffix[:2] / f"{event_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "dkg.event.v1",
                "event_id": event_id,
                "event_type": "claim.proposed",
                "occurred_at": "2026-08-20T12:00:00Z",
                "recorded_at": "2026-08-20T12:00:00Z",
                "pack_id": COMMON,
                "actor": {"actor_type": "human", "actor_id": "holdout"},
                "subject_refs": ["clm_holdout"],
                "caused_by_event_ids": [],
                "correlation_id": None,
                "idempotency_key": f"holdout-{event_id}",
                "evidence_refs": [],
                "source_snapshot_refs": [],
                "payload": {"claim_text": marker},
            }
        ),
        encoding="utf-8",
    )


def put_redaction(data_root: Path, event_id: str, marker: str) -> None:
    suffix = event_id.removeprefix("evt_")
    path = (
        data_root
        / "canonical"
        / "events"
        / "_redactions"
        / suffix[:2]
        / f"{event_id}.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "event_id": event_id,
                "pack_id": COMMON,
                "reason": marker,
                "authority": "holdout",
                "redacted_at": "2026-08-20T12:30:00Z",
            }
        ),
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"authorization": ""},
        {"authorization": "Basic abc"},
        {"authorization": "Bearer"},
        {"authorization": "Bearer wrong"},
        {"authorization": f"Bearer {TOKEN} "},
        {"authorization": f"Bearer {TOKEN}\textra"},
        {"authorization": f"Bearer {TOKEN.upper()}"},
    ],
)
def test_holdout_absent_malformed_and_wrong_auth_fail_closed(
    tmp_path: Path, headers: dict[str, str]
) -> None:
    app = create_chatgpt_action_app_from_settings(make_settings(tmp_path))
    with TestClient(app, base_url="http://internal:8787") as client:
        response = client.post("/actions/search", headers=headers, json={"query": "x"})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_holdout_duplicate_authorization_header_fails_closed(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(make_settings(tmp_path))
    with TestClient(app, base_url="http://internal:8787") as client:
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


def test_holdout_scheme_case_is_allowed_but_token_case_is_exact(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(make_settings(tmp_path))
    with TestClient(app, base_url="http://internal:8787") as client:
        allowed = client.post(
            "/actions/search",
            headers={"authorization": f"bEaReR {TOKEN}"},
            json={"query": "x"},
        )
        denied = client.post(
            "/actions/search",
            headers={"authorization": f"Bearer {TOKEN.upper()}"},
            json={"query": "x"},
        )
    assert allowed.status_code == 200
    assert denied.status_code == 401


def test_holdout_fixed_origin_resists_forged_forwarded_and_host_headers(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(make_settings(tmp_path))
    forged = {
        "forwarded": "proto=http;host=attacker.invalid",
        "x-forwarded-proto": "https",
        "x-forwarded-host": "attacker.invalid",
        "x-forwarded-port": "443",
        "host": "attacker.invalid",
    }
    with TestClient(
        app,
        base_url="https://attacker.invalid",
        client=("203.0.113.80", 55000),
    ) as client:
        response = client.get("/openapi.json", headers=forged)
    assert response.status_code == 200
    assert response.json()["servers"] == [{"url": PUBLIC_ORIGIN}]


def test_holdout_direct_https_host_fails_closed_without_origin_authority(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(
        make_settings(tmp_path, public_base_url=None)
    )
    with TestClient(
        app,
        base_url="https://attacker.invalid",
        client=("203.0.113.80", 55000),
    ) as client:
        response = client.get(
            "/openapi.json",
            headers={"host": "forged-public-host.invalid"},
        )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "https_origin_required"
    assert "forged-public-host.invalid" not in response.text
    assert "attacker.invalid" not in response.text


def test_holdout_untrusted_forwarded_headers_fail_closed_without_fixed_origin(
    tmp_path: Path,
) -> None:
    app = create_chatgpt_action_app_from_settings(
        make_settings(
            tmp_path,
            public_base_url=None,
            trusted_proxy_cidrs=("10.0.0.0/8",),
        )
    )
    with TestClient(
        app,
        base_url="http://internal.invalid:8787",
        client=("203.0.113.80", 50000),
    ) as client:
        response = client.get(
            "/openapi.json",
            headers={
                "x-forwarded-proto": "https",
                "x-forwarded-host": "attacker.invalid",
            },
        )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "https_origin_required"
    assert "attacker.invalid" not in response.text
    assert "http://internal" not in response.text


def test_holdout_trusted_proxy_requires_unambiguous_https_headers(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(
        make_settings(
            tmp_path,
            public_base_url=None,
            trusted_proxy_cidrs=("10.0.0.0/8",),
        )
    )
    with TestClient(
        app,
        base_url="http://internal.invalid:8787",
        client=("10.1.2.3", 50000),
    ) as client:
        valid = client.get(
            "/openapi.json",
            headers={
                "x-forwarded-proto": "https",
                "x-forwarded-host": "fossil-proxy.example.invalid",
            },
        )
        assert valid.status_code == 200
        assert valid.json()["servers"] == [
            {"url": "https://fossil-proxy.example.invalid"}
        ]

        for headers in (
            {},
            {"x-forwarded-proto": "http", "x-forwarded-host": "fossil.example.test"},
            {"x-forwarded-proto": "https"},
            {"x-forwarded-proto": "https", "x-forwarded-host": "bad host"},
            {
                "x-forwarded-proto": "https,http",
                "x-forwarded-host": "fossil.example.test",
            },
            {
                "x-forwarded-proto": "https",
                "x-forwarded-host": "fossil.example.test,attacker.invalid",
            },
            {"x-forwarded-proto": "https", "x-forwarded-host": "user@host.invalid"},
        ):
            response = client.get("/openapi.json", headers=headers)
            assert response.status_code == 503
            assert '"url":"http://' not in response.text.replace(" ", "")


def test_holdout_openapi_is_valid_custom_gpt_bounded_and_truthful(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(make_settings(tmp_path))
    with TestClient(app, base_url="http://internal:8787") as client:
        response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    validate_spec(schema)

    assert schema["openapi"].startswith("3.1.")
    assert schema["servers"] == [{"url": PUBLIC_ORIGIN}]
    assert set(schema["paths"]) == ACTION_PATHS
    assert isinstance(schema["components"]["schemas"], dict)
    assert set(schema["components"]["schemas"]) >= {
        "ErrorDetail",
        "ErrorEnvelope",
        "SearchRequest",
        "ReadRequest",
        "SearchResult",
        "FossilEvent",
        "CapabilitiesResponse",
    }
    assert not set(schema["components"]["schemas"]).intersection(
        {"LineageRequest", "LineageResponse", "LineageNode", "Citation"}
    )
    for name in (
        "SearchResult",
        "FossilEvent",
        "CapabilitiesResponse",
    ):
        assert schema["components"]["schemas"][name].get("properties")

    operation_ids = [
        operation["operationId"]
        for path in schema["paths"].values()
        for operation in path.values()
    ]
    assert len(operation_ids) == len(set(operation_ids)) == 3
    assert schema["components"]["securitySchemes"]["BearerAuth"]["scheme"] == "bearer"
    assert schema["components"]["schemas"]["CapabilitiesResponse"]["properties"][
        "action_capabilities"
    ]["const"] == ["search", "read"]

    serialized = json.dumps(schema).lower()
    assert '"url": "http://' not in serialized
    assert TOKEN.lower() not in serialized
    for forbidden in (
        '"/mcp"',
        '"/ingest"',
        '"/actions/lineage"',
        '"/actions/propose"',
        '"/actions/validate"',
        '"/actions/commit"',
        '"/actions/redact"',
        '"/filesystem"',
    ):
        assert forbidden not in serialized


def test_holdout_oversized_malformed_and_streamed_payloads_fail_closed(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(make_settings(tmp_path, max_bytes=64))

    def large_chunks():
        yield b'{"query":"'
        yield b"x" * 40
        yield b"y" * 40
        yield b'"}'

    with TestClient(app, base_url="http://internal:8787") as client:
        actual = client.post(
            "/actions/search",
            headers=auth(),
            content=json.dumps({"query": "x" * 100}).encode(),
        )
        declared = client.post(
            "/actions/search",
            headers={
                **auth(),
                "content-type": "application/json",
                "content-length": "9999",
            },
            content=b'{"query":"x"}',
        )
        chunked = client.post(
            "/actions/search",
            headers={
                **auth(),
                "content-type": "application/json",
                "transfer-encoding": "chunked",
            },
            content=large_chunks(),
        )
        understated = client.post(
            "/actions/search",
            headers={
                **auth(),
                "content-type": "application/json",
                "content-length": "10",
            },
            content=large_chunks(),
        )
        malformed = client.post(
            "/actions/search", headers=auth(), content=b"{not-json"
        )
        non_object = client.post(
            "/actions/search", headers=auth(), json=["not", "object"]
        )
    assert actual.status_code == 413
    assert declared.status_code == 413
    assert chunked.status_code == 413
    assert understated.status_code == 413
    assert malformed.status_code == 400
    assert non_object.status_code == 400


def test_holdout_unknown_lineage_and_mutation_like_paths_are_not_routable(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(make_settings(tmp_path))
    prohibited = [
        "/mcp",
        "/ingest",
        "/actions/lineage",
        "/actions/propose",
        "/actions/validate",
        "/actions/commit",
        "/actions/redact",
        "/actions/write",
        "/neo4j",
        "/graph",
        "/filesystem",
        "/admin",
        "/unknown",
    ]
    with TestClient(app, base_url="http://internal:8787") as client:
        for path in prohibited:
            assert client.get(path, headers=auth()).status_code == 404, path
            assert client.post(path, headers=auth(), json={}).status_code == 404, path


def test_holdout_unsupported_methods_return_405(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(make_settings(tmp_path))
    with TestClient(app, base_url="http://internal:8787") as client:
        assert client.post("/openapi.json").status_code == 405
        assert client.get("/actions/search", headers=auth()).status_code == 405
        assert client.get("/actions/read", headers=auth()).status_code == 405
        assert client.post("/actions/capabilities", headers=auth()).status_code == 405


def test_holdout_path_capability_and_search_limit_smuggling_are_rejected(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(make_settings(tmp_path))
    with TestClient(app, base_url="http://internal:8787") as client:
        for event_id in (
            "../../../../etc/passwd",
            "evt_../../../../etc/passwd",
            "evt_abcdefghijklmnop/../../secret",
            "C:\\Windows\\System32\\drivers\\etc\\hosts",
            "file:///etc/passwd",
        ):
            response = client.post(
                "/actions/read", headers=auth(), json={"event_id": event_id}
            )
            assert response.status_code == 400, event_id

        assert client.post(
            "/actions/search",
            headers=auth(),
            json={"query": "x", "cypher": "MATCH (n) DETACH DELETE n"},
        ).status_code == 400
        assert client.post(
            "/actions/read",
            headers=auth(),
            json={"event_id": "evt_abcdefghijklmnop", "commit": True},
        ).status_code == 400

        assert client.post(
            "/actions/search", headers=auth(), json={"query": "x", "limit": 100}
        ).status_code == 200
        assert client.post(
            "/actions/search", headers=auth(), json={"query": "x", "limit": 101}
        ).status_code == 400
        assert client.post(
            "/actions/search", headers=auth(), json={"query": "x", "limit": True}
        ).status_code == 400


def test_holdout_redaction_tombstone_and_redacted_bytes_never_search_or_read(tmp_path: Path) -> None:
    configured = make_settings(tmp_path)
    redacted_id = "evt_cccccccccccccccc"
    visible_id = "evt_dddddddddddddddd"
    put_event(configured.data_root, redacted_id, "private-redacted-payload-marker")
    put_event(configured.data_root, visible_id, "public-visible-marker")
    put_redaction(configured.data_root, redacted_id, "tombstone-redaction-marker")

    app = create_chatgpt_action_app_from_settings(configured)
    with TestClient(app, base_url="http://internal:8787") as client:
        by_payload = client.post(
            "/actions/search",
            headers=auth(),
            json={"query": "private-redacted-payload-marker"},
        )
        by_tombstone = client.post(
            "/actions/search",
            headers=auth(),
            json={"query": "tombstone-redaction-marker"},
        )
        visible = client.post(
            "/actions/search",
            headers=auth(),
            json={"query": "public-visible-marker"},
        )
        read = client.post(
            "/actions/read", headers=auth(), json={"event_id": redacted_id}
        )

    assert by_payload.status_code == 200 and by_payload.json() == []
    assert by_tombstone.status_code == 200 and by_tombstone.json() == []
    assert [row["event_id"] for row in visible.json()] == [visible_id]
    assert read.status_code == 404
    assert "redact" not in read.text.lower()
    assert "tombstone-redaction-marker" not in read.text


def test_holdout_empty_canonical_data_returns_empty_search_without_fabrication(
    tmp_path: Path,
) -> None:
    app = create_chatgpt_action_app_from_settings(make_settings(tmp_path))
    with TestClient(app, base_url="http://internal:8787") as client:
        response = client.post(
            "/actions/search", headers=auth(), json={"query": "anything"}
        )
    assert response.status_code == 200
    assert response.json() == []


def test_holdout_secret_and_local_configuration_do_not_leak(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(make_settings(tmp_path))
    with TestClient(app, base_url="http://internal:8787") as client:
        responses = [
            client.get("/openapi.json"),
            client.get("/actions/capabilities", headers=auth()),
            client.post("/actions/search", json={"query": "x"}),
            client.post("/actions/search", headers=auth(), content=b"not-json"),
            client.post(
                "/actions/read",
                headers=auth(),
                json={"event_id": "evt_aaaaaaaaaaaaaaaa"},
            ),
        ]
    for response in responses:
        assert TOKEN not in response.text
        assert str(tmp_path) not in response.text
        assert "FOSSIL_ACTION_BEARER_TOKEN" not in response.text
        assert "D:\\FossilBrokerWorker" not in response.text
