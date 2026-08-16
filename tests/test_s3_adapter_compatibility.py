from __future__ import annotations

from pathlib import Path

import fossil_core.s3_storage as legacy_module
from fossil_core.adapters.s3 import (
    RemoteObjectConflict,
    RemoteStoreUnavailable,
    S3ArtifactStore,
    S3DurableEventStore,
)
from fossil_core.ports import ArtifactStorePort, EventStorePort
from fossil_core.s3_storage import (
    RemoteObjectConflict as LegacyRemoteObjectConflict,
    RemoteStoreUnavailable as LegacyRemoteStoreUnavailable,
    S3ArtifactStore as LegacyS3ArtifactStore,
    S3DurableEventStore as LegacyS3DurableEventStore,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "events" / "v1.schema.json"


def test_legacy_s3_paths_alias_canonical_adapter_objects():
    assert LegacyRemoteObjectConflict is RemoteObjectConflict
    assert LegacyRemoteStoreUnavailable is RemoteStoreUnavailable
    assert LegacyS3ArtifactStore is S3ArtifactStore
    assert LegacyS3DurableEventStore is S3DurableEventStore
    assert RemoteObjectConflict.__module__ == "fossil_core.adapters.s3.storage"
    assert RemoteStoreUnavailable.__module__ == "fossil_core.adapters.s3.storage"
    assert S3ArtifactStore.__module__ == "fossil_core.adapters.s3.storage"
    assert S3DurableEventStore.__module__ == "fossil_core.adapters.s3.storage"


def test_legacy_s3_all_surface_is_unchanged():
    assert legacy_module.__all__ == [
        "RemoteStoreUnavailable",
        "S3ArtifactStore",
        "S3DurableEventStore",
    ]
    assert legacy_module.RemoteObjectConflict is RemoteObjectConflict


def test_canonical_s3_adapters_still_satisfy_storage_ports_without_remote_calls():
    inert_client = object()
    artifact_store = S3ArtifactStore(bucket="contract-only", client=inert_client)
    event_store = S3DurableEventStore(
        bucket="contract-only",
        schema_path=SCHEMA,
        client=inert_client,
    )

    assert isinstance(artifact_store, ArtifactStorePort)
    assert isinstance(event_store, EventStorePort)
