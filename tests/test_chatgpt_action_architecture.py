from __future__ import annotations

import ast
from pathlib import Path

from fossil_core.runtime import chatgpt_action
from fossil_core.runtime.chatgpt_action_server import (
    ChatGPTActionServerSettings,
    build_chatgpt_action_adapter,
)


TOKEN = "architecture-token-0123456789abcdef"


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_action_route_allowlist_is_exact_and_write_or_lineage_tools_are_not_mapped() -> None:
    assert chatgpt_action._ACTION_ROUTE_ALLOWLIST == frozenset(
        {
            "/openapi.json",
            "/actions/search",
            "/actions/read",
            "/actions/capabilities",
        }
    )
    assert chatgpt_action._ACTION_PATHS == {
        "/actions/search": "fossil.search",
        "/actions/read": "fossil.read",
    }
    assert set(chatgpt_action._ACTION_PATHS.values()).isdisjoint(
        {
            "fossil.lineage",
            "fossil.propose",
            "fossil.validate",
            "fossil.commit",
            "fossil.manage",
        }
    )


def test_standalone_server_does_not_import_projection_or_mutable_event_store() -> None:
    server_path = root() / "src" / "fossil_core" / "runtime" / "chatgpt_action_server.py"
    modules = imported_modules(server_path)
    assert not any("graphiti" in module.lower() for module in modules)
    assert not any("neo4j" in module.lower() for module in modules)
    assert not any(
        module.endswith("event_store") and "adapters.filesystem" in module
        for module in modules
    )

    source = server_path.read_text(encoding="utf-8")
    assert "DurableEventStore(" not in source
    assert "proxy_headers=False" in source
    assert 'bucket.name == "_redactions"' in source
    assert "self.is_redacted(event_id)" in source


def test_read_only_adapter_exposes_no_mutation_methods_or_lineage_provider(tmp_path: Path) -> None:
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

    assert adapter.service.lineages == {}
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


def test_origin_and_streaming_guards_are_encoded_in_public_middleware() -> None:
    source = (
        root() / "src" / "fossil_core" / "runtime" / "chatgpt_action.py"
    ).read_text(encoding="utf-8")
    assert "request.url.scheme == \"https\"" not in source
    assert "return self._trusted_proxy_origin(request)" in source
    assert "async for chunk in request.stream():" in source
    assert "total > self.max_request_body_size" in source
    assert "await request.body()" not in source


def test_container_and_ci_encode_non_root_loopback_read_only_contract() -> None:
    dockerfile = (root() / "docker" / "chatgpt-action" / "Dockerfile").read_text(
        encoding="utf-8"
    )
    workflow = (
        root() / ".github" / "workflows" / "chatgpt-action-container.yml"
    ).read_text(encoding="utf-8")

    assert "useradd --uid 10001" in dockerfile
    assert "USER fossil" in dockerfile
    assert 'ENTRYPOINT ["fossil-chatgpt-action"]' in dockerfile
    assert "127.0.0.1:8787:8787" in workflow
    assert ":/var/lib/fossil:ro" in workflow
    assert 'test "$(docker exec fossil-chatgpt-action id -u)" = "10001"' in workflow
    assert "HostIp" in workflow
    assert 'eq .Destination "/var/lib/fossil"' in workflow
    assert "canonical mount unexpectedly writable" in workflow


def test_no_real_secret_is_committed_to_action_package() -> None:
    paths = [
        root() / "config" / "chatgpt-action.env.example",
        root() / "docker" / "chatgpt-action" / "Dockerfile",
        root() / ".github" / "workflows" / "chatgpt-action-container.yml",
        root() / "docs" / "operations" / "CHATGPT-ACTION-PDD.md",
        root() / "docs" / "operations" / "CHATGPT-ACTION-SDD.md",
        root() / "docs" / "operations" / "CHATGPT-ACTION-INVARIANTS.md",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)

    assert "sk-" not in combined
    assert "ghp_" not in combined
    assert "-----BEGIN PRIVATE KEY-----" not in combined
    assert TOKEN not in combined
