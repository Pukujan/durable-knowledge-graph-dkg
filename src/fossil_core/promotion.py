from __future__ import annotations

from typing import Any, Iterable


def build_promotion_event(
    *,
    source_pack_id: str,
    target_pack_id: str,
    subject_refs: Iterable[str],
    actor: dict[str, Any],
    occurred_at: str,
    recorded_at: str,
    idempotency_key: str,
    evidence_refs: Iterable[str] = (),
    reason: str = "",
) -> dict[str, Any]:
    """Create the explicit durable event for cross-pack knowledge promotion.

    Promotion never mutates the source pack. The target pack records a new
    event whose payload points back to the source pack and whose evidence refs
    preserve why the promotion was accepted.
    """
    subjects = list(subject_refs)
    if not subjects:
        raise ValueError("promotion requires at least one stable subject reference")
    if source_pack_id == target_pack_id:
        raise ValueError("promotion requires different source and target packs")

    return {
        "schema_version": "dkg.event.v1",
        "event_type": "knowledge.promoted",
        "occurred_at": occurred_at,
        "recorded_at": recorded_at,
        "pack_id": target_pack_id,
        "actor": actor,
        "subject_refs": subjects,
        "idempotency_key": idempotency_key,
        "evidence_refs": list(evidence_refs),
        "payload": {
            "source_pack_id": source_pack_id,
            "target_pack_id": target_pack_id,
            "reason": reason,
        },
        "provenance": {
            "method": "explicit_cross_pack_promotion",
        },
    }
