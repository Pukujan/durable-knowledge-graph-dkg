from __future__ import annotations

import pytest
from hypothesis import given, settings, strategies as st

from fossil_core.domain.lifecycle import (
    CLAIM_STATES,
    RELATION_STATES,
    KnowledgeState,
    LifecycleError,
)

PACK = "pack_269099f7b2ba43b7a99b9427d64092de"
CLAIM = "clm_property_claim_000000000001"
PREMISE = "clm_property_premise_000000001"
OTHER_PREMISE = "clm_property_other_premise_00001"
DEPENDENT = "clm_property_dependent_00000001"
OTHER_DEPENDENT = "clm_property_other_dependent_0001"
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


@pytest.mark.parametrize("event_type", ["claim.state_changed", "claim.superseded"])
def test_claim_events_reject_mismatched_from_state(event_type: str) -> None:
    state = KnowledgeState.replay(claim_with_state(CLAIM, "supported", "claim"))
    payload = {"from_state": "proposed"}
    if event_type == "claim.state_changed":
        payload["to_state"] = "disputed"
    else:
        payload["superseded_by"] = "clm_property_replacement_0002"

    with pytest.raises(LifecycleError):
        state.apply(event(event_type, CLAIM, payload, f"claim:mismatch:{event_type}"))

    assert state.claims[CLAIM] == "supported"
    assert state.claim_history[CLAIM] == ["proposed", "supported"]


@pytest.mark.parametrize("event_type", ["relation.state_changed", "relation.superseded"])
def test_relation_events_reject_mismatched_from_state(event_type: str) -> None:
    state = KnowledgeState()
    state.apply(
        event(
            "relation.proposed",
            RELATION,
            {
                "relation_id": RELATION,
                "relation_type": "SUPPORTS",
                "source_ref": "clm_property_source_000000001",
                "target_ref": "clm_property_target_000000001",
                "state": "active",
            },
            "relation:mismatch:propose",
        )
    )
    payload = {"relation_id": RELATION, "from_state": "proposed"}
    if event_type == "relation.state_changed":
        payload["to_state"] = "disputed"

    with pytest.raises(LifecycleError):
        state.apply(event(event_type, RELATION, payload, f"relation:mismatch:{event_type}"))

    assert state.relations[RELATION].state == "active"
    assert state.relation_history[RELATION] == ["active"]


def test_relation_proposal_without_state_defaults_to_proposed() -> None:
    state = KnowledgeState()
    state.apply(
        event(
            "relation.proposed",
            RELATION,
            {
                "relation_id": RELATION,
                "relation_type": "SUPPORTS",
                "source_ref": "clm_property_source_000000001",
                "target_ref": "clm_property_target_000000001",
            },
            "relation:default-state",
        )
    )

    assert state.relations[RELATION].state == "proposed"
    assert state.relation_history[RELATION] == ["proposed"]


def test_stale_propagation_skips_irrelevant_relations_and_continues_to_valid_dependency() -> None:
    events = [
        *claim_with_state(PREMISE, "supported", "premise"),
        *claim_with_state(OTHER_PREMISE, "supported", "other-premise"),
        *claim_with_state(DEPENDENT, "supported", "dependent"),
        *claim_with_state(OTHER_DEPENDENT, "supported", "other-dependent"),
        event(
            "relation.proposed",
            "rel_property_irrelevant_support_01",
            {
                "relation_id": "rel_property_irrelevant_support_01",
                "relation_type": "SUPPORTS",
                "source_ref": OTHER_DEPENDENT,
                "target_ref": PREMISE,
                "state": "active",
            },
            "dependency:irrelevant-type",
        ),
        event(
            "relation.proposed",
            "rel_property_wrong_target_00001",
            {
                "relation_id": "rel_property_wrong_target_00001",
                "relation_type": "DEPENDS_ON",
                "source_ref": OTHER_DEPENDENT,
                "target_ref": OTHER_PREMISE,
                "state": "active",
            },
            "dependency:wrong-target",
        ),
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
            "dependency:valid",
        ),
        event(
            "claim.superseded",
            PREMISE,
            {"from_state": "supported", "superseded_by": "clm_property_replacement_0003"},
            "premise:supersede:mixed-relations",
        ),
    ]

    state = KnowledgeState.replay(events)

    assert state.claims[DEPENDENT] == "stale_pending_review"
    assert state.claim_history[DEPENDENT] == ["proposed", "supported", "stale_pending_review"]
    assert state.claims[OTHER_DEPENDENT] == "supported"
    assert state.claim_history[OTHER_DEPENDENT] == ["proposed", "supported"]
