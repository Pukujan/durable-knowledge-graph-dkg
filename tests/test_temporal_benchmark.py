from __future__ import annotations

import json
from pathlib import Path

from dkg.temporal_benchmark import TemporalPhase, TemporalQueryCase, run_temporal_evolution_benchmark


AI = "pack_f024177f89a5442db84171c3dd7f58e5"
OLD = "clm_old_sqlite_000000000001"
DEPENDENT = "clm_sqlite_proto_0000000001"
NEW = "clm_durable_core_000000000001"
UNRELATED = "clm_unrelated_rag_00000000001"
DEPENDS = "rel_depends_sqlite_000000001"
SUPERSEDES = "rel_durable_supersedes_000001"


def _write_event(root: Path, event: dict) -> None:
    event_id = str(event["event_id"])
    suffix = event_id.removeprefix("evt_")
    path = root / "events" / suffix[:2] / f"{event_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(event), encoding="utf-8")


def _event(
    event_id: str,
    event_type: str,
    subject_refs: list[str],
    payload: dict,
    recorded_at: str,
) -> dict:
    return {
        "schema_version": "dkg.event.v1",
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": recorded_at,
        "recorded_at": recorded_at,
        "pack_id": AI,
        "actor": {"actor_type": "importer", "actor_id": "temporal-test"},
        "subject_refs": subject_refs,
        "payload": payload,
    }


def _fixture(tmp_path: Path) -> Path:
    root = tmp_path / "ai"
    root.mkdir()
    (root / "manifest.json").write_text(
        json.dumps({"pack_id": AI, "event_roots": ["events"]}),
        encoding="utf-8",
    )

    events = [
        _event(
            "evt_000000000000000000000001",
            "claim.proposed",
            [OLD],
            {"claim_text": "SQLite is the canonical corpus database."},
            "2026-08-10T05:26:00Z",
        ),
        _event(
            "evt_000000000000000000000002",
            "claim.state_changed",
            [OLD],
            {"from_state": "proposed", "to_state": "supported"},
            "2026-08-10T05:26:01Z",
        ),
        _event(
            "evt_000000000000000000000003",
            "claim.proposed",
            [DEPENDENT],
            {"claim_text": "The SQLite prototype depends on the canonical SQLite premise."},
            "2026-08-10T05:26:02Z",
        ),
        _event(
            "evt_000000000000000000000004",
            "claim.state_changed",
            [DEPENDENT],
            {"from_state": "proposed", "to_state": "supported"},
            "2026-08-10T05:26:03Z",
        ),
        _event(
            "evt_000000000000000000000005",
            "relation.proposed",
            [DEPENDS, DEPENDENT, OLD],
            {
                "relation_id": DEPENDS,
                "relation_type": "DEPENDS_ON",
                "source_ref": DEPENDENT,
                "target_ref": OLD,
                "state": "active",
            },
            "2026-08-10T05:26:04Z",
        ),
        _event(
            "evt_000000000000000000000006",
            "claim.proposed",
            [NEW],
            {
                "claim_text": (
                    "Immutable evidence plus append-only knowledge events are durable truth; "
                    "retrieval systems are rebuildable projections."
                )
            },
            "2026-08-10T05:26:05Z",
        ),
        _event(
            "evt_000000000000000000000007",
            "claim.state_changed",
            [NEW],
            {"from_state": "proposed", "to_state": "supported"},
            "2026-08-10T05:26:06Z",
        ),
        _event(
            "evt_000000000000000000000008",
            "relation.proposed",
            [SUPERSEDES, NEW, OLD],
            {
                "relation_id": SUPERSEDES,
                "relation_type": "SUPERSEDES",
                "source_ref": NEW,
                "target_ref": OLD,
                "state": "active",
            },
            "2026-08-10T05:26:07Z",
        ),
        _event(
            "evt_000000000000000000000009",
            "claim.superseded",
            [OLD],
            {"from_state": "supported", "superseded_by": NEW},
            "2026-08-10T05:26:08Z",
        ),
        _event(
            "evt_000000000000000000000010",
            "claim.proposed",
            [UNRELATED],
            {"claim_text": "Retrieved content is untrusted data."},
            "2026-08-10T14:02:00Z",
        ),
        _event(
            "evt_000000000000000000000011",
            "claim.state_changed",
            [UNRELATED],
            {"from_state": "proposed", "to_state": "supported"},
            "2026-08-10T14:02:01Z",
        ),
    ]
    for event in events:
        _write_event(root, event)
    return root


def test_temporal_benchmark_replays_current_and_historical_truth(tmp_path, monkeypatch):
    root = _fixture(tmp_path)
    monkeypatch.setattr("dkg.pack_corpus.validate_pack_fixtures", lambda *args, **kwargs: None)

    current_new = TemporalQueryCase(
        case_id="current-durable-core",
        query="What is the current durable truth using immutable evidence and append-only knowledge events?",
        pack_ids=(AI,),
        relevant_ids=frozenset({NEW}),
    )
    historical_old = TemporalQueryCase(
        case_id="historical-sqlite",
        query="What was the former canonical corpus database SQLite premise?",
        pack_ids=(AI,),
        relevant_ids=frozenset({OLD}),
    )
    phases = [
        TemporalPhase(
            phase_id="sqlite-current",
            as_of_recorded_at="2026-08-10T05:26:04Z",
            expected_states={OLD: "supported", DEPENDENT: "supported", DEPENDS: "active"},
            queries=(
                TemporalQueryCase(
                    case_id="current-sqlite",
                    query="What is the current canonical corpus database SQLite premise?",
                    pack_ids=(AI,),
                    relevant_ids=frozenset({OLD}),
                ),
            ),
        ),
        TemporalPhase(
            phase_id="durable-core-current",
            as_of_recorded_at="2026-08-10T05:26:08Z",
            expected_states={
                OLD: "superseded",
                DEPENDENT: "stale_pending_review",
                NEW: "supported",
                SUPERSEDES: "active",
            },
            queries=(current_new, historical_old),
        ),
        TemporalPhase(
            phase_id="later-corpus-growth",
            as_of_recorded_at=None,
            expected_states={
                OLD: "superseded",
                DEPENDENT: "stale_pending_review",
                NEW: "supported",
                UNRELATED: "supported",
            },
            queries=(current_new, historical_old),
        ),
    ]

    report = run_temporal_evolution_benchmark(
        [root],
        schemas_root=tmp_path / "schemas",
        phases=phases,
    )

    assert report["passed"] is True
    assert report["phase_count"] == 3
    assert report["authority_rule"] == "durable lifecycle/lineage state outranks retrieval score"

    second = report["phases"][1]
    changes = {item["id"]: item for item in second["transition_from_previous"]["state_changes"]}
    assert changes[OLD]["before_state"] == "supported"
    assert changes[OLD]["after_state"] == "superseded"
    assert changes[DEPENDENT]["before_state"] == "supported"
    assert changes[DEPENDENT]["after_state"] == "stale_pending_review"

    stability = report["repeated_query_stability"]
    assert stability["current-durable-core"]["all_full_recall"] is True
    assert stability["current-durable-core"]["no_current_state_leakage"] is True
    assert stability["historical-sqlite"]["all_full_recall"] is True


def test_temporal_benchmark_rejects_wrong_expected_state(tmp_path, monkeypatch):
    root = _fixture(tmp_path)
    monkeypatch.setattr("dkg.pack_corpus.validate_pack_fixtures", lambda *args, **kwargs: None)

    report = run_temporal_evolution_benchmark(
        [root],
        schemas_root=tmp_path / "schemas",
        phases=[
            TemporalPhase(
                phase_id="bad-expectation",
                as_of_recorded_at="2026-08-10T05:26:08Z",
                expected_states={OLD: "supported"},
                queries=(),
            )
        ],
    )

    assert report["passed"] is False
    check = report["phases"][0]["state_checks"][0]
    assert check["observed_state"] == "superseded"
    assert check["passed"] is False
