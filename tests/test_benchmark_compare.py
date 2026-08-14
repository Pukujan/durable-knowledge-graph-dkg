from __future__ import annotations

from fossil_core.benchmark import RetrievalBenchmarkCase
from fossil_core.benchmark_compare import classify_context_probe, classify_retrieval_result, comparative_summary


PACK = "pack_f024177f89a5442db84171c3dd7f58e5"
OTHER = "pack_269099f7b2ba43b7a99b9427d64092de"


def cases():
    return [
        RetrievalBenchmarkCase(
            case_id="current_case",
            query="What is the current architecture?",
            pack_ids=(PACK,),
            relevant_ids=frozenset({"current"}),
            category="current-vs-historical",
        ),
        RetrievalBenchmarkCase(
            case_id="bundle_case",
            query="Retrieve the former and current conclusions.",
            pack_ids=(PACK,),
            relevant_ids=frozenset({"former", "current"}),
            category="decision-lineage",
        ),
    ]


def documents():
    return [
        {"id": "current", "pack_id": PACK, "text": "current", "current_state": "supported"},
        {"id": "former", "pack_id": PACK, "text": "former", "current_state": "superseded"},
        {"id": "stale", "pack_id": PACK, "text": "stale", "current_state": "stale_pending_review"},
        {"id": "other", "pack_id": OTHER, "text": "other", "current_state": "supported"},
    ]


def result():
    return {
        "benchmark_id": "bench_test_000000000000000000000001",
        "service": {"implementation": "test"},
        "metrics": {"hit_rate": 0.5},
        "observations": [
            {
                "case_id": "current_case",
                "category": "current-vs-historical",
                "returned_ids": ["stale", "former"],
                "relevant_ids": ["current"],
                "recall_at_k": 0.0,
                "reciprocal_rank": 0.0,
                "failed": True,
            },
            {
                "case_id": "bundle_case",
                "category": "decision-lineage",
                "returned_ids": ["former", "other"],
                "relevant_ids": ["current", "former"],
                "recall_at_k": 0.5,
                "reciprocal_rank": 1.0,
                "failed": False,
            },
        ],
    }


def test_failure_taxonomy_classifies_miss_partial_recall_leakage_and_pack_violation():
    classified = classify_retrieval_result(result(), cases=cases(), documents=documents())

    assert classified["counts"] == {
        "retrieval_miss": 1,
        "incomplete_multi_target_recall": 2,
        "bad_ranking": 0,
        "stale_superseded_leakage": 1,
        "pack_isolation_violation": 1,
    }
    assert classified["examples"]["stale_superseded_leakage"][0]["case_id"] == "current_case"
    assert classified["examples"]["pack_isolation_violation"][0]["violating_ids"] == ["other"]
    assert classified["unsupported_confidence_leakage"]["applicable"] is False


def test_bad_ranking_is_separate_from_full_miss():
    value = result()
    value["observations"][0] = {
        "case_id": "current_case",
        "category": "current-vs-historical",
        "returned_ids": ["former", "current"],
        "relevant_ids": ["current"],
        "recall_at_k": 1.0,
        "reciprocal_rank": 0.5,
        "failed": False,
    }

    classified = classify_retrieval_result(value, cases=cases(), documents=documents())

    assert classified["counts"]["retrieval_miss"] == 0
    assert classified["counts"]["bad_ranking"] == 1
    assert classified["counts"]["stale_superseded_leakage"] == 1


def test_context_probe_distinguishes_truncation_from_wrong_selection():
    clean = classify_context_probe(
        {
            "chars_used": 120,
            "max_chars": 4000,
            "items": [
                {"id": "former", "context_truncated": False},
                {"id": "stale", "context_truncated": False},
            ],
        }
    )
    truncated = classify_context_probe(
        {
            "chars_used": 4000,
            "max_chars": 4000,
            "items": [{"id": "current", "context_truncated": True}],
        }
    )

    assert clean["context_truncation_or_overload"] is False
    assert clean["item_ids"] == ["former", "stale"]
    assert truncated["context_truncation_or_overload"] is True
    assert truncated["truncated_ids"] == ["current"]


def test_comparative_summary_never_selects_a_policy():
    summary = comparative_summary(
        {"candidate": result()},
        cases=cases(),
        documents=documents(),
        context_probes={
            "candidate": {
                "chars_used": 100,
                "max_chars": 4000,
                "items": [{"id": "former", "context_truncated": False}],
            }
        },
    )

    assert summary["schema_version"] == "fossil.gate2-comparison.v1"
    assert summary["case_count"] == 2
    assert summary["service_count"] == 1
    assert summary["selection"]["selected"] is None
    assert summary["services"]["candidate"]["context_probe"]["context_truncation_or_overload"] is False
