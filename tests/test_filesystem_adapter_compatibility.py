from __future__ import annotations

from pathlib import Path

from fossil_core import (
    ArtifactIntegrityError as RootArtifactIntegrityError,
    ArtifactStore as RootArtifactStore,
    DurableEventStore as RootDurableEventStore,
    IdempotencyConflict as RootIdempotencyConflict,
)
from fossil_core.adapters.filesystem import (
    ArtifactIntegrityError,
    ArtifactRedactedError,
    ArtifactStore,
    DurableEventStore,
    EventRedactedError,
    EventRedactionConflict,
    IdempotencyConflict,
)
from fossil_core.artifact_store import (
    ArtifactIntegrityError as LegacyArtifactIntegrityError,
    ArtifactRedactedError as LegacyArtifactRedactedError,
    ArtifactStore as LegacyArtifactStore,
)
from fossil_core.event_store import (
    DurableEventStore as LegacyDurableEventStore,
    EventRedactedError as LegacyEventRedactedError,
    EventRedactionConflict as LegacyEventRedactionConflict,
    IdempotencyConflict as LegacyIdempotencyConflict,
)
from fossil_core.ports import ArtifactStorePort, EventStorePort


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "events" / "v1.schema.json"


def test_artifact_store_legacy_and_root_paths_alias_canonical_filesystem_adapter():
    assert LegacyArtifactStore is RootArtifactStore is ArtifactStore
    assert LegacyArtifactIntegrityError is RootArtifactIntegrityError is ArtifactIntegrityError
    assert LegacyArtifactRedactedError is ArtifactRedactedError
    assert ArtifactStore.__module__ == "fossil_core.adapters.filesystem.artifact_store"
    assert ArtifactIntegrityError.__module__ == "fossil_core.adapters.filesystem.artifact_store"
    assert ArtifactRedactedError.__module__ == "fossil_core.adapters.filesystem.artifact_store"


def test_event_store_legacy_and_root_paths_alias_canonical_filesystem_adapter():
    assert LegacyDurableEventStore is RootDurableEventStore is DurableEventStore
    assert LegacyIdempotencyConflict is RootIdempotencyConflict is IdempotencyConflict
    assert LegacyEventRedactedError is EventRedactedError
    assert LegacyEventRedactionConflict is EventRedactionConflict
    assert DurableEventStore.__module__ == "fossil_core.adapters.filesystem.event_store"
    assert IdempotencyConflict.__module__ == "fossil_core.adapters.filesystem.event_store"
    assert EventRedactedError.__module__ == "fossil_core.adapters.filesystem.event_store"
    assert EventRedactionConflict.__module__ == "fossil_core.adapters.filesystem.event_store"


def test_canonical_filesystem_adapters_still_satisfy_storage_ports(tmp_path):
    artifact_store = ArtifactStore(tmp_path / "artifacts")
    event_store = DurableEventStore(tmp_path / "events", SCHEMA)

    assert isinstance(artifact_store, ArtifactStorePort)
    assert isinstance(event_store, EventStorePort)
