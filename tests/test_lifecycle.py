import pytest

from fossil_core.lifecycle import KnowledgeState

PACK = "pack_269099f7b2ba43b7a99b9427d64092de"


def event(event_type, subject, payload, key):
    return {
        "schema_version": "dkg.event.v1",
        "event_type": event_type,
        "occurred_at": "2026-08-09T17:21:00Z",
        "recorded_at": "2026-08-09T17:21:01Z",
        "pack_id": PACK,
        "actor": {"actor_type": "system", "actor_id": "test"},
        "subject_refs": [subject],
        "idempotency_key": key,
        "payload": payload,
    }


def test_disputed_can_remain_a_valid_state_and_history_survives():
    state = KnowledgeState()
    claim = "clm_disputed_00000000000001"
    state.apply(event("claim.proposed", claim, {"claim_text": "X"}, "claim-x"))
    state.apply(
        event(
            "claim.state_changed",
            claim,
            {"from_state": "proposed", "to_state": "disputed"},
            "claim-x-disputed",
        )
    )
    assert state.claims[claim] == "disputed"
    assert state.claim_history[claim] == ["proposed", "disputed"]


@pytest.mark.parametrize(
    "relation_type",
    ["SUPPORTS", "CHALLENGES", "CONTRADICTS", "REFINES", "DEPENDS_ON"],
)
def test_argument_relation_types_have_independent_lifecycle(relation_type):
    state = KnowledgeState()
    relation_id = f"rel_{relation_type.lower()}_00000000000001"
    state.apply(
        event(
            "relation.proposed",
            relation_id,
            {
                "relation_id": relation_id,
                "relation_type": relation_type,
                "source_ref": "clm_source_000000000000001",
                "target_ref": "clm_target_000000000000001",
                "state": "active",
            },
            f"relation:{relation_type}",
        )
    )
    state.apply(
        event(
            "relation.state_changed",
            relation_id,
            {"relation_id": relation_id, "from_state": "active", "to_state": "disputed"},
            f"relation:{relation_type}:disputed",
        )
    )
    state.apply(
        event(
            "relation.superseded",
            relation_id,
            {"relation_id": relation_id, "from_state": "disputed"},
            f"relation:{relation_type}:superseded",
        )
    )
    assert state.relations[relation_id].state == "superseded"
    assert state.relation_history[relation_id] == ["active", "disputed", "superseded"]


def test_superseding_premise_marks_active_dependents_stale():
    events = []
    premise = "clm_premise_000000000000001"
    dependent = "clm_dependent_000000000001"

    for claim in (premise, dependent):
        events.append(event("claim.proposed", claim, {"claim_text": claim}, f"propose:{claim}"))
        events.append(
            event(
                "claim.state_changed",
                claim,
                {"from_state": "proposed", "to_state": "supported"},
                f"support:{claim}",
            )
        )

    relation_id = "rel_dependency_00000000000001"
    events.append(
        event(
            "relation.proposed",
            relation_id,
            {
                "relation_id": relation_id,
                "relation_type": "DEPENDS_ON",
                "source_ref": dependent,
                "target_ref": premise,
                "state": "active",
            },
            "dependency",
        )
    )
    events.append(
        event(
            "claim.superseded",
            premise,
            {"from_state": "supported", "superseded_by": "clm_new_000000000000000001"},
            "supersede-premise",
        )
    )

    state = KnowledgeState.replay(events)
    assert state.claims[premise] == "superseded"
    assert state.claims[dependent] == "stale_pending_review"
    assert state.claim_history[dependent] == ["proposed", "supported", "stale_pending_review"]
    assert state.relations[relation_id].state == "active"
