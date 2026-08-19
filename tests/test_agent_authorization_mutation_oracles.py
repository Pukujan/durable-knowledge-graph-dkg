from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from fossil_core.agent import AgentContext, AgentProvenanceError, CorpusService, SkillRegistry
from fossil_core.pack import PackAccess


COMMON = "pack_269099f7b2ba43b7a99b9427d64092de"
AI = "pack_f024177f89a5442db84171c3dd7f58e5"


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def registry() -> SkillRegistry:
    return SkillRegistry(
        root() / "skills", root() / "schemas" / "agent-skill" / "v1.schema.json"
    )


def access_ai() -> PackAccess:
    return PackAccess(
        pack_id=AI,
        read_mounts=frozenset({COMMON, AI}),
        write_targets=frozenset({AI}),
    )


def context(*, skill_version: str = "1.1.0") -> AgentContext:
    return AgentContext(
        actor_id="agent-authorization-fixture",
        model_id="fixture-model-v1",
        harness_version="fixture-harness-v2",
        skill_id="skill_research-ingestion",
        skill_version=skill_version,
    )


class RecordingEventStore:
    def __init__(self) -> None:
        self.prepared: dict[str, Any] | None = None

    def prepare(self, event: dict[str, Any]) -> dict[str, Any]:
        self.prepared = event
        return event


def proposal_kwargs() -> dict[str, Any]:
    return {
        "event_type": "claim.proposed",
        "pack_id": AI,
        "subject_refs": ["clm_agent_authorization_fixture"],
        "payload": {"claim_text": "authorization remains server-owned"},
        "occurred_at": "2026-08-19T06:48:00Z",
        "recorded_at": "2026-08-19T06:48:01Z",
        "idempotency_key": "agent-authorization-fixture-v1",
    }


def test_propose_rejects_stale_registered_skill_version_before_prepare() -> None:
    events = RecordingEventStore()
    service = CorpusService(event_store=events, skills=registry())

    with pytest.raises(AgentProvenanceError):
        service.propose(
            **proposal_kwargs(),
            access=access_ai(),
            context=context(skill_version="0.0.0"),
        )

    assert events.prepared is None


def test_propose_deep_copies_nested_payload_before_event_store_boundary() -> None:
    events = RecordingEventStore()
    service = CorpusService(event_store=events, skills=registry())
    nested_payload = {
        "claim_text": "caller mutation must not rewrite prepared evidence",
        "metadata": {"tags": ["original"]},
    }
    kwargs = proposal_kwargs()
    kwargs["payload"] = nested_payload

    proposal = service.propose(**kwargs, access=access_ai(), context=context())
    nested_payload["metadata"]["tags"].append("mutated-after-propose")

    assert events.prepared is proposal
    assert proposal["payload"] == {
        "claim_text": "caller mutation must not rewrite prepared evidence",
        "metadata": {"tags": ["original"]},
    }
