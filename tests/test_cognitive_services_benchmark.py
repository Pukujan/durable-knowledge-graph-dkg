from __future__ import annotations

from pathlib import Path

from dkg.benchmark import (
    BenchmarkValidator,
    ModelBenchmark,
    ModelBenchmarkCase,
    RetrievalBenchmark,
    RetrievalBenchmarkCase,
)
from dkg.event_store import DurableEventStore
from dkg.services import (
    BM25Retriever,
    BudgetedContextProvider,
    CallableCandidateModelService,
    EmbeddingRetriever,
    HashEmbeddingProvider,
    PolicyVerificationService,
    RiskEscalationPolicy,
    TokenOverlapReranker,
)


COMMON = "pack_269099f7b2ba43b7a99b9427d64092de"
AI = "pack_f024177f89a5442db84171c3dd7f58e5"


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def documents() -> list[dict]:
    return [
        {
            "id": "doc_common_kedb",
            "pack_id": COMMON,
            "text": "Failure learning uses KEDB records inside a MAPE-K improvement loop.",
        },
        {
            "id": "doc_ai_temporal_graph",
            "pack_id": AI,
            "text": "Graphiti projects temporal knowledge into a rebuildable Neo4j graph.",
        },
        {
            "id": "doc_ai_translation",
            "pack_id": AI,
            "text": "Representation mismatch motivates an AI translation layer for the learning UX.",
        },
        {
            "id": "doc_common_sources",
            "pack_id": COMMON,
            "text": "Citation provenance resolves evidence to immutable source snapshots and spans.",
        },
    ]


def test_initial_retrieval_embedding_reranker_and_context_implementations_are_replaceable():
    lexical = BM25Retriever(documents())
    lexical_result = lexical.search(
        "failure learning KEDB",
        pack_ids=[COMMON],
        limit=3,
    )
    assert lexical_result[0]["id"] == "doc_common_kedb"
    assert all(result["pack_id"] == COMMON for result in lexical_result)
    assert lexical.metadata()["implementation"] == "bm25"

    embedder = HashEmbeddingProvider(dimension=64)
    assert embedder.model_id.startswith("fossil-hash-embedding-64")
    vectors = embedder.embed(["same tokens", "same tokens"])
    assert vectors[0] == vectors[1]
    assert round(sum(value * value for value in vectors[0]), 8) == 1.0

    vector = EmbeddingRetriever(documents(), embedder)
    vector_result = vector.search(
        "representation mismatch translation",
        pack_ids=[AI],
        limit=3,
    )
    assert vector_result[0]["id"] == "doc_ai_translation"
    assert vector.metadata()["model_id"] == embedder.model_id

    reranker = TokenOverlapReranker()
    reranked = reranker.rerank(
        "temporal knowledge graph",
        lexical.search("graph knowledge temporal", pack_ids=[AI], limit=5),
        limit=2,
    )
    assert reranked[0]["id"] == "doc_ai_temporal_graph"
    assert reranked[0]["rerank"]["service"]["implementation"] == "token-overlap"

    context = BudgetedContextProvider(
        lexical,
        reranker=reranker,
        max_chars=72,
    )
    built = context.build_context(
        {"query": "temporal knowledge graph", "pack_ids": [AI], "limit": 2}
    )
    assert built["chars_used"] <= 72
    assert built["items"][0]["id"] == "doc_ai_temporal_graph"
    assert built["service"]["runtime"] == {
        "retriever": "bm25",
        "reranker": "token-overlap",
    }


def test_retrieval_benchmark_records_quality_latency_memory_cost_and_failure_rates():
    retriever = BM25Retriever(documents())
    cases = [
        RetrievalBenchmarkCase(
            "case_kedb",
            "failure learning KEDB",
            (COMMON,),
            frozenset({"doc_common_kedb"}),
            "failure-learning",
        ),
        RetrievalBenchmarkCase(
            "case_temporal",
            "temporal knowledge graph",
            (AI,),
            frozenset({"doc_ai_temporal_graph"}),
            "temporal-graph",
        ),
        RetrievalBenchmarkCase(
            "case_translation",
            "representation mismatch translation layer",
            (AI,),
            frozenset({"doc_ai_translation"}),
            "representation-mismatch",
        ),
    ]
    result = RetrievalBenchmark(limit=3).run(retriever, cases)
    BenchmarkValidator(root() / "schemas" / "benchmark" / "v1.schema.json").validate(result)

    assert result["kind"] == "retrieval"
    assert result["metrics"]["hit_rate"] == 1.0
    assert result["metrics"]["mean_recall_at_k"] == 1.0
    assert result["metrics"]["mrr"] == 1.0
    assert result["metrics"]["mean_latency_ms"] >= 0
    assert result["metrics"]["p95_latency_ms"] >= 0
    assert result["metrics"]["peak_python_alloc_bytes"] >= 0
    assert result["metrics"]["estimated_cost_usd"] == 0
    assert result["metrics"]["failure_rate_by_category"] == {
        "failure-learning": 0.0,
        "representation-mismatch": 0.0,
        "temporal-graph": 0.0,
    }


def test_candidate_model_benchmark_preserves_provider_versions_without_granting_authority():
    def specialist(task: dict) -> dict:
        text = str(task["text"]).lower()
        return {"label": "stale" if "outdated" in text else "active"}

    model = CallableCandidateModelService(
        specialist,
        provider="local-fixture",
        provider_version="2026.08",
        model_id="bounded-staleness-specialist-v1",
        implementation_version="1",
        local=True,
        runtime={"engine": "python-fixture"},
    )
    direct = model.run({"text": "this assumption is outdated"})
    assert direct["output"] == {"label": "stale"}
    assert direct["authority"] == "candidate_only"
    assert direct["service"]["provider"] == "local-fixture"
    assert direct["service"]["provider_version"] == "2026.08"
    assert direct["service"]["model_id"] == "bounded-staleness-specialist-v1"

    result = ModelBenchmark().run(
        model,
        [
            ModelBenchmarkCase(
                "stale_1",
                {"text": "outdated dependency"},
                {"label": "stale"},
                "staleness",
            ),
            ModelBenchmarkCase(
                "active_1",
                {"text": "current dependency"},
                {"label": "active"},
                "staleness",
            ),
        ],
    )
    BenchmarkValidator(root() / "schemas" / "benchmark" / "v1.schema.json").validate(result)
    assert result["metrics"]["exact_match_rate"] == 1.0
    assert result["metrics"]["failure_rate_by_category"] == {"staleness": 0.0}
    assert all(item["authority"] == "candidate_only" for item in result["observations"])


def test_risk_policy_requires_independent_evidence_for_candidate_truth_changes():
    verifier = PolicyVerificationService(
        RiskEscalationPolicy(
            uncertainty_threshold=0.25,
            min_independent_evidence_for_truth_change=1,
        )
    )

    no_evidence = verifier.verify(
        {
            "requested_action": "commit",
            "truth_change": True,
            "risk": "low",
            "uncertainty": 0.1,
            "authority": "candidate_only",
            "independent_evidence_refs": [],
        }
    )
    assert no_evidence["decision"] == "escalate"
    assert "insufficient_independent_evidence" in no_evidence["reasons"]

    independently_supported = verifier.verify(
        {
            "requested_action": "commit",
            "truth_change": True,
            "risk": "low",
            "uncertainty": 0.1,
            "authority": "candidate_only",
            "independent_evidence_refs": ["snap_primary_measurement_001"],
        }
    )
    assert independently_supported["decision"] == "allow_commit_after_verification"
    assert independently_supported["source_authority"] == "candidate_only"
    assert independently_supported["service"]["runtime"]["policy_id"] == (
        "fossil-risk-escalation-v1"
    )

    high_risk = verifier.verify(
        {
            "requested_action": "commit",
            "truth_change": True,
            "risk": "high",
            "uncertainty": 0.1,
            "authority": "candidate_only",
            "independent_evidence_refs": ["snap_primary_measurement_001"],
        }
    )
    assert high_risk["decision"] == "escalate"
    assert "high_risk" in high_risk["reasons"]

    proposal_only = verifier.verify(
        {
            "requested_action": "propose",
            "truth_change": True,
            "risk": "high",
            "uncertainty": 0.9,
            "authority": "candidate_only",
            "independent_evidence_refs": [],
        }
    )
    assert proposal_only["decision"] == "allow_proposal"


def test_model_provider_and_benchmark_versions_can_be_committed_as_event_provenance(tmp_path):
    events = DurableEventStore(
        tmp_path / "events",
        root() / "schemas" / "events" / "v1.schema.json",
    )
    committed = events.commit(
        {
            "schema_version": "dkg.event.v1",
            "event_type": "review.completed",
            "occurred_at": "2026-08-10T01:40:00Z",
            "recorded_at": "2026-08-10T01:40:00Z",
            "pack_id": AI,
            "actor": {
                "actor_type": "agent",
                "actor_id": "benchmark-review-agent",
                "model_id": "bounded-staleness-specialist-v1",
                "harness_version": "fossil-benchmark-harness-v1",
                "skill_id": "stale-assumption-review",
                "skill_version": "1",
            },
            "subject_refs": ["clm_benchmark_review_fixture"],
            "idempotency_key": "benchmark-review-provenance-v1",
            "payload": {"decision": "candidate_only"},
            "provenance": {
                "method": "specialist_benchmark_review",
                "model_provider": "local-fixture",
                "model_provider_version": "2026.08",
                "model_runtime": "python-fixture",
                "model_service_version": "1",
                "benchmark_ref": "bench_fixture_reference_001",
            },
        }
    )
    assert committed["provenance"]["model_provider"] == "local-fixture"
    assert committed["provenance"]["model_provider_version"] == "2026.08"
    assert committed["provenance"]["benchmark_ref"] == "bench_fixture_reference_001"
