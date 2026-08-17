from __future__ import annotations

import argparse
import json
from pathlib import Path

from fossil_core.application.rebuild import retrieval_documents_from_pack_fixtures
from fossil_core.benchmark import BenchmarkValidator, RetrievalBenchmark
from fossil_core.benchmark_cases import load_benchmark_case_set, retrieval_cases_from_case_set
from fossil_core.services import BM25Retriever, EmbeddingRetriever, HashEmbeddingProvider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Gate 2 retrieval controls against validated real FOSSIL pack roots."
    )
    parser.add_argument("--common-root", type=Path, required=True)
    parser.add_argument("--ai-root", type=Path, required=True)
    parser.add_argument(
        "--case-set",
        type=Path,
        default=Path("benchmarks/gate2/real-corpus-seed-v1.json"),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=5)
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

    services = {
        "bm25-control": BM25Retriever(documents, version="gate2-control-v1"),
        "hash-embedding-control": EmbeddingRetriever(
            documents,
            HashEmbeddingProvider(dimension=128, version="gate2-control-v1"),
            version="gate2-control-v1",
        ),
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
            "output": str(path),
        }

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
