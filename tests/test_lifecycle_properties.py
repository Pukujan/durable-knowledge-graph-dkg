from __future__ import annotations

from hypothesis import given, settings, strategies as st

from fossil_core.domain.lifecycle import CLAIM_STATES, RELATION_STATES, KnowledgeState

PACK = "pack_269099f7b2ba43b7a99b9427d64092de"
CLAIM = "clm_property_claim_000000000001"
PREMISE = "clm_property_premise_000000001"
DEPENDENT = "clm_property_dependent_00000001"
RELATION = "rel_property_dependency_00000001"
TERMINAL_CLAIM_STATES = frozenset({"superseded", "retracted", "rejected"})
NONTERMINAL_CLAIM_STATES = CLAIM_STATES - TERMINAL_CLAIM_STATES


def event(event_type: str, subject: str, payload: dict, key: str) -> dict:
    return {
        "schema_version": "dkg.event.v1",
        "event_type": event_type,
        "occurred_at": "2026-08-19T01:45:00Z",
        "recorded_at": "2026-08-19T01:45:01Z",
        "pack_id": PACK,
        "actor": {"actor_type": "system", "actor_id": "property-test"},
        "subject_refs": [subject],
        "idempotency_key": key,
        "payload": payload,
    }


def claim_with_state(claim_id: str, target: str, key_prefix: str) -> list[dict]:
    events = [event("claim.proposed", claim_id, {"claim_text": claim_id}, f"{key_prefix}:propose")]
    if target != "proposed":
        events.append(
            event(
                "claim.state_changed",
                claim_id,
                {"from_state": "proposed", "to_state": target},
                f"{key_prefix}:state:{target}",
            )
        )
    return events


@settings(max_examples=160, derandomize=True)
@given(
    transitions=st.lists(
        st.sampled_from(sorted(CLAIM_STATES)),
        min_size=0,
        max_size=12,
    )
)
def test_generated_claim_history_is_preserved_and_replay_is_deterministic(
    transitions: list[str],
) -> None:
    events = [event("claim.proposed", CLAIM, {"claim_text": CLAIM}, "claim:propose")]
    current = "proposed"
    for index, target in enumerate(transitions):
        events.append(
            event(
                "claim.state_changed",
                CLAIM,
                {"from_state": current, "to_state": target},
                f"claim:state:{index}:{target}",
            )
        )
        current = target

    first = KnowledgeState.replay(events)
    second = KnowledgeState.replay(events)

    assert first == second
    assert first.claims[CLAIM] == current
    assert first.claim_history[CLAIM] == ["proposed", *transitions]


@settings(max_examples=160, derandomize=True)
@given(
    initial_state=st.sampled_from(sorted(RELATION_STATES)),
    transitions=st.lists(
        st.sampled_from(sorted(RELATION_STATES)),
        min_size=0,
        max_size=12,
    ),
)
def test_generated_relation_history_is_preserved(
    initial_state: str,
    transitions: list[str],
) -> None:
    events = [
        event(
            "relation.proposed",
            RELATION,
            {
                "relation_id": RELATION,
                "relation_type": "SUPPORTS",
                "source_ref": "clm_property_source_000000001",
                "target_ref": "clm_property_target_000000001",
                "state": initial_state,
            },
            "relation:propose",
        )
    ]
    current = initial_state
    for index, target in enumerate(transitions):
        events.append(
            event(
                "relation.state_changed",
                RELATION,
                {
                    "relation_id": RELATION,
                    "from_state": current,
                    "to_state": target,
                },
                f"relation:state:{index}:{target}",
            )
        )
        current = target

    state = KnowledgeState.replay(events)

    assert state.relations[RELATION].state == current
    assert state.relation_history[RELATION] == [initial_state, *transitions]


@settings(max_examples=80, derandomize=True)
@given(dependent_state=st.sampled_from(sorted(NONTERMINAL_CLAIM_STATES)))
def test_superseding_premise_stales_every_active_nonterminal_dependent(
    dependent_state: str,
) -> None:
    events = [
        *claim_with_state(PREMISE, "supported", "premise"),
        *claim_with_state(DEPENDENT, dependent_state, "dependent"),
        event(
            "relation.proposed",
            RELATION,
            {
                "relation_id": RELATION,
                "relation_type": "DEPENDS_ON",
                "source_ref": DEPENDENT,
                "target_ref": PREMISE,
                "state": "active",
            },
            "dependency:active",
        ),
        event(
            "claim.superseded",
            PREMISE,
            {"from_state": "supported", "superseded_by": "clm_property_replacement_0001"},
            "premise:supersede",
        ),
    ]

    state = KnowledgeState.replay(events)

    assert state.claims[PREMISE] == "superseded"
    assert state.claims[DEPENDENT] == "stale_pending_review"
    assert state.claim_history[DEPENDENT][-1] == "stale_pending_review"


@settings(max_examples=40, derandomize=True)
@given(dependent_state=st.sampled_from(sorted(TERMINAL_CLAIM_STATES)))
def test_superseding_premise_does_not_revive_terminal_dependents(
    dependent_state: str,
) -> None:
    events = [
        *claim_with_state(PREMISE, "supported", "premise"),
        *claim_with_state(DEPENDENT, dependent_state, "dependent"),
        event(
            "relation.proposed",
            RELATION,
            {
                "relation_id": RELATION,
                "relation_type": "DEPENDS_ON",
                "source_ref": DEPENDENT,
                "target_ref": PREMISE,
                "state": "active",
            },
            "dependency:active",
        ),
        event(
            "claim.superseded",
            PREMISE,
            {"from_state": "supported", "superseded_by": "clm_property_replacement_0001"},
            "premise:supersede",
        ),
    ]

    state = KnowledgeState.replay(events)

    assert state.claims[DEPENDENT] == dependent_state
    assert state.claim_history[DEPENDENT] == ["proposed", dependent_state]
