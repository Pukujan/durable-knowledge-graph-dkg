from __future__ import annotations

import importlib
import warnings

import pytest

import fossil_core
import fossil_core.promotion as legacy_promotion
from fossil_core.domain.promotion import build_promotion_event


def _event() -> dict:
    return build_promotion_event(
        source_pack_id="pack_source",
        target_pack_id="pack_target",
        subject_refs=["clm_1", "clm_2"],
        actor={"actor_type": "human", "actor_id": "user"},
        occurred_at="2026-08-09T17:21:00Z",
        recorded_at="2026-08-09T17:21:01Z",
        idempotency_key="promote:source:target:1",
        evidence_refs=["src_1"],
        reason="Reviewed for cross-pack reuse.",
    )


def test_promotion_exports_preserve_canonical_object_identity():
    assert legacy_promotion.build_promotion_event is build_promotion_event
    assert fossil_core.build_promotion_event is build_promotion_event

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        legacy_dkg = importlib.import_module("dkg")
    assert legacy_dkg.build_promotion_event is build_promotion_event


def test_promotion_event_shape_is_unchanged():
    assert _event() == {
        "schema_version": "dkg.event.v1",
        "event_type": "knowledge.promoted",
        "occurred_at": "2026-08-09T17:21:00Z",
        "recorded_at": "2026-08-09T17:21:01Z",
        "pack_id": "pack_target",
        "actor": {"actor_type": "human", "actor_id": "user"},
        "subject_refs": ["clm_1", "clm_2"],
        "idempotency_key": "promote:source:target:1",
        "evidence_refs": ["src_1"],
        "payload": {
            "source_pack_id": "pack_source",
            "target_pack_id": "pack_target",
            "reason": "Reviewed for cross-pack reuse.",
        },
        "provenance": {"method": "explicit_cross_pack_promotion"},
    }


def test_promotion_still_requires_subject_and_cross_pack_boundary():
    common = {
        "actor": {"actor_type": "human", "actor_id": "user"},
        "occurred_at": "2026-08-09T17:21:00Z",
        "recorded_at": "2026-08-09T17:21:01Z",
        "idempotency_key": "promotion-test",
    }

    with pytest.raises(
        ValueError, match="promotion requires at least one stable subject reference"
    ):
        build_promotion_event(
            source_pack_id="pack_source",
            target_pack_id="pack_target",
            subject_refs=[],
            **common,
        )

    with pytest.raises(
        ValueError, match="promotion requires different source and target packs"
    ):
        build_promotion_event(
            source_pack_id="pack_same",
            target_pack_id="pack_same",
            subject_refs=["clm_1"],
            **common,
        )


def test_legacy_promotion_preserves_historical_implicit_star_surface():
    assert not hasattr(legacy_promotion, "__all__")
    public_names = sorted(
        name for name in vars(legacy_promotion) if not name.startswith("_")
    )
    assert public_names == ["Any", "Iterable", "annotations", "build_promotion_event"]
