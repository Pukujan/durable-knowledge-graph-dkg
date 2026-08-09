from __future__ import annotations

import json
from pathlib import Path

import pytest

from dkg.artifact_store import ArtifactStore
from dkg.conversation import (
    ConversationLineage,
    ConversationProvenanceError,
    ConversationStore,
)
from dkg.event_store import DurableEventStore


COMMON_PACK = "pack_269099f7b2ba43b7a99b9427d64092de"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def conversation_store(tmp_path: Path) -> ConversationStore:
    return ConversationStore(
        tmp_path / "conversations",
        ArtifactStore(tmp_path / "artifacts"),
        repo_root() / "schemas" / "conversation" / "v1.schema.json",
    )


def test_verbatim_message_must_exactly_match_immutable_source_span(tmp_path):
    store = conversation_store(tmp_path)
    exact = "User: this exact sentence survives."
    source = store.add_source(
        exact.encode("utf-8"),
        evidence_status="verbatim",
        media_type="text/plain",
        label="exported transcript",
    )
    span = store.span_for_text(source, exact)
    envelope = {
        "schema_version": "fossil.conversation.v1",
        "conversation_id": "conv_verbatim_fixture_001",
        "source_status": "verbatim",
        "sources": [source],
        "spans": [span],
        "messages": [
            {
                "message_id": "msg_verbatim_001",
                "sequence": 0,
                "parent_message_id": None,
                "occurred_at": None,
                "actor": {
                    "actor_id": "human-fixture",
                    "role": "human",
                    "provider": None,
                    "model_id": None,
                    "run_id": None,
                    "tool_id": None,
                },
                "evidence_status": "verbatim",
                "text": exact,
                "source_span_refs": [span["span_id"]],
            }
        ],
    }

    committed = store.commit(envelope)
    assert store.resolve_span_text(committed, span["span_id"]) == exact
    assert store.artifact_store.verify(source["artifact_id"])

    forged = json.loads(json.dumps(envelope))
    forged["conversation_id"] = "conv_verbatim_fixture_002"
    forged["messages"][0]["text"] = "A polished paraphrase pretending to be exact."
    with pytest.raises(ConversationProvenanceError, match="exactly equal"):
        store.commit(forged)


def test_reconstructed_source_cannot_be_silently_upgraded_to_verbatim(tmp_path):
    store = conversation_store(tmp_path)
    recovered = "Recovered concept, explicitly reconstructed."
    source = store.add_source(
        recovered.encode("utf-8"),
        evidence_status="reconstructed",
        label="recovery checkpoint",
    )
    span = store.span_for_text(source, recovered)
    envelope = {
        "schema_version": "fossil.conversation.v1",
        "conversation_id": "conv_reconstruction_fixture_001",
        "source_status": "mixed",
        "reconstruction_basis_refs": ["recovery:test"],
        "sources": [source],
        "spans": [span],
        "messages": [
            {
                "message_id": "msg_reconstruction_001",
                "sequence": 0,
                "parent_message_id": None,
                "occurred_at": None,
                "actor": {
                    "actor_id": "recovery-importer",
                    "role": "other",
                    "provider": None,
                    "model_id": None,
                    "run_id": None,
                    "tool_id": None,
                },
                "evidence_status": "verbatim",
                "text": recovered,
                "source_span_refs": [span["span_id"]],
            }
        ],
    }

    with pytest.raises(ConversationProvenanceError, match="reconstructed source spans"):
        store.commit(envelope)


def build_recovered_benchmark(tmp_path: Path):
    root = repo_root()
    spec = json.loads(
        (root / "examples" / "conversation-lineage" / "recovered-dkg-lineage-v1.json").read_text(
            encoding="utf-8"
        )
    )
    source_bytes = (root / spec["source_path"]).read_bytes()
    store = conversation_store(tmp_path)
    source = store.add_source(
        source_bytes,
        evidence_status=spec["source_evidence_status"],
        media_type="text/markdown",
        label="reconstructed DKG conversation-lineage benchmark",
        external_ref=spec["source_path"],
    )

    spans = []
    messages = []
    node_sources: dict[str, tuple[str, str]] = {}
    parent_message_id = None
    for sequence, node_spec in enumerate(spec["nodes"]):
        marker = node_spec["source_marker"]
        span = store.span_for_text(source, marker)
        message_id = f"msg_recovered_{sequence:03d}"
        spans.append(span)
        messages.append(
            {
                "message_id": message_id,
                "sequence": sequence,
                "parent_message_id": parent_message_id,
                "occurred_at": None,
                "actor": {
                    "actor_id": "reconstructed-conversation-importer",
                    "role": "other",
                    "provider": None,
                    "model_id": None,
                    "run_id": None,
                    "tool_id": None,
                },
                "evidence_status": "reconstructed",
                "text": marker,
                "source_span_refs": [span["span_id"]],
            }
        )
        node_sources[node_spec["node_id"]] = (message_id, span["span_id"])
        parent_message_id = message_id

    envelope = store.commit(
        {
            "schema_version": "fossil.conversation.v1",
            "conversation_id": spec["conversation_id"],
            "source_status": "reconstructed",
            "title": "Recovered DKG intellectual-lineage benchmark",
            "reconstruction_basis_refs": spec["reconstruction_basis_refs"],
            "sources": [source],
            "spans": spans,
            "messages": messages,
        }
    )

    lineage_nodes = []
    for node_spec in spec["nodes"]:
        message_id, span_id = node_sources[node_spec["node_id"]]
        lineage_nodes.append(
            {
                "node_id": node_spec["node_id"],
                "kind": node_spec["kind"],
                "label": node_spec["label"],
                "text": node_spec["source_marker"],
                "evidence_status": "reconstructed",
                "position_state": node_spec["position_state"],
                "source_message_refs": [message_id],
                "source_span_refs": [span_id],
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


def test_recovered_conversation_lineage_benchmark_reconstructs_required_path(tmp_path):
    spec, store, envelope, lineage = build_recovered_benchmark(tmp_path)

    report = lineage.benchmark(
        required_path=spec["required_path"],
        current_conclusion_ref=spec["benchmark_current_conclusion_ref"],
        opposing_pairs=[tuple(pair) for pair in spec["opposing_pairs"]],
    )

    assert report["passed"] is True
    assert report["path_matches"] is True
    assert report["citations_resolve"] is True
    assert report["current_conclusion_queryable"] is True
    assert report["historical_path_queryable"] is True
    assert all(report["opposing_positions_queryable"].values())

    labels = [node["label"] for node in lineage.path(spec["required_path"][0], spec["required_path"][-1])]
    assert labels == [
        "learning UX / parabola",
        "representation mismatch",
        "AI translation layer",
        "failure learning",
        "MAPE-K / KEDB",
        "truth maintenance",
        "temporal knowledge graph",
    ]

    current_labels = {node["label"] for node in lineage.current_conclusions()}
    assert "temporal knowledge graph" in current_labels
    assert "rebuildable graph projection" in current_labels

    database_opposition = {
        node["node_id"]
        for node in lineage.opposing_positions("ln_durable_events_position_change")
    }
    assert database_opposition == {"ln_database_canonical"}

    for node_id in spec["required_path"]:
        citations = lineage.citations(node_id)
        assert len(citations) == 1
        assert citations[0]["artifact_id"] == envelope["sources"][0]["artifact_id"]
        assert citations[0]["evidence_status"] == "reconstructed"
        assert citations[0]["text"].startswith("[")
        assert store.artifact_store.verify(citations[0]["artifact_id"])


def test_recovered_lineage_contains_required_intellectual_roles(tmp_path):
    _, _, _, lineage = build_recovered_benchmark(tmp_path)
    kinds = {node["kind"] for node in lineage.lineage["nodes"]}
    assert {
        "observation",
        "claim",
        "challenge",
        "rebuttal",
        "assumption",
        "conclusion",
        "position_change",
        "decision",
    }.issubset(kinds)

    reconstructed = {
        node["evidence_status"] for node in lineage.lineage["nodes"]
    }
    assert reconstructed == {"reconstructed"}


def test_conversation_ingestion_event_points_to_source_artifact(tmp_path):
    spec, store, envelope, _ = build_recovered_benchmark(tmp_path)
    event_store = DurableEventStore(
        tmp_path / "events", repo_root() / "schemas" / "events" / "v1.schema.json"
    )
    event = store.build_ingested_event(
        envelope,
        pack_id=COMMON_PACK,
        actor_id="conversation-importer-v1",
        occurred_at="2026-08-09T22:58:00Z",
        recorded_at="2026-08-09T22:58:00Z",
    )
    accepted = event_store.commit(event)

    assert accepted["event_type"] == "conversation.ingested"
    assert accepted["subject_refs"] == [spec["conversation_id"]]
    assert accepted["payload"]["source_status"] == "reconstructed"
    assert accepted["evidence_refs"] == [envelope["sources"][0]["artifact_id"]]
    assert store.artifact_store.verify(accepted["evidence_refs"][0])
    assert event_store.commit(event)["event_id"] == accepted["event_id"]
