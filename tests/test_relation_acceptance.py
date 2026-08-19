from __future__ import annotations

from pathlib import Path

import pytest
from jsonschema import ValidationError

from fossil_core.adapters.s3.storage import S3DurableEventStore
from fossil_core.domain.event_contracts import EventContractError
from fossil_core.domain.lifecycle import KnowledgeState
from fossil_core.event_store import DurableEventStore


ROOT = Path(__file__).parents[1]
SCHEMA = ROOT / "schemas/events/v1.schema.json"
PACK = "pack_269099f7b2ba43b7a99b9427d64092de"
RELATION = "rel_ontology_gate_fixture_000001"
SOURCE = "clm_ontology_gate_source_000001"
TARGET = "clm_ontology_gate_target_000001"


def _event(event_type: str, payload: dict, *, key: str) -> dict:
    return {
        "schema_version": "dkg.event.v1",
        "event_type": event_type,
        "occurred_at": "2026-08-19T16:10:00Z",
        "recorded_at": "2026-08-19T16:10:01Z",
        "pack_id": PACK,
        "actor": {"actor_type": "system", "actor_id": "ontology-gate-test"},
        "subject_refs": [RELATION],
        "idempotency_key": key,
        "payload": payload,
        "provenance": {"method": "ontology-gate-test"},
    }


def _proposal(*, state: str = "proposed") -> dict:
    return _event(
        "relation.proposed",
        {
            "relation_id": RELATION,
            "relation_type": "DEPENDS_ON",
            "source_ref": SOURCE,
            "target_ref": TARGET,
            "state": state,
        },
        key=f"relation-proposal:{state}",
    )


def _acceptance(**overrides: str) -> dict:
    payload = {
        "relation_id": RELATION,
        "from_state": "proposed",
        "to_state": "active",
        "ontology_ref": "dkg.core@1.0.0",
        "relation_type": "DEPENDS_ON",
        "source_ref": SOURCE,
        "source_type": "Claim",
        "target_ref": TARGET,
        "target_type": "Claim",
    }
    payload.update(overrides)
    return _event("relation.state_changed", payload, key="relation-acceptance")


def _resolver(endpoint_types: dict[str, str]):
    return endpoint_types.get


def _claim_resolver():
    return _resolver({SOURCE: "Claim", TARGET: "Claim"})


def test_new_relation_proposal_cannot_smuggle_active_state_into_durable_projection(tmp_path):
    store = DurableEventStore(tmp_path / "events", SCHEMA)

    with pytest.raises(EventContractError, match="relation.proposed.*proposed"):
        store.commit(_proposal(state="active"))
    assert list(store.iter_events()) == []


def test_relation_proposal_remains_cheap_and_durable_as_proposed(tmp_path):
    store = DurableEventStore(tmp_path / "events", SCHEMA)

    committed = store.commit(_proposal())

    assert committed["payload"]["state"] == "proposed"
    assert KnowledgeState.replay([committed]).relations[RELATION].state == "proposed"


def test_accepted_relation_transition_requires_self_contained_ontology_fields(tmp_path):
    store = DurableEventStore(
        tmp_path / "events",
        SCHEMA,
        endpoint_type_resolver=_claim_resolver(),
    )
    candidate = _acceptance()
    candidate["payload"].pop("source_type")

    with pytest.raises(ValidationError):
        store.commit(candidate)


def test_accepted_relation_transition_fails_closed_without_identity_resolver(tmp_path):
    store = DurableEventStore(tmp_path / "events", SCHEMA)

    with pytest.raises(EventContractError, match="endpoint identity.*resolver"):
        store.commit(_acceptance())
    assert list(store.iter_events()) == []


def test_accepted_relation_transition_fails_when_endpoint_identity_is_unresolved(tmp_path):
    store = DurableEventStore(
        tmp_path / "events",
        SCHEMA,
        endpoint_type_resolver=_resolver({SOURCE: "Claim"}),
    )

    with pytest.raises(EventContractError, match="target endpoint identity.*could not be resolved"):
        store.commit(_acceptance())


def test_accepted_relation_transition_rejects_wrong_ontology_revision(tmp_path):
    store = DurableEventStore(
        tmp_path / "events",
        SCHEMA,
        endpoint_type_resolver=_claim_resolver(),
    )

    with pytest.raises(EventContractError, match="ontology_ref"):
        store.commit(_acceptance(ontology_ref="dkg.core@0.9.0"))


def test_declared_endpoint_kind_must_match_independent_resolution(tmp_path):
    store = DurableEventStore(
        tmp_path / "events",
        SCHEMA,
        endpoint_type_resolver=_claim_resolver(),
    )

    with pytest.raises(EventContractError, match="source_type.*does not match resolved"):
        store.commit(_acceptance(source_type="Concept"))


def test_accepted_relation_transition_rejects_ontology_invalid_resolved_kind(tmp_path):
    store = DurableEventStore(
        tmp_path / "events",
        SCHEMA,
        endpoint_type_resolver=_resolver({SOURCE: "Evidence", TARGET: "Claim"}),
    )

    with pytest.raises(EventContractError, match="source_type.*not valid"):
        store.commit(_acceptance(source_type="Evidence"))


def test_valid_accepted_relation_transition_is_resolved_and_replayable(tmp_path):
    store = DurableEventStore(
        tmp_path / "events",
        SCHEMA,
        endpoint_type_resolver=_claim_resolver(),
    )
    proposed = store.commit(_proposal())
    accepted = store.commit(_acceptance())

    state = KnowledgeState.replay([proposed, accepted])
    assert state.relations[RELATION].state == "active"
    assert state.relation_history[RELATION] == ["proposed", "active"]


def test_s3_validate_uses_the_same_endpoint_identity_resolver_seam():
    store = S3DurableEventStore(
        bucket="ontology-gate-fixture",
        schema_path=SCHEMA,
        client=object(),
        endpoint_type_resolver=_claim_resolver(),
    )

    validated = store.validate(_acceptance())
    assert validated["payload"]["to_state"] == "active"


def test_historical_active_relation_proposal_remains_replayable_without_revalidation(tmp_path):
    store = DurableEventStore(tmp_path / "events", SCHEMA)
    historical = _proposal(state="active")
    historical.pop("idempotency_key")
    historical["event_id"] = "evt_historical_active_relation_000001"
    path = store._event_path(historical["event_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(store._canonical(historical))

    loaded = store.get(historical["event_id"])
    assert loaded == historical
    assert KnowledgeState.replay([loaded]).relations[RELATION].state == "active"
