from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any


PROMOTION_CONTRACT_VERSION = "dkg.promotion.v2"
PromotionSourceResolver = Callable[[str, str, str], Mapping[str, Any] | None]


class PromotionSourceError(ValueError):
    """The exact source meaning for a promotion cannot be resolved safely."""


def build_promotion_event(
    *,
    source_pack_id: str,
    source_pack_revision: str,
    source_event_id: str,
    target_pack_id: str,
    subject_refs: Iterable[str],
    actor: dict[str, Any],
    occurred_at: str,
    recorded_at: str,
    idempotency_key: str,
    evidence_refs: Iterable[str] = (),
    reason: str = "",
) -> dict[str, Any]:
    """Create a self-contained v2 cross-pack promotion event.

    Promotion never mutates the source pack. The target event pins the exact
    mounted source revision and source event that contain the promoted subjects.
    """

    subjects = list(subject_refs)
    if not subjects:
        raise ValueError("promotion requires at least one stable subject reference")
    if source_pack_id == target_pack_id:
        raise ValueError("promotion requires different source and target packs")
    if not source_pack_revision or not source_pack_revision.strip():
        raise ValueError("promotion requires an exact non-empty source pack revision")
    if not source_event_id or not source_event_id.strip():
        raise ValueError("promotion requires a stable source event ID")

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
            "contract_version": PROMOTION_CONTRACT_VERSION,
            "source_pack_id": source_pack_id,
            "source_pack_revision": source_pack_revision,
            "source_event_id": source_event_id,
            "target_pack_id": target_pack_id,
            "reason": reason,
        },
        "provenance": {"method": "explicit_cross_pack_promotion"},
    }


def validate_promotion_source(
    event: Mapping[str, Any],
    *,
    resolver: PromotionSourceResolver | None,
) -> Mapping[str, Any]:
    """Resolve and bind a new accepted promotion to exact source meaning.

    ``resolver`` is the mounted-pack authority seam. It resolves the exact
    ``(source pack_id, source revision, source event_id)`` tuple. A missing,
    redacted, unavailable, or mismatched source therefore fails closed without
    coupling this domain rule to a storage provider.
    """

    payload = event.get("payload")
    if not isinstance(payload, Mapping):
        raise PromotionSourceError("promotion payload must be an object")

    source_pack_id = str(payload.get("source_pack_id", ""))
    source_revision = str(payload.get("source_pack_revision", ""))
    source_event_id = str(payload.get("source_event_id", ""))
    target_pack_id = str(payload.get("target_pack_id", ""))
    durable_pack_id = str(event.get("pack_id", ""))

    if target_pack_id != durable_pack_id:
        raise PromotionSourceError(
            "promotion target_pack_id must equal durable pack_id"
        )
    if source_pack_id == target_pack_id:
        raise PromotionSourceError(
            "promotion requires different source and target packs"
        )
    if resolver is None:
        raise PromotionSourceError(
            "promotion source cannot be accepted without a source resolver"
        )

    try:
        resolved = resolver(source_pack_id, source_revision, source_event_id)
    except Exception as exc:
        raise PromotionSourceError(
            "promotion source event is not resolvable at the pinned source revision"
        ) from exc
    if resolved is None:
        raise PromotionSourceError(
            "promotion source event is not resolvable at the pinned source revision"
        )

    resolved_pack_id = str(resolved.get("pack_id", ""))
    resolved_event_id = str(resolved.get("event_id", ""))
    if resolved_pack_id != source_pack_id:
        raise PromotionSourceError(
            "resolved source pack does not match promotion source_pack_id"
        )
    if resolved_event_id != source_event_id:
        raise PromotionSourceError(
            "resolved source event does not match promotion source_event_id"
        )

    promoted_subjects = event.get("subject_refs")
    source_subjects = resolved.get("subject_refs")
    if not isinstance(promoted_subjects, list) or not promoted_subjects:
        raise PromotionSourceError("promotion requires stable subject_refs")
    if not isinstance(source_subjects, list) or not set(promoted_subjects).issubset(
        set(source_subjects)
    ):
        raise PromotionSourceError(
            "promotion subject_refs must be present in the pinned source event"
        )

    return resolved


__all__ = [
    "PROMOTION_CONTRACT_VERSION",
    "PromotionSourceError",
    "PromotionSourceResolver",
    "build_promotion_event",
    "validate_promotion_source",
]
