from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from fossil_core.adapters.s3.storage import S3DurableEventStore
from fossil_core.domain.event_contracts import EVENT_TYPE_CONTRACTS, EventContractError
from fossil_core.domain.promotion import (
    PROMOTION_CONTRACT_VERSION,
    build_promotion_event,
)
from fossil_core.event_store import DurableEventStore


ROOT = Path(__file__).parents[1]
SCHEMA = ROOT / "schemas/events/v1.schema.json"
SOURCE_PACK = "pack_f024177f89a5442db84171c3dd7f58e5"
TARGET_PACK = "pack_269099f7b2ba43b7a99b9427d64092de"
SOURCE_REVISION = "git:source@0123456789abcdef"
SOURCE_EVENT_ID = "evt_source_promotion_fixture_000001"
SUBJECT = "clm_promotion_fixture_000001"


def source_event(*, subjects: list[str] | None = None) -> dict:
    return {
        "schema_version": "dkg.event.v1",
        "event_id": SOURCE_EVENT_ID,
        "event_type": "claim.proposed",
        "occurred_at": "2026-08-19T16:40:00Z",
        "recorded_at": "2026-08-19T16:40:01Z",
        "pack_id": SOURCE_PACK,
        "actor": {"actor_type": "human", "actor_id": "reviewer"},
        "subject_refs": list(subjects or [SUBJECT]),
        "payload": {"claim_text": "Promotable source knowledge."},
    }


def resolver_for(event: dict | None = None):
    resolved = deepcopy(event or source_event())

    def resolve(pack_id: str, revision: str, event_id: str):
        if (
            pack_id == SOURCE_PACK
            and revision == SOURCE_REVISION
            and event_id == SOURCE_EVENT_ID
        ):
            return deepcopy(resolved)
        return None

    return resolve


def promotion_event(**payload_overrides: str) -> dict:
    event = build_promotion_event(
        source_pack_id=SOURCE_PACK,
        source_pack_revision=SOURCE_REVISION,
        source_event_id=SOURCE_EVENT_ID,
        target_pack_id=TARGET_PACK,
        subject_refs=[SUBJECT],
        actor={"actor_type": "human", "actor_id": "reviewer"},
        occurred_at="2026-08-19T16:41:00Z",
        recorded_at="2026-08-19T16:41:01Z",
        idempotency_key="promotion-v2:fixture",
        evidence_refs=["art_promotion_review_000001"],
        reason="Reviewed for common-pack reuse.",
    )
    event["payload"].update(payload_overrides)
    return event


def test_builder_emits_versioned_self_contained_source_pin():
    event = promotion_event()

    assert EVENT_TYPE_CONTRACTS["knowledge.promoted"].contract_version.endswith(".v2")
    assert event["payload"] == {
        "contract_version": PROMOTION_CONTRACT_VERSION,
        "source_pack_id": SOURCE_PACK,
        "source_pack_revision": SOURCE_REVISION,
        "source_event_id": SOURCE_EVENT_ID,
        "target_pack_id": TARGET_PACK,
        "reason": "Reviewed for common-pack reuse.",
    }
    assert event["pack_id"] == TARGET_PACK
    assert event["subject_refs"] == [SUBJECT]
    assert event["provenance"]["method"] == "explicit_cross_pack_promotion"


def test_prepare_remains_cheap_but_new_promotion_acceptance_fails_closed_without_source_resolver(tmp_path):
    store = DurableEventStore(tmp_path / "events", SCHEMA)
    event = promotion_event()

    assert store.prepare(event)["payload"]["source_event_id"] == SOURCE_EVENT_ID
    with pytest.raises(EventContractError, match="promotion source.*resolver"):
        store.validate(event)
    with pytest.raises(EventContractError, match="promotion source.*resolver"):
        store.commit(event)
    assert list(store.iter_events()) == []


def test_resolver_is_keyed_by_exact_source_pack_revision_and_event(tmp_path):
    calls: list[tuple[str, str, str]] = []

    def resolver(pack_id: str, revision: str, event_id: str):
        calls.append((pack_id, revision, event_id))
        return source_event()

    store = DurableEventStore(
        tmp_path / "events",
        SCHEMA,
        promotion_source_resolver=resolver,
    )
    committed = store.commit(promotion_event())

    assert committed["payload"]["source_pack_revision"] == SOURCE_REVISION
    assert calls == [(SOURCE_PACK, SOURCE_REVISION, SOURCE_EVENT_ID)]


def test_wrong_or_unmounted_source_revision_fails_closed(tmp_path):
    store = DurableEventStore(
        tmp_path / "events",
        SCHEMA,
        promotion_source_resolver=resolver_for(),
    )

    with pytest.raises(EventContractError, match="source event.*not resolvable"):
        store.commit(promotion_event(source_pack_revision="git:source@wrong"))


def test_missing_or_redacted_source_event_fails_closed(tmp_path):
    def redacted(_pack_id: str, _revision: str, _event_id: str):
        raise FileNotFoundError("source event redacted")

    missing = DurableEventStore(
        tmp_path / "missing-events",
        SCHEMA,
        promotion_source_resolver=lambda *_args: None,
    )
    with pytest.raises(EventContractError, match="source event.*not resolvable"):
        missing.commit(promotion_event())

    redacted_store = DurableEventStore(
        tmp_path / "redacted-events",
        SCHEMA,
        promotion_source_resolver=redacted,
    )
    with pytest.raises(EventContractError, match="source event.*not resolvable"):
        redacted_store.commit(promotion_event())


def test_resolved_source_identity_must_match_pin(tmp_path):
    wrong_pack = source_event()
    wrong_pack["pack_id"] = TARGET_PACK
    store = DurableEventStore(
        tmp_path / "events",
        SCHEMA,
        promotion_source_resolver=resolver_for(wrong_pack),
    )
    with pytest.raises(EventContractError, match="resolved source pack"):
        store.commit(promotion_event())

    wrong_event = source_event()
    wrong_event["event_id"] = "evt_wrong_source_event_000001"
    store = DurableEventStore(
        tmp_path / "events-2",
        SCHEMA,
        promotion_source_resolver=resolver_for(wrong_event),
    )
    with pytest.raises(EventContractError, match="resolved source event"):
        store.commit(promotion_event())


def test_promotion_subjects_must_be_present_in_pinned_source_event(tmp_path):
    store = DurableEventStore(
        tmp_path / "events",
        SCHEMA,
        promotion_source_resolver=resolver_for(source_event(subjects=["clm_other_000001"])),
    )

    with pytest.raises(EventContractError, match="subject_refs.*source event"):
        store.commit(promotion_event())


def test_target_pack_must_equal_durable_event_pack(tmp_path):
    event = promotion_event(target_pack_id=SOURCE_PACK)
    store = DurableEventStore(
        tmp_path / "events",
        SCHEMA,
        promotion_source_resolver=resolver_for(),
    )

    with pytest.raises(EventContractError, match="target_pack_id.*durable pack_id"):
        store.commit(event)


def test_source_and_target_pack_must_differ_at_acceptance_even_for_direct_event_mutation(tmp_path):
    event = promotion_event(source_pack_id=TARGET_PACK)
    store = DurableEventStore(
        tmp_path / "events",
        SCHEMA,
        promotion_source_resolver=resolver_for(),
    )

    with pytest.raises(EventContractError, match="different source and target"):
        store.commit(event)


def test_s3_validate_uses_same_provider_neutral_source_resolver():
    calls: list[tuple[str, str, str]] = []

    def resolver(pack_id: str, revision: str, event_id: str):
        calls.append((pack_id, revision, event_id))
        return source_event()

    store = S3DurableEventStore(
        bucket="promotion-pin-fixture",
        schema_path=SCHEMA,
        client=object(),
        promotion_source_resolver=resolver,
    )

    validated = store.validate(promotion_event())
    assert validated["payload"]["source_event_id"] == SOURCE_EVENT_ID
    assert calls == [(SOURCE_PACK, SOURCE_REVISION, SOURCE_EVENT_ID)]


def test_historical_unpinned_promotion_remains_replayable_without_silent_upgrade(tmp_path):
    store = DurableEventStore(tmp_path / "events", SCHEMA)
    historical = promotion_event()
    historical["payload"] = {
        "source_pack_id": SOURCE_PACK,
        "target_pack_id": TARGET_PACK,
        "reason": "historical v1 promotion",
    }
    historical.pop("idempotency_key")
    historical["event_id"] = "evt_historical_promotion_v1_000001"
    path = store._event_path(historical["event_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(store._canonical(historical))

    assert store.get(historical["event_id"]) == historical
    assert list(store.iter_events()) == [historical]
