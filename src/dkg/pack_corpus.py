from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Iterable

from .lifecycle import KnowledgeState
from .pack_fixture import validate_pack_fixtures


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _events_for_pack(root: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for relative in manifest["event_roots"]:
        event_root = root / str(relative)
        for path in sorted(event_root.glob("*/*.json")):
            events.append(_load_json(path))
    return sorted(events, key=lambda event: (str(event["recorded_at"]), str(event["event_id"])))


def retrieval_documents_from_pack_fixtures(
    pack_roots: Iterable[Path],
    *,
    schemas_root: Path,
) -> list[dict[str, Any]]:
    """Build deterministic retrieval documents from validated durable packs.

    This is a rebuildable benchmark/search projection. Claim and relation IDs remain
    the durable corpus identities; generated document text is never canonical truth.
    """

    roots = [Path(root) for root in pack_roots]
    validate_pack_fixtures(roots, schemas_root=schemas_root)

    manifests: dict[str, dict[str, Any]] = {}
    events_by_pack: dict[str, list[dict[str, Any]]] = {}
    state_by_pack: dict[str, KnowledgeState] = {}
    claim_text: dict[str, str] = {}
    claim_event: dict[str, dict[str, Any]] = {}
    relation_event: dict[str, dict[str, Any]] = {}

    for root in roots:
        manifest = _load_json(root / "manifest.json")
        pack_id = str(manifest["pack_id"])
        manifests[pack_id] = manifest
        events = _events_for_pack(root, manifest)
        events_by_pack[pack_id] = events
        state_by_pack[pack_id] = KnowledgeState.replay(events)
        for event in events:
            if event["event_type"] == "claim.proposed":
                claim_id = str(event["subject_refs"][0])
                claim_text[claim_id] = str(event["payload"]["claim_text"])
                claim_event[claim_id] = event
            elif event["event_type"] == "relation.proposed":
                relation_event[str(event["payload"]["relation_id"])] = event

    documents: list[dict[str, Any]] = []
    for pack_id in sorted(events_by_pack):
        state = state_by_pack[pack_id]
        for claim_id in sorted(state.claims):
            event = claim_event[claim_id]
            document = {
                "id": claim_id,
                "pack_id": pack_id,
                "text": claim_text[claim_id],
                "document_type": "claim",
                "current_state": state.claims[claim_id],
                "state_history": list(state.claim_history[claim_id]),
                "proposed_event_id": str(event["event_id"]),
                "evidence_refs": [str(item) for item in event.get("evidence_refs", [])],
                "source_snapshot_refs": [
                    str(item) for item in event.get("source_snapshot_refs", [])
                ],
            }
            citation = event.get("payload", {}).get("citation")
            if isinstance(citation, dict):
                document["citation"] = copy.deepcopy(citation)
            documents.append(document)

        for relation_id in sorted(state.relations):
            relation = state.relations[relation_id]
            event = relation_event[relation_id]
            source_text = claim_text.get(relation.source_ref, relation.source_ref)
            target_text = claim_text.get(relation.target_ref, relation.target_ref)
            documents.append(
                {
                    "id": relation_id,
                    "pack_id": pack_id,
                    "text": (
                        f"{source_text}\n"
                        f"Relation: {relation.relation_type}\n"
                        f"{target_text}"
                    ),
                    "document_type": "relation",
                    "relation_type": relation.relation_type,
                    "source_ref": relation.source_ref,
                    "target_ref": relation.target_ref,
                    "current_state": relation.state,
                    "state_history": list(state.relation_history[relation_id]),
                    "proposed_event_id": str(event["event_id"]),
                    "evidence_refs": [str(item) for item in event.get("evidence_refs", [])],
                    "source_snapshot_refs": [
                        str(item) for item in event.get("source_snapshot_refs", [])
                    ],
                }
            )

    documents.sort(key=lambda document: (str(document["pack_id"]), str(document["id"])))
    return documents
