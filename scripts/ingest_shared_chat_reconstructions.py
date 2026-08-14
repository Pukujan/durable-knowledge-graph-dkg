"""Ingest public shared-chat checkpoints through the durable FOSSIL contracts.

The input is intentionally a small, explicit manifest rather than a scraper.
The public ChatGPT share pages used for this import expose rendered copies, not
the original export bytes, so every source/message/lineage object is committed
as ``reconstructed`` and retains the public URL as an external reference.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from dkg.artifact_store import ArtifactStore
from dkg.conversation import ConversationLineage, ConversationStore
from dkg.event_store import DurableEventStore
from dkg.io import publish_immutable


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def _publish_json(path: Path, value: Any) -> None:
    data = _canonical(value)
    if publish_immutable(path, data):
        return
    existing = json.loads(path.read_text(encoding="utf-8"))
    if _canonical(existing) != data:
        raise RuntimeError(f"immutable output conflict: {path}")


def _actor(actor: dict[str, Any], *, role: str, actor_id: str) -> dict[str, Any]:
    return {
        "actor_id": actor_id,
        "role": role,
        "provider": "ChatGPT share page" if role == "assistant" else None,
        "model_id": None,
        "run_id": None,
        "tool_id": None,
    }


def _build_envelope(
    spec: dict[str, Any],
    *,
    repo_root: Path,
    conversation_store: ConversationStore,
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_path = repo_root / spec["source_path"]
    source_bytes = source_path.read_bytes()
    source = conversation_store.add_source(
        source_bytes,
        evidence_status="reconstructed",
        media_type="text/markdown",
        label=spec["source_label"],
        external_ref=spec["external_ref"],
    )

    messages: list[dict[str, Any]] = []
    spans: list[dict[str, Any]] = []
    previous_message_id: str | None = None
    message_by_index: dict[int, tuple[str, str]] = {}
    for sequence, message_spec in enumerate(spec["messages"]):
        marker = str(message_spec["marker"])
        span = conversation_store.span_for_text(source, marker)
        message_id = str(message_spec["message_id"])
        spans.append(span)
        messages.append(
            {
                "message_id": message_id,
                "sequence": sequence,
                "parent_message_id": previous_message_id,
                "occurred_at": None,
                "actor": _actor(
                    {},
                    role=str(message_spec["role"]),
                    actor_id=str(message_spec["actor_id"]),
                ),
                "evidence_status": "reconstructed",
                "text": marker,
                "source_span_refs": [span["span_id"]],
            }
        )
        message_by_index[sequence] = (message_id, span["span_id"])
        previous_message_id = message_id

    envelope = conversation_store.commit(
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
    return envelope, {"message_by_index": message_by_index}


def _build_lineage(
    spec: dict[str, Any],
    *,
    conversation_store: ConversationStore,
    envelope: dict[str, Any],
    message_by_index: dict[int, tuple[str, str]],
    repo_root: Path,
) -> dict[str, Any]:
    nodes = []
    for node_spec in spec["lineage"]["nodes"]:
        message_id, span_id = message_by_index[int(node_spec["message_index"])]
        nodes.append(
            {
                "node_id": node_spec["node_id"],
                "kind": node_spec["kind"],
                "label": node_spec["label"],
                "text": node_spec["text"],
                "evidence_status": "reconstructed",
                "position_state": node_spec["position_state"],
                "source_message_refs": [message_id],
                "source_span_refs": [span_id],
            }
        )

    lineage = {
        "schema_version": "fossil.conversation-lineage.v1",
        "lineage_id": spec["lineage"]["lineage_id"],
        "conversation_id": spec["conversation_id"],
        "nodes": nodes,
        "edges": copy.deepcopy(spec["lineage"]["edges"]),
        "current_conclusion_refs": copy.deepcopy(
            spec["lineage"]["current_conclusion_refs"]
        ),
    }
    ConversationLineage(
        lineage,
        schema_path=repo_root / "schemas" / "conversation-lineage" / "v1.schema.json",
        conversation_store=conversation_store,
        envelope=envelope,
    )
    return lineage


def ingest_manifest(
    manifest_path: Path,
    output_root: Path,
    *,
    repo_root: Path | None = None,
) -> list[dict[str, Any]]:
    """Ingest every conversation in a manifest and return stable output refs."""

    manifest_path = Path(manifest_path)
    repo_root = Path(repo_root or manifest_path.parents[2])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output_root = Path(output_root)
    artifact_store = ArtifactStore(output_root / "artifacts")
    conversation_store = ConversationStore(
        output_root / "conversations",
        artifact_store,
        repo_root / "schemas" / "conversation" / "v1.schema.json",
    )
    event_store = DurableEventStore(
        output_root / "events", repo_root / "schemas" / "events" / "v1.schema.json"
    )
    actor = manifest["actor"]
    results: list[dict[str, Any]] = []
    for spec in manifest["conversations"]:
        envelope, build_state = _build_envelope(
            spec, repo_root=repo_root, conversation_store=conversation_store
        )
        lineage = _build_lineage(
            spec,
            conversation_store=conversation_store,
            envelope=envelope,
            message_by_index=build_state["message_by_index"],
            repo_root=repo_root,
        )
        _publish_json(
            output_root / "lineages" / f"{lineage['lineage_id']}.json", lineage
        )

        event = conversation_store.build_ingested_event(
            envelope,
            pack_id=manifest["pack_id"],
            actor_id=actor["actor_id"],
            occurred_at=manifest["observed_at"],
            recorded_at=manifest["observed_at"],
        )
        event["actor"] = {
            "actor_type": "importer",
            "actor_id": actor["actor_id"],
            "harness_version": actor["harness_version"],
            "skill_id": actor["skill_id"],
            "skill_version": actor["skill_version"],
        }
        event["correlation_id"] = manifest["import_id"]
        event["payload_schema"] = "schemas/conversation/v1.schema.json"
        event["payload"]["lineage_id"] = lineage["lineage_id"]
        event["provenance"] = {
            "method": "reconstructed_shared_chat_import",
            "prompt_or_policy_ref": "skills/research-ingestion/manifest.json",
            "benchmark_ref": lineage["lineage_id"],
        }
        committed_event = event_store.commit(event)
        results.append(
            {
                "conversation_id": envelope["conversation_id"],
                "conversation_path": str(
                    conversation_store._path(envelope["conversation_id"])
                ),
                "lineage_id": lineage["lineage_id"],
                "lineage_path": str(
                    output_root / "lineages" / f"{lineage['lineage_id']}.json"
                ),
                "event_id": committed_event["event_id"],
                "artifact_ids": [
                    source["artifact_id"] for source in envelope["sources"]
                ],
            }
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            {"imported": ingest_manifest(args.manifest, args.output)},
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
