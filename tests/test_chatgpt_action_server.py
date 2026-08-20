from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from fossil_core.runtime.chatgpt_action import add_chatgpt_action_api
from fossil_core.runtime.chatgpt_action_server import (
    ChatGPTActionServerSettings,
    build_chatgpt_action_adapter,
    create_chatgpt_action_app_from_environment,
    create_chatgpt_action_app_from_settings,
)


TOKEN = "server-test-token-0123456789abcdef"
PUBLIC_ORIGIN = "https://fossil-action.example.test"
COMMON = "pack_269099f7b2ba43b7a99b9427d64092de"


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def settings(
    tmp_path: Path,
    *,
    public_base_url: str | None = PUBLIC_ORIGIN,
    trusted_proxy_cidrs: tuple[str, ...] = (),
    max_bytes: int = 65536,
) -> ChatGPTActionServerSettings:
    data_root = tmp_path / "data"
    (data_root / "canonical" / "events").mkdir(parents=True, exist_ok=True)
    return ChatGPTActionServerSettings(
        repository_root=root(),
        data_root=data_root,
        pack_manifest_path=Path("examples/packs/common/manifest.json"),
        bearer_token=TOKEN,
        max_request_body_size=max_bytes,
        public_base_url=public_base_url,
        trusted_proxy_cidrs=trusted_proxy_cidrs,
    )


def auth() -> dict[str, str]:
    return {"authorization": f"Bearer {TOKEN}"}


def write_event(data_root: Path, event_id: str, marker: str) -> dict:
    suffix = event_id.removeprefix("evt_")
    path = data_root / "canonical" / "events" / suffix[:2] / f"{event_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "schema_version": "dkg.event.v1",
        "event_id": event_id,
        "event_type": "claim.proposed",
        "occurred_at": "2026-08-20T12:00:00Z",
        "recorded_at": "2026-08-20T12:00:00Z",
        "pack_id": COMMON,
        "actor": {"actor_type": "human", "actor_id": "fixture"},
        "subject_refs": ["clm_fixture"],
        "caused_by_event_ids": [],
        "correlation_id": None,
        "idempotency_key": f"fixture-{event_id}",
        "evidence_refs": [],
        "source_snapshot_refs": [],
        "payload": {"claim_text": marker},
    }
    path.write_text(json.dumps(event), encoding="utf-8")
    return event


def write_redaction(data_root: Path, event_id: str, marker: str) -> None:
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
                "redacted_at": "2026-08-20T12:30:00Z",
                "reason": marker,
                "authority": "fixture",
            }
        ),
        encoding="utf-8",
    )


def test_settings_from_environment_and_validation(tmp_path: Path):
    env = {
        "FOSSIL_REPOSITORY_ROOT": str(root()),
        "FOSSIL_DATA_ROOT": str(tmp_path / "data"),
        "FOSSIL_PACK_MANIFEST": "examples/packs/common/manifest.json",
        "FOSSIL_ACTION_BEARER_TOKEN": TOKEN,
        "FOSSIL_ACTION_HOST": "0.0.0.0",
        "FOSSIL_ACTION_PORT": "8787",
        "FOSSIL_ACTION_MAX_REQUEST_BYTES": "65536",
        "FOSSIL_ACTION_PUBLIC_BASE_URL": PUBLIC_ORIGIN,
        "FOSSIL_ACTION_TRUSTED_PROXY_CIDRS": "172.30.1.10/32,10.0.0.0/8",
    }
    parsed = ChatGPTActionServerSettings.from_environment(env)
    assert parsed.host == "0.0.0.0"
    assert parsed.port == 8787
    assert parsed.max_request_body_size == 65536
    assert parsed.public_base_url == PUBLIC_ORIGIN
    assert parsed.trusted_proxy_cidrs == ("172.30.1.10/32", "10.0.0.0/8")

    with pytest.raises(ValueError):
        ChatGPTActionServerSettings.from_environment({**env, "FOSSIL_ACTION_PORT": "bad"})
    with pytest.raises(ValueError):
        ChatGPTActionServerSettings.from_environment(
            {**env, "FOSSIL_ACTION_PUBLIC_BASE_URL": "http://example.test"}
        )
    with pytest.raises(ValueError):
        ChatGPTActionServerSettings.from_environment(
            {**env, "FOSSIL_ACTION_TRUSTED_PROXY_CIDRS": "0.0.0.0/not-a-prefix"}
        )


def test_standalone_adapter_is_read_only_and_has_no_lineage_provider(tmp_path: Path):
    configured = settings(tmp_path)
    adapter = build_chatgpt_action_adapter(configured)

    assert adapter.service.lineages == {}
    store = adapter.service.event_store
    assert hasattr(store, "get") and hasattr(store, "iter_events")
    for forbidden in ("commit", "prepare", "validate", "redact", "put", "delete", "write"):
        assert not hasattr(store, forbidden)

    app = create_chatgpt_action_app_from_settings(configured)
    with TestClient(app, base_url="http://internal:8787") as client:
        schema = client.get("/openapi.json")
        assert schema.status_code == 200
        assert set(schema.json()["paths"]) == {
            "/actions/search",
            "/actions/read",
            "/actions/capabilities",
        }
        assert "/actions/lineage" not in schema.json()["paths"]

        capabilities = client.get("/actions/capabilities", headers=auth())
        assert capabilities.status_code == 200
        assert capabilities.json()["action_capabilities"] == ["search", "read"]

        lineage = client.post(
            "/actions/lineage",
            headers=auth(),
            json={"conversation_id": "conv_abcdefghijklmnop"},
        )
        assert lineage.status_code == 404


def test_empty_canonical_store_returns_empty_search(tmp_path: Path):
    app = create_chatgpt_action_app_from_settings(settings(tmp_path))
    with TestClient(app, base_url="http://internal:8787") as client:
        response = client.post(
            "/actions/search", headers=auth(), json={"query": "anything"}
        )
    assert response.status_code == 200
    assert response.json() == []


def test_redacted_event_and_tombstone_never_cross_search_or_read_boundary(tmp_path: Path):
    configured = settings(tmp_path)
    redacted_id = "evt_aaaaaaaaaaaaaaaa"
    visible_id = "evt_bbbbbbbbbbbbbbbb"
    write_event(configured.data_root, redacted_id, "redacted-payload-marker")
    write_event(configured.data_root, visible_id, "visible-payload-marker")
    write_redaction(configured.data_root, redacted_id, "tombstone-only-marker")

    app = create_chatgpt_action_app_from_settings(configured)
    with TestClient(app, base_url="http://internal:8787") as client:
        redacted_payload_search = client.post(
            "/actions/search",
            headers=auth(),
            json={"query": "redacted-payload-marker"},
        )
        tombstone_search = client.post(
            "/actions/search",
            headers=auth(),
            json={"query": "tombstone-only-marker"},
        )
        visible_search = client.post(
            "/actions/search",
            headers=auth(),
            json={"query": "visible-payload-marker"},
        )
        redacted_read = client.post(
            "/actions/read", headers=auth(), json={"event_id": redacted_id}
        )

    assert redacted_payload_search.status_code == 200
    assert redacted_payload_search.json() == []
    assert tombstone_search.status_code == 200
    assert tombstone_search.json() == []
    assert visible_search.status_code == 200
    assert [item["event_id"] for item in visible_search.json()] == [visible_id]
    assert redacted_read.status_code == 404
    assert "redact" not in redacted_read.text.lower()
    assert "tombstone-only-marker" not in redacted_read.text


def test_direct_https_host_is_not_an_origin_authority(tmp_path: Path):
    configured = settings(tmp_path, public_base_url=None)
    app = create_chatgpt_action_app_from_settings(configured)
    with TestClient(
        app,
        base_url="https://attacker-controlled.example",
        client=("203.0.113.80", 50000),
    ) as client:
        response = client.get(
            "/openapi.json",
            headers={"host": "attacker-controlled.example"},
        )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "https_origin_required"
    assert "attacker-controlled.example" not in response.text


def test_trusted_proxy_https_origin_is_accepted_and_untrusted_forgery_is_not(tmp_path: Path):
    configured = settings(
        tmp_path,
        public_base_url=None,
        trusted_proxy_cidrs=("10.0.0.0/8",),
    )
    app = create_chatgpt_action_app_from_settings(configured)

    with TestClient(
        app,
        base_url="http://internal:8787",
        client=("10.1.2.3", 50000),
    ) as trusted:
        good = trusted.get(
            "/openapi.json",
            headers={
                "x-forwarded-proto": "https",
                "x-forwarded-host": "public.example.test",
            },
        )
    assert good.status_code == 200
    assert good.json()["servers"] == [{"url": "https://public.example.test"}]

    with TestClient(
        app,
        base_url="http://internal:8787",
        client=("203.0.113.80", 50000),
    ) as untrusted:
        bad = untrusted.get(
            "/openapi.json",
            headers={
                "x-forwarded-proto": "https",
                "x-forwarded-host": "attacker.invalid",
            },
        )
    assert bad.status_code == 503
    assert "attacker.invalid" not in bad.text


class CountingAdapter:
    def __init__(self) -> None:
        self.calls = 0
        self.service = SimpleNamespace(service_version="test")

    def invoke(self, tool_name: str, arguments: dict):
        self.calls += 1
        return []


def streamed_app(adapter: CountingAdapter) -> Starlette:
    return add_chatgpt_action_api(
        Starlette(),
        adapter=adapter,
        bearer_token=TOKEN,
        max_request_body_size=64,
        public_base_url=PUBLIC_ORIGIN,
    )


@pytest.mark.parametrize(
    "extra_headers",
    [
        {"transfer-encoding": "chunked"},
        {"content-length": "10"},
    ],
)
def test_streaming_limit_rejects_chunked_or_underdeclared_body_before_adapter(
    extra_headers: dict[str, str],
) -> None:
    adapter = CountingAdapter()
    app = streamed_app(adapter)

    def chunks():
        yield b'{"query":"'
        yield b"x" * 40
        yield b"y" * 40
        yield b'"}'

    with TestClient(app, base_url="http://internal:8787") as client:
        response = client.post(
            "/actions/search",
            headers={**auth(), **extra_headers, "content-type": "application/json"},
            content=chunks(),
        )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"
    assert adapter.calls == 0


def test_declared_oversize_is_rejected_before_adapter(tmp_path: Path) -> None:
    adapter = CountingAdapter()
    app = streamed_app(adapter)
    with TestClient(app, base_url="http://internal:8787") as client:
        response = client.post(
            "/actions/search",
            headers={
                **auth(),
                "content-type": "application/json",
                "content-length": "9999",
            },
            content=b'{"query":"x"}',
        )
    assert response.status_code == 413
    assert adapter.calls == 0


def test_environment_composition_uses_same_hardened_app(tmp_path: Path):
    data_root = tmp_path / "data"
    (data_root / "canonical" / "events").mkdir(parents=True)
    env = {
        "FOSSIL_REPOSITORY_ROOT": str(root()),
        "FOSSIL_DATA_ROOT": str(data_root),
        "FOSSIL_PACK_MANIFEST": "examples/packs/common/manifest.json",
        "FOSSIL_ACTION_BEARER_TOKEN": TOKEN,
        "FOSSIL_ACTION_PUBLIC_BASE_URL": PUBLIC_ORIGIN,
    }
    app = create_chatgpt_action_app_from_environment(env)
    with TestClient(app, base_url="http://internal:8787") as client:
        schema = client.get("/openapi.json")
        empty = client.post(
            "/actions/search", headers=auth(), json={"query": "nothing"}
        )
        lineage = client.post(
            "/actions/lineage",
            headers=auth(),
            json={"conversation_id": "conv_abcdefghijklmnop"},
        )
    assert schema.status_code == 200
    assert "/actions/lineage" not in schema.json()["paths"]
    assert empty.status_code == 200 and empty.json() == []
    assert lineage.status_code == 404
