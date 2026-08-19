from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from fossil_core.temporal_benchmark import (
    DependencyImpactExpectation,
    DisagreementExpectation,
    LongitudinalPhase,
    PositionChangeExpectation,
    TemporalQueryCase,
    run_longitudinal_epistemic_benchmark,
)


PACK = "pack_f024177f89a5442db84171c3dd7f58e5"
ASSUMPTION = "clm_longitudinal_assumption_000001"
DEPENDENT = "clm_longitudinal_dependent_000001"
REPLACEMENT = "clm_longitudinal_replacement_000001"
DECISION = "dec_longitudinal_decision_000001"
DEPENDS_CLAIM = "rel_longitudinal_depends_claim_000001"
DEPENDS_DECISION = "rel_longitudinal_depends_decision_000001"
CONTRADICTS = "rel_longitudinal_contradicts_000001"
LATER_ONTOLOGY = "rel_longitudinal_later_ontology_000001"
_BASE_TIME = datetime(2026, 8, 19, 17, 0, tzinfo=timezone.utc)


def _timestamp(index: int) -> str:
    value = _BASE_TIME + timedelta(minutes=index)
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _event(
    index: int,
    event_type: str,
    subject_refs: list[str],
    payload: dict,
    *,
    evidence_refs: list[str] | None = None,
    caused_by_event_ids: list[str] | None = None,
) -> dict:
    value = {
        "schema_version": "dkg.event.v1",
        "event_id": f"evt_longitudinal_{index:018d}",
        "event_type": event_type,
        "occurred_at": _timestamp(index),
        "recorded_at": _timestamp(index),
        "pack_id": PACK,
        "actor": {"actor_type": "system", "actor_id": "longitudinal-benchmark"},
        "subject_refs": subject_refs,
        "payload": payload,
    }
    if evidence_refs is not None:
        value["evidence_refs"] = evidence_refs
    if caused_by_event_ids is not None:
        value["caused_by_event_ids"] = caused_by_event_ids
    return value


def _write_fixture(root: Path, events: list[dict]) -> Path:
    root.mkdir(parents=True)
    (root / "manifest.json").write_text(
        json.dumps({"pack_id": PACK, "event_roots": ["events"]}),
        encoding="utf-8",
    )
    # Write out of order so replay correctness cannot depend on filesystem order.
    for event in reversed(events):
        event_id = str(event["event_id"])
        suffix = event_id.removeprefix("evt_")
        path = root / "events" / suffix[:2] / f"{event_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(event), encoding="utf-8")
    return root


def _evolution_events() -> list[dict]:
    proposed_old = _event(
        0,
        "claim.proposed",
        [ASSUMPTION],
        {"claim_text": "SQLite is the canonical corpus database."},
        evidence_refs=["ev_sqlite_design_note"],
    )
    supported_old = _event(
        1,
        "claim.state_changed",
        [ASSUMPTION],
        {"from_state": "proposed", "to_state": "supported"},
        evidence_refs=["ev_sqlite_prototype_result"],
        caused_by_event_ids=[proposed_old["event_id"]],
    )
    proposed_dependent = _event(
        2,
        "claim.proposed",
        [DEPENDENT],
        {"claim_text": "The prototype should build around the canonical SQLite premise."},
        evidence_refs=["ev_prototype_plan"],
    )
    supported_dependent = _event(
        3,
        "claim.state_changed",
        [DEPENDENT],
        {"from_state": "proposed", "to_state": "supported"},
        evidence_refs=["ev_prototype_review"],
    )
    depends_claim = _event(
        4,
        "relation.proposed",
        [DEPENDS_CLAIM, DEPENDENT, ASSUMPTION],
        {
            "relation_id": DEPENDS_CLAIM,
            "relation_type": "DEPENDS_ON",
            "source_ref": DEPENDENT,
            "source_type": "Claim",
            "target_ref": ASSUMPTION,
            "target_type": "Assumption",
            "ontology_ref": "dkg.core@1.0.0",
            "state": "active",
        },
    )
    depends_decision = _event(
        5,
        "relation.proposed",
        [DEPENDS_DECISION, DECISION, ASSUMPTION],
        {
            "relation_id": DEPENDS_DECISION,
            "relation_type": "DEPENDS_ON",
            "source_ref": DECISION,
            "source_type": "Decision",
            "target_ref": ASSUMPTION,
            "target_type": "Assumption",
            "ontology_ref": "dkg.core@1.0.0",
            "state": "active",
        },
        evidence_refs=["ev_architecture_decision_record"],
    )
    proposed_new = _event(
        6,
        "claim.proposed",
        [REPLACEMENT],
        {"claim_text": "Append-only durable events are canonical; SQLite was only a prototype."},
        evidence_refs=["ev_durable_store_proof"],
    )
    supported_new = _event(
        7,
        "claim.state_changed",
        [REPLACEMENT],
        {"from_state": "proposed", "to_state": "supported"},
        evidence_refs=["ev_rebuild_proof"],
        caused_by_event_ids=[proposed_new["event_id"]],
    )
    contradiction = _event(
        8,
        "relation.proposed",
        [CONTRADICTS, REPLACEMENT, ASSUMPTION],
        {
            "relation_id": CONTRADICTS,
            "relation_type": "CONTRADICTS",
            "source_ref": REPLACEMENT,
            "source_type": "Claim",
            "target_ref": ASSUMPTION,
            "target_type": "Assumption",
            "ontology_ref": "dkg.core@1.0.0",
            "state": "active",
        },
        evidence_refs=["ev_durable_store_proof", "ev_rebuild_proof"],
    )
    disputed_old = _event(
        9,
        "claim.state_changed",
        [ASSUMPTION],
        {"from_state": "supported", "to_state": "disputed"},
        evidence_refs=["ev_durable_store_proof"],
        caused_by_event_ids=[contradiction["event_id"]],
    )
    superseded_old = _event(
        10,
        "claim.superseded",
        [ASSUMPTION],
        {"from_state": "disputed", "superseded_by": REPLACEMENT},
        evidence_refs=["ev_rebuild_proof"],
        caused_by_event_ids=[supported_new["event_id"], contradiction["event_id"]],
    )
    later_ontology = _event(
        11,
        "relation.proposed",
        [LATER_ONTOLOGY, REPLACEMENT, DEPENDENT],
        {
            "relation_id": LATER_ONTOLOGY,
            "relation_type": "RELATED_TO",
            "source_ref": REPLACEMENT,
            "source_type": "Claim",
            "target_ref": DEPENDENT,
            "target_type": "Claim",
            "ontology_ref": "dkg.core@2.0.0",
            "state": "active",
        },
    )
    return [
        proposed_old,
        supported_old,
        proposed_dependent,
        supported_dependent,
        depends_claim,
        depends_decision,
        proposed_new,
        supported_new,
        contradiction,
        disputed_old,
        superseded_old,
        later_ontology,
    ]


def _phases(events: list[dict]) -> list[LongitudinalPhase]:
    historical_old = TemporalQueryCase(
        case_id="historical-sqlite",
        # Existing retrieval policy intentionally requires an explicit temporal cue;
        # bare "Was ...?" remains neutral because it can ask about current acceptance.
        query="What historical canonical SQLite premise was superseded?",
        pack_ids=(PACK,),
        relevant_ids=frozenset({ASSUMPTION}),
    )
    current_new = TemporalQueryCase(
        case_id="current-durable-store",
        query="What is the current durable canonical storage position?",
        pack_ids=(PACK,),
        relevant_ids=frozenset({REPLACEMENT}),
    )
    contradiction_id = events[8]["event_id"]
    superseded_id = events[10]["event_id"]

    return [
        LongitudinalPhase(
            phase_id="before-challenge",
            as_of_recorded_at=_timestamp(5),
            expected_states={ASSUMPTION: "supported", DEPENDENT: "supported"},
            queries=(historical_old,),
        ),
        LongitudinalPhase(
            phase_id="disputed",
            as_of_recorded_at=_timestamp(9),
            expected_states={
                ASSUMPTION: "disputed",
                DEPENDENT: "supported",
                REPLACEMENT: "supported",
                CONTRADICTS: "active",
            },
            queries=(current_new, historical_old),
            expected_position_changes=(
                PositionChangeExpectation(
                    subject_id=ASSUMPTION,
                    event_id=events[9]["event_id"],
                    to_state="disputed",
                    evidence_refs=frozenset({"ev_durable_store_proof"}),
                    caused_by_event_ids=frozenset({contradiction_id}),
                ),
            ),
            expected_dependency_impacts=(
                DependencyImpactExpectation(
                    dependent_ref=DECISION,
                    premise_ref=ASSUMPTION,
                    relation_id=DEPENDS_DECISION,
                    premise_state="disputed",
                ),
                DependencyImpactExpectation(
                    dependent_ref=DEPENDENT,
                    premise_ref=ASSUMPTION,
                    relation_id=DEPENDS_CLAIM,
                    premise_state="disputed",
                ),
            ),
            expected_disagreements=(
                DisagreementExpectation(
                    relation_id=CONTRADICTS,
                    relation_type="CONTRADICTS",
                    source_ref=REPLACEMENT,
                    target_ref=ASSUMPTION,
                ),
            ),
        ),
        LongitudinalPhase(
            phase_id="superseded-after-ontology-evolution",
            as_of_recorded_at=None,
            expected_states={
                ASSUMPTION: "superseded",
                DEPENDENT: "stale_pending_review",
                REPLACEMENT: "supported",
                CONTRADICTS: "active",
                LATER_ONTOLOGY: "active",
            },
            queries=(current_new, historical_old),
            expected_position_changes=(
                PositionChangeExpectation(
                    subject_id=ASSUMPTION,
                    event_id=superseded_id,
                    to_state="superseded",
                    evidence_refs=frozenset({"ev_rebuild_proof"}),
                    caused_by_event_ids=frozenset(
                        {events[7]["event_id"], contradiction_id}
                    ),
                ),
            ),
            expected_dependency_impacts=(
                DependencyImpactExpectation(
                    dependent_ref=DECISION,
                    premise_ref=ASSUMPTION,
                    relation_id=DEPENDS_DECISION,
                    premise_state="superseded",
                ),
                DependencyImpactExpectation(
                    dependent_ref=DEPENDENT,
                    premise_ref=ASSUMPTION,
                    relation_id=DEPENDS_CLAIM,
                    premise_state="superseded",
                ),
            ),
            expected_disagreements=(
                DisagreementExpectation(
                    relation_id=CONTRADICTS,
                    relation_type="CONTRADICTS",
                    source_ref=REPLACEMENT,
                    target_ref=ASSUMPTION,
                ),
            ),
        ),
    ]


def test_longitudinal_benchmark_answers_epistemic_history_and_dependency_questions(
    tmp_path: Path, monkeypatch
):
    events = _evolution_events()
    root = _write_fixture(tmp_path / "pack", events)
    monkeypatch.setattr(
        "fossil_core.application.rebuild.pack_corpus.validate_pack_fixtures",
        lambda *args, **kwargs: None,
    )

    report = run_longitudinal_epistemic_benchmark(
        [root],
        schemas_root=tmp_path / "schemas",
        phases=_phases(events),
        benchmark_id="longitudinal-epistemic-fixture-v1",
    )

    assert report["schema_version"] == "fossil.longitudinal-benchmark.v1"
    assert report["passed"] is True
    assert report["authority_rule"] == (
        "durable event replay determines epistemic state; retrieval is observational"
    )
    assert report["measurement_boundary"] == {
        "canonical_source": "local durable pack replay",
        "remote_canonical_object_scans_during_query": 0,
    }

    first, disputed, final = report["phases"]
    assert first["beliefs"][ASSUMPTION]["state"] == "supported"
    assert first["beliefs"][ASSUMPTION]["evidence_refs"] == [
        "ev_sqlite_design_note",
        "ev_sqlite_prototype_result",
    ]
    assert disputed["beliefs"][ASSUMPTION]["state"] == "disputed"
    assert final["beliefs"][ASSUMPTION]["state"] == "superseded"
    assert final["ontology_refs_observed"] == ["dkg.core@1.0.0", "dkg.core@2.0.0"]

    change = next(
        item
        for item in disputed["position_changes"]
        if item["event_id"] == events[9]["event_id"]
    )
    assert change == {
        "subject_id": ASSUMPTION,
        "event_id": events[9]["event_id"],
        "event_type": "claim.state_changed",
        "recorded_at": _timestamp(9),
        "from_state": "supported",
        "to_state": "disputed",
        "evidence_refs": ["ev_durable_store_proof"],
        "caused_by_event_ids": [events[8]["event_id"]],
    }

    impacts = {
        (item["dependent_ref"], item["premise_ref"]): item
        for item in final["dependency_impacts"]
    }
    assert impacts[(DECISION, ASSUMPTION)]["dependent_type"] == "Decision"
    assert impacts[(DECISION, ASSUMPTION)]["premise_state"] == "superseded"
    assert impacts[(DEPENDENT, ASSUMPTION)]["dependent_state"] == "stale_pending_review"

    disagreement = next(
        item for item in final["disagreements"] if item["relation_id"] == CONTRADICTS
    )
    assert disagreement["relation_type"] == "CONTRADICTS"
    assert disagreement["ontology_ref"] == "dkg.core@1.0.0"

    assert all(phase["rebuild_equivalent"] for phase in report["phases"])
    assert report["historical_answer_stability"]["historical-sqlite"] == {
        "observations": 3,
        "all_full_recall": True,
        "no_current_state_leakage": True,
    }

    schema = json.loads(
        (
            Path(__file__).parents[1]
            / "schemas/benchmark/longitudinal-v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(report)


def _large_corpus_events(claim_count: int = 320, decision_count: int = 80) -> list[dict]:
    events: list[dict] = []
    index = 0
    for claim_index in range(claim_count):
        claim_id = f"clm_scale_{claim_index:024d}"
        events.append(
            _event(
                index,
                "claim.proposed",
                [claim_id],
                {"claim_text": f"Scale claim {claim_index} durable epistemic benchmark."},
                evidence_refs=[f"ev_scale_{claim_index:06d}"],
            )
        )
        index += 1
        events.append(
            _event(
                index,
                "claim.state_changed",
                [claim_id],
                {"from_state": "proposed", "to_state": "supported"},
            )
        )
        index += 1

    premise = "clm_scale_000000000000000000000000"
    for decision_index in range(decision_count):
        decision_id = f"dec_scale_{decision_index:024d}"
        relation_id = f"rel_scale_{decision_index:024d}"
        events.append(
            _event(
                index,
                "relation.proposed",
                [relation_id, decision_id, premise],
                {
                    "relation_id": relation_id,
                    "relation_type": "DEPENDS_ON",
                    "source_ref": decision_id,
                    "source_type": "Decision",
                    "target_ref": premise,
                    "target_type": "Assumption",
                    "ontology_ref": "dkg.core@1.0.0",
                    "state": "active",
                },
            )
        )
        index += 1
    return events


def test_longitudinal_benchmark_measures_materially_larger_local_replay_without_remote_scan(
    tmp_path: Path, monkeypatch
):
    events = _large_corpus_events()
    root = _write_fixture(tmp_path / "large-pack", events)
    monkeypatch.setattr(
        "fossil_core.application.rebuild.pack_corpus.validate_pack_fixtures",
        lambda *args, **kwargs: None,
    )
    target = "clm_scale_000000000000000000000319"

    report = run_longitudinal_epistemic_benchmark(
        [root],
        schemas_root=tmp_path / "schemas",
        phases=[
            LongitudinalPhase(
                phase_id="large-current",
                as_of_recorded_at=None,
                expected_states={target: "supported"},
                queries=(
                    TemporalQueryCase(
                        case_id="large-current-target",
                        query="Scale claim 319 durable epistemic benchmark",
                        pack_ids=(PACK,),
                        relevant_ids=frozenset({target}),
                        limit=5,
                    ),
                ),
            )
        ],
        benchmark_id="longitudinal-scale-fixture-v1",
    )

    phase = report["phases"][0]
    assert report["passed"] is True
    assert phase["event_count"] == len(events) == 720
    assert phase["claim_count"] == 320
    assert phase["decision_count"] == 80
    assert phase["relation_count"] == 80
    assert phase["projection_build_ms"] >= 0
    assert phase["query_latency_ms"] >= 0
    assert phase["rebuild_equivalent"] is True
    assert report["scale"] == {
        "max_event_count": 720,
        "max_claim_count": 320,
        "max_decision_count": 80,
        "max_relation_count": 80,
    }
    assert report["measurement_boundary"]["remote_canonical_object_scans_during_query"] == 0
