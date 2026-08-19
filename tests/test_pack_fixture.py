from __future__ import annotations

import json
from pathlib import Path

import pytest

from fossil_core.artifact_store import ArtifactStore
from fossil_core.event_store import DurableEventStore
from fossil_core.pack_fixture import PackFixtureIntegrityError, validate_pack_fixtures
from fossil_core.source import SourceSnapshotStore


COMMON = "pack_269099f7b2ba43b7a99b9427d64092de"
AI = "pack_f024177f89a5442db84171c3dd7f58e5"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def schemas_root() -> Path:
    return repo_root() / "schemas"


def write_pack_manifest(
    root: Path,
    *,
    pack_id: str,
    name: str,
    kind: str,
    read_mounts: list[str],
    write_targets: list[str],
    dependencies: list[dict] | None = None,
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "contract_version": "dkg.pack.v1",
        "pack_id": pack_id,
        "name": name,
        "kind": kind,
        "schema_version": "1.0.0",
        "dependencies": dependencies or [],
        "read_mounts": read_mounts,
        "write_targets": write_targets,
        "event_roots": ["events"],
        "artifact_manifests": ["artifacts/manifest.jsonl"],
        "placement_hint": "unspecified",
        "projection_namespace": pack_id,
        "source_policy_ref": None,
        "created_at": "2026-08-10T05:00:00Z",
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (root / "events").mkdir(parents=True, exist_ok=True)
    (root / "artifacts").mkdir(parents=True, exist_ok=True)
    (root / "artifacts" / "manifest.jsonl").write_text("", encoding="utf-8")


def source_store(root: Path) -> SourceSnapshotStore:
    artifacts = ArtifactStore(root / "artifacts")
    return SourceSnapshotStore(
        root / "sources",
        artifacts,
        schemas_root() / "source-snapshot" / "v1.schema.json",
        schemas_root() / "citation" / "v1.schema.json",
    )


def put_source(root: Path, *, text: str, ref: str, retrieved_at: str):
    store = source_store(root)
    snapshot = store.put_snapshot(
        text.encode("utf-8"),
        locator={"repository_ref": ref},
        retrieved_at=retrieved_at,
        source_role="local",
        quality={
            "authority": None,
            "directness": None,
            "independence": None,
            "reproducibility": None,
            "timeliness": None,
            "notes": "fixture quality remains claim-specific",
        },
        version_metadata={"commit_sha": "a" * 40},
        media_type="text/plain",
    )
    citation = store.create_citation(
        snapshot["snapshot_id"],
        byte_start=0,
        byte_end=len(text.encode("utf-8")),
    )
    return snapshot, citation


def write_artifact_index(root: Path) -> None:
    manifests = []
    for path in sorted((root / "artifacts" / "manifests").glob("*/*.json")):
        manifests.append(json.loads(path.read_text(encoding="utf-8")))
    content = "".join(
        json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n"
        for item in manifests
    )
    (root / "artifacts" / "manifest.jsonl").write_text(content, encoding="utf-8")


def event_store(root: Path) -> DurableEventStore:
    return DurableEventStore(root / "events", schemas_root() / "events" / "v1.schema.json")


def claim_event(
    *,
    pack_id: str,
    claim_id: str,
    event_type: str,
    key: str,
    recorded_at: str,
    citation: dict,
    artifact_id: str,
    snapshot_id: str,
    from_state: str | None = None,
    caused_by: list[str] | None = None,
) -> dict:
    payload = {"citation": citation}
    if event_type == "claim.proposed":
        payload["claim_text"] = f"fixture claim {claim_id}"
    else:
        payload.update({"from_state": from_state, "to_state": "supported"})
    return {
        "schema_version": "dkg.event.v1",
        "event_type": event_type,
        "occurred_at": recorded_at,
        "recorded_at": recorded_at,
        "pack_id": pack_id,
        "actor": {"actor_type": "importer", "actor_id": "fixture"},
        "subject_refs": [claim_id],
        "caused_by_event_ids": caused_by or [],
        "idempotency_key": key,
        "evidence_refs": [artifact_id],
        "source_snapshot_refs": [snapshot_id],
        "payload": payload,
        "provenance": {"method": "fixture"},
    }


def build_two_pack_fixture(tmp_path: Path):
    common = tmp_path / "common"
    ai = tmp_path / "ai"
    write_pack_manifest(
        common,
        pack_id=COMMON,
        name="common",
        kind="common",
        read_mounts=[COMMON],
        write_targets=[COMMON],
    )
    write_pack_manifest(
        ai,
        pack_id=AI,
        name="ai-systems",
        kind="domain",
        read_mounts=[COMMON, AI],
        write_targets=[AI],
        dependencies=[{"pack_id": COMMON, "required": True, "reason": "shared rules"}],
    )

    common_snapshot, common_citation = put_source(
        common,
        text="Model agreement is not external evidence.",
        ref="Pukujan/fossil-core@" + "a" * 40 + ":policies/source-quality-v1.md",
        retrieved_at="2026-08-10T05:01:00Z",
    )
    ai_snapshot, ai_citation = put_source(
        ai,
        text="Candidate authority comes from the separate evidence and risk policy.",
        ref="Pukujan/fossil-core@" + "a" * 40 + ":docs/proof.md",
        retrieved_at="2026-08-10T05:01:01Z",
    )
    write_artifact_index(common)
    write_artifact_index(ai)

    common_claim = "clm_common_model_evidence_000001"
    common_store = event_store(common)
    proposed_common = common_store.commit(
        claim_event(
            pack_id=COMMON,
            claim_id=common_claim,
            event_type="claim.proposed",
            key="common:proposed",
            recorded_at="2026-08-10T05:02:00Z",
            citation=common_citation,
            artifact_id=common_snapshot["artifact_id"],
            snapshot_id=common_snapshot["snapshot_id"],
        )
    )
    common_store.commit(
        claim_event(
            pack_id=COMMON,
            claim_id=common_claim,
            event_type="claim.state_changed",
            key="common:supported",
            recorded_at="2026-08-10T05:02:01Z",
            citation=common_citation,
            artifact_id=common_snapshot["artifact_id"],
            snapshot_id=common_snapshot["snapshot_id"],
            from_state="proposed",
            caused_by=[proposed_common["event_id"]],
        )
    )

    ai_claim = "clm_ai_candidate_authority_000001"
    ai_store = event_store(ai)
    proposed_ai = ai_store.commit(
        claim_event(
            pack_id=AI,
            claim_id=ai_claim,
            event_type="claim.proposed",
            key="ai:proposed",
            recorded_at="2026-08-10T05:02:02Z",
            citation=ai_citation,
            artifact_id=ai_snapshot["artifact_id"],
            snapshot_id=ai_snapshot["snapshot_id"],
        )
    )
    ai_store.commit(
        claim_event(
            pack_id=AI,
            claim_id=ai_claim,
            event_type="claim.state_changed",
            key="ai:supported",
            recorded_at="2026-08-10T05:02:03Z",
            citation=ai_citation,
            artifact_id=ai_snapshot["artifact_id"],
            snapshot_id=ai_snapshot["snapshot_id"],
            from_state="proposed",
            caused_by=[proposed_ai["event_id"]],
        )
    )
    relation_id = "rel_ai_depends_common_000001"
    relation = ai_store.commit(
        {
            "schema_version": "dkg.event.v1",
            "event_type": "relation.proposed",
            "occurred_at": "2026-08-10T05:02:04Z",
            "recorded_at": "2026-08-10T05:02:04Z",
            "pack_id": AI,
            "actor": {"actor_type": "importer", "actor_id": "fixture"},
            "subject_refs": [relation_id, ai_claim, common_claim],
            "caused_by_event_ids": [proposed_ai["event_id"]],
            "idempotency_key": "ai:depends-common",
            "evidence_refs": [ai_snapshot["artifact_id"], common_snapshot["artifact_id"]],
            "source_snapshot_refs": [
                ai_snapshot["snapshot_id"],
                common_snapshot["snapshot_id"],
            ],
            "payload": {
                "relation_id": relation_id,
                "relation_type": "DEPENDS_ON",
                "source_ref": ai_claim,
                "target_ref": common_claim,
                "state": "proposed",
            },
            "provenance": {"method": "fixture"},
        }
    )
    ai_store.commit(
        {
            "schema_version": "dkg.event.v1",
            "event_type": "relation.state_changed",
            "occurred_at": "2026-08-10T05:02:05Z",
            "recorded_at": "2026-08-10T05:02:05Z",
            "pack_id": AI,
            "actor": {"actor_type": "importer", "actor_id": "fixture"},
            "subject_refs": [relation_id, ai_claim, common_claim],
            "caused_by_event_ids": [relation["event_id"]],
            "idempotency_key": "ai:depends-common:active",
            "evidence_refs": [ai_snapshot["artifact_id"], common_snapshot["artifact_id"]],
            "source_snapshot_refs": [
                ai_snapshot["snapshot_id"],
                common_snapshot["snapshot_id"],
            ],
            "payload": {
                "relation_id": relation_id,
                "from_state": "proposed",
                "to_state": "active",
                "ontology_ref": "dkg.core@1.0.0",
                "relation_type": "DEPENDS_ON",
                "source_ref": ai_claim,
                "source_type": "Claim",
                "target_ref": common_claim,
                "target_type": "Claim",
            },
            "provenance": {"method": "fixture"},
        }
    )
    return {
        "common": common,
        "ai": ai,
        "common_snapshot": common_snapshot,
        "common_citation": common_citation,
        "ai_snapshot": ai_snapshot,
        "ai_citation": ai_citation,
        "relation": relation,
    }


def test_pack_fixture_audit_validates_content_identity_citations_mounts_and_replay(tmp_path):
    fixture = build_two_pack_fixture(tmp_path)

    report = validate_pack_fixtures(
        [fixture["common"], fixture["ai"]],
        schemas_root=schemas_root(),
    )

    assert report.pack_ids == (COMMON, AI)
    assert report.artifact_count == 2
    assert report.snapshot_count == 2
    assert report.event_count == 6
    assert report.citation_count == 4
    assert report.claim_count == 2
    assert report.relation_count == 1


def test_pack_fixture_audit_rejects_cross_pack_reference_without_read_mount(tmp_path):
    fixture = build_two_pack_fixture(tmp_path)
    manifest_path = fixture["ai"] / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["dependencies"] = []
    manifest["read_mounts"] = [AI]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(PackFixtureIntegrityError, match="not mounted"):
        validate_pack_fixtures(
            [fixture["common"], fixture["ai"]],
            schemas_root=schemas_root(),
        )


def test_pack_fixture_audit_rejects_corrupted_artifact_bytes(tmp_path):
    fixture = build_two_pack_fixture(tmp_path)
    artifact = fixture["common_snapshot"]["artifact_id"]
    digest = fixture["common_snapshot"]["content_hash"]["digest"]
    blob = fixture["common"] / "artifacts" / "blobs" / "sha256" / digest[:2] / digest
    blob.write_bytes(b"corrupted source bytes")

    with pytest.raises(PackFixtureIntegrityError, match="artifact hash mismatch"):
        validate_pack_fixtures(
            [fixture["common"], fixture["ai"]],
            schemas_root=schemas_root(),
        )


def test_pack_fixture_audit_rejects_citation_hash_not_matching_source_bytes(tmp_path):
    fixture = build_two_pack_fixture(tmp_path)
    event_id = fixture["relation"]["caused_by_event_ids"][0]
    event_path = fixture["ai"] / "events" / event_id.removeprefix("evt_")[:2] / f"{event_id}.json"
    event = json.loads(event_path.read_text(encoding="utf-8"))
    event["payload"]["citation"]["passage_hash"]["digest"] = "0" * 64
    event_path.write_text(json.dumps(event), encoding="utf-8")

    with pytest.raises(PackFixtureIntegrityError, match="citation passage hash"):
        validate_pack_fixtures(
            [fixture["common"], fixture["ai"]],
            schemas_root=schemas_root(),
        )
