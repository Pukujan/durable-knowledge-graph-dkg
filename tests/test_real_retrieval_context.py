from __future__ import annotations

from dkg.real_retrieval import LifecycleIntentReranker, RerankedRetriever
from dkg.services import BudgetedContextProvider


PACK = "pack_f024177f89a5442db84171c3dd7f58e5"


class FixedRetriever:
    def metadata(self):
        return {
            "kind": "retriever",
            "provider": "test",
            "provider_version": "1",
            "implementation": "fixed",
            "implementation_version": "1",
            "model_id": None,
            "local": True,
            "estimated_cost_per_call_usd": 0.0,
            "runtime": {},
        }

    def search(self, query: str, *, pack_ids: list[str], limit: int = 20):
        candidates = [
            {
                "id": "stale_history",
                "pack_id": PACK,
                "text": "Former SQLite canonical architecture.",
                "current_state": "stale_pending_review",
            },
            {
                "id": "current_architecture",
                "pack_id": PACK,
                "text": "Current accepted durable architecture uses immutable evidence and append-only events.",
                "current_state": "supported",
            },
        ]
        return [
            {
                **candidate,
                "retrieval": {
                    "rank": rank,
                    "score": 1.0 / rank,
                    "service": self.metadata(),
                },
            }
            for rank, candidate in enumerate(candidates[:limit], start=1)
            if candidate["pack_id"] in set(pack_ids)
        ]


def test_budgeted_context_provider_accepts_lifecycle_aware_retriever_without_contract_changes():
    retriever = RerankedRetriever(
        FixedRetriever(),
        LifecycleIntentReranker(version="gate2"),
        candidate_multiplier=2,
        version="gate2",
    )
    context = BudgetedContextProvider(
        retriever,
        max_chars=120,
        version="gate2",
    ).build_context(
        {
            "query": "What is the current accepted architecture?",
            "pack_ids": [PACK],
            "limit": 2,
        }
    )

    assert context["items"][0]["id"] == "current_architecture"
    assert context["items"][0]["current_state"] == "supported"
    assert context["chars_used"] <= context["max_chars"] == 120
    assert context["service"]["implementation"] == "budgeted-retrieval-context"
    assert context["service"]["runtime"]["retriever"] == "reranked-retriever"
