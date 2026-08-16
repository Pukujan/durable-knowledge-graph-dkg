from __future__ import annotations

from pathlib import Path

from fossil_core.artifact_store import ArtifactStore
from fossil_core.event_store import DurableEventStore
from fossil_core.ports import ArtifactStorePort, EventStorePort
from fossil_core.ports.artifact_store import ArtifactStorePort as BoundedArtifactStorePort
from fossil_core.ports.event_store import EventStorePort as BoundedEventStorePort
from fossil_core.s3_storage import S3ArtifactStore, S3DurableEventStore
from fossil_core.storage_ports import ArtifactStorePort as LegacyArtifactStorePort
from fossil_core.storage_ports import EventStorePort as LegacyEventStorePort


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "events" / "v1.schema.json"


def test_legacy_storage_port_paths_alias_canonical_protocols():
    assert LegacyArtifactStorePort is ArtifactStorePort is BoundedArtifactStorePort
    assert LegacyEventStorePort is EventStorePort is BoundedEventStorePort
    assert ArtifactStorePort.__module__ == "fossil_core.ports.artifact_store"
    assert EventStorePort.__module__ == "fossil_core.ports.event_store"


def test_existing_filesystem_stores_satisfy_canonical_ports(tmp_path):
    artifact_store = ArtifactStore(tmp_path / "artifacts")
    event_store = DurableEventStore(tmp_path / "events", SCHEMA)

    assert isinstance(artifact_store, ArtifactStorePort)
    assert isinstance(event_store, EventStorePort)


def test_existing_s3_stores_satisfy_canonical_ports_without_remote_calls():
    inert_client = object()
    artifact_store = S3ArtifactStore(bucket="contract-only", client=inert_client)
    event_store = S3DurableEventStore(
        bucket="contract-only",
        schema_path=SCHEMA,
        client=inert_client,
    )

    assert isinstance(artifact_store, ArtifactStorePort)
    assert isinstance(event_store, EventStorePort)
