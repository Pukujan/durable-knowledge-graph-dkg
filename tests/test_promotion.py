from pathlib import Path

from dkg.event_store import DurableEventStore
from dkg.promotion import build_promotion_event

ROOT = Path(__file__).parents[1]
SCHEMA = ROOT / "schemas/events/v1.schema.json"


def test_promotion_is_new_target_event_with_source_provenance(tmp_path: Path):
    source = "pack_f024177f89a5442db84171c3dd7f58e5"
    target = "pack_269099f7b2ba43b7a99b9427d64092de"
    subject = "clm_example_0000000000000001"

    event = build_promotion_event(
        source_pack_id=source,
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
    assert event["provenance"]["method"] == "explicit_cross_pack_promotion"

    store = DurableEventStore(tmp_path / "common-events", SCHEMA)
    committed = store.commit(event)
    assert committed["subject_refs"] == [subject]
    assert len(list(store.iter_events())) == 1
