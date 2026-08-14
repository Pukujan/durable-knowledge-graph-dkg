from __future__ import annotations

from pathlib import Path

import pytest

from dkg.agent import (
    AgentContext,
    AgentProvenanceError,
    CapabilityError,
    CorpusService,
    SkillRegistry,
    ThinMCPAdapter,
)
from dkg.event_store import DurableEventStore
from dkg.pack import PackAccess, PackBoundaryError


COMMON = "pack_269099f7b2ba43b7a99b9427d64092de"
AI = "pack_f024177f89a5442db84171c3dd7f58e5"


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def registry() -> SkillRegistry:
    return SkillRegistry(
        root() / "skills", root() / "schemas" / "agent-skill" / "v1.schema.json"
    )


def store(tmp_path: Path) -> DurableEventStore:
    return DurableEventStore(
        tmp_path / "events", root() / "schemas" / "events" / "v1.schema.json"
    )


def access_ai() -> PackAccess:
    return PackAccess(
        pack_id=AI,
        read_mounts=frozenset({COMMON, AI}),
        write_targets=frozenset({AI}),
    )


def access_common_admin() -> PackAccess:
    return PackAccess(
        pack_id=COMMON,
        read_mounts=frozenset({COMMON, AI}),
        write_targets=frozenset({COMMON}),
    )


def context(skill_id: str) -> AgentContext:
    return AgentContext(
        actor_id="agent-fixture",
        model_id="fixture-model-v1",
        harness_version="fixture-harness-v2",
        skill_id=skill_id,
        skill_version="1.1.0" if skill_id == "skill_research-ingestion" else "1.0.0",
    )


def test_six_required_skills_validate_and_methodology_is_progressively_disclosed():
    skills = registry()
    manifests = skills.list_skills()
    assert {manifest["skill_id"] for manifest in manifests} == {
        "skill_corpus-search",
        "skill_research-ingestion",
        "skill_citation-audit",
        "skill_contradiction-review",
        "skill_stale-assumption-review",
        "skill_knowledge-promotion",
    }

    discovered = skills.discover("contradiction evidence")
    assert any(item["skill_id"] == "skill_contradiction-review" for item in discovered)
    assert not skills.methodology_loaded("skill_contradiction-review")
    assert all("methodology" not in item for item in discovered)

    methodology = skills.load_methodology("skill_contradiction-review")
    assert "multi-model agreement" in methodology
    assert skills.methodology_loaded("skill_contradiction-review")


def test_agent_proposal_carries_actor_model_harness_and_skill_provenance(tmp_path):
    service = CorpusService(event_store=store(tmp_path), skills=registry())
    ctx = context("skill_research-ingestion")
    proposal = service.propose(
        event_type="claim.proposed",
        pack_id=AI,
        subject_refs=["clm_agent_boundary_fixture"],
        payload={"claim_text": "Durable commit precedes projection."},
        occurred_at="2026-08-09T23:20:00Z",
        recorded_at="2026-08-09T23:20:00Z",
        idempotency_key="agent-boundary-proposal-v1",
        evidence_refs=["art_fixture_evidence_001"],
        access=access_ai(),
        context=ctx,
    )

    assert proposal["actor"] == {
        "actor_type": "agent",
        "actor_id": "agent-fixture",
        "model_id": "fixture-model-v1",
        "harness_version": "fixture-harness-v2",
        "skill_id": "skill_research-ingestion",
        "skill_version": "1.1.0",
    }
    assert proposal["provenance"]["method"] == "agent_proposal"
    assert proposal["provenance"]["prompt_or_policy_ref"] == (
        "skill_research-ingestion@1.1.0"
    )
    assert proposal["event_id"].startswith("evt_")
    assert list(service.event_store.iter_events()) == []

    validated = service.validate(proposal, access=access_ai(), context=ctx)
    assert validated == proposal
    assert list(service.event_store.iter_events()) == []

    accepted = service.commit(proposal, access=access_ai(), context=ctx)
    assert accepted == proposal
    assert service.commit(proposal, access=access_ai(), context=ctx) == accepted
    assert [item["event_id"] for item in service.event_store.iter_events()] == [
        accepted["event_id"]
    ]
    assert not hasattr(service, "graph")
    assert not hasattr(service, "neo4j")


def test_pack_boundary_and_skill_capability_both_gate_mutation(tmp_path):
    service = CorpusService(event_store=store(tmp_path), skills=registry())
    ingestion = context("skill_research-ingestion")

    with pytest.raises(PackBoundaryError):
        service.propose(
            event_type="claim.proposed",
            pack_id=COMMON,
            subject_refs=["clm_forbidden_common_write"],
            payload={"claim_text": "should fail"},
            occurred_at="2026-08-09T23:21:00Z",
            recorded_at="2026-08-09T23:21:00Z",
            idempotency_key="forbidden-common-write-v1",
            access=access_ai(),
            context=ingestion,
        )

    review_ctx = context("skill_contradiction-review")
    proposal = service.propose(
        event_type="claim.proposed",
        pack_id=AI,
        subject_refs=["clm_review_only"],
        payload={"claim_text": "review proposal"},
        occurred_at="2026-08-09T23:22:00Z",
        recorded_at="2026-08-09T23:22:00Z",
        idempotency_key="review-proposal-v1",
        access=access_ai(),
        context=review_ctx,
    )
    with pytest.raises(CapabilityError, match="does not grant.*commit"):
        service.commit(proposal, access=access_ai(), context=review_ctx)


def test_commit_rejects_forged_agent_provenance(tmp_path):
    service = CorpusService(event_store=store(tmp_path), skills=registry())
    ctx = context("skill_research-ingestion")
    proposal = service.propose(
        event_type="claim.proposed",
        pack_id=AI,
        subject_refs=["clm_forged_actor"],
        payload={"claim_text": "forgery check"},
        occurred_at="2026-08-09T23:23:00Z",
        recorded_at="2026-08-09T23:23:00Z",
        idempotency_key="forged-actor-v1",
        access=access_ai(),
        context=ctx,
    )
    proposal["actor"]["model_id"] = "different-model"

    with pytest.raises(AgentProvenanceError, match="does not match session context"):
        service.commit(proposal, access=access_ai(), context=ctx)
    assert list(service.event_store.iter_events()) == []


def test_search_and_read_only_cross_mounted_packs(tmp_path):
    events = store(tmp_path)
    common_event = events.commit(
        {
            "schema_version": "dkg.event.v1",
            "event_type": "claim.proposed",
            "occurred_at": "2026-08-09T23:24:00Z",
            "recorded_at": "2026-08-09T23:24:00Z",
            "pack_id": COMMON,
            "actor": {"actor_type": "system", "actor_id": "fixture"},
            "subject_refs": ["clm_shared_search_fixture"],
            "idempotency_key": "shared-search-fixture-v1",
            "payload": {"claim_text": "shared searchable knowledge"},
        }
    )
    ai_event = events.commit(
        {
            "schema_version": "dkg.event.v1",
            "event_type": "claim.proposed",
            "occurred_at": "2026-08-09T23:25:00Z",
            "recorded_at": "2026-08-09T23:25:00Z",
            "pack_id": AI,
            "actor": {"actor_type": "system", "actor_id": "fixture"},
            "subject_refs": ["clm_ai_search_fixture"],
            "idempotency_key": "ai-search-fixture-v1",
            "payload": {"claim_text": "AI local searchable knowledge"},
        }
    )
    service = CorpusService(event_store=events, skills=registry())
    ctx = context("skill_corpus-search")

    results = service.search("searchable", access=access_ai(), context=ctx)
    assert {item["event_id"] for item in results} == {
        common_event["event_id"],
        ai_event["event_id"],
    }
    assert service.read(common_event["event_id"], access=access_ai(), context=ctx) == common_event

    common_only = PackAccess(
        pack_id=COMMON,
        read_mounts=frozenset({COMMON}),
        write_targets=frozenset({COMMON}),
    )
    with pytest.raises(PackBoundaryError):
        service.read(ai_event["event_id"], access=common_only, context=ctx)


class FakeLineage:
    def current_conclusions(self):
        return [{"node_id": "ln_current", "label": "current"}]

    def historical_nodes(self):
        return [{"node_id": "ln_old", "label": "historical"}]

    def node(self, node_id: str):
        return {"node_id": node_id, "label": "selected"}

    def citations(self, node_id: str):
        return [{"node_id": node_id, "artifact_id": "art_fixture_citation"}]

    def opposing_positions(self, node_id: str):
        return [{"node_id": "ln_opposing", "opposes": node_id}]


def test_lineage_is_protocol_independent_and_pack_gated(tmp_path):
    service = CorpusService(
        event_store=store(tmp_path),
        skills=registry(),
        lineages={"conv_fixture_0001": (COMMON, FakeLineage())},
    )
    ctx = context("skill_corpus-search")
    result = service.lineage(
        "conv_fixture_0001",
        node_id="ln_current",
        access=access_ai(),
        context=ctx,
    )
    assert result["pack_id"] == COMMON
    assert result["current_conclusions"][0]["node_id"] == "ln_current"
    assert result["citations"][0]["artifact_id"] == "art_fixture_citation"


def test_knowledge_promotion_is_new_durable_target_event(tmp_path):
    service = CorpusService(event_store=store(tmp_path), skills=registry())
    ctx = context("skill_knowledge-promotion")
    access = PackAccess(
        pack_id=AI,
        read_mounts=frozenset({AI, COMMON}),
        write_targets=frozenset({COMMON}),
    )
    proposal = service.propose_promotion(
        source_pack_id=AI,
        target_pack_id=COMMON,
        subject_refs=["clm_reusable_agent_method"],
        occurred_at="2026-08-09T23:26:00Z",
        recorded_at="2026-08-09T23:26:00Z",
        idempotency_key="agent-promotion-v1",
        evidence_refs=["art_promotion_evidence"],
        reason="reusable across projects",
        access=access,
        context=ctx,
    )
    assert proposal["event_type"] == "knowledge.promoted"
    assert proposal["pack_id"] == COMMON
    assert proposal["payload"]["source_pack_id"] == AI
    assert proposal["actor"]["skill_id"] == "skill_knowledge-promotion"
    accepted = service.commit(proposal, access=access, context=ctx)
    assert accepted["event_id"] == proposal["event_id"]


def test_thin_mcp_adapter_has_allowlisted_surface_and_no_graph_escape_hatch(tmp_path):
    service = CorpusService(event_store=store(tmp_path), skills=registry())
    ctx = context("skill_citation-audit")
    adapter = ThinMCPAdapter(service=service, access=access_ai(), context=ctx)

    assert set(adapter.list_tools()) == {
        "fossil.search",
        "fossil.read",
        "fossil.lineage",
        "fossil.propose",
        "fossil.validate",
        "fossil.commit",
        "fossil.manage",
    }
    capabilities = adapter.invoke("fossil.manage", {"action": "capabilities"})
    assert capabilities["arbitrary_graph_mutation"] is False
    assert "graph.execute" not in capabilities["capabilities"]

    with pytest.raises(CapabilityError, match="not in the FOSSIL agent capability surface"):
        adapter.invoke("neo4j.cypher", {"query": "MATCH (n) DETACH DELETE n"})
    with pytest.raises(CapabilityError, match="not in the FOSSIL agent capability surface"):
        adapter.invoke("graphiti.add_episode", {"content": "bypass durable event"})
