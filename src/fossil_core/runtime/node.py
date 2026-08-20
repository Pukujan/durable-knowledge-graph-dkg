from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from fossil_core.adapters.filesystem.artifact_store import ArtifactStore
from fossil_core.adapters.filesystem.event_store import DurableEventStore
from fossil_core.agent import CorpusService, SkillRegistry
from fossil_core.application.ingest.pack_validation import KnowledgePackValidator
from fossil_core.application.ingest.reviewed_evidence import ReviewedEvidenceIngestService
from fossil_core.domain.pack import PackAccess
from fossil_core.projection.graphiti import GraphitiProjectionAdapter
from fossil_core.projection.ledger import ProjectionLedger
from fossil_core.source import SourceSnapshotStore

from .projector import ProjectorWorker


_BUILD_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True)
class FilesystemNodePaths:
    """Separate canonical truth from rebuildable operational state."""

    data_root: Path

    @property
    def canonical_root(self) -> Path:
        return self.data_root / "canonical"

    @property
    def artifacts_root(self) -> Path:
        return self.canonical_root / "artifacts"

    @property
    def sources_root(self) -> Path:
        return self.canonical_root / "sources"

    @property
    def events_root(self) -> Path:
        return self.canonical_root / "events"

    @property
    def operational_root(self) -> Path:
        return self.data_root / "operational"

    @property
    def projection_ledger_root(self) -> Path:
        return self.operational_root / "projection-ledger"


@dataclass(frozen=True)
class FilesystemNodeConfig:
    repository_root: Path
    data_root: Path
    pack_manifest_path: Path
    projection_build_id: str
    projection_build_manifest: Mapping[str, Any]
    poll_interval_seconds: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "repository_root", Path(self.repository_root))
        object.__setattr__(self, "data_root", Path(self.data_root))
        object.__setattr__(self, "pack_manifest_path", Path(self.pack_manifest_path))
        object.__setattr__(
            self, "projection_build_manifest", dict(self.projection_build_manifest)
        )
        if not _BUILD_ID.fullmatch(self.projection_build_id):
            raise ValueError(
                "projection_build_id must be a non-empty path-safe identifier"
            )
        if self.poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be positive")

    @property
    def paths(self) -> FilesystemNodePaths:
        return FilesystemNodePaths(self.data_root)


@dataclass(frozen=True)
class FilesystemFossilNode:
    """Concrete NODE-01 composition without introducing a second authority."""

    config: FilesystemNodeConfig
    paths: FilesystemNodePaths
    pack_manifest: dict[str, Any]
    pack_access: PackAccess
    artifact_store: ArtifactStore
    source_store: SourceSnapshotStore
    event_store: DurableEventStore
    corpus_service: CorpusService
    reviewed_ingest: ReviewedEvidenceIngestService
    projection: GraphitiProjectionAdapter
    projector: ProjectorWorker

    async def run_projector_async(self, stop_event: asyncio.Event) -> None:
        await self.projection.initialize_async()
        try:
            await self.projector.run_forever(stop_event)
        finally:
            await self.projection.close_async()


def _schema(repository_root: Path, *parts: str) -> Path:
    return repository_root / "schemas" / Path(*parts)


def _graphiti_from_environment() -> tuple[Any, Any]:
    from graphiti_core import Graphiti
    from graphiti_core.nodes import EpisodeType

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ["NEO4J_PASSWORD"]
    return Graphiti(uri, user, password), EpisodeType.json


def compose_filesystem_node(
    config: FilesystemNodeConfig,
    *,
    graphiti_client: Any | None = None,
    episode_type_json: Any | None = None,
    visibility_policy: Any | None = None,
) -> FilesystemFossilNode:
    """Compose one filesystem-backed FOSSIL node around existing contracts.

    With no injected Graphiti client, the projection client is constructed from
    the existing Neo4j environment contract. Tests may inject a client without
    importing the optional Graphiti dependency.
    """

    repository_root = config.repository_root
    paths = config.paths

    pack_validator = KnowledgePackValidator(
        _schema(repository_root, "knowledge-pack", "v1.schema.json")
    )
    pack_manifest_path = config.pack_manifest_path
    if not pack_manifest_path.is_absolute():
        pack_manifest_path = repository_root / pack_manifest_path
    pack_manifest = pack_validator.load_and_validate(pack_manifest_path)
    pack_access = PackAccess.from_manifest(pack_manifest)

    artifact_store = ArtifactStore(paths.artifacts_root)
    source_store = SourceSnapshotStore(
        paths.sources_root,
        artifact_store,
        _schema(repository_root, "source-snapshot", "v1.schema.json"),
        _schema(repository_root, "citation", "v1.schema.json"),
    )
    event_store = DurableEventStore(
        paths.events_root,
        _schema(repository_root, "events", "v1.schema.json"),
    )
    skills = SkillRegistry(
        repository_root / "skills",
        _schema(repository_root, "agent-skill", "v1.schema.json"),
    )
    corpus_service = CorpusService(event_store=event_store, skills=skills)
    reviewed_ingest = ReviewedEvidenceIngestService(
        source_store=source_store,
        event_store=event_store,
        pack_validator=pack_validator,
    )

    if graphiti_client is None:
        if episode_type_json is not None:
            raise ValueError(
                "episode_type_json is only valid when graphiti_client is injected"
            )
        graphiti_client, episode_type_json = _graphiti_from_environment()
    elif episode_type_json is None:
        raise ValueError(
            "episode_type_json is required when graphiti_client is injected"
        )

    ledger = ProjectionLedger(
        paths.projection_ledger_root,
        GraphitiProjectionAdapter.name,
        build_id=config.projection_build_id,
    )
    projection = GraphitiProjectionAdapter(
        client=graphiti_client,
        ledger=ledger,
        build_manifest=dict(config.projection_build_manifest),
        episode_type_json=episode_type_json,
        visibility_policy=visibility_policy,
    )
    projector = ProjectorWorker(
        event_store=event_store,
        projection=projection,
        ledger=projection.ledger,
        poll_interval_seconds=config.poll_interval_seconds,
    )

    return FilesystemFossilNode(
        config=config,
        paths=paths,
        pack_manifest=pack_manifest,
        pack_access=pack_access,
        artifact_store=artifact_store,
        source_store=source_store,
        event_store=event_store,
        corpus_service=corpus_service,
        reviewed_ingest=reviewed_ingest,
        projection=projection,
        projector=projector,
    )


__all__ = [
    "FilesystemFossilNode",
    "FilesystemNodeConfig",
    "FilesystemNodePaths",
    "compose_filesystem_node",
]
