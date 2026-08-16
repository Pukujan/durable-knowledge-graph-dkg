from __future__ import annotations

import json
import re
from pathlib import Path

from dkg.artifact_store import ArtifactStore
from dkg.conversation import ConversationLineage, ConversationStore
from dkg.event_store import DurableEventStore
from dkg.pack_fixture import validate_pack_fixtures

FIXTURE = "examples/conversation-lineage/time-to-crawl-v1.json"
PACK_ID = "pack_time_to_crawl_scope_20260816"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _turn_bodies(source_text: str) -> list[tuple[str, str]]:
    heading = re.compile(r"(?m)^## Turn \d+ — (assistant|human)\n")
    matches = list(heading.finditer(source_text))
    assert matches
    turns = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(source_text)
        turns.append((match.group(1), source_text[match.end() : end].rstrip("\n")))
    return turns


def build_fixture(tmp_path: Path):
    root = repo_root()
    spec = json.loads((root / FIXTURE).read_text(encoding="utf-8"))
    source_path = root / spec["source_path"]
    source_bytes = source_path.read_bytes()
    source_text = source_bytes.decode("utf-8")
    turns = _turn_bodies(source_text)

    store = ConversationStore(
        tmp_path / "conversations",
        ArtifactStore(tmp_path / "artifacts"),
        root / "schemas" / "conversation" / "v1.schema.json",
    )
    source = store.add_source(
        source_bytes,
        evidence_status=spec["source_evidence_status"],
        media_type="text/markdown",
        label=spec["title"],
        external_ref=spec["reconstruction_basis_refs"][0],
    )

    spans = []
    messages = []
    message_ids = {}
    parent_message_id = None
    for sequence, (role, text) in enumerate(turns):
        span = store.span_for_text(source, text)
        spans.append(span)
        message_id = f"msg_time_to_crawl_{sequence:03d}"
        message_ids[sequence] = message_id
        messages.append(
            {
                "message_id": message_id,
                "sequence": sequence,
                "parent_message_id": parent_message_id,
                "occurred_at": None,
                "actor": {
                    "actor_id": f"{role}-shared-page",
                    "role": role,
                    "provider": "chatgpt" if role == "assistant" else None,
                    "model_id": None,
                    "run_id": None,
                    "tool_id": None,
                },
                "evidence_status": "reconstructed",
                "text": text,
                "source_span_refs": [span["span_id"]],
            }
        )
        parent_message_id = message_id

    lineage_nodes = []
    for node_spec in spec["nodes"]:
        span = store.span_for_text(source, node_spec["source_marker"])
        spans.append(span)
        node = {
            "node_id": node_spec["node_id"],
            "kind": node_spec["kind"],
            "label": node_spec["label"],
            "text": node_spec["text"],
            "evidence_status": "reconstructed",
            "position_state": node_spec["position_state"],
            "source_message_refs": [message_ids[node_spec["source_turn"]]],
            "source_span_refs": [span["span_id"]],
        }
        for key in (
            "epistemic_class",
            "operational_state",
            "applicability_scope",
            "critique_purpose",
            "external_source_refs",
        ):
            if key in node_spec:
                node[key] = node_spec[key]
        lineage_nodes.append(node)

    envelope = store.commit(
        {
            "schema_version": "fossil.conversation.v1",
            "conversation_id": spec["conversation_id"],
            "source_status": "reconstructed",
            "title": spec["title"],
            "reconstruction_basis_refs": spec["reconstruction_basis_refs"],
            "sources": [source],
            "spans": spans,
            "messages": messages,
        }
    )
    lineage = ConversationLineage(
        {
            "schema_version": "fossil.conversation-lineage.v1",
            "lineage_id": spec["lineage_id"],
            "conversation_id": spec["conversation_id"],
            "nodes": lineage_nodes,
            "edges": spec["edges"],
            "current_conclusion_refs": spec["current_conclusion_refs"],
        },
        schema_path=root / "schemas" / "conversation-lineage" / "v1.schema.json",
        conversation_store=store,
        envelope=envelope,
    )
    return spec, store, envelope, lineage


def test_time_to_crawl_scope_preserves_lineage_and_reconstructed_status(tmp_path):
    spec, store, envelope, lineage = build_fixture(tmp_path)
    report = lineage.benchmark(
        required_path=spec["required_path"],
        current_conclusion_ref="ln_time_walking_skeleton_001",
        opposing_pairs=[],
    )

    assert report["passed"] is True
    assert report["path_matches"] is True
    assert report["citations_resolve"] is True
    assert report["current_conclusion_queryable"] is True
    assert envelope["source_status"] == "reconstructed"
    assert all(message["evidence_status"] == "reconstructed" for message in envelope["messages"])
    assert all(node["evidence_status"] == "reconstructed" for node in lineage.lineage["nodes"])
    assert store.artifact_store.verify(envelope["sources"][0]["artifact_id"])


def test_unresolved_vps_validation_gap_is_not_promoted(tmp_path):
    spec, _, _, lineage = build_fixture(tmp_path)
    assert "ln_time_vps_gap_001" not in spec["current_conclusion_refs"]
    assert lineage.node("ln_time_vps_gap_001")["position_state"] == "unresolved"


def test_time_to_crawl_pack_is_schema_and_provenance_valid():
    root = repo_root()
    report = validate_pack_fixtures(
        [root / "examples" / "packs" / "time-to-crawl"],
        schemas_root=root / "schemas",
    )
    assert report.pack_ids == (PACK_ID,)
    assert report.artifact_count == 2
    assert report.snapshot_count == 2
    assert report.claim_count == 10
    assert report.relation_count == 9
    assert report.event_count == 21


def test_time_to_crawl_conversation_event_is_idempotent(tmp_path):
    spec, store, envelope, _ = build_fixture(tmp_path)
    events = DurableEventStore(
        tmp_path / "events",
        repo_root() / "schemas" / "events" / "v1.schema.json",
    )
    event = store.build_ingested_event(
        envelope,
        pack_id=PACK_ID,
        actor_id="time-to-crawl-conversation-importer-v1",
        occurred_at="2026-08-16T00:00:00Z",
        recorded_at="2026-08-16T00:00:00Z",
    )
    accepted = events.commit(event)
    assert accepted["event_type"] == "conversation.ingested"
    assert events.commit(event)["event_id"] == accepted["event_id"]
    assert accepted["payload"]["source_status"] == spec["source_evidence_status"]
