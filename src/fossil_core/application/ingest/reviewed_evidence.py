from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .pack_validation import KnowledgePackValidator
from ...source import SourceSnapshotStore


REVIEWED_EVIDENCE_RECEIPT_VERSION = "fossil.reviewed-evidence-ingest-receipt.v1"
_RAW_LOG_SOURCE_KINDS = frozenset({"raw_ci_log", "raw_build_log", "raw_runtime_log"})


class ReviewedEvidenceIngestError(ValueError):
    """Reviewed evidence cannot satisfy the frozen ingestion policy."""


@dataclass(frozen=True)
class ReviewedSource:
    data: bytes
    source_kind: str
    source_role: str
    locator: Mapping[str, Any]
    retrieved_at: str
    quality: Mapping[str, Any]
    published_at: str | None = None
    version_metadata: Mapping[str, Any] | None = None
    derivation: Mapping[str, Any] | None = None
    media_type: str = "application/octet-stream"


@dataclass(frozen=True)
class ReviewedClaimDraft:
    subject_ref: str
    claim_text: str
    reason: str = ""


def _receipt_id(correlation_id: str, review_ref: str, pack_id: str) -> str:
    digest = hashlib.sha256(
        f"{correlation_id}\x1f{review_ref}\x1f{pack_id}".encode("utf-8")
    ).hexdigest()
    return f"ingest_receipt_{digest[:24]}"


class ReviewedEvidenceIngestService:
    """Provenance-first reviewed evidence ingestion over existing durable contracts.

    This service intentionally cannot emit accepted knowledge. It preserves an
    allowed reviewed source as an immutable source snapshot, constructs only
    ``claim.proposed`` events that reference that source, validates the complete
    proposal batch through the real durable event gate, and only then commits the
    proposals. Shared/common acceptance remains a separate review/promotion act.
    """

    def __init__(
        self,
        *,
        source_store: SourceSnapshotStore,
        event_store: Any,
        pack_validator: KnowledgePackValidator,
    ) -> None:
        self.source_store = source_store
        self.event_store = event_store
        self.pack_validator = pack_validator

    @staticmethod
    def _base_receipt(
        *,
        pack_id: str,
        source_kind: str,
        review_ref: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        return {
            "schema_version": REVIEWED_EVIDENCE_RECEIPT_VERSION,
            "receipt_id": _receipt_id(correlation_id, review_ref, pack_id),
            "authority": "non_authoritative_receipt",
            "pack_id": pack_id,
            "review_ref": review_ref,
            "correlation_id": correlation_id,
            "source": {
                "source_kind": source_kind,
                "preserved": False,
                "artifact_id": None,
                "snapshot_id": None,
            },
            "validation": {
                "pack": "passed",
                "source": "not_run",
                "events": "not_run",
                "provenance": "not_run",
                "evidence": "not_run",
                "ontology": "not_applicable",
            },
            "proposal_event_ids": [],
            "proposal_count": 0,
            "accepted_count": 0,
            "requires_explicit_promotion": True,
            "rejection_reason": None,
        }

    def ingest(
        self,
        *,
        pack_manifest: Mapping[str, Any],
        source: ReviewedSource,
        claims: Sequence[ReviewedClaimDraft],
        review_ref: str,
        actor: Mapping[str, Any],
        occurred_at: str,
        recorded_at: str,
        correlation_id: str,
        requested_outcome: str = "proposed",
    ) -> dict[str, Any]:
        manifest = copy.deepcopy(dict(pack_manifest))
        self.pack_validator.validate(manifest)
        pack_id = str(manifest["pack_id"])
        if pack_id not in manifest["write_targets"]:
            raise ReviewedEvidenceIngestError(
                "reviewed evidence ingest requires the target pack as an explicit write target"
            )
        if not review_ref or not correlation_id:
            raise ReviewedEvidenceIngestError(
                "reviewed evidence ingest requires review_ref and correlation_id"
            )
        if requested_outcome != "proposed":
            raise ReviewedEvidenceIngestError(
                "accepted shared knowledge requires explicit review/promotion; "
                "reviewed evidence ingest emits proposals only"
            )

        receipt = self._base_receipt(
            pack_id=pack_id,
            source_kind=source.source_kind,
            review_ref=review_ref,
            correlation_id=correlation_id,
        )

        if source.source_kind in _RAW_LOG_SOURCE_KINDS:
            receipt["status"] = "rejected"
            receipt["rejection_reason"] = "raw_ci_or_log_noise_not_wholesale_ingestable"
            receipt["validation"]["source"] = "rejected_by_ingest_policy"
            return receipt

        snapshot = self.source_store.put_snapshot(
            source.data,
            locator=source.locator,
            retrieved_at=source.retrieved_at,
            published_at=source.published_at,
            source_role=source.source_role,
            quality=source.quality,
            version_metadata=source.version_metadata,
            derivation=source.derivation,
            media_type=source.media_type,
        )
        artifact_id = str(snapshot["artifact_id"])
        snapshot_id = str(snapshot["snapshot_id"])
        receipt["source"] = {
            "source_kind": source.source_kind,
            "preserved": True,
            "artifact_id": artifact_id,
            "snapshot_id": snapshot_id,
        }
        receipt["validation"]["source"] = "passed"

        if not claims:
            raise ReviewedEvidenceIngestError(
                "reviewed evidence ingest requires at least one synthesis proposal"
            )

        prepared_events: list[dict[str, Any]] = []
        for index, draft in enumerate(claims):
            if not draft.subject_ref.strip():
                raise ReviewedEvidenceIngestError(
                    "reviewed synthesis requires a stable subject_ref"
                )
            if not draft.claim_text.strip():
                raise ReviewedEvidenceIngestError(
                    "reviewed synthesis requires non-empty claim_text"
                )
            event = {
                "schema_version": "dkg.event.v1",
                "event_type": "claim.proposed",
                "occurred_at": occurred_at,
                "recorded_at": recorded_at,
                "pack_id": pack_id,
                "actor": copy.deepcopy(dict(actor)),
                "subject_refs": [draft.subject_ref],
                "correlation_id": correlation_id,
                "idempotency_key": (
                    f"reviewed-evidence-ingest:{correlation_id}:{index}:{draft.subject_ref}"
                ),
                "evidence_refs": [artifact_id],
                "source_snapshot_refs": [snapshot_id],
                "payload": {
                    "claim_text": draft.claim_text,
                    "reason": draft.reason,
                },
                "provenance": {
                    "method": "reviewed_evidence_ingest",
                    "review_ref": review_ref,
                    "source_snapshot_ref": snapshot_id,
                    "prompt_or_policy_ref": "skills/research-ingestion/manifest.json",
                },
            }
            prepared_events.append(self.event_store.validate(event))

        receipt["validation"].update(
            {
                "events": "passed",
                "provenance": "passed",
                "evidence": "passed",
            }
        )

        committed = [self.event_store.commit(event) for event in prepared_events]
        receipt["status"] = "proposed"
        receipt["proposal_event_ids"] = [str(event["event_id"]) for event in committed]
        receipt["proposal_count"] = len(committed)
        return receipt


__all__ = [
    "REVIEWED_EVIDENCE_RECEIPT_VERSION",
    "ReviewedClaimDraft",
    "ReviewedEvidenceIngestError",
    "ReviewedEvidenceIngestService",
    "ReviewedSource",
]
