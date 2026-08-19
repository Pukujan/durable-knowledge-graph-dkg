from __future__ import annotations

from pathlib import Path

import pytest

import fossil_core.adapters.s3.storage as s3_storage
from fossil_core.domain.event_contracts import EventContractError
from fossil_core.s3_storage import S3ArtifactStore, S3DurableEventStore


ROOT = Path(__file__).parents[1]
SCHEMA = ROOT / "schemas/events/v1.schema.json"
PACK = "pack_269099f7b2ba43b7a99b9427d64092de"
SOURCE = "clm_s3_mutation_source_000001"
TARGET = "clm_s3_mutation_target_000001"
PROMOTION_SOURCE_PACK = "pack_f024177f89a5442db84171c3dd7f58e5"
PROMOTION_SOURCE_REVISION = "git:source@aaaaaaaa"
PROMOTION_SOURCE_EVENT = "evt_s3_mutation_promotion_source_0001"
PROMOTION_SUBJECT = "clm_s3_mutation_promotion_subject_0001"


def accepted_relation(*, source_type: str = "Claim") -> dict:
    return {
        "schema_version": "dkg.event.v1",
        "event_type": "relation.state_changed",
        "occurred_at": "2026-08-19T16:20:00Z",
        "recorded_at": "2026-08-19T16:20:01Z",
        "pack_id": PACK,
        "actor": {"actor_type": "system", "actor_id": "s3-mutation-oracle"},
        "subject_refs": ["rel_s3_mutation_000001"],
        "idempotency_key": "s3-mutation:accepted-relation",
        "payload": {
            "relation_id": "rel_s3_mutation_000001",
            "from_state": "proposed",
            "to_state": "active",
            "ontology_ref": "dkg.core@1.0.0",
            "relation_type": "DEPENDS_ON",
            "source_ref": SOURCE,
            "source_type": source_type,
            "target_ref": TARGET,
            "target_type": "Claim",
        },
        "provenance": {"method": "s3-mutation-oracle"},
    }


def promotion_event() -> dict:
    return {
        "schema_version": "dkg.event.v1",
        "event_type": "knowledge.promoted",
        "occurred_at": "2026-08-19T16:31:00Z",
        "recorded_at": "2026-08-19T16:31:01Z",
        "pack_id": PACK,
        "actor": {"actor_type": "system", "actor_id": "s3-mutation-oracle"},
        "subject_refs": [PROMOTION_SUBJECT],
        "idempotency_key": "s3-mutation:pinned-promotion",
        "evidence_refs": ["art_s3_mutation_promotion_evidence"],
        "payload": {
            "contract_version": "dkg.promotion.v2",
            "source_pack_id": PROMOTION_SOURCE_PACK,
            "source_pack_revision": PROMOTION_SOURCE_REVISION,
            "source_event_id": PROMOTION_SOURCE_EVENT,
            "target_pack_id": PACK,
            "reason": "reviewed reusable knowledge",
        },
        "provenance": {"method": "explicit_cross_pack_promotion"},
    }


def test_s3_store_default_prefixes_and_resolver_remain_empty():
    artifacts = S3ArtifactStore(bucket="fixture", client=object())
    events = S3DurableEventStore(
        bucket="fixture", schema_path=SCHEMA, client=object()
    )

    assert artifacts.backend.prefix == ""
    assert events.backend.prefix == ""
    assert events.endpoint_type_resolver is None
    assert events.promotion_source_resolver is None


def test_s3_event_store_preserves_exact_endpoint_resolver_identity():
    resolver = {SOURCE: "Claim", TARGET: "Claim"}.get
    events = S3DurableEventStore(
        bucket="fixture",
        schema_path=SCHEMA,
        client=object(),
        endpoint_type_resolver=resolver,
    )

    assert events.endpoint_type_resolver is resolver


def test_s3_promotion_source_resolver_is_retained_and_forwarded_before_provider_write():
    calls: list[tuple[str, str, str]] = []

    def resolver(pack_id: str, revision: str, event_id: str):
        calls.append((pack_id, revision, event_id))
        return None

    events = S3DurableEventStore(
        bucket="fixture",
        schema_path=SCHEMA,
        client=object(),
        promotion_source_resolver=resolver,
    )
    assert events.promotion_source_resolver is resolver

    with pytest.raises(EventContractError, match="not resolvable at the pinned source revision"):
        events.validate(promotion_event())
    assert calls == [
        (PROMOTION_SOURCE_PACK, PROMOTION_SOURCE_REVISION, PROMOTION_SOURCE_EVENT)
    ]

    calls.clear()
    with pytest.raises(EventContractError, match="not resolvable at the pinned source revision"):
        events.commit(promotion_event())
    assert calls == [
        (PROMOTION_SOURCE_PACK, PROMOTION_SOURCE_REVISION, PROMOTION_SOURCE_EVENT)
    ]


def test_s3_validate_forwards_endpoint_resolver_to_acceptance_gate():
    resolver = {SOURCE: "Claim", TARGET: "Claim"}.get
    events = S3DurableEventStore(
        bucket="fixture",
        schema_path=SCHEMA,
        client=object(),
        endpoint_type_resolver=resolver,
    )

    validated = events.validate(accepted_relation())
    assert validated["payload"]["source_type"] == "Claim"

    with pytest.raises(EventContractError, match="source_type.*does not match resolved"):
        events.validate(accepted_relation(source_type="Concept"))


def test_s3_commit_forwards_endpoint_resolver_before_any_provider_write():
    resolver = {SOURCE: "Claim", TARGET: "Claim"}.get
    events = S3DurableEventStore(
        bucket="fixture",
        schema_path=SCHEMA,
        client=object(),
        endpoint_type_resolver=resolver,
    )

    with pytest.raises(EventContractError, match="source_type.*does not match resolved"):
        events.commit(accepted_relation(source_type="Concept"))


def test_backend_slash_normalization_does_not_strip_valid_x_characters():
    backend = s3_storage._S3ObjectBackend(
        bucket="fixture", prefix="XproofX", client=object()
    )

    assert backend.prefix == "XproofX"
    assert backend.key("X/item") == "XproofX/X/item"


def test_s3_artifact_put_file_preserves_default_media_type(monkeypatch, tmp_path: Path):
    source = tmp_path / "artifact.bin"
    source.write_bytes(b"default media")
    store = S3ArtifactStore(bucket="fixture", client=object())
    captured: dict[str, object] = {}

    def fake_put_bytes(data: bytes, *, media_type: str):
        captured.update(data=data, media_type=media_type)
        return {"media_type": media_type}

    monkeypatch.setattr(store, "put_bytes", fake_put_bytes)

    assert store.put_file(source) == {"media_type": "application/octet-stream"}
    assert captured == {
        "data": b"default media",
        "media_type": "application/octet-stream",
    }
