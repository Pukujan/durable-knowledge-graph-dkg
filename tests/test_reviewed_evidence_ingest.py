from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from fossil_core.application.ingest.pack_validation import KnowledgePackValidator
from fossil_core.application.ingest.reviewed_evidence import (
    ReviewedClaimDraft,
    ReviewedEvidenceIngestError,
    ReviewedEvidenceIngestService,
    ReviewedSource,
)
from fossil_core.artifact_store import ArtifactStore
from fossil_core.event_store import DurableEventStore
from fossil_core.source import SourceSnapshotStore


ROOT = Path(__file__).resolve().parents[1]
PACK = "pack_269099f7b2ba43b7a99b9427d64092de"


def _manifest(*, kind: str = "common") -> dict:
    return {
        "contract_version": "dkg.pack.v1",
        "pack_id": PACK,
        "name": "reviewed ingest fixture",
        "kind": kind,
        "schema_version": "dkg.event.v1",
        "dependencies": [],
        "read_mounts": [PACK],
        "write_targets": [PACK],
        "event_roots": ["events/"],
        "artifact_manifests": [],
        "placement_hint": "unspecified",
        "projection_namespace": "reviewed-ingest-fixture",
    }


def _service(tmp_path: Path) -> ReviewedEvidenceIngestService:
    artifact_store = ArtifactStore(tmp_path / "artifacts")
    source_store = SourceSnapshotStore(
        tmp_path / "sources",
        artifact_store,
        ROOT / "schemas" / "source-snapshot" / "v1.schema.json",
        ROOT / "schemas" / "citation" / "v1.schema.json",
    )
    event_store = DurableEventStore(
        tmp_path / "events", ROOT / "schemas" / "events" / "v1.schema.json"
    )
    pack_validator = KnowledgePackValidator(
        ROOT / "schemas" / "knowledge-pack" / "v1.schema.json"
    )
    return ReviewedEvidenceIngestService(
        source_store=source_store,
        event_store=event_store,
        pack_validator=pack_validator,
    )


def _source(*, source_kind: str = "research") -> ReviewedSource:
    return ReviewedSource(
        data=b"Primary research says durable event replay remains authoritative.\n",
        source_kind=source_kind,
        source_role="primary",
        locator={"identifier": "research-note-2026-08-19"},
        retrieved_at="2026-08-19T19:40:00Z",
        published_at="2026-08-19T19:35:00Z",
        media_type="text/plain",
        quality={
            "authority": 0.8,
            "directness": 1.0,
            "independence": 0.7,
            "reproducibility": 0.9,
            "timeliness": 1.0,
            "notes": "reviewed primary research fixture",
        },
    )


def _draft(index: int = 1) -> ReviewedClaimDraft:
    return ReviewedClaimDraft(
        subject_ref=f"clm_reviewed_ingest_{index:06d}",
        claim_text="Durable event replay remains the authority substrate.",
        reason="Reviewed research synthesis; proposal only pending promotion/review.",
    )


def test_reviewed_ingest_preserves_source_first_and_emits_proposals_with_compact_receipt(
    tmp_path: Path,
):
    service = _service(tmp_path)

    receipt = service.ingest(
        pack_manifest=_manifest(kind="common"),
        source=_source(),
        claims=[_draft(1), _draft(2)],
        review_ref="review:architecture:2026-08-19",
        actor={
            "actor_type": "importer",
            "actor_id": "reviewed-evidence-ingest",
            "harness_version": "fixture-v1",
            "skill_id": "skill_research-ingestion",
            "skill_version": "1.1.0",
        },
        occurred_at="2026-08-19T19:41:00Z",
        recorded_at="2026-08-19T19:41:01Z",
        correlation_id="reviewed-ingest-fixture-1",
    )

    assert receipt["schema_version"] == "fossil.reviewed-evidence-ingest-receipt.v1"
    assert receipt["status"] == "proposed"
    assert receipt["authority"] == "non_authoritative_receipt"
    assert receipt["pack_id"] == PACK
    assert receipt["source"]["preserved"] is True
    assert receipt["source"]["source_kind"] == "research"
    assert receipt["source"]["artifact_id"].startswith("art_")
    assert receipt["source"]["snapshot_id"].startswith("snap_")
    assert receipt["validation"] == {
        "pack": "passed",
        "source": "passed",
        "events": "passed",
        "provenance": "passed",
        "evidence": "passed",
        "ontology": "not_applicable",
    }
    assert receipt["proposal_count"] == 2
    assert receipt["accepted_count"] == 0
    assert receipt["requires_explicit_promotion"] is True
    assert receipt["review_ref"] == "review:architecture:2026-08-19"

    snapshots = list(service.source_store.iter_snapshots())
    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert service.source_store.artifact_store.read_bytes(snapshot["artifact_id"]) == _source().data

    events = list(service.event_store.iter_events())
    assert len(events) == 2
    assert {event["event_type"] for event in events} == {"claim.proposed"}
    assert {event["event_id"] for event in events} == set(receipt["proposal_event_ids"])
    for event in events:
        assert event["evidence_refs"] == [snapshot["artifact_id"]]
        assert event["source_snapshot_refs"] == [snapshot["snapshot_id"]]
        assert event["provenance"]["method"] == "reviewed_evidence_ingest"
        assert event["provenance"]["benchmark_ref"] == receipt["review_ref"]
        assert event["provenance"]["prompt_or_policy_ref"] == (
            "skills/research-ingestion/manifest.json"
        )
        assert "Primary research says" not in json.dumps(event["payload"])

    schema = json.loads(
        (ROOT / "schemas" / "reviewed-evidence-ingest" / "receipt-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(receipt)


def test_raw_ci_and_build_log_noise_is_rejected_before_canonical_preservation(tmp_path: Path):
    service = _service(tmp_path)

    for source_kind in ("raw_ci_log", "raw_build_log", "raw_runtime_log"):
        receipt = service.ingest(
            pack_manifest=_manifest(),
            source=_source(source_kind=source_kind),
            claims=[_draft()],
            review_ref="review:noise-filter",
            actor={"actor_type": "importer", "actor_id": "noise-filter"},
            occurred_at="2026-08-19T19:42:00Z",
            recorded_at="2026-08-19T19:42:01Z",
            correlation_id=f"noise:{source_kind}",
        )
        assert receipt["status"] == "rejected"
        assert receipt["rejection_reason"] == "raw_ci_or_log_noise_not_wholesale_ingestable"
        assert receipt["source"]["preserved"] is False
        assert receipt["proposal_count"] == 0
        assert receipt["accepted_count"] == 0

    assert list(service.source_store.iter_snapshots()) == []
    assert list(service.event_store.iter_events()) == []
    assert list((tmp_path / "artifacts").rglob("*.json")) == []


def test_reviewed_ingest_cannot_directly_accept_shared_or_architecture_knowledge(tmp_path: Path):
    service = _service(tmp_path)

    with pytest.raises(
        ReviewedEvidenceIngestError,
        match="accepted shared knowledge requires explicit review/promotion",
    ):
        service.ingest(
            pack_manifest=_manifest(kind="common"),
            source=_source(),
            claims=[_draft()],
            review_ref="review:architecture:accepted",
            actor={"actor_type": "human", "actor_id": "reviewer"},
            occurred_at="2026-08-19T19:43:00Z",
            recorded_at="2026-08-19T19:43:01Z",
            correlation_id="accepted-bypass",
            requested_outcome="accepted",
        )

    assert list(service.source_store.iter_snapshots()) == []
    assert list(service.event_store.iter_events()) == []


def test_pack_validation_happens_before_source_or_event_mutation(tmp_path: Path):
    service = _service(tmp_path)
    invalid_manifest = _manifest()
    invalid_manifest["read_mounts"] = []

    with pytest.raises(Exception, match="read itself"):
        service.ingest(
            pack_manifest=invalid_manifest,
            source=_source(),
            claims=[_draft()],
            review_ref="review:invalid-pack",
            actor={"actor_type": "importer", "actor_id": "reviewed-evidence-ingest"},
            occurred_at="2026-08-19T19:44:00Z",
            recorded_at="2026-08-19T19:44:01Z",
            correlation_id="invalid-pack",
        )

    assert list(service.source_store.iter_snapshots()) == []
    assert list(service.event_store.iter_events()) == []


def test_event_validation_occurs_before_any_proposal_commit_but_after_source_preservation(tmp_path: Path):
    service = _service(tmp_path)
    bad = ReviewedClaimDraft(
        subject_ref="",
        claim_text="This draft has no stable subject identity.",
        reason="adversarial fixture",
    )

    with pytest.raises(ReviewedEvidenceIngestError, match="stable subject_ref"):
        service.ingest(
            pack_manifest=_manifest(),
            source=_source(),
            claims=[_draft(1), bad],
            review_ref="review:bad-draft",
            actor={"actor_type": "importer", "actor_id": "reviewed-evidence-ingest"},
            occurred_at="2026-08-19T19:45:00Z",
            recorded_at="2026-08-19T19:45:01Z",
            correlation_id="bad-draft",
        )

    # Source-first durability is preserved, but the all-events validation pass
    # prevents a partial proposal batch from being committed.
    assert len(list(service.source_store.iter_snapshots())) == 1
    assert list(service.event_store.iter_events()) == []
