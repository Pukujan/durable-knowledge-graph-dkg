from __future__ import annotations

import json
from pathlib import Path

from dkg.artifact_store import ArtifactStore
from dkg.conversation import ConversationLineage, ConversationStore
from dkg.event_store import DurableEventStore
from scripts.ingest_shared_chat_reconstructions import ingest_manifest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "examples" / "shared-chat-ingestion" / "2026-08-14.json"


def test_both_shared_chat_checkpoints_ingest_as_reconstructed_and_idempotent(tmp_path):
    first = ingest_manifest(MANIFEST, tmp_path / "run", repo_root=ROOT)
    second = ingest_manifest(MANIFEST, tmp_path / "run", repo_root=ROOT)

    assert first == second
    assert {item["conversation_id"] for item in first} == {
        "conv_shared_chat_llm_bias_20260814",
        "conv_shared_chat_p001_eval_20260814",
    }
    assert len(list((tmp_path / "run" / "events").rglob("evt_*.json"))) == 2
    assert len(list((tmp_path / "run" / "conversations").rglob("conv_*.json"))) == 2
    assert len(list((tmp_path / "run" / "lineages").glob("lin_*.json"))) == 2

    artifact_store = ArtifactStore(tmp_path / "run" / "artifacts")
    event_store = DurableEventStore(
        tmp_path / "run" / "events", ROOT / "schemas" / "events" / "v1.schema.json"
    )
    events = list(event_store.iter_events())
    assert {event["event_type"] for event in events} == {"conversation.ingested"}
    assert all(event["payload"]["source_status"] == "reconstructed" for event in events)
    assert all(
        event["actor"]["skill_id"] == "skill_research-ingestion" for event in events
    )
    assert all(
        event["provenance"]["method"] == "reconstructed_shared_chat_import"
        for event in events
    )
    for event in events:
        assert all(artifact_store.verify(artifact_id) for artifact_id in event["evidence_refs"])


def test_shared_chat_lineages_keep_current_verdicts_and_reconstructed_citations(tmp_path):
    results = ingest_manifest(MANIFEST, tmp_path / "run", repo_root=ROOT)
    conversation_store = ConversationStore(
        tmp_path / "run" / "conversations",
        ArtifactStore(tmp_path / "run" / "artifacts"),
        ROOT / "schemas" / "conversation" / "v1.schema.json",
    )

    expected_labels = {
        "conv_shared_chat_llm_bias_20260814": "Prototype verdict",
        "conv_shared_chat_p001_eval_20260814": "Research-only verdict",
    }
    for result in results:
        envelope = json.loads(Path(result["conversation_path"]).read_text(encoding="utf-8"))
        lineage_data = json.loads(Path(result["lineage_path"]).read_text(encoding="utf-8"))
        lineage = ConversationLineage(
            lineage_data,
            schema_path=ROOT / "schemas" / "conversation-lineage" / "v1.schema.json",
            conversation_store=conversation_store,
            envelope=envelope,
        )

        assert envelope["source_status"] == "reconstructed"
        assert envelope["sources"][0]["external_ref"].startswith("https://chatgpt.com/share/")
        assert all(node["evidence_status"] == "reconstructed" for node in lineage_data["nodes"])
        assert expected_labels[envelope["conversation_id"]] in {
            node["label"] for node in lineage.current_conclusions()
        }
        assert all(
            citation["evidence_status"] == "reconstructed"
            for node_id in lineage_data["current_conclusion_refs"]
            for citation in lineage.citations(node_id)
        )
