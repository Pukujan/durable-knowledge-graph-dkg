from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from dkg.artifact_store import ArtifactRedactedError, ArtifactStore
from dkg.event_store import DurableEventStore
from dkg.projection.graphiti import GraphitiProjectionAdapter
from dkg.projection.ledger import ProjectionLedger
from dkg.source import (
    CitationIntegrityError,
    CitationLaunderingError,
    RedactionPolicy,
    SourceLifecycleState,
    SourceSnapshotStore,
    build_redaction_event,
    build_source_state_event,
)


COMMON = "pack_269099f7b2ba43b7a99b9427d64092de"


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def source_store(tmp_path: Path) -> SourceSnapshotStore:
    return SourceSnapshotStore(
        tmp_path / "sources",
        ArtifactStore(tmp_path / "artifacts"),
        root() / "schemas" / "source-snapshot" / "v1.schema.json",
        root() / "schemas" / "citation" / "v1.schema.json",
    )


def quality(**overrides):
    return {
        "authority": 0.9,
        "directness": 1.0,
        "independence": 0.8,
        "reproducibility": 0.7,
        "timeliness": 0.95,
        "notes": "fixture dimensions are independent, not one source tier",
        **overrides,
    }


def actor():
    return {"actor_type": "system", "actor_id": "source-fixture"}


def test_source_snapshot_records_locator_times_hash_version_and_quality_dimensions(tmp_path):
    store = source_store(tmp_path)
    data = b"Versioned primary source with exact evidence."
    snapshot = store.put_snapshot(
        data,
        locator={"url": "https://example.test/source"},
        retrieved_at="2026-08-09T23:30:00Z",
        published_at="2026-08-01T12:00:00Z",
        source_role="primary",
        quality=quality(),
        version_metadata={
            "etag": '"v1"',
            "last_modified": "Fri, 01 Aug 2026 12:00:00 GMT",
            "version_id": "source-v1",
        },
        media_type="text/plain",
    )

    assert snapshot["locator"]["url"] == "https://example.test/source"
    assert snapshot["retrieved_at"] == "2026-08-09T23:30:00Z"
    assert snapshot["published_at"] == "2026-08-01T12:00:00Z"
    assert snapshot["content_hash"]["digest"] == hashlib.sha256(data).hexdigest()
    assert snapshot["version_metadata"]["etag"] == '"v1"'
    assert set(snapshot["quality"]) >= {
        "authority",
        "directness",
        "independence",
        "reproducibility",
        "timeliness",
    }
    assert "quality_tier" not in snapshot
    assert store.artifact_store.verify(snapshot["artifact_id"])

    with pytest.raises(ValueError, match="non-empty URL, identifier, or repository_ref"):
        store.put_snapshot(
            b"orphan",
            locator={},
            retrieved_at="2026-08-09T23:31:00Z",
            source_role="primary",
            quality=quality(),
        )


def test_mutable_source_snapshots_coexist_historically(tmp_path):
    store = source_store(tmp_path)
    locator = {"url": "https://example.test/mutable"}
    first = store.put_snapshot(
        b"Mutable source version one",
        locator=locator,
        retrieved_at="2026-08-09T23:32:00Z",
        source_role="primary",
        quality=quality(timeliness=0.8),
        version_metadata={"etag": '"one"'},
        media_type="text/plain",
    )
    second = store.put_snapshot(
        b"Mutable source version two",
        locator=locator,
        retrieved_at="2026-08-10T00:32:00Z",
        source_role="primary",
        quality=quality(timeliness=1.0),
        version_metadata={"etag": '"two"'},
        media_type="text/plain",
    )

    assert first["source_id"] == second["source_id"]
    assert first["snapshot_id"] != second["snapshot_id"]
    versions = store.versions(first["source_id"])
    assert [item["snapshot_id"] for item in versions] == [
        first["snapshot_id"],
        second["snapshot_id"],
    ]
    assert store.artifact_store.read_bytes(first["artifact_id"]) == b"Mutable source version one"
    assert store.artifact_store.read_bytes(second["artifact_id"]) == b"Mutable source version two"


def test_exact_passage_citation_resolves_snapshot_bytes_and_detects_mismatch(tmp_path):
    store = source_store(tmp_path)
    data = b"prefix | exact cited passage | suffix"
    snapshot = store.put_snapshot(
        data,
        locator={"identifier": "fixture:exact-passage"},
        retrieved_at="2026-08-09T23:33:00Z",
        source_role="local",
        quality=quality(),
        media_type="text/plain",
    )
    target = b"exact cited passage"
    start = data.index(target)
    citation = store.create_citation(
        snapshot["snapshot_id"], byte_start=start, byte_end=start + len(target)
    )
    resolved = store.resolve_citation(citation)

    assert resolved["bytes"] == target
    assert resolved["text"] == "exact cited passage"
    assert citation["passage_hash"]["digest"] == hashlib.sha256(target).hexdigest()

    other = store.put_snapshot(
        b"different source bytes",
        locator={"identifier": "fixture:other"},
        retrieved_at="2026-08-09T23:34:00Z",
        source_role="local",
        quality=quality(),
    )
    forged = dict(citation)
    forged["artifact_id"] = other["artifact_id"]
    with pytest.raises(CitationIntegrityError, match="does not match"):
        store.resolve_citation(forged)


def test_derived_summary_cannot_masquerade_as_primary_citation(tmp_path):
    store = source_store(tmp_path)
    primary = store.put_snapshot(
        b"Primary measurement: 42.",
        locator={"url": "https://example.test/measurement"},
        retrieved_at="2026-08-09T23:35:00Z",
        source_role="primary",
        quality=quality(authority=1.0, directness=1.0),
        media_type="text/plain",
    )
    derived = store.put_snapshot(
        b"Summary says the measurement was 42.",
        locator={"identifier": "summary:measurement"},
        retrieved_at="2026-08-09T23:36:00Z",
        source_role="derived",
        quality=quality(directness=0.4, independence=0.1),
        derivation={
            "method": "human-summary",
            "parent_snapshot_refs": [primary["snapshot_id"]],
        },
        media_type="text/plain",
    )

    primary_citation = store.create_citation(primary["snapshot_id"])
    derived_citation = store.create_citation(derived["snapshot_id"])
    assert store.resolve_citation(
        primary_citation, allowed_source_roles={"primary"}
    )["snapshot"]["source_role"] == "primary"
    with pytest.raises(CitationLaunderingError, match="cannot satisfy"):
        store.resolve_citation(derived_citation, allowed_source_roles={"primary"})

    with pytest.raises(ValueError, match="requires explicit parent_snapshot_refs"):
        store.put_snapshot(
            b"untraceable summary",
            locator={"identifier": "summary:untraceable"},
            retrieved_at="2026-08-09T23:37:00Z",
            source_role="derived",
            quality=quality(),
        )


def test_source_stale_retracted_and_restored_are_explicit_replayable_events(tmp_path):
    snapshots = source_store(tmp_path)
    snapshot = snapshots.put_snapshot(
        b"source lifecycle fixture",
        locator={"repository_ref": "repo@example:docs/source.md"},
        retrieved_at="2026-08-09T23:38:00Z",
        source_role="local",
        quality=quality(),
    )
    events = DurableEventStore(
        tmp_path / "events", root() / "schemas" / "events" / "v1.schema.json"
    )
    lifecycle = []
    for sequence, event_type in enumerate(
        ("source.stale", "source.retracted", "source.restored"), start=1
    ):
        event = build_source_state_event(
            event_type=event_type,
            snapshot_id=snapshot["snapshot_id"],
            source_id=snapshot["source_id"],
            pack_id=COMMON,
            actor=actor(),
            occurred_at=f"2026-08-09T23:4{sequence}:00Z",
            recorded_at=f"2026-08-09T23:4{sequence}:00Z",
            idempotency_key=f"source-lifecycle-{sequence}",
            reason=event_type,
        )
        lifecycle.append(events.commit(event))

    assert SourceLifecycleState.replay(lifecycle[:1]).status(snapshot["snapshot_id"]) == "stale"
    assert SourceLifecycleState.replay(lifecycle[:2]).status(snapshot["snapshot_id"]) == "retracted"
    final = SourceLifecycleState.replay(reversed(lifecycle))
    assert final.status(snapshot["snapshot_id"]) == "active"


def test_redaction_writes_tombstone_then_removes_bytes_and_blocks_rehydration(tmp_path):
    store = source_store(tmp_path)
    secret = b"private evidence that must be deletable"
    snapshot = store.put_snapshot(
        secret,
        locator={"identifier": "private:fixture"},
        retrieved_at="2026-08-09T23:45:00Z",
        source_role="local",
        quality=quality(),
        media_type="text/plain",
    )
    artifact_id = snapshot["artifact_id"]
    assert store.artifact_store.read_bytes(artifact_id) == secret

    tombstone = store.artifact_store.redact(
        artifact_id,
        reason="privacy deletion request",
        authority="fixture-data-controller",
        redacted_at="2026-08-09T23:46:00Z",
        request_ref="privacy-request-001",
    )
    assert tombstone["artifact_id"] == artifact_id
    assert store.artifact_store.get_manifest(artifact_id)["content_hash"] == tombstone["content_hash"]
    assert store.artifact_store.is_redacted(artifact_id)
    with pytest.raises(ArtifactRedactedError):
        store.artifact_store.read_bytes(artifact_id)
    with pytest.raises(ArtifactRedactedError, match="cannot be republished"):
        store.artifact_store.put_bytes(secret)

    assert store.artifact_store.redact(
        artifact_id,
        reason="privacy deletion request",
        authority="fixture-data-controller",
        redacted_at="2026-08-09T23:46:00Z",
        request_ref="privacy-request-001",
    ) == tombstone

    exported = store.export_snapshot(snapshot["snapshot_id"])
    assert exported["redacted"] is True
    assert exported["content"] is None
    assert exported["redaction"]["request_ref"] == "privacy-request-001"


def test_redaction_event_is_durable_and_exports_hide_affected_knowledge(tmp_path):
    snapshots = source_store(tmp_path)
    snapshot = snapshots.put_snapshot(
        b"sensitive cited source",
        locator={"identifier": "sensitive:source"},
        retrieved_at="2026-08-09T23:47:00Z",
        source_role="local",
        quality=quality(),
    )
    event_store = DurableEventStore(
        tmp_path / "events", root() / "schemas" / "events" / "v1.schema.json"
    )
    knowledge = event_store.commit(
        {
            "schema_version": "dkg.event.v1",
            "event_type": "claim.proposed",
            "occurred_at": "2026-08-09T23:48:00Z",
            "recorded_at": "2026-08-09T23:48:00Z",
            "pack_id": COMMON,
            "actor": actor(),
            "subject_refs": ["clm_sensitive_fixture"],
            "idempotency_key": "sensitive-fixture-v1",
            "evidence_refs": [snapshot["artifact_id"]],
            "source_snapshot_refs": [snapshot["snapshot_id"]],
            "payload": {"claim_text": "sensitive fixture claim"},
        }
    )
    policy = RedactionPolicy(snapshots)
    assert policy.export_event(knowledge) == knowledge

    tombstone = snapshots.artifact_store.redact(
        snapshot["artifact_id"],
        reason="legal deletion",
        authority="fixture-privacy-officer",
        redacted_at="2026-08-09T23:49:00Z",
        request_ref="legal-erase-7",
    )
    redaction_event = event_store.commit(
        build_redaction_event(
            tombstone=tombstone,
            pack_id=COMMON,
            actor=actor(),
            occurred_at="2026-08-09T23:49:00Z",
            recorded_at="2026-08-09T23:49:00Z",
            idempotency_key="redaction-sensitive-fixture-v1",
            snapshot_ids=[snapshot["snapshot_id"]],
        )
    )

    assert redaction_event["event_type"] == "evidence.redacted"
    assert redaction_event["payload"]["artifact_id"] == snapshot["artifact_id"]
    assert policy.export_event(knowledge) is None
    assert policy.event_visible(redaction_event) is True


class FakeGraphitiRedaction:
    def __init__(self):
        self.add_calls: list[dict] = []
        self.remove_calls: list[str] = []

    async def add_episode(self, **kwargs):
        self.add_calls.append(kwargs)
        return SimpleNamespace(episode=SimpleNamespace(uuid="episode-sensitive-001"))

    async def remove_episode(self, episode_uuid: str):
        self.remove_calls.append(episode_uuid)


async def _active_projection_redaction(tmp_path: Path):
    snapshots = source_store(tmp_path)
    snapshot = snapshots.put_snapshot(
        b"projection-sensitive source",
        locator={"identifier": "projection:sensitive"},
        retrieved_at="2026-08-09T23:50:00Z",
        source_role="local",
        quality=quality(),
    )
    events = DurableEventStore(
        tmp_path / "events", root() / "schemas" / "events" / "v1.schema.json"
    )
    knowledge = events.commit(
        {
            "schema_version": "dkg.event.v1",
            "event_type": "claim.proposed",
            "occurred_at": "2026-08-09T23:51:00Z",
            "recorded_at": "2026-08-09T23:51:00Z",
            "pack_id": COMMON,
            "actor": actor(),
            "subject_refs": ["clm_projection_sensitive"],
            "idempotency_key": "projection-sensitive-v1",
            "evidence_refs": [snapshot["artifact_id"]],
            "source_snapshot_refs": [snapshot["snapshot_id"]],
            "payload": {"claim_text": "projection sensitive claim"},
        }
    )
    policy = RedactionPolicy(snapshots)
    client = FakeGraphitiRedaction()
    ledger = ProjectionLedger(tmp_path / "ledger", "graphiti-neo4j", build_id="active-a")
    adapter = GraphitiProjectionAdapter(
        client=client,
        ledger=ledger,
        build_manifest={"projection_build_id": "active-a"},
        episode_type_json="json",
        visibility_policy=policy,
    )

    first = await adapter.apply_event_async(knowledge)
    assert first.status == "applied"
    applied = ledger.get_applied(knowledge["event_id"])
    assert applied["episode_uuid"] == "episode-sensitive-001"

    snapshots.artifact_store.redact(
        snapshot["artifact_id"],
        reason="projection redaction fixture",
        authority="fixture",
        redacted_at="2026-08-09T23:52:00Z",
    )
    purged = await adapter.purge_redacted_async(events_root=events.root)
    assert [receipt.status for receipt in purged] == ["redacted"]
    assert client.remove_calls == ["episode-sensitive-001"]
    assert ledger.is_redacted(knowledge["event_id"])
    assert ledger.get_applied(knowledge["event_id"]) is not None

    retry = await adapter.apply_event_async(knowledge)
    assert retry.status == "skipped"
    assert retry.detail == "projection redacted"
    assert len(client.add_calls) == 1

    fresh_client = FakeGraphitiRedaction()
    fresh = GraphitiProjectionAdapter(
        client=fresh_client,
        ledger=ProjectionLedger(
            tmp_path / "ledger", "graphiti-neo4j", build_id="redaction-aware-rebuild"
        ),
        build_manifest={"projection_build_id": "redaction-aware-rebuild"},
        episode_type_json="json",
        visibility_policy=policy,
    )
    receipts = await fresh.rebuild_async(events_root=events.root)
    assert [receipt.status for receipt in receipts] == ["redacted"]
    assert fresh_client.add_calls == []


def test_active_projection_is_purged_and_redacted_event_is_not_rebuilt(tmp_path):
    asyncio.run(_active_projection_redaction(tmp_path))


def test_old_projection_receipt_without_episode_uuid_requires_safe_rebuild(tmp_path):
    ledger = ProjectionLedger(tmp_path / "ledger", "graphiti-neo4j", build_id="legacy")
    event_id = "evt_00000000000000000000000000000099"
    ledger.record_applied(event_id, {"group_id": COMMON, "episode_name": "legacy"})
    adapter = GraphitiProjectionAdapter(
        client=FakeGraphitiRedaction(),
        ledger=ledger,
        build_manifest={"projection_build_id": "legacy"},
        episode_type_json="json",
    )
    receipt = asyncio.run(adapter.remove_event_async(event_id))
    assert receipt.status == "failed"
    assert "rebuild required" in receipt.detail
    assert ledger.is_redacted(event_id) is False
