from __future__ import annotations

from pathlib import Path

from fossil_core.runtime.chatgpt_action_server import (
    ChatGPTActionServerSettings,
    build_chatgpt_action_adapter,
)


TOKEN = "architecture-token-0123456789abcdef"


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_action_source_does_not_publish_private_protocols_or_projection_clients() -> None:
    action = (root() / "src" / "fossil_core" / "runtime" / "chatgpt_action.py").read_text(
        encoding="utf-8"
    )
    server = (
        root() / "src" / "fossil_core" / "runtime" / "chatgpt_action_server.py"
    ).read_text(encoding="utf-8")

    assert '"/mcp"' not in action
    assert '"/ingest"' not in action
    assert "Graphiti" not in server
    assert "neo4j" not in server.lower()
    assert "DurableEventStore(" not in server
    assert "proxy_headers=False" in server


def test_read_only_adapter_exposes_no_mutation_methods(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    (data_root / "canonical" / "events").mkdir(parents=True)
    settings = ChatGPTActionServerSettings(
        repository_root=root(),
        data_root=data_root,
        pack_manifest_path=Path("examples/packs/common/manifest.json"),
        bearer_token=TOKEN,
    )
    adapter = build_chatgpt_action_adapter(settings)
    store = adapter.service.event_store

    assert {name for name in ("get", "iter_events", "is_redacted") if hasattr(store, name)} == {
        "get",
        "iter_events",
        "is_redacted",
    }
    for forbidden in (
        "commit",
        "prepare",
        "validate",
        "redact",
        "put",
        "delete",
        "write",
        "publish",
    ):
        assert not hasattr(store, forbidden)


def test_container_and_ci_encode_non_root_read_only_contract() -> None:
    dockerfile = (root() / "docker" / "chatgpt-action" / "Dockerfile").read_text(
        encoding="utf-8"
    )
    workflow = (
        root() / ".github" / "workflows" / "chatgpt-action-container.yml"
    ).read_text(encoding="utf-8")

    assert "useradd --uid 10001" in dockerfile
    assert "USER fossil" in dockerfile
    assert 'ENTRYPOINT ["fossil-chatgpt-action"]' in dockerfile
    assert ":/var/lib/fossil:ro" in workflow
    assert 'test "$(docker exec fossil-chatgpt-action id -u)" = "10001"' in workflow
    assert "canonical mount unexpectedly writable" in workflow


def test_no_real_secret_is_committed_to_action_package() -> None:
    paths = [
        root() / "config" / "chatgpt-action.env.example",
        root() / "docker" / "chatgpt-action" / "Dockerfile",
        root() / ".github" / "workflows" / "chatgpt-action-container.yml",
        root() / "docs" / "operations" / "CHATGPT-ACTION-PDD.md",
        root() / "docs" / "operations" / "CHATGPT-ACTION-SDD.md",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)

    assert "sk-" not in combined
    assert "ghp_" not in combined
    assert "-----BEGIN PRIVATE KEY-----" not in combined
    assert TOKEN not in combined
