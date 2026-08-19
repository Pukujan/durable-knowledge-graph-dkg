from pathlib import Path

from fossil_core.event_store import DurableEventStore
from fossil_core.promotion import build_promotion_event

ROOT = Path(__file__).parents[1]
SCHEMA = ROOT / "schemas/events/v1.schema.json"


def test_promotion_is_new_target_event_with_exact_source_provenance(tmp_path: Path):
    source = "pack_f024177f89a5442db84171c3dd7f58e5"
    source_revision = "git:source@0123456789abcdef"
    source_event_id = "evt_source_example_000000000001"
    target = "pack_269099f7b2ba43b7a99b9427d64092de"
    subject = "clm_example_0000000000000001"
    source_event = {
        "event_id": source_event_id,
        "pack_id": source,
        "subject_refs": [subject],
    }

    event = build_promotion_event(
        source_pack_id=source,
        source_pack_revision=source_revision,
        source_event_id=source_event_id,
        target_pack_id=target,
        subject_refs=[subject],
        actor={"actor_type": "human", "actor_id": "user"},
        occurred_at="2026-08-09T17:21:00Z",
        recorded_at="2026-08-09T17:21:01Z",
        idempotency_key="promote:plugin-harness:claim-1:common",
        evidence_refs=["src_example_0000000000000001"],
        reason="Useful across projects after review.",
    )

    assert event["pack_id"] == target
    assert event["payload"]["source_pack_id"] == source
    assert event["payload"]["source_pack_revision"] == source_revision
    assert event["payload"]["source_event_id"] == source_event_id
    assert event["provenance"]["method"] == "explicit_cross_pack_promotion"

    store = DurableEventStore(
        tmp_path / "common-events",
        SCHEMA,
        promotion_source_resolver=lambda pack_id, revision, event_id: (
            source_event
            if (pack_id, revision, event_id)
            == (source, source_revision, source_event_id)
            else None
        ),
    )
    committed = store.commit(event)
    assert committed["subject_refs"] == [subject]
    assert len(list(store.iter_events())) == 1
