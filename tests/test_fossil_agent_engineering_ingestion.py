from __future__ import annotations

import json
import re
from pathlib import Path

from dkg.artifact_store import ArtifactStore
from dkg.conversation import ConversationLineage, ConversationStore
from dkg.pack_fixture import validate_pack_fixtures

FIXTURE = "examples/conversation-lineage/fossil-agent-engineering-substrate-v1.json"
PACK_ID = "pack_fossil_agent_engineering_20260816"


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
    source_bytes = (root / spec["source_path"]).read_bytes()
    turns = _turn_bodies(source_bytes.decode("utf-8"))
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
        message_id = f"msg_fossil_agent_engineering_{sequence:03d}"
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
        for key in ("epistemic_class", "operational_state", "applicability_scope"):
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


def test_agent_engineering_lineage_preserves_current_proposals_and_history(tmp_path):
    spec, store, envelope, lineage = build_fixture(tmp_path)
    report = lineage.benchmark(
        required_path=spec["required_path"],
        current_conclusion_ref="ln_fossil_rag_build_001",
        opposing_pairs=[],
    )
    assert report["passed"] is True
    assert report["path_matches"] is True
    assert report["citations_resolve"] is True
    assert report["current_conclusion_queryable"] is True
    assert envelope["source_status"] == "reconstructed"
    assert all(node["evidence_status"] == "reconstructed" for node in lineage.lineage["nodes"])
    assert store.artifact_store.verify(envelope["sources"][0]["artifact_id"])


def test_historical_handoff_is_not_current_architecture(tmp_path):
    spec, _, _, lineage = build_fixture(tmp_path)
    assert "ln_fossil_handoff_observation_001" not in spec["current_conclusion_refs"]
    assert "ln_fossil_live_gap_001" not in spec["current_conclusion_refs"]
    assert lineage.node("ln_fossil_live_gap_001")["position_state"] == "unresolved"


def test_agent_engineering_pack_is_schema_and_provenance_valid():
    root = repo_root()
    report = validate_pack_fixtures(
        [root / "examples" / "packs" / "fossil-agent-engineering"],
        schemas_root=root / "schemas",
    )
    assert report.pack_ids == (PACK_ID,)
    assert report.artifact_count == 2
    assert report.snapshot_count == 2
    assert report.claim_count == 15
    assert report.relation_count == 14
    assert report.event_count == 31

