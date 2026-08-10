from __future__ import annotations

import argparse
import json
from pathlib import Path

from dkg.benchmark import BenchmarkValidator, RetrievalBenchmark
from dkg.benchmark_cases import load_benchmark_case_set, retrieval_cases_from_case_set
from dkg.pack_corpus import retrieval_documents_from_pack_fixtures
from dkg.real_retrieval import (
    LifecycleIntentReranker,
    ReciprocalRankFusionRetriever,
    RerankedRetriever,
    SentenceTransformerEmbeddingProvider,
)
from dkg.semantic_retriever import SemanticEmbeddingRetriever
from dkg.services import BM25Retriever, BudgetedContextProvider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Gate 2 real semantic/hybrid retrieval candidates on validated FOSSIL packs."
    )
    parser.add_argument("--common-root", type=Path, required=True)
    parser.add_argument("--ai-root", type=Path, required=True)
    parser.add_argument(
        "--case-set",
        type=Path,
        default=Path("benchmarks/gate2/real-corpus-history-v2.json"),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--device", default="cpu")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    schemas_root = repo_root / "schemas"
    case_set = load_benchmark_case_set(
        args.case_set,
        schemas_root / "benchmark" / "case-set-v1.schema.json",
    )
    cases = retrieval_cases_from_case_set(case_set)
    documents = retrieval_documents_from_pack_fixtures(
        [args.common_root, args.ai_root],
        schemas_root=schemas_root,
    )

    embedder = SentenceTransformerEmbeddingProvider(device=args.device)
    dense = SemanticEmbeddingRetriever(
        documents,
        embedder,
        version="gate2-bge-v1",
    )
    lexical = BM25Retriever(documents, version="gate2-bm25-v1")
    rrf = ReciprocalRankFusionRetriever(
        [lexical, dense],
        rrf_k=60,
        candidate_multiplier=4,
        version="gate2-bge-bm25-rrf-v1",
    )
    hybrid = RerankedRetriever(
        rrf,
        LifecycleIntentReranker(version="gate2-lifecycle-v1"),
        candidate_multiplier=4,
        version="gate2-bge-bm25-rrf-lifecycle-v1",
    )

    services = {
        "bge-dense": dense,
        "bge-bm25-rrf-lifecycle": hybrid,
    }
    benchmark = RetrievalBenchmark(limit=args.limit)
    validator = BenchmarkValidator(schemas_root / "benchmark" / "v1.schema.json")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, dict] = {}
    for name, service in services.items():
        result = benchmark.run(service, cases)
        validator.validate(result)
        path = args.output_dir / f"{name}.json"
        path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        summary[name] = {
            "benchmark_id": result["benchmark_id"],
            "case_count": result["case_count"],
            "metrics": result["metrics"],
            "service": result["service"],
            "output": str(path),
        }

    ai_pack = "pack_f024177f89a5442db84171c3dd7f58e5"
    context = BudgetedContextProvider(
        hybrid,
        max_chars=4_000,
        version="gate2-real-candidates-v1",
    ).build_context(
        {
            "query": "What is the current accepted durable architecture after storage alternatives were reconsidered?",
            "pack_ids": [ai_pack],
            "limit": args.limit,
        }
    )
    summary["context_smoke"] = {
        "chars_used": context["chars_used"],
        "item_ids": [item["id"] for item in context["items"]],
        "service": context["service"],
    }

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
