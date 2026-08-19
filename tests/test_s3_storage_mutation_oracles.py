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


def test_s3_store_default_prefixes_and_resolver_remain_empty():
    artifacts = S3ArtifactStore(bucket="fixture", client=object())
    events = S3DurableEventStore(
        bucket="fixture", schema_path=SCHEMA, client=object()
    )

    assert artifacts.backend.prefix == ""
    assert events.backend.prefix == ""
    assert events.endpoint_type_resolver is None


def test_s3_event_store_preserves_exact_endpoint_resolver_identity():
    resolver = {SOURCE: "Claim", TARGET: "Claim"}.get
    events = S3DurableEventStore(
        bucket="fixture",
        schema_path=SCHEMA,
        client=object(),
        endpoint_type_resolver=resolver,
    )

    assert events.endpoint_type_resolver is resolver


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
