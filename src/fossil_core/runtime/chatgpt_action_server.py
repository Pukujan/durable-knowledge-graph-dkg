from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping
from urllib.parse import urlparse

from starlette.applications import Starlette

from fossil_core.adapters.mcp import ThinMCPAdapter
from fossil_core.agent import AgentContext, CorpusService, SkillRegistry
from fossil_core.application.ingest.pack_validation import KnowledgePackValidator
from fossil_core.domain.pack import PackAccess
from fossil_core.event_store import EventRedactedError

from .chatgpt_action import add_chatgpt_action_api


_EVENT_ID = re.compile(r"^evt_[A-Za-z0-9_-]{16,128}$")


class _ReadOnlyEventStore:
    """Filesystem view that implements only the event reads used by this edge."""

    def __init__(self, root: Path):
        self.root = Path(root)
        if not self.root.is_dir():
            raise FileNotFoundError(f"canonical event store does not exist: {self.root}")
        self.redactions = self.root / "_redactions"

    @staticmethod
    def _validate_event_id(event_id: str) -> str:
        if not _EVENT_ID.fullmatch(event_id):
            raise ValueError("event_id is not a valid FOSSIL event identifier")
        return event_id

    def _event_path(self, event_id: str) -> Path:
        event_id = self._validate_event_id(event_id)
        suffix = event_id.removeprefix("evt_")
        return self.root / suffix[:2] / f"{event_id}.json"

    def _redaction_path(self, event_id: str) -> Path:
        event_id = self._validate_event_id(event_id)
        suffix = event_id.removeprefix("evt_")
        return self.redactions / suffix[:2] / f"{event_id}.json"

    def is_redacted(self, event_id: str) -> bool:
        return self._redaction_path(event_id).exists()

    def get(self, event_id: str) -> dict[str, Any]:
        if self.is_redacted(event_id):
            raise EventRedactedError(f"event {event_id} has been redacted")
        return json.loads(self._event_path(event_id).read_text(encoding="utf-8"))

    def iter_events(self) -> Iterator[dict[str, Any]]:
        for path in sorted(self.root.glob("*/*.json")):
            yield json.loads(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class ChatGPTActionServerSettings:
    """Runtime-only configuration for the public read-only Action edge."""

    repository_root: Path
    data_root: Path
    pack_manifest_path: Path
    bearer_token: str
    host: str = "127.0.0.1"
    port: int = 8787
    max_request_body_size: int = 64 * 1024
    public_base_url: str | None = None

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
        if self.max_request_body_size < 1 or self.max_request_body_size > 1024 * 1024:
            raise ValueError("FOSSIL_ACTION_MAX_REQUEST_BYTES must be between 1 and 1048576")
        if self.public_base_url is not None:
            parsed = urlparse(self.public_base_url)
            if parsed.scheme != "https" or not parsed.netloc or parsed.path not in {"", "/"}:
                raise ValueError(
                    "FOSSIL_ACTION_PUBLIC_BASE_URL must be an origin-only https:// URL"
                )
            object.__setattr__(self, "public_base_url", self.public_base_url.rstrip("/"))

    @classmethod
    def from_environment(
        cls, environment: Mapping[str, str] | None = None
    ) -> "ChatGPTActionServerSettings":
        env = os.environ if environment is None else environment
        repository_root = Path(env.get("FOSSIL_REPOSITORY_ROOT", Path.cwd()))
        raw_port = env.get("FOSSIL_ACTION_PORT", "8787")
        raw_max = env.get("FOSSIL_ACTION_MAX_REQUEST_BYTES", str(64 * 1024))
        try:
            port = int(raw_port)
        except ValueError as exc:
            raise ValueError("FOSSIL_ACTION_PORT must be an integer") from exc
        try:
            max_request_body_size = int(raw_max)
        except ValueError as exc:
            raise ValueError("FOSSIL_ACTION_MAX_REQUEST_BYTES must be an integer") from exc
        return cls(
            repository_root=repository_root,
            data_root=Path(env.get("FOSSIL_DATA_ROOT", repository_root / "data")),
            pack_manifest_path=Path(
                env.get("FOSSIL_PACK_MANIFEST", "examples/packs/common/manifest.json")
            ),
            bearer_token=env.get("FOSSIL_ACTION_BEARER_TOKEN", ""),
            host=env.get("FOSSIL_ACTION_HOST", "127.0.0.1"),
            port=port,
            max_request_body_size=max_request_body_size,
            public_base_url=env.get("FOSSIL_ACTION_PUBLIC_BASE_URL") or None,
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

    event_store = _ReadOnlyEventStore(settings.data_root / "canonical" / "events")
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


def create_chatgpt_action_app_from_settings(
    settings: ChatGPTActionServerSettings,
) -> Starlette:
    adapter = build_chatgpt_action_adapter(settings)
    return add_chatgpt_action_api(
        Starlette(),
        adapter=adapter,
        bearer_token=settings.bearer_token,
        max_request_body_size=settings.max_request_body_size,
        public_base_url=settings.public_base_url,
    )


def create_chatgpt_action_app_from_environment(
    environment: Mapping[str, str] | None = None,
) -> Starlette:
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
        proxy_headers=False,
    )


__all__ = [
    "ChatGPTActionServerSettings",
    "build_chatgpt_action_adapter",
    "create_chatgpt_action_app_from_environment",
    "create_chatgpt_action_app_from_settings",
    "main",
]
