from __future__ import annotations

import json
from pathlib import Path

from dkg.pack_corpus import retrieval_documents_from_pack_fixtures


COMMON = "pack_269099f7b2ba43b7a99b9427d64092de"
AI = "pack_f024177f89a5442db84171c3dd7f58e5"


def _write_event(root: Path, event: dict) -> None:
    event_id = str(event["event_id"])
    suffix = event_id.removeprefix("evt_")
    path = root / "events" / suffix[:2] / f"{event_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(event), encoding="utf-8")


def _event(
    *,
    event_id: str,
    event_type: str,
    pack_id: str,
    subject_refs: list[str],
    payload: dict,
    recorded_at: str,
) -> dict:
    return {
        "schema_version": "dkg.event.v1",
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": recorded_at,
        "recorded_at": recorded_at,
        "pack_id": pack_id,
        "actor": {"actor_type": "importer", "actor_id": "test"},
        "subject_refs": subject_refs,
        "payload": payload,
    }


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    common = tmp_path / "common"
    ai = tmp_path / "ai"
    for root, manifest in (
        (
            common,
            {
                "pack_id": COMMON,
                "event_roots": ["events"],
            },
        ),
        (
            ai,
            {
                "pack_id": AI,
                "event_roots": ["events"],
            },
        ),
    ):
        root.mkdir(parents=True)
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    common_claim = "clm_common_model_evidence_000001"
    common_citation = {
        "schema_version": "fossil.citation.v1",
        "citation_id": "cite_common_000001",
        "snapshot_id": "snap_common_000001",
        "artifact_id": "art_common_000000000001",
        "byte_start": 0,
        "byte_end": 41,
        "passage_hash": {"algorithm": "sha256", "digest": "0" * 64},
    }
    _write_event(
        common,
        _event(
            event_id="evt_common_proposed_000001",
            event_type="claim.proposed",
            pack_id=COMMON,
            subject_refs=[common_claim],
            payload={
                "claim_text": "Model agreement is not external evidence.",
                "citation": common_citation,
            },
            recorded_at="2026-08-10T05:20:00Z",
        ),
    )
    _write_event(
        common,
        _event(
            event_id="evt_common_supported_00001",
            event_type="claim.state_changed",
            pack_id=COMMON,
            subject_refs=[common_claim],
            payload={"from_state": "proposed", "to_state": "supported"},
            recorded_at="2026-08-10T05:20:01Z",
        ),
    )

    ai_claim = "clm_ai_candidate_authority_000001"
    ai_citation = {
        "schema_version": "fossil.citation.v1",
        "citation_id": "cite_ai_000000001",
        "snapshot_id": "snap_ai_000000001",
        "artifact_id": "art_ai_000000000000001",
        "byte_start": 0,
        "byte_end": 64,
        "passage_hash": {"algorithm": "sha256", "digest": "1" * 64},
    }
    _write_event(
        ai,
        _event(
            event_id="evt_ai_proposed_000000001",
            event_type="claim.proposed",
            pack_id=AI,
            subject_refs=[ai_claim],
            payload={
                "claim_text": "Candidate authority comes from evidence and risk policy.",
                "citation": ai_citation,
            },
            recorded_at="2026-08-10T05:20:02Z",
        ),
    )
    _write_event(
        ai,
        _event(
            event_id="evt_ai_supported_00000001",
            event_type="claim.state_changed",
            pack_id=AI,
            subject_refs=[ai_claim],
            payload={"from_state": "proposed", "to_state": "supported"},
            recorded_at="2026-08-10T05:20:03Z",
        ),
    )
    relation_id = "rel_ai_depends_common_000001"
    _write_event(
        ai,
        _event(
            event_id="evt_ai_relation_000000001",
            event_type="relation.proposed",
            pack_id=AI,
            subject_refs=[relation_id, ai_claim, common_claim],
            payload={
                "relation_id": relation_id,
                "relation_type": "DEPENDS_ON",
                "source_ref": ai_claim,
                "target_ref": common_claim,
                "state": "active",
            },
            recorded_at="2026-08-10T05:20:04Z",
        ),
    )
    return common, ai


def test_pack_projection_preserves_claim_state_history_and_citation(tmp_path, monkeypatch):
    common, ai = _fixture(tmp_path)
    monkeypatch.setattr("dkg.pack_corpus.validate_pack_fixtures", lambda *args, **kwargs: None)

    documents = retrieval_documents_from_pack_fixtures(
        [common, ai],
        schemas_root=tmp_path / "schemas",
    )
    claims = {document["id"]: document for document in documents if document["document_type"] == "claim"}

    common_claim = claims["clm_common_model_evidence_000001"]
    assert common_claim["pack_id"] == COMMON
    assert common_claim["current_state"] == "supported"
    assert common_claim["state_history"] == ["proposed", "supported"]
    assert common_claim["citation"]["citation_id"] == "cite_common_000001"

    ai_claim = claims["clm_ai_candidate_authority_000001"]
    assert ai_claim["pack_id"] == AI
    assert ai_claim["current_state"] == "supported"
    assert ai_claim["citation"]["citation_id"] == "cite_ai_000000001"


def test_pack_projection_materializes_cross_pack_relation_with_durable_identity(tmp_path, monkeypatch):
    common, ai = _fixture(tmp_path)
    monkeypatch.setattr("dkg.pack_corpus.validate_pack_fixtures", lambda *args, **kwargs: None)

    documents = retrieval_documents_from_pack_fixtures(
        [ai, common],
        schemas_root=tmp_path / "schemas",
    )
    relations = [document for document in documents if document["document_type"] == "relation"]

    assert len(relations) == 1
    relation = relations[0]
    assert relation["id"] == "rel_ai_depends_common_000001"
    assert relation["pack_id"] == AI
    assert relation["relation_type"] == "DEPENDS_ON"
    assert relation["current_state"] == "active"
    assert relation["state_history"] == ["active"]
    assert "Candidate authority comes from evidence and risk policy." in relation["text"]
    assert "Model agreement is not external evidence." in relation["text"]
