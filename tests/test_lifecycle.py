from dkg.lifecycle import KnowledgeState

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


def test_disputed_can_remain_a_valid_state():
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


def test_superseding_premise_marks_active_dependents_stale():
    state = KnowledgeState()
    premise = "clm_premise_000000000000001"
    dependent = "clm_dependent_000000000001"

    for claim in (premise, dependent):
        state.apply(event("claim.proposed", claim, {"claim_text": claim}, f"propose:{claim}"))
        state.apply(
            event(
                "claim.state_changed",
                claim,
                {"from_state": "proposed", "to_state": "supported"},
                f"support:{claim}",
            )
        )

    relation_id = "rel_dependency_00000000000001"
    state.apply(
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
    state.apply(
        event(
            "claim.superseded",
            premise,
            {"from_state": "supported", "superseded_by": "clm_new_000000000000000001"},
            "supersede-premise",
        )
    )

    assert state.claims[premise] == "superseded"
    assert state.claims[dependent] == "stale_pending_review"
    assert state.relations[relation_id].state == "active"
