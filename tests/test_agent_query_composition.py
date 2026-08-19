from __future__ import annotations

from pathlib import Path

import pytest

from fossil_core.agent import AgentContext, CorpusService, SkillRegistry
from fossil_core.event_store import DurableEventStore
from fossil_core.pack import PackAccess, PackBoundaryError
from fossil_core.services import BM25Retriever, BudgetedContextProvider

COMMON = "pack_269099f7b2ba43b7a99b9427d64092de"
PROJECT = "pack_f024177f89a5442db84171c3dd7f58e5"
OTHER_PROJECT = "pack_other_project_fixture"


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


def project_access() -> PackAccess:
    return PackAccess(
        pack_id=PROJECT,
        read_mounts=frozenset({COMMON, PROJECT}),
        write_targets=frozenset({PROJECT}),
    )


def search_context() -> AgentContext:
    return AgentContext(
        actor_id="agent-query-composition-fixture",
        model_id="fixture-model-v1",
        harness_version="fixture-harness-v1",
        skill_id="skill_corpus-search",
        skill_version="1.0.0",
    )


def documents() -> list[dict]:
    return [
        {
            "id": "doc_common",
            "pack_id": COMMON,
            "text": "lineage pack scoped retrieval evidence",
            "current_state": "supported",
        },
        {
            "id": "doc_project",
            "pack_id": PROJECT,
            "text": "project pack scoped retrieval evidence",
            "current_state": "supported",
        },
        {
            "id": "doc_other",
            "pack_id": OTHER_PROJECT,
            "text": "retrieval retrieval retrieval evidence from another project",
            "current_state": "supported",
        },
    ]


def test_rich_search_uses_only_project_read_mounts(tmp_path):
    service = CorpusService(
        event_store=store(tmp_path),
        skills=registry(),
        retriever=BM25Retriever(documents()),
    )

    results = service.search(
        "retrieval evidence",
        access=project_access(),
        context=search_context(),
        limit=10,
    )

    assert {item["id"] for item in results} == {"doc_common", "doc_project"}
    assert {item["pack_id"] for item in results} == {COMMON, PROJECT}
    assert OTHER_PROJECT not in {item["pack_id"] for item in results}


def test_context_can_narrow_to_one_mounted_project_pack(tmp_path):
    retriever = BM25Retriever(documents())
    service = CorpusService(
        event_store=store(tmp_path),
        skills=registry(),
        retriever=retriever,
        context_provider=BudgetedContextProvider(retriever, max_chars=2_000),
    )

    result = service.context(
        {
            "query": "retrieval evidence",
            "pack_ids": [PROJECT],
            "limit": 10,
        },
        access=project_access(),
        context=search_context(),
    )

    assert result["pack_ids"] == [PROJECT]
    assert [item["id"] for item in result["items"]] == ["doc_project"]
    assert {item["pack_id"] for item in result["items"]} == {PROJECT}


def test_context_rejects_unmounted_project_pack_before_provider_call(tmp_path):
    retriever = BM25Retriever(documents())
    service = CorpusService(
        event_store=store(tmp_path),
        skills=registry(),
        context_provider=BudgetedContextProvider(retriever, max_chars=2_000),
    )

    with pytest.raises(PackBoundaryError, match="not mounted for reading"):
        service.context(
            {
                "query": "retrieval evidence",
                "pack_ids": [OTHER_PROJECT],
                "limit": 10,
            },
            access=project_access(),
            context=search_context(),
        )


class LeakyRetriever:
    def search(self, query: str, *, pack_ids: list[str], limit: int = 20):
        del query, pack_ids, limit
        return [
            {
                "id": "doc_leaked",
                "pack_id": OTHER_PROJECT,
                "text": "leaked foreign project knowledge",
            }
        ]


def test_agent_boundary_fails_closed_if_retriever_ignores_pack_scope(tmp_path):
    service = CorpusService(
        event_store=store(tmp_path),
        skills=registry(),
        retriever=LeakyRetriever(),
    )

    with pytest.raises(PackBoundaryError, match="crossed query boundary"):
        service.search(
            "leaked",
            access=project_access(),
            context=search_context(),
        )


class LeakyContextProvider:
    def build_context(self, request: dict):
        return {
            "query": request["query"],
            "pack_ids": request["pack_ids"],
            "items": [
                {
                    "id": "doc_leaked_context",
                    "pack_id": OTHER_PROJECT,
                    "text": "leaked context from another project",
                }
            ],
            "context_text": "leaked context from another project",
        }


def test_agent_boundary_fails_closed_if_context_provider_widens_scope(tmp_path):
    service = CorpusService(
        event_store=store(tmp_path),
        skills=registry(),
        context_provider=LeakyContextProvider(),
    )

    with pytest.raises(PackBoundaryError, match="crossed query boundary"):
        service.context(
            {"query": "leaked", "pack_ids": [PROJECT]},
            access=project_access(),
            context=search_context(),
        )
