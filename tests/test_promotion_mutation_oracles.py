from __future__ import annotations

import copy

import pytest

from fossil_core.domain.promotion import (
    PromotionSourceError,
    build_promotion_event,
    validate_promotion_source,
)

SOURCE_PACK = "pack_source_0123456789abcdef"
TARGET_PACK = "pack_target_0123456789abcdef"
SOURCE_REVISION = "rev_source_0123456789abcdef"
SOURCE_EVENT = "evt_source_0123456789abcdef"
SUBJECT = "clm_subject_0123456789abcdef"


def _promotion_event() -> dict:
    return build_promotion_event(
        source_pack_id=SOURCE_PACK,
        source_pack_revision=SOURCE_REVISION,
        source_event_id=SOURCE_EVENT,
        target_pack_id=TARGET_PACK,
        subject_refs=[SUBJECT],
        actor_id="reviewer",
        occurred_at="2026-08-19T20:00:00Z",
        recorded_at="2026-08-19T20:00:01Z",
        idempotency_key="promotion-mutation-oracle",
    )


def _permissive_resolver(pack_id: str, revision: str, event_id: str) -> dict:
    return {
        "pack_id": pack_id,
        "event_id": event_id,
        "subject_refs": [SUBJECT],
        "revision": revision,
    }


def test_builder_default_reason_and_exact_source_pins_are_observable() -> None:
    event = _promotion_event()

    assert event["payload"]["reason"] == ""
    assert event["payload"]["source_pack_id"] == SOURCE_PACK
    assert event["payload"]["source_pack_revision"] == SOURCE_REVISION
    assert event["payload"]["source_event_id"] == SOURCE_EVENT
    assert event["payload"]["target_pack_id"] == TARGET_PACK


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_pack_revision", "   "),
        ("source_event_id", "\t\n"),
    ],
)
def test_builder_rejects_whitespace_only_exact_source_pins(field: str, value: str) -> None:
    kwargs = {
        "source_pack_id": SOURCE_PACK,
        "source_pack_revision": SOURCE_REVISION,
        "source_event_id": SOURCE_EVENT,
        "target_pack_id": TARGET_PACK,
        "subject_refs": [SUBJECT],
        "actor_id": "reviewer",
        "occurred_at": "2026-08-19T20:00:00Z",
        "recorded_at": "2026-08-19T20:00:01Z",
        "idempotency_key": "promotion-whitespace-pin",
    }
    kwargs[field] = value

    with pytest.raises(ValueError):
        build_promotion_event(**kwargs)


@pytest.mark.parametrize("field", ["source_pack_id", "source_pack_revision", "source_event_id"])
@pytest.mark.parametrize("mode", ["missing", "empty", "whitespace"])
def test_validator_rejects_absent_or_blank_source_pins_before_permissive_resolution(
    field: str,
    mode: str,
) -> None:
    event = _promotion_event()
    if mode == "missing":
        event["payload"].pop(field)
    elif mode == "empty":
        event["payload"][field] = ""
    else:
        event["payload"][field] = "   "

    with pytest.raises(PromotionSourceError):
        validate_promotion_source(event, resolver=_permissive_resolver)


@pytest.mark.parametrize(
    "bad_subject_refs",
    [SUBJECT, (SUBJECT,), {SUBJECT: True}],
)
def test_validator_rejects_non_list_promoted_subject_refs(bad_subject_refs: object) -> None:
    event = _promotion_event()
    event["subject_refs"] = bad_subject_refs

    with pytest.raises(PromotionSourceError):
        validate_promotion_source(event, resolver=_permissive_resolver)


def test_validator_does_not_mutate_promotion_or_resolved_source() -> None:
    event = _promotion_event()
    source = _permissive_resolver(SOURCE_PACK, SOURCE_REVISION, SOURCE_EVENT)
    event_before = copy.deepcopy(event)
    source_before = copy.deepcopy(source)

    resolved = validate_promotion_source(event, resolver=lambda *_args: source)

    assert resolved is source
    assert event == event_before
    assert source == source_before
