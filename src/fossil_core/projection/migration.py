from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterable, Mapping, Sequence

from fossil_core.io import publish_immutable
from fossil_core.lifecycle import KnowledgeState


def canonical_event_order(event: Mapping[str, Any]) -> tuple[str, str]:
    """Stable replay order for immutable events.

    `recorded_at` is the corpus commit time and therefore the primary ordering
    signal for state reconstruction. `event_id` is a deterministic tie breaker.
    Filesystem paths and graph-native identifiers are deliberately excluded.
    """

    return str(event["recorded_at"]), str(event["event_id"])


def ordered_events(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(events, key=canonical_event_order)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True)
class SemanticSnapshot:
    """Projection-independent semantic invariants used for migration checks.

    Graph-native node/edge IDs are intentionally absent. A projection inspector
    may reconstruct this shape from a database, while the expected snapshot can
    be built directly from immutable FOSSIL events.
    """

    event_ids: tuple[str, ...]
    pack_event_ids: tuple[tuple[str, tuple[str, ...]], ...]
    namespace_subject_refs: tuple[tuple[str, tuple[str, ...]], ...]
    provenance_by_event: tuple[tuple[str, str], ...]
    claim_states: tuple[tuple[str, str], ...]
    relation_states: tuple[tuple[str, str, str, str, str], ...]
    event_type_counts: tuple[tuple[str, int], ...]

    @classmethod
    def from_events(cls, events: Iterable[dict[str, Any]]) -> "SemanticSnapshot":
        replay = ordered_events(events)
        state = KnowledgeState.replay(replay)

        pack_events: dict[str, list[str]] = {}
        namespace_subjects: dict[str, set[str]] = {}
        event_type_counts: dict[str, int] = {}
        provenance: list[tuple[str, str]] = []

        for event in replay:
            event_id = str(event["event_id"])
            pack_id = str(event["pack_id"])
            pack_events.setdefault(pack_id, []).append(event_id)
            namespace_subjects.setdefault(pack_id, set()).update(
                str(ref) for ref in event.get("subject_refs", [])
            )
            event_type = str(event["event_type"])
            event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
            provenance.append(
                (
                    event_id,
                    _canonical_json(
                        {
                            "actor": event.get("actor"),
                            "caused_by_event_ids": event.get("caused_by_event_ids", []),
                            "evidence_refs": event.get("evidence_refs", []),
                            "source_snapshot_refs": event.get("source_snapshot_refs", []),
                            "provenance": event.get("provenance", {}),
                        }
                    ),
                )
            )

        relations = tuple(
            sorted(
                (
                    relation_id,
                    relation.relation_type,
                    relation.source_ref,
                    relation.target_ref,
                    relation.state,
                )
                for relation_id, relation in state.relations.items()
            )
        )

        return cls(
            event_ids=tuple(event["event_id"] for event in replay),
            pack_event_ids=tuple(
                (pack_id, tuple(event_ids))
                for pack_id, event_ids in sorted(pack_events.items())
            ),
            namespace_subject_refs=tuple(
                (pack_id, tuple(sorted(subject_refs)))
                for pack_id, subject_refs in sorted(namespace_subjects.items())
            ),
            provenance_by_event=tuple(sorted(provenance)),
            claim_states=tuple(sorted(state.claims.items())),
            relation_states=relations,
            event_type_counts=tuple(sorted(event_type_counts.items())),
        )

    def digest(self) -> str:
        payload = _canonical_json(asdict(self)).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class ComparisonReport:
    current_slot: str | None
    candidate_slot: str
    expected_digest: str
    candidate_digest: str
    current_digest: str | None
    mismatches: tuple[str, ...]
    benchmark_results: tuple[tuple[str, bool], ...]

    @property
    def passed(self) -> bool:
        return not self.mismatches and all(result for _, result in self.benchmark_results)


class ProjectionComparator:
    """Compare projection semantics without depending on physical graph IDs."""

    FIELDS = (
        "event_ids",
        "pack_event_ids",
        "namespace_subject_refs",
        "provenance_by_event",
        "claim_states",
        "relation_states",
        "event_type_counts",
    )

    @classmethod
    def compare(
        cls,
        *,
        expected: SemanticSnapshot,
        candidate: SemanticSnapshot,
        candidate_slot: str,
        current: SemanticSnapshot | None = None,
        current_slot: str | None = None,
        benchmarks: Mapping[str, bool] | None = None,
    ) -> ComparisonReport:
        mismatches = tuple(
            field for field in cls.FIELDS if getattr(expected, field) != getattr(candidate, field)
        )
        benchmark_results = tuple(sorted((benchmarks or {}).items()))
        return ComparisonReport(
            current_slot=current_slot,
            candidate_slot=candidate_slot,
            expected_digest=expected.digest(),
            candidate_digest=candidate.digest(),
            current_digest=current.digest() if current is not None else None,
            mismatches=mismatches,
            benchmark_results=benchmark_results,
        )


class ProjectionSwitchLedger:
    """Append-only operational history of active projection selection.

    Projection selection is not canonical knowledge, but preserving switch history
    makes migrations explainable and allows rollback by writing another switch.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.switch_root = self.root / "switches"

    @staticmethod
    def _canonical(value: Mapping[str, Any]) -> bytes:
        return (_canonical_json(value) + "\n").encode("utf-8")

    def record_switch(
        self,
        *,
        from_slot: str | None,
        to_slot: str,
        comparison: ComparisonReport,
        build_manifest: Mapping[str, Any],
        switched_at: str | None = None,
    ) -> dict[str, Any]:
        if not comparison.passed:
            raise ValueError("candidate projection cannot become active before checks pass")
        if comparison.candidate_slot != to_slot:
            raise ValueError("comparison candidate slot does not match switch target")

        active = self.active_slot()
        if active is not None and from_slot != active:
            raise ValueError(
                f"switch source {from_slot!r} does not match active projection {active!r}"
            )

        timestamp = switched_at or datetime.now(timezone.utc).isoformat()
        switch_id = f"switch_{uuid.uuid4().hex}"
        payload = {
            "switch_id": switch_id,
            "switched_at": timestamp,
            "from_slot": from_slot,
            "to_slot": to_slot,
            "expected_semantic_digest": comparison.expected_digest,
            "candidate_semantic_digest": comparison.candidate_digest,
            "mismatches": list(comparison.mismatches),
            "benchmark_results": dict(comparison.benchmark_results),
            "build_manifest": dict(build_manifest),
        }
        path = self.switch_root / f"{timestamp.replace(':', '_')}-{switch_id}.json"
        if not publish_immutable(path, self._canonical(payload)):
            raise RuntimeError(f"projection switch record already exists: {path}")
        return payload

    def iter_switches(self) -> list[dict[str, Any]]:
        records = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in self.switch_root.glob("*.json")
        ]
        return sorted(records, key=lambda record: (record["switched_at"], record["switch_id"]))

    def active_slot(self) -> str | None:
        records = self.iter_switches()
        return records[-1]["to_slot"] if records else None


class ProjectionMigrationHarness:
    """Orchestrate destructive rebuild and guarded blue/green activation."""

    def __init__(self, switch_ledger: ProjectionSwitchLedger):
        self.switch_ledger = switch_ledger

    async def destructive_rebuild(
        self,
        *,
        destroy: Callable[[], Awaitable[None]],
        rebuild: Callable[[], Awaitable[Sequence[Any]]],
    ) -> Sequence[Any]:
        await destroy()
        receipts = await rebuild()
        failed = [receipt for receipt in receipts if getattr(receipt, "status", None) == "failed"]
        if failed:
            raise RuntimeError(f"projection rebuild contained {len(failed)} failed receipt(s)")
        return receipts

    def compare_and_switch(
        self,
        *,
        expected: SemanticSnapshot,
        candidate: SemanticSnapshot,
        candidate_slot: str,
        build_manifest: Mapping[str, Any],
        current: SemanticSnapshot | None = None,
        current_slot: str | None = None,
        benchmarks: Mapping[str, bool] | None = None,
        switched_at: str | None = None,
    ) -> tuple[ComparisonReport, dict[str, Any]]:
        report = ProjectionComparator.compare(
            expected=expected,
            candidate=candidate,
            candidate_slot=candidate_slot,
            current=current,
            current_slot=current_slot,
            benchmarks=benchmarks,
        )
        if not report.passed:
            raise ValueError(
                "candidate projection failed migration checks: "
                + ", ".join(report.mismatches or [
                    name for name, passed in report.benchmark_results if not passed
                ])
            )
        switch = self.switch_ledger.record_switch(
            from_slot=current_slot,
            to_slot=candidate_slot,
            comparison=report,
            build_manifest=build_manifest,
            switched_at=switched_at,
        )
        return report, switch
