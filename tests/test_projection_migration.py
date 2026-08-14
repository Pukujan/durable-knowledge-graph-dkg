from __future__ import annotations

import asyncio
import json
from dataclasses import replace

import pytest

from fossil_core.contracts import ProjectionReceipt
from fossil_core.projection.graphiti import GraphitiProjectionAdapter
from fossil_core.projection.ledger import ProjectionLedger
from fossil_core.projection.migration import (
    ProjectionComparator,
    ProjectionMigrationHarness,
    ProjectionSwitchLedger,
    SemanticSnapshot,
    ordered_events,
)


COMMON = "pack_269099f7b2ba43b7a99b9427d64092de"
AI = "pack_f024177f89a5442db84171c3dd7f58e5"


def event(
    n: int,
    event_type: str,
    pack_id: str,
    subject: str,
    payload: dict,
    *,
    occurred_at: str | None = None,
) -> dict:
    recorded = f"2026-08-09T20:{n:02d}:00Z"
    return {
        "schema_version": "dkg.event.v1",
        "event_id": f"evt_{n:032x}",
        "event_type": event_type,
        "occurred_at": occurred_at or recorded,
        "recorded_at": recorded,
        "pack_id": pack_id,
        "actor": {"actor_type": "system", "actor_id": "migration-fixture"},
        "subject_refs": [subject],
        "payload": payload,
        "provenance": {
            "method": "migration-fixture",
            "software_commit": "test",
            "ontology_version": "1.0.0",
        },
    }


def migration_events() -> list[dict]:
    """Exercise lifecycle, ontology evolution, time, and cross-pack references."""

    return [
        event(1, "claim.proposed", COMMON, "clm_premise", {"claim_text": "premise"}),
        event(
            2,
            "claim.state_changed",
            COMMON,
            "clm_premise",
            {"from_state": "proposed", "to_state": "supported"},
        ),
        event(3, "claim.proposed", AI, "clm_dependent", {"claim_text": "dependent"}),
        event(
            4,
            "claim.state_changed",
            AI,
            "clm_dependent",
            {"from_state": "proposed", "to_state": "supported"},
        ),
        event(5, "claim.proposed", AI, "clm_disputed", {"claim_text": "disputed"}),
        event(
            6,
            "claim.state_changed",
            AI,
            "clm_disputed",
            {"from_state": "proposed", "to_state": "disputed"},
        ),
        event(
            7,
            "relation.proposed",
            AI,
            "clm_dependent",
            {
                "relation_id": "rel_cross_pack_dep",
                "relation_type": "DEPENDS_ON",
                "source_ref": "clm_dependent",
                "target_ref": "clm_premise",
                "state": "active",
            },
        ),
        event(
            8,
            "ontology.concept_renamed",
            COMMON,
            "concept_old",
            {"concept_id": "concept_old", "new_label": "Concept New"},
        ),
        event(
            9,
            "ontology.concept_split",
            COMMON,
            "concept_new",
            {"source_concept_id": "concept_new", "target_concept_ids": ["concept_a", "concept_b"]},
        ),
        event(
            10,
            "ontology.concept_merged",
            COMMON,
            "concept_merged",
            {"source_concept_ids": ["concept_a", "concept_b"], "target_concept_id": "concept_merged"},
        ),
        event(
            11,
            "claim.superseded",
            COMMON,
            "clm_premise",
            {"from_state": "supported", "superseded_by": "clm_replacement"},
            occurred_at="2026-07-01T00:00:00Z",
        ),
        event(12, "claim.proposed", COMMON, "clm_replacement", {"claim_text": "replacement"}),
    ]


def test_semantic_snapshot_preserves_stable_migration_invariants():
    fixture = migration_events()
    snapshot = SemanticSnapshot.from_events(reversed(fixture))

    assert snapshot.event_ids == tuple(event["event_id"] for event in fixture)
    assert ("clm_disputed", "disputed") in snapshot.claim_states
    assert ("clm_dependent", "stale_pending_review") in snapshot.claim_states
    assert (
        "rel_cross_pack_dep",
        "DEPENDS_ON",
        "clm_dependent",
        "clm_premise",
        "active",
    ) in snapshot.relation_states
    namespaces = dict(snapshot.namespace_subject_refs)
    assert "clm_premise" in namespaces[COMMON]
    assert "clm_dependent" in namespaces[AI]
    event_types = dict(snapshot.event_type_counts)
    assert event_types["ontology.concept_renamed"] == 1
    assert event_types["ontology.concept_split"] == 1
    assert event_types["ontology.concept_merged"] == 1


def test_recorded_at_not_filesystem_or_occurred_at_controls_replay_order():
    events = migration_events()
    # The supersession represents an older real-world time, but was recorded later.
    ordered = ordered_events([events[10], events[0], events[1]])
    assert [item["event_id"] for item in ordered] == [
        events[0]["event_id"],
        events[1]["event_id"],
        events[10]["event_id"],
    ]


def test_build_scoped_ledger_does_not_inherit_stale_applied_markers(tmp_path):
    event_id = migration_events()[0]["event_id"]
    build_a = ProjectionLedger(tmp_path, "graphiti-neo4j", build_id="build-a")
    build_b = ProjectionLedger(tmp_path, "graphiti-neo4j", build_id="build-b")

    build_a.record_applied(event_id, {"group_id": COMMON})

    assert build_a.is_applied(event_id)
    assert not build_b.is_applied(event_id)
    assert build_a.get_applied(event_id)["projection_build_id"] == "build-a"


def test_blue_green_switch_requires_equal_semantics_and_passing_benchmarks(tmp_path):
    expected = SemanticSnapshot.from_events(migration_events())
    switch_ledger = ProjectionSwitchLedger(tmp_path / "active")
    harness = ProjectionMigrationHarness(switch_ledger)

    report, switch = harness.compare_and_switch(
        expected=expected,
        current=expected,
        current_slot="blue",
        candidate=expected,
        candidate_slot="green",
        benchmarks={"lineage_reconstruction": True, "namespace_isolation": True},
        build_manifest={"projection_build_id": "green-build-1", "software_commit": "abc"},
        switched_at="2026-08-09T21:00:00+00:00",
    )

    assert report.passed
    assert switch["from_slot"] == "blue"
    assert switch["to_slot"] == "green"
    assert switch_ledger.active_slot() == "green"
    assert switch["expected_semantic_digest"] == expected.digest()


def test_switch_ledger_rejects_stale_source_after_activation(tmp_path):
    expected = SemanticSnapshot.from_events(migration_events())
    switch_ledger = ProjectionSwitchLedger(tmp_path / "active")
    harness = ProjectionMigrationHarness(switch_ledger)

    harness.compare_and_switch(
        expected=expected,
        current=expected,
        current_slot="blue",
        candidate=expected,
        candidate_slot="green",
        build_manifest={"projection_build_id": "green-build-1"},
        switched_at="2026-08-09T21:00:00+00:00",
    )
    assert switch_ledger.active_slot() == "green"

    with pytest.raises(ValueError, match="does not match active projection"):
        harness.compare_and_switch(
            expected=expected,
            current=expected,
            current_slot="blue",
            candidate=expected,
            candidate_slot="red",
            build_manifest={"projection_build_id": "red-build-stale"},
            switched_at="2026-08-09T21:05:00+00:00",
        )
    assert switch_ledger.active_slot() == "green"


def test_blue_green_switch_rejects_semantic_or_benchmark_mismatch(tmp_path):
    expected = SemanticSnapshot.from_events(migration_events())
    missing_event_candidate = replace(expected, event_ids=expected.event_ids[:-1])
    switch_ledger = ProjectionSwitchLedger(tmp_path / "active")
    harness = ProjectionMigrationHarness(switch_ledger)

    with pytest.raises(ValueError, match="event_ids"):
        harness.compare_and_switch(
            expected=expected,
            candidate=missing_event_candidate,
            candidate_slot="green",
            build_manifest={"projection_build_id": "green-build-bad"},
        )
    assert switch_ledger.active_slot() is None

    with pytest.raises(ValueError, match="lineage_reconstruction"):
        harness.compare_and_switch(
            expected=expected,
            candidate=expected,
            candidate_slot="green",
            benchmarks={"lineage_reconstruction": False},
            build_manifest={"projection_build_id": "green-build-bad-benchmark"},
        )
    assert switch_ledger.active_slot() is None


def test_destructive_rebuild_destroys_first_and_rejects_failed_receipts(tmp_path):
    calls: list[str] = []
    harness = ProjectionMigrationHarness(ProjectionSwitchLedger(tmp_path / "switches"))

    async def destroy():
        calls.append("destroy")

    async def rebuild_ok():
        calls.append("rebuild")
        return [ProjectionReceipt("fake", "1", "evt_a", "applied")]

    receipts = asyncio.run(harness.destructive_rebuild(destroy=destroy, rebuild=rebuild_ok))
    assert calls == ["destroy", "rebuild"]
    assert receipts[0].status == "applied"

    async def rebuild_bad():
        return [ProjectionReceipt("fake", "1", "evt_a", "failed", "boom")]

    with pytest.raises(RuntimeError, match="failed receipt"):
        asyncio.run(harness.destructive_rebuild(destroy=destroy, rebuild=rebuild_bad))


class FakeGraphiti:
    def __init__(self):
        self.calls: list[dict] = []

    async def add_episode(self, **kwargs):
        self.calls.append(kwargs)


def test_graphiti_rebuild_replays_sequentially_in_recorded_order(tmp_path):
    events_root = tmp_path / "events"
    # Store events in deliberately misleading hash-path order.
    early = migration_events()[0]
    later = migration_events()[1]
    for directory, item in (("00", later), ("ff", early)):
        path = events_root / directory / f"{item['event_id']}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(item), encoding="utf-8")

    client = FakeGraphiti()
    adapter = GraphitiProjectionAdapter(
        client=client,
        ledger=ProjectionLedger(tmp_path / "ledger", "graphiti-neo4j", build_id="rebuild-1"),
        build_manifest={"projection_build_id": "rebuild-1"},
        episode_type_json="json",
    )

    receipts = asyncio.run(adapter.rebuild_async(events_root=events_root))

    assert [receipt.status for receipt in receipts] == ["applied", "applied"]
    projected_ids = [json.loads(call["episode_body"])["event_id"] for call in client.calls]
    assert projected_ids == [early["event_id"], later["event_id"]]
