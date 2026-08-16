from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from dkg.artifact_store import ArtifactStore
from dkg.event_store import DurableEventStore
from dkg.pack_fixture import validate_pack_fixtures
from dkg.source import SourceSnapshotStore

PACK_ID = "pack_time_to_crawl_scope_20260816"
PACK_ROOT = REPO_ROOT / "examples" / "packs" / "time-to-crawl"
FIXTURE_PATH = REPO_ROOT / "examples" / "conversation-lineage" / "time-to-crawl-v1.json"
TRANSCRIPT_PATH = REPO_ROOT / "docs" / "recovery" / "2026-08-16-time-to-crawl-transcript.md"
SHARED_URL = "https://chatgpt.com/share/6a81ec29-8d24-83ea-9fdd-db97df8ee576?ogimg=plain"
RECORDED_AT = "2026-08-16T00:00:00Z"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _find_span(data: bytes, marker: str) -> tuple[int, int]:
    target = marker.encode("utf-8")
    start = data.find(target)
    if start < 0:
        raise ValueError(f"lineage marker is absent from source artifact: {marker[:120]!r}")
    return start, start + len(target)


def _citation(source_store: SourceSnapshotStore, snapshot: dict[str, Any], marker: str) -> dict[str, Any]:
    data = source_store.artifact_store.read_bytes(snapshot["artifact_id"])
    start, end = _find_span(data, marker)
    return source_store.create_citation(snapshot["snapshot_id"], byte_start=start, byte_end=end)


def _claim_id(node_id: str) -> str:
    return f"clm_time_to_crawl_{node_id.removeprefix('ln_time_')}"


def _relation_type(lineage_relation_type: str) -> str:
    return {
        "supports": "SUPPORTS",
        "challenges": "CHALLENGES",
        "rebuts": "CONTRADICTS",
        "reframes": "REFINES",
        "supersedes": "SUPERSEDES",
        "depends_on": "DEPENDS_ON",
        "leads_to": "RELATED_TO",
    }.get(lineage_relation_type, "RELATED_TO")


def _event_base(
    event_type: str,
    *,
    subject_refs: list[str],
    idempotency_key: str,
    evidence_refs: list[str],
    source_snapshot_refs: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": "dkg.event.v1",
        "event_type": event_type,
        "occurred_at": RECORDED_AT,
        "recorded_at": RECORDED_AT,
        "pack_id": PACK_ID,
        "actor": {
            "actor_type": "importer",
            "actor_id": "time-to-crawl-scope-importer-v1",
            "model_id": None,
            "harness_version": "fossil-core-local-import-v1",
            "skill_id": "skill_research-ingestion",
            "skill_version": "1.0.0",
        },
        "subject_refs": subject_refs,
        "idempotency_key": idempotency_key,
        "evidence_refs": evidence_refs,
        "source_snapshot_refs": source_snapshot_refs,
        "provenance": {
            "method": "reconstructed-conversation-lineage-import",
            "software_commit": None,
            "ontology_version": "dkg.core@1.x",
            "benchmark_ref": "examples/conversation-lineage/time-to-crawl-v1.json",
        },
    }


def _write_artifact_index(artifact_root: Path) -> None:
    manifests = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((artifact_root / "manifests").glob("*/*.json"))
    ]
    content = "".join(_canonical(item) + "\n" for item in manifests)
    index = artifact_root / "manifest.jsonl"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(content, encoding="utf-8")


def _capture_shared_page() -> bytes:
    request = Request(
        SHARED_URL,
        headers={"User-Agent": "fossil-core-research-ingestion/1.0"},
    )
    with urlopen(request, timeout=30) as response:
        return response.read()


def _already_ingested() -> dict[str, Any] | None:
    event_root = PACK_ROOT / "events"
    if not event_root.is_dir() or not any(event_root.glob("*/*.json")):
        return None
    report = validate_pack_fixtures(
        [PACK_ROOT],
        schemas_root=REPO_ROOT / "schemas",
    )
    return {
        "pack_id": PACK_ID,
        "status": "already-present",
        "event_count": report.event_count,
        "claim_count": report.claim_count,
        "relation_count": report.relation_count,
    }


def ingest() -> dict[str, Any]:
    existing = _already_ingested()
    if existing is not None:
        return existing
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    transcript_bytes = TRANSCRIPT_PATH.read_bytes()
    raw_page_bytes = _capture_shared_page()

    artifacts = ArtifactStore(PACK_ROOT / "artifacts")
    source_store = SourceSnapshotStore(
        PACK_ROOT / "sources",
        artifacts,
        REPO_ROOT / "schemas" / "source-snapshot" / "v1.schema.json",
        REPO_ROOT / "schemas" / "citation" / "v1.schema.json",
    )
    events = DurableEventStore(
        PACK_ROOT / "events",
        REPO_ROOT / "schemas" / "events" / "v1.schema.json",
    )

    raw_snapshot = source_store.put_snapshot(
        raw_page_bytes,
        locator={"url": SHARED_URL},
        retrieved_at=RECORDED_AT,
        source_role="local",
        quality={
            "authority": None,
            "directness": 1.0,
            "independence": 0.0,
            "reproducibility": 0.8,
            "timeliness": 1.0,
            "notes": "Raw public shared-page HTML captured for provenance; rendered message content remains a reconstructed source.",
        },
        version_metadata={"version_id": "shared-page-html-capture-2026-08-16"},
        media_type="text/html",
    )
    transcript_snapshot = source_store.put_snapshot(
        transcript_bytes,
        locator={"url": SHARED_URL, "fragment": "normalized-decision-bearing-transcript"},
        retrieved_at=RECORDED_AT,
        source_role="reconstructed",
        quality={
            "authority": None,
            "directness": 0.4,
            "independence": 0.0,
            "reproducibility": 0.8,
            "timeliness": 1.0,
            "notes": "Normalized decision-bearing reconstruction derived from the raw shared-page capture; not a verbatim export.",
        },
        version_metadata={"version_id": "normalized-transcript-2026-08-16"},
        media_type="text/markdown",
        derivation={"parent_snapshot_refs": [raw_snapshot["snapshot_id"]], "method": "visible-payload-normalization"},
    )
    evidence_refs = [raw_snapshot["artifact_id"], transcript_snapshot["artifact_id"]]
    snapshot_refs = [raw_snapshot["snapshot_id"], transcript_snapshot["snapshot_id"]]

    transcript_ingested = _event_base(
        "conversation.ingested",
        subject_refs=[fixture["conversation_id"]],
        idempotency_key=f"conversation-ingested:{fixture['conversation_id']}",
        evidence_refs=evidence_refs,
        source_snapshot_refs=snapshot_refs,
    )
    transcript_ingested["payload"] = {
        "conversation_id": fixture["conversation_id"],
        "lineage_id": fixture["lineage_id"],
        "source_status": fixture["source_evidence_status"],
        "source_snapshot_ids": snapshot_refs,
        "message_count": 8,
        "source_revision": SHARED_URL,
    }
    events.commit(transcript_ingested)

    lineage_event = _event_base(
        "conversation.lineage_recorded",
        subject_refs=[fixture["lineage_id"], fixture["conversation_id"]],
        idempotency_key=f"conversation-lineage-recorded:{fixture['lineage_id']}",
        evidence_refs=evidence_refs,
        source_snapshot_refs=snapshot_refs,
    )
    lineage_event["payload"] = {
        "conversation_id": fixture["conversation_id"],
        "lineage_id": fixture["lineage_id"],
        "source_status": fixture["source_evidence_status"],
        "required_path": fixture["required_path"],
        "current_conclusion_refs": fixture["current_conclusion_refs"],
        "benchmark_cases": fixture["benchmark_cases"],
        "lineage_fixture_ref": str(FIXTURE_PATH.relative_to(REPO_ROOT)),
        "source_revision": SHARED_URL,
    }
    events.commit(lineage_event)

    claim_events: dict[str, dict[str, Any]] = {}
    for node in fixture["nodes"]:
        citation = _citation(source_store, transcript_snapshot, node["source_marker"])
        claim_id = _claim_id(node["node_id"])
        event = _event_base(
            "claim.proposed",
            subject_refs=[claim_id],
            idempotency_key=f"claim-proposed:{fixture['lineage_id']}:{node['node_id']}",
            evidence_refs=[transcript_snapshot["artifact_id"]],
            source_snapshot_refs=[transcript_snapshot["snapshot_id"]],
        )
        event["payload"] = {
            "claim_text": node["label"],
            "citation": citation,
            "conversation_id": fixture["conversation_id"],
            "lineage_id": fixture["lineage_id"],
            "lineage_node_id": node["node_id"],
            "kind": node["kind"],
            "position_state": node["position_state"],
            "epistemic_class": node["epistemic_class"],
            "evidence_status": "reconstructed",
            "authority_state": "candidate_only",
        }
        for key in ("operational_state", "applicability_scope"):
            if key in node:
                event["payload"][key] = node[key]
        claim_events[node["node_id"]] = events.commit(event)

    for edge in fixture["edges"]:
        source_claim = _claim_id(edge["source_node_id"])
        target_claim = _claim_id(edge["target_node_id"])
        relation_id = f"rel_time_to_crawl_{edge['edge_id'].removeprefix('le_time_')}"
        relation_event = _event_base(
            "relation.proposed",
            subject_refs=[relation_id, source_claim, target_claim],
            idempotency_key=f"relation-proposed:{fixture['lineage_id']}:{edge['edge_id']}",
            evidence_refs=[transcript_snapshot["artifact_id"]],
            source_snapshot_refs=[transcript_snapshot["snapshot_id"]],
        )
        relation_event["caused_by_event_ids"] = [
            claim_events[edge["source_node_id"]]["event_id"],
            claim_events[edge["target_node_id"]]["event_id"],
        ]
        relation_event["payload"] = {
            "relation_id": relation_id,
            "relation_type": _relation_type(edge["relation_type"]),
            "lineage_relation_type": edge["relation_type"],
            "source_ref": source_claim,
            "target_ref": target_claim,
            "state": "proposed",
            "conversation_id": fixture["conversation_id"],
            "lineage_id": fixture["lineage_id"],
            "lineage_edge_id": edge["edge_id"],
            "authority_state": "candidate_only",
        }
        events.commit(relation_event)

    _write_artifact_index(PACK_ROOT / "artifacts")
    return {
        "pack_id": PACK_ID,
        "conversation_id": fixture["conversation_id"],
        "lineage_id": fixture["lineage_id"],
        "artifact_ids": evidence_refs,
        "snapshot_ids": snapshot_refs,
        "claim_count": len(claim_events),
        "relation_count": len(fixture["edges"]),
        "raw_page_sha256": hashlib.sha256(raw_page_bytes).hexdigest(),
    }


if __name__ == "__main__":
    print(json.dumps(ingest(), indent=2, sort_keys=True))
