from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp.server.transport_security import TransportSecuritySettings
from starlette.testclient import TestClient

from fossil_core.agent import AgentContext
from fossil_core.runtime import FilesystemNodeConfig, compose_filesystem_node
from fossil_core.runtime.network import create_node_network_app


COMMON = "pack_269099f7b2ba43b7a99b9427d64092de"
PUBLIC_HOST = "fossil.design-bakery.com"
TOKEN = "public-mcp-holdout-token-0123456789abcdef"
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
    return Path(__file__).resolve().parents[2]


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


def compose(tmp_path: Path):
    config = FilesystemNodeConfig(
        repository_root=root(),
        data_root=tmp_path / "node-data",
        pack_manifest_path=root() / "examples" / "packs" / "common" / "manifest.json",
        projection_build_id="public-mcp-holdout",
        projection_build_manifest={
            "graphiti_version": "0.29.3",
            "neo4j_version": "test",
            "model_id": "test-model",
            "ontology_version": "1.0.0",
            "software_commit": "holdout",
        },
        poll_interval_seconds=0.01,
    )
    return compose_filesystem_node(
        config,
        graphiti_client=FakeGraphiti(),
        episode_type_json="json",
    )


def context(skill_id: str, skill_version: str) -> AgentContext:
    return AgentContext(
        actor_id=f"public-mcp-holdout-{skill_id}",
        model_id="fixture-model",
        harness_version="fixture-harness",
        skill_id=skill_id,
        skill_version=skill_version,
    )


def writer_context() -> AgentContext:
    return context("skill_research-ingestion", "1.1.0")


def reader_context() -> AgentContext:
    return context("skill_corpus-search", "1.0.0")


def public_security() -> TransportSecuritySettings:
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[PUBLIC_HOST, f"{PUBLIC_HOST}:*"],
        allowed_origins=[],
    )


def auth_headers(token: str = TOKEN) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}


def mcp_headers(
    token: str | None = TOKEN,
    *,
    method: str = "tools/list",
    name: str | None = None,
) -> dict[str, str]:
    headers = {
        "content-type": "application/json",
        "accept": "application/json, text/event-stream",
        "mcp-protocol-version": "2026-07-28",
        "mcp-method": method,
    }
    if name is not None:
        headers["mcp-name"] = name
    if token is not None:
        headers.update(auth_headers(token))
    return headers


def envelope(method: str, params: dict | None = None, *, request_id: int = 1) -> dict:
    payload_params = dict(params or {})
    payload_params.setdefault(
        "_meta",
        {
            "io.modelcontextprotocol/protocolVersion": "2026-07-28",
            "io.modelcontextprotocol/clientInfo": {
                "name": "fossil-public-holdout",
                "version": "1",
            },
            "io.modelcontextprotocol/clientCapabilities": {},
        },
    )
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": payload_params,
    }


def make_app(
    tmp_path: Path,
    *,
    agent_context: AgentContext | None = None,
    transport_security: TransportSecuritySettings | None = None,
    max_mcp_request_body_size: int = 1024 * 1024,
):
    return create_node_network_app(
        compose(tmp_path),
        context=agent_context or writer_context(),
        bearer_token=TOKEN,
        transport_security=transport_security,
        host="127.0.0.1",
        max_mcp_request_body_size=max_mcp_request_body_size,
    )


@pytest.mark.parametrize(
    "authorization",
    [
        None,
        "",
        "Basic abc",
        "Bearer",
        "Bearer wrong",
        f"Bearer {TOKEN} ",
        f"Bearer {TOKEN}\textra",
        f"Bearer {TOKEN.upper()}",
    ],
)
def test_holdout_authentication_fails_closed(
    tmp_path: Path, authorization: str | None
) -> None:
    app = make_app(
        tmp_path,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        ),
    )
    headers = mcp_headers(token=None)
    if authorization is not None:
        headers["authorization"] = authorization
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post("/mcp", headers=headers, json=envelope("tools/list"))
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert TOKEN not in response.text


def test_holdout_duplicate_authorization_header_fails_closed(tmp_path: Path) -> None:
    app = make_app(
        tmp_path,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        ),
    )
    headers = [
        ("authorization", f"Bearer {TOKEN}"),
        ("authorization", "Bearer attacker"),
        ("content-type", "application/json"),
        ("accept", "application/json, text/event-stream"),
        ("mcp-protocol-version", "2026-07-28"),
        ("mcp-method", "tools/list"),
    ]
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/mcp",
            headers=headers,
            content=json.dumps(envelope("tools/list")).encode(),
        )
    assert response.status_code == 401
    assert TOKEN not in response.text


def test_holdout_public_hostname_requires_explicit_transport_security(
    tmp_path: Path,
) -> None:
    default_app = make_app(tmp_path / "default")
    with TestClient(default_app, base_url=f"https://{PUBLIC_HOST}") as client:
        rejected = client.post(
            "/mcp",
            headers=mcp_headers(),
            json=envelope("tools/list"),
        )
    assert rejected.status_code == 421

    public_app = make_app(tmp_path / "public", transport_security=public_security())
    with TestClient(public_app, base_url=f"https://{PUBLIC_HOST}") as client:
        allowed = client.post(
            "/mcp",
            headers=mcp_headers(),
            json=envelope("tools/list"),
        )
        forged_host = client.post(
            "/mcp",
            headers={**mcp_headers(), "host": "attacker.invalid"},
            json=envelope("tools/list"),
        )
        forged_origin = client.post(
            "/mcp",
            headers={**mcp_headers(), "origin": "https://attacker.invalid"},
            json=envelope("tools/list"),
        )

    assert allowed.status_code == 200
    assert tuple(tool["name"] for tool in allowed.json()["result"]["tools"]) == EXPECTED_TOOLS
    assert forged_host.status_code == 421
    assert forged_origin.status_code == 403


def test_holdout_unauthenticated_requests_are_rejected_before_parsing_or_dispatch(
    tmp_path: Path,
) -> None:
    app = make_app(
        tmp_path,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        ),
        max_mcp_request_body_size=128,
    )
    huge_invalid = b"{" + (b"x" * 4096)
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/mcp",
            headers={
                "content-type": "application/json",
                "accept": "application/json, text/event-stream",
                "mcp-protocol-version": "2026-07-28",
            },
            content=huge_invalid,
        )
    assert response.status_code == 401


def test_holdout_authenticated_mcp_body_limit_remains_enforced(tmp_path: Path) -> None:
    app = make_app(
        tmp_path,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        ),
        max_mcp_request_body_size=256,
    )
    oversized = json.dumps(
        envelope("tools/list", {"padding": "x" * 4096})
    ).encode()
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post("/mcp", headers=mcp_headers(), content=oversized)
    assert response.status_code == 413


def test_holdout_bearer_token_does_not_replace_fossil_skill_authority(
    tmp_path: Path,
) -> None:
    app = make_app(
        tmp_path,
        agent_context=reader_context(),
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        ),
    )
    proposal = {
        "name": "fossil.propose",
        "arguments": {
            "event_type": "claim.proposed",
            "pack_id": COMMON,
            "subject_refs": ["clm_public_holdout"],
            "payload": {"claim_text": "Bearer auth must not grant write authority."},
            "occurred_at": "2026-08-20T20:00:00Z",
            "recorded_at": "2026-08-20T20:00:00Z",
            "idempotency_key": "public-mcp-holdout-reader-write-v1",
        },
    }
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/mcp",
            headers=mcp_headers(method="tools/call", name="fossil.propose"),
            json=envelope("tools/call", proposal),
        )
    assert response.status_code == 200
    serialized = response.text
    assert "does not grant corpus capability propose" in serialized
    assert '"isError":true' in serialized.replace(" ", "")


def test_holdout_graph_shell_filesystem_and_vendor_specific_routes_are_absent(
    tmp_path: Path,
) -> None:
    app = make_app(
        tmp_path,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        ),
    )
    prohibited = (
        "/neo4j",
        "/graph",
        "/filesystem",
        "/shell",
        "/admin",
        "/openapi.json",
        "/actions/search",
        "/actions/read",
    )
    with TestClient(app, base_url="http://localhost") as client:
        for path in prohibited:
            response = client.post(path, headers=auth_headers(), json={})
            assert response.status_code == 404, path


def test_holdout_ingest_is_authenticated_and_pack_scope_still_fails_closed(
    tmp_path: Path,
) -> None:
    app = make_app(
        tmp_path,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        ),
    )
    payload = {
        "pack_id": "pack_forbidden_public_holdout",
        "source": {},
        "claims": [],
        "review_ref": "review:public-holdout",
        "occurred_at": "2026-08-20T20:00:00Z",
        "recorded_at": "2026-08-20T20:00:00Z",
        "correlation_id": "public-mcp-holdout",
    }
    with TestClient(app, base_url="http://localhost") as client:
        unauthenticated = client.post("/ingest", json=payload)
        authenticated = client.post(
            "/ingest",
            headers=auth_headers(),
            json=payload,
        )
    assert unauthenticated.status_code == 401
    assert authenticated.status_code == 403
    assert authenticated.json()["error"]["code"] == "unauthorized_pack"
