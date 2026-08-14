import asyncio
import json

from fossil_core.projection.graphiti import GraphitiProjectionAdapter
from fossil_core.projection.ledger import ProjectionLedger


class FakeGraphiti:
    def __init__(self):
        self.calls = []
        self.fail = False

    async def add_episode(self, **kwargs):
        if self.fail:
            raise RuntimeError("temporary graph failure")
        self.calls.append(kwargs)


def sample_event():
    return {
        "event_id": "evt_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "event_type": "claim.proposed",
        "occurred_at": "2026-08-09T17:21:00Z",
        "pack_id": "pack_269099f7b2ba43b7a99b9427d64092de",
        "subject_refs": ["clm_example_0000000000000001"],
        "payload": {"claim_text": "x"},
    }


def adapter(tmp_path, client):
    return GraphitiProjectionAdapter(
        client=client,
        ledger=ProjectionLedger(tmp_path / "projection-ledger", "graphiti-neo4j"),
        build_manifest={
            "graphiti_version": "0.29.3",
            "neo4j_version": "5.26",
            "model_id": "test-model",
            "ontology_version": "1.0.0",
            "software_commit": "test",
        },
        episode_type_json="json",
    )


def test_pack_id_is_projection_namespace_and_retry_is_idempotent(tmp_path):
    client = FakeGraphiti()
    projection = adapter(tmp_path, client)
    event = sample_event()

    first = asyncio.run(projection.apply_event_async(event))
    second = asyncio.run(projection.apply_event_async(event))

    assert first.status == "applied"
    assert second.status == "skipped"
    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["group_id"] == event["pack_id"]
    assert json.loads(call["episode_body"])["event_id"] == event["event_id"]
    applied = projection.ledger.get_applied(event["event_id"])
    assert applied["build_manifest"]["graphiti_version"] == "0.29.3"


def test_failure_is_recorded_and_event_can_be_retried(tmp_path):
    client = FakeGraphiti()
    projection = adapter(tmp_path, client)
    event = sample_event()

    client.fail = True
    failed = asyncio.run(projection.apply_event_async(event))
    assert failed.status == "failed"
    assert not projection.ledger.is_applied(event["event_id"])
    failures = list(
        (tmp_path / "projection-ledger" / "graphiti-neo4j" / "failures").rglob("*.json")
    )
    assert len(failures) == 1

    client.fail = False
    applied = asyncio.run(projection.apply_event_async(event))
    assert applied.status == "applied"
    assert projection.ledger.is_applied(event["event_id"])
