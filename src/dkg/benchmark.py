from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
import time
import tracemalloc
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator, FormatChecker


@dataclass(frozen=True)
class RetrievalBenchmarkCase:
    case_id: str
    query: str
    pack_ids: tuple[str, ...]
    relevant_ids: frozenset[str]
    category: str = "general"

    def __post_init__(self) -> None:
        if not self.case_id or not self.query or not self.pack_ids or not self.relevant_ids:
            raise ValueError("retrieval benchmark cases require id/query/packs/relevant ids")


@dataclass(frozen=True)
class ModelBenchmarkCase:
    case_id: str
    task: Mapping[str, Any]
    expected_output: Mapping[str, Any]
    category: str = "general"

    def __post_init__(self) -> None:
        if not self.case_id or not self.expected_output:
            raise ValueError("model benchmark cases require id and expected output")


@dataclass(frozen=True)
class BenchmarkEnvironment:
    python: str = field(default_factory=lambda: sys.version.split()[0])
    platform: str = field(default_factory=platform.platform)

    def as_dict(self) -> dict[str, str]:
        return {"python": self.python, "platform": self.platform}


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return ordered[index]


def _failure_rates(failures: Mapping[str, int], totals: Mapping[str, int]) -> dict[str, float]:
    return {
        category: failures.get(category, 0) / total if total else 0.0
        for category, total in sorted(totals.items())
    }


def _benchmark_id(kind: str, service: Mapping[str, Any], case_ids: Iterable[str]) -> str:
    payload = json.dumps(
        {
            "kind": kind,
            "service": dict(service),
            "cases": sorted(case_ids),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"bench_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"


class BenchmarkValidator:
    def __init__(self, schema_path: Path) -> None:
        schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(schema, format_checker=FormatChecker())

    def validate(self, result: Mapping[str, Any]) -> None:
        self.validator.validate(dict(result))


class RetrievalBenchmark:
    def __init__(self, *, limit: int = 5) -> None:
        if limit < 1:
            raise ValueError("benchmark limit must be positive")
        self.limit = int(limit)

    def run(self, retriever: Any, cases: Iterable[RetrievalBenchmarkCase]) -> dict[str, Any]:
        case_list = list(cases)
        if not case_list:
            raise ValueError("retrieval benchmark requires at least one case")
        service = retriever.metadata()
        latencies_ms: list[float] = []
        recalls: list[float] = []
        reciprocal_ranks: list[float] = []
        failures: dict[str, int] = {}
        totals: dict[str, int] = {}
        observations: list[dict[str, Any]] = []

        tracemalloc.start()
        try:
            for case in case_list:
                totals[case.category] = totals.get(case.category, 0) + 1
                started = time.perf_counter()
                results = retriever.search(
                    case.query,
                    pack_ids=list(case.pack_ids),
                    limit=self.limit,
                )
                latency_ms = (time.perf_counter() - started) * 1000.0
                latencies_ms.append(latency_ms)
                returned_ids = [str(result["id"]) for result in results]
                found = case.relevant_ids & set(returned_ids)
                recall = len(found) / len(case.relevant_ids)
                recalls.append(recall)
                reciprocal_rank = 0.0
                for rank, identifier in enumerate(returned_ids, start=1):
                    if identifier in case.relevant_ids:
                        reciprocal_rank = 1.0 / rank
                        break
                reciprocal_ranks.append(reciprocal_rank)
                failed = not found
                if failed:
                    failures[case.category] = failures.get(case.category, 0) + 1
                observations.append(
                    {
                        "case_id": case.case_id,
                        "category": case.category,
                        "returned_ids": returned_ids,
                        "relevant_ids": sorted(case.relevant_ids),
                        "recall_at_k": recall,
                        "reciprocal_rank": reciprocal_rank,
                        "latency_ms": latency_ms,
                        "failed": failed,
                    }
                )
            _, peak_bytes = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()

        call_cost = float(service.get("estimated_cost_per_call_usd", 0.0))
        return {
            "schema_version": "fossil.benchmark.v1",
            "benchmark_id": _benchmark_id(
                "retrieval", service, (case.case_id for case in case_list)
            ),
            "kind": "retrieval",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "service": service,
            "environment": BenchmarkEnvironment().as_dict(),
            "case_count": len(case_list),
            "metrics": {
                "limit": self.limit,
                "hit_rate": sum(not item["failed"] for item in observations) / len(case_list),
                "mean_recall_at_k": sum(recalls) / len(recalls),
                "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks),
                "mean_latency_ms": sum(latencies_ms) / len(latencies_ms),
                "p95_latency_ms": _percentile(latencies_ms, 0.95),
                "peak_python_alloc_bytes": peak_bytes,
                "estimated_cost_usd": call_cost * len(case_list),
                "failure_rate_by_category": _failure_rates(failures, totals),
            },
            "observations": observations,
        }


class ModelBenchmark:
    """Bounded-task benchmark; it measures candidates, not truth authority."""

    def run(self, service: Any, cases: Iterable[ModelBenchmarkCase]) -> dict[str, Any]:
        case_list = list(cases)
        if not case_list:
            raise ValueError("model benchmark requires at least one case")
        metadata = service.metadata()
        latencies_ms: list[float] = []
        failures: dict[str, int] = {}
        totals: dict[str, int] = {}
        observations: list[dict[str, Any]] = []

        tracemalloc.start()
        try:
            for case in case_list:
                totals[case.category] = totals.get(case.category, 0) + 1
                started = time.perf_counter()
                response = service.run(dict(case.task))
                latency_ms = (time.perf_counter() - started) * 1000.0
                latencies_ms.append(latency_ms)
                output = dict(response.get("output", {}))
                expected = dict(case.expected_output)
                matched = all(output.get(key) == value for key, value in expected.items())
                if not matched:
                    failures[case.category] = failures.get(case.category, 0) + 1
                observations.append(
                    {
                        "case_id": case.case_id,
                        "category": case.category,
                        "expected_output": expected,
                        "observed_output": output,
                        "authority": response.get("authority"),
                        "latency_ms": latency_ms,
                        "failed": not matched,
                    }
                )
            _, peak_bytes = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()

        cost = float(metadata.get("estimated_cost_per_call_usd", 0.0)) * len(case_list)
        return {
            "schema_version": "fossil.benchmark.v1",
            "benchmark_id": _benchmark_id(
                "model", metadata, (case.case_id for case in case_list)
            ),
            "kind": "model",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "service": metadata,
            "environment": BenchmarkEnvironment().as_dict(),
            "case_count": len(case_list),
            "metrics": {
                "exact_match_rate": sum(not item["failed"] for item in observations)
                / len(case_list),
                "mean_latency_ms": sum(latencies_ms) / len(latencies_ms),
                "p95_latency_ms": _percentile(latencies_ms, 0.95),
                "peak_python_alloc_bytes": peak_bytes,
                "estimated_cost_usd": cost,
                "failure_rate_by_category": _failure_rates(failures, totals),
            },
            "observations": observations,
        }
