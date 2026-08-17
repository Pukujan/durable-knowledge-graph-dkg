from __future__ import annotations

import argparse
import json
from pathlib import Path

from fossil_core.adapters.vector import SemanticEmbeddingRetriever
from fossil_core.adapters.vector.sentence_transformers import SentenceTransformerEmbeddingProvider
from fossil_core.application.evaluation.benchmark import BenchmarkValidator, RetrievalBenchmark
from fossil_core.application.evaluation.cases import load_benchmark_case_set, retrieval_cases_from_case_set
from fossil_core.application.rebuild import retrieval_documents_from_pack_fixtures
from fossil_core.benchmark_compare import comparative_summary
from fossil_core.real_retrieval import (
    LifecycleIntentReranker,
    ReciprocalRankFusionRetriever,
    RerankedRetriever,
)
from fossil_core.services import (
    BM25Retriever,
    BudgetedContextProvider,
    EmbeddingRetriever,
    HashEmbeddingProvider,
)


CURRENT_ARCHITECTURE_QUERY = (
    "What is the current accepted durable architecture after storage alternatives were reconsidered?"
)
AI_PACK = "pack_f024177f89a5442db84171c3dd7f58e5"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run all Gate 2 retrieval competitors in one environment."
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
    parser.add_argument("--context-max-chars", type=int, default=4_000)
    parser.add_argument("--device", default="cpu")
    return parser.parse_args()


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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

    bm25 = BM25Retriever(documents, version="gate2-comparison-v1")
    hash_retriever = EmbeddingRetriever(
        documents,
        HashEmbeddingProvider(dimension=128, version="gate2-comparison-v1"),
        version="gate2-comparison-v1",
    )
    semantic_provider = SentenceTransformerEmbeddingProvider(device=args.device)
    dense = SemanticEmbeddingRetriever(
        documents,
        semantic_provider,
        version="gate2-comparison-bge-v1",
    )
    rrf = ReciprocalRankFusionRetriever(
        [bm25, dense],
        rrf_k=60,
        candidate_multiplier=4,
        version="gate2-comparison-rrf-v1",
    )
    hybrid = RerankedRetriever(
        rrf,
        LifecycleIntentReranker(version="gate2-comparison-lifecycle-v1"),
        candidate_multiplier=4,
        version="gate2-comparison-hybrid-v1",
    )

    services = {
        "bm25-control": bm25,
        "hash-embedding-control": hash_retriever,
        "bge-dense": dense,
        "bge-bm25-rrf-lifecycle": hybrid,
    }
    benchmark = RetrievalBenchmark(limit=args.limit)
    validator = BenchmarkValidator(schemas_root / "benchmark" / "v1.schema.json")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, dict] = {}
    contexts: dict[str, dict] = {}
    for name, service in services.items():
        result = benchmark.run(service, cases)
        validator.validate(result)
        results[name] = result
        _write_json(args.output_dir / f"{name}.benchmark.json", result)

        context = BudgetedContextProvider(
            service,
            max_chars=args.context_max_chars,
            version="gate2-comparison-context-v1",
        ).build_context(
            {
                "query": CURRENT_ARCHITECTURE_QUERY,
                "pack_ids": [AI_PACK],
                "limit": args.limit,
            }
        )
        contexts[name] = context

    comparison = comparative_summary(
        results,
        cases=cases,
        documents=documents,
        context_probes=contexts,
    )
    comparison["inputs"] = {
        "case_set_id": case_set["case_set_id"],
        "corpus": case_set["corpus"],
        "limit": args.limit,
        "context_max_chars": args.context_max_chars,
        "context_query": CURRENT_ARCHITECTURE_QUERY,
    }

    _write_json(args.output_dir / "context-probes.json", contexts)
    _write_json(args.output_dir / "comparison.json", comparison)

    print(json.dumps(comparison, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
