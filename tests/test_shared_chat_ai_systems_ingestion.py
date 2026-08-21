from __future__ import annotations

import json
from pathlib import Path

from fossil_core.artifact_store import ArtifactStore
from fossil_core.event_store import DurableEventStore
from scripts.ingest_shared_chat_reconstructions import ingest_manifest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "examples" / "shared-chat-ingestion" / "2026-08-21.json"


def test_ai_systems_shared_chat_ingests_as_reconstructed_and_idempotent(tmp_path):
    first = ingest_manifest(MANIFEST, tmp_path / "run", repo_root=ROOT)
    second = ingest_manifest(MANIFEST, tmp_path / "run", repo_root=ROOT)

    assert first == second
    assert [item["conversation_id"] for item in first] == [
        "conv_shared_chat_ai_systems_knowledge_pack_20260821"
    ]

    event_store = DurableEventStore(
        tmp_path / "run" / "events", ROOT / "schemas" / "events" / "v1.schema.json"
    )
    events = list(event_store.iter_events())
    assert len(events) == 1
    assert events[0]["pack_id"] == "pack_f024177f89a5442db84171c3dd7f58e5"
    assert events[0]["event_type"] == "conversation.ingested"
    assert events[0]["payload"]["source_status"] == "reconstructed"
    assert events[0]["provenance"]["method"] == "reconstructed_shared_chat_import"

    artifact_store = ArtifactStore(tmp_path / "run" / "artifacts")
    assert all(artifact_store.verify(ref) for ref in events[0]["evidence_refs"])

    envelope = json.loads(Path(first[0]["conversation_path"]).read_text(encoding="utf-8"))
    lineage = json.loads(Path(first[0]["lineage_path"]).read_text(encoding="utf-8"))
    assert envelope["source_status"] == "reconstructed"
    assert envelope["sources"][0]["external_ref"].endswith(
        "6a88c1e9-ea00-83ea-8970-8b5434049e15?ogimg=plain"
    )
    assert {node["label"] for node in lineage["nodes"]} >= {
        "Promote only important evidenced knowledge",
        "Knowledge must be invalidatable",
        "Ingest as reconstructed AI-systems research",
    }
    assert all(node["evidence_status"] == "reconstructed" for node in lineage["nodes"])
