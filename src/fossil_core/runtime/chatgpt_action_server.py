from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from fossil_core.adapters.filesystem.event_store import DurableEventStore
from fossil_core.adapters.mcp import ThinMCPAdapter
from fossil_core.agent import AgentContext, CorpusService, SkillRegistry
from fossil_core.application.ingest.pack_validation import KnowledgePackValidator
from fossil_core.domain.pack import PackAccess

from .chatgpt_action import create_chatgpt_action_app


@dataclass(frozen=True)
class ChatGPTActionServerSettings:
    """Runtime-only configuration for the public read-only Action edge."""

    repository_root: Path
    data_root: Path
    pack_manifest_path: Path
    bearer_token: str
    host: str = "127.0.0.1"
    port: int = 8787

    def __post_init__(self) -> None:
        object.__setattr__(self, "repository_root", Path(self.repository_root))
        object.__setattr__(self, "data_root", Path(self.data_root))
        object.__setattr__(self, "pack_manifest_path", Path(self.pack_manifest_path))
        if not self.bearer_token or self.bearer_token != self.bearer_token.strip():
            raise ValueError("FOSSIL_ACTION_BEARER_TOKEN must be a non-empty trimmed secret")
        if len(self.bearer_token) < 32:
            raise ValueError("FOSSIL_ACTION_BEARER_TOKEN must contain at least 32 characters")
        if not self.host or self.host != self.host.strip():
            raise ValueError("FOSSIL_ACTION_HOST must be a non-empty trimmed host")
        if self.port < 1 or self.port > 65535:
            raise ValueError("FOSSIL_ACTION_PORT must be between 1 and 65535")

    @classmethod
    def from_environment(
        cls, environment: Mapping[str, str] | None = None
    ) -> "ChatGPTActionServerSettings":
        env = os.environ if environment is None else environment
        token = env.get("FOSSIL_ACTION_BEARER_TOKEN", "")
        repository_root = Path(env.get("FOSSIL_REPOSITORY_ROOT", Path.cwd()))
        data_root = Path(env.get("FOSSIL_DATA_ROOT", repository_root / "data"))
        pack_manifest = Path(
            env.get(
                "FOSSIL_PACK_MANIFEST",
                "examples/packs/common/manifest.json",
            )
        )
        raw_port = env.get("FOSSIL_ACTION_PORT", "8787")
        try:
            port = int(raw_port)
        except ValueError as exc:
            raise ValueError("FOSSIL_ACTION_PORT must be an integer") from exc
        return cls(
            repository_root=repository_root,
            data_root=data_root,
            pack_manifest_path=pack_manifest,
            bearer_token=token,
            host=env.get("FOSSIL_ACTION_HOST", "127.0.0.1"),
            port=port,
        )


def _schema(repository_root: Path, *parts: str) -> Path:
    return repository_root / "schemas" / Path(*parts)


def build_chatgpt_action_adapter(
    settings: ChatGPTActionServerSettings,
) -> ThinMCPAdapter:
    """Build only the canonical read boundary; do not construct Graphiti/Neo4j."""

    repository_root = settings.repository_root
    manifest_path = settings.pack_manifest_path
    if not manifest_path.is_absolute():
        manifest_path = repository_root / manifest_path

    pack_validator = KnowledgePackValidator(
        _schema(repository_root, "knowledge-pack", "v1.schema.json")
    )
    manifest = pack_validator.load_and_validate(manifest_path)
    access = PackAccess.from_manifest(manifest)

    event_store = DurableEventStore(
        settings.data_root / "canonical" / "events",
        _schema(repository_root, "events", "v1.schema.json"),
    )
    skills = SkillRegistry(
        repository_root / "skills",
        _schema(repository_root, "agent-skill", "v1.schema.json"),
    )
    service = CorpusService(event_store=event_store, skills=skills)
    context = AgentContext(
        actor_id="chatgpt-action-readonly",
        model_id="chatgpt",
        harness_version="custom-gpt-action-v1",
        skill_id="skill_corpus-search",
        skill_version="1.0.0",
    )
    return ThinMCPAdapter(service=service, access=access, context=context)


def create_chatgpt_action_app_from_settings(settings: ChatGPTActionServerSettings):
    adapter = build_chatgpt_action_adapter(settings)
    return create_chatgpt_action_app(
        adapter=adapter,
        bearer_token=settings.bearer_token,
    )


def create_chatgpt_action_app_from_environment(
    environment: Mapping[str, str] | None = None,
):
    return create_chatgpt_action_app_from_settings(
        ChatGPTActionServerSettings.from_environment(environment)
    )


def main() -> None:
    """Run the Action edge; TLS is intentionally terminated upstream."""

    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover - packaging guard
        raise RuntimeError(
            "uvicorn is required; install fossil-core with the 'node' extra"
        ) from exc

    settings = ChatGPTActionServerSettings.from_environment()
    app = create_chatgpt_action_app_from_settings(settings)
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        access_log=False,
        server_header=False,
    )


__all__ = [
    "ChatGPTActionServerSettings",
    "build_chatgpt_action_adapter",
    "create_chatgpt_action_app_from_environment",
    "create_chatgpt_action_app_from_settings",
    "main",
]
