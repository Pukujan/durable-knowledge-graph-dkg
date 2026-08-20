from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from fossil_core.runtime.chatgpt_action_server import (
    ChatGPTActionServerSettings,
    build_chatgpt_action_adapter,
    create_chatgpt_action_app_from_settings,
)


TOKEN = "a" * 48


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def settings(tmp_path: Path, **overrides) -> ChatGPTActionServerSettings:
    data_root = tmp_path / "fossil-data"
    (data_root / "canonical" / "events").mkdir(parents=True, exist_ok=True)
    values = {
        "repository_root": root(),
        "data_root": data_root,
        "pack_manifest_path": Path("examples/packs/common/manifest.json"),
        "bearer_token": TOKEN,
    }
    values.update(overrides)
    return ChatGPTActionServerSettings(**values)


def test_settings_parse_secretless_runtime_configuration(tmp_path: Path) -> None:
    parsed = ChatGPTActionServerSettings.from_environment(
        {
            "FOSSIL_REPOSITORY_ROOT": str(root()),
            "FOSSIL_DATA_ROOT": str(tmp_path / "data"),
            "FOSSIL_PACK_MANIFEST": "examples/packs/common/manifest.json",
            "FOSSIL_ACTION_BEARER_TOKEN": TOKEN,
            "FOSSIL_ACTION_HOST": "0.0.0.0",
            "FOSSIL_ACTION_PORT": "8787",
            "FOSSIL_ACTION_MAX_REQUEST_BYTES": "32768",
            "FOSSIL_ACTION_PUBLIC_BASE_URL": "https://fossil.example.test/",
            "FOSSIL_ACTION_TRUSTED_PROXY_CIDRS": "10.0.0.0/8, 192.168.65.1/32",
        }
    )

    assert parsed.repository_root == root()
    assert parsed.data_root == tmp_path / "data"
    assert parsed.pack_manifest_path == Path("examples/packs/common/manifest.json")
    assert parsed.host == "0.0.0.0"
    assert parsed.port == 8787
    assert parsed.max_request_body_size == 32768
    assert parsed.public_base_url == "https://fossil.example.test"
    assert parsed.trusted_proxy_cidrs == ("10.0.0.0/8", "192.168.65.1/32")


def test_settings_fail_closed_for_invalid_runtime_configuration(tmp_path: Path) -> None:
    base = {
        "FOSSIL_REPOSITORY_ROOT": str(root()),
        "FOSSIL_DATA_ROOT": str(tmp_path / "data"),
    }

    with pytest.raises(ValueError, match="non-empty"):
        ChatGPTActionServerSettings.from_environment(base)

    with pytest.raises(ValueError, match="at least 32"):
        ChatGPTActionServerSettings.from_environment(
            {**base, "FOSSIL_ACTION_BEARER_TOKEN": "too-short"}
        )

    with pytest.raises(ValueError, match="PORT must be an integer"):
        ChatGPTActionServerSettings.from_environment(
            {
                **base,
                "FOSSIL_ACTION_BEARER_TOKEN": TOKEN,
                "FOSSIL_ACTION_PORT": "not-a-port",
            }
        )

    with pytest.raises(ValueError, match="MAX_REQUEST_BYTES must be an integer"):
        ChatGPTActionServerSettings.from_environment(
            {
                **base,
                "FOSSIL_ACTION_BEARER_TOKEN": TOKEN,
                "FOSSIL_ACTION_MAX_REQUEST_BYTES": "not-a-number",
            }
        )

    for value in (0, 1024 * 1024 + 1):
        with pytest.raises(ValueError, match="between 1 and 1048576"):
            settings(tmp_path, max_request_body_size=value)

    for url in (
        "http://fossil.example.test",
        "https://",
        "https://user:pass@fossil.example.test",
        "https://fossil.example.test/path",
        "https://fossil.example.test?query=1",
    ):
        with pytest.raises(ValueError, match="origin-only https"):
            settings(tmp_path, public_base_url=url)

    with pytest.raises(ValueError, match="invalid FOSSIL_ACTION_TRUSTED_PROXY_CIDRS"):
        settings(tmp_path, trusted_proxy_cidrs=("not-a-cidr",))


def test_standalone_adapter_bootstraps_empty_data_without_neo4j(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    adapter = build_chatgpt_action_adapter(settings(tmp_path))

    assert adapter.context.skill_id == "skill_corpus-search"
    assert adapter.context.skill_version == "1.0.0"
    assert adapter.invoke("fossil.search", {"query": "nothing-yet"}) == []
    assert adapter.service.event_store.root == (
        tmp_path / "fossil-data" / "canonical" / "events"
    )
    for mutation_method in (
        "commit",
        "prepare",
        "validate",
        "redact",
        "put",
        "delete",
    ):
        assert not hasattr(adapter.service.event_store, mutation_method)


def test_standalone_adapter_requires_existing_canonical_store(tmp_path: Path) -> None:
    configured = ChatGPTActionServerSettings(
        repository_root=root(),
        data_root=tmp_path / "missing-data",
        pack_manifest_path=Path("examples/packs/common/manifest.json"),
        bearer_token=TOKEN,
    )

    with pytest.raises(FileNotFoundError, match="canonical event store does not exist"):
        build_chatgpt_action_adapter(configured)


def test_event_read_rejects_filesystem_escape_identifiers(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(
        settings(tmp_path, public_base_url="https://fossil.example.test")
    )
    headers = {"authorization": f"Bearer {TOKEN}"}
    with TestClient(app, base_url="http://internal:8787") as client:
        for event_id in (
            "../../../../etc/passwd",
            "evt_../../../../etc/passwd",
            "evt_abcdefghijklmnop/../../secret",
            "C:\\Windows\\win.ini",
            "file:///etc/passwd",
        ):
            response = client.post(
                "/actions/read", headers=headers, json={"event_id": event_id}
            )
            assert response.status_code == 400
            assert response.json()["error"]["code"] == "invalid_request"


def test_fixed_https_origin_overrides_all_forwarded_headers(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(
        settings(tmp_path, public_base_url="https://fossil.example.test")
    )
    with TestClient(
        app, base_url="http://internal:8787", client=("203.0.113.44", 50000)
    ) as client:
        schema = client.get(
            "/openapi.json",
            headers={
                "x-forwarded-proto": "https",
                "x-forwarded-host": "attacker.invalid",
            },
        )
        assert schema.status_code == 200
        assert schema.json()["servers"] == [{"url": "https://fossil.example.test"}]


def test_trusted_proxy_headers_generate_public_https_origin(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(
        settings(tmp_path, trusted_proxy_cidrs=("10.0.0.0/8",))
    )
    with TestClient(
        app, base_url="http://internal:8787", client=("10.20.30.40", 50000)
    ) as client:
        schema = client.get(
            "/openapi.json",
            headers={
                "x-forwarded-proto": "https",
                "x-forwarded-host": "fossil.example.test",
            },
        )
        assert schema.status_code == 200
        assert schema.json()["servers"] == [{"url": "https://fossil.example.test"}]


def test_forged_or_incomplete_proxy_headers_never_publish_http_or_attacker_origin(
    tmp_path: Path,
) -> None:
    app = create_chatgpt_action_app_from_settings(
        settings(tmp_path, trusted_proxy_cidrs=("10.0.0.0/8",))
    )

    with TestClient(
        app, base_url="http://internal:8787", client=("203.0.113.44", 50000)
    ) as untrusted:
        forged = untrusted.get(
            "/openapi.json",
            headers={
                "x-forwarded-proto": "https",
                "x-forwarded-host": "attacker.invalid",
            },
        )
        assert forged.status_code == 503
        assert "attacker.invalid" not in forged.text
        assert "http://internal" not in forged.text

    with TestClient(
        app, base_url="http://internal:8787", client=("10.20.30.40", 50000)
    ) as trusted:
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
        ):
            response = trusted.get("/openapi.json", headers=headers)
            assert response.status_code == 503
            assert "http://internal" not in response.text


def test_direct_https_request_needs_no_proxy_headers(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(settings(tmp_path))
    with TestClient(app, base_url="https://fossil.example.test") as client:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert response.json()["servers"] == [{"url": "https://fossil.example.test"}]


def test_deployed_action_app_exposes_only_read_edge_and_empty_search(tmp_path: Path) -> None:
    app = create_chatgpt_action_app_from_settings(
        settings(tmp_path, public_base_url="https://fossil.example.test")
    )

    with TestClient(app, base_url="http://internal:8787") as client:
        denied = client.post("/actions/search", json={"query": "FOSSIL"})
        assert denied.status_code == 401

        headers = {"authorization": f"Bearer {TOKEN}"}
        searched = client.post(
            "/actions/search", headers=headers, json={"query": "FOSSIL"}
        )
        assert searched.status_code == 200
        assert searched.json() == []

        capabilities = client.get("/actions/capabilities", headers=headers)
        assert capabilities.status_code == 200
        assert capabilities.json()["durable_writes_exposed"] is False

        for path in (
            "/mcp",
            "/ingest",
            "/actions/propose",
            "/actions/validate",
            "/actions/commit",
            "/actions/redact",
            "/neo4j",
            "/graph",
            "/filesystem",
        ):
            assert client.get(path, headers=headers).status_code == 404


def test_container_contract_keeps_secret_runtime_only_and_avoids_proxy_autotrust() -> None:
    dockerfile = (root() / "docker" / "chatgpt-action" / "Dockerfile").read_text(
        encoding="utf-8"
    )
    example = (root() / "config" / "chatgpt-action.env.example").read_text(
        encoding="utf-8"
    )
    server = (
        root() / "src" / "fossil_core" / "runtime" / "chatgpt_action_server.py"
    ).read_text(encoding="utf-8")

    assert "FOSSIL_ACTION_BEARER_TOKEN=" not in dockerfile
    assert "USER fossil" in dockerfile
    assert 'ENTRYPOINT ["fossil-chatgpt-action"]' in dockerfile
    assert "replace-with-a-random-secret" in example
    assert "FOSSIL_ACTION_PUBLIC_BASE_URL=https://fossil-action.example.invalid" in example
    assert "FOSSIL_ACTION_TRUSTED_PROXY_CIDRS=" in example
    assert "proxy_headers=False" in server
    assert TOKEN not in example
