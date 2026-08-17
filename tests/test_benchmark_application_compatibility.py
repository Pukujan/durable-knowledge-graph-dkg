from __future__ import annotations

import inspect

import fossil_core.application.evaluation.benchmark as canonical_benchmark
import fossil_core.benchmark as legacy_benchmark


EXPECTED_IMPLICIT_NAMESPACE = {
    "Any",
    "BenchmarkEnvironment",
    "BenchmarkValidator",
    "Draft202012Validator",
    "FormatChecker",
    "Iterable",
    "Mapping",
    "ModelBenchmark",
    "ModelBenchmarkCase",
    "Path",
    "RetrievalBenchmark",
    "RetrievalBenchmarkCase",
    "annotations",
    "dataclass",
    "datetime",
    "field",
    "hashlib",
    "json",
    "math",
    "platform",
    "sys",
    "time",
    "timezone",
    "tracemalloc",
}

SEMANTIC_SYMBOLS = (
    "RetrievalBenchmarkCase",
    "ModelBenchmarkCase",
    "BenchmarkEnvironment",
    "BenchmarkValidator",
    "RetrievalBenchmark",
    "ModelBenchmark",
)


def test_benchmark_legacy_namespace_and_identity_are_frozen():
    assert not hasattr(legacy_benchmark, "__all__")
    assert {
        name for name in vars(legacy_benchmark) if not name.startswith("_")
    } == EXPECTED_IMPLICIT_NAMESPACE

    for name in SEMANTIC_SYMBOLS:
        assert getattr(legacy_benchmark, name) is getattr(canonical_benchmark, name)


def test_benchmark_call_shapes_are_unchanged():
    retrieval_init = list(
        inspect.signature(canonical_benchmark.RetrievalBenchmark).parameters.values()
    )
    assert [parameter.name for parameter in retrieval_init] == ["limit"]
    assert retrieval_init[0].kind is inspect.Parameter.KEYWORD_ONLY
    assert retrieval_init[0].default == 5

    retrieval_run = list(
        inspect.signature(canonical_benchmark.RetrievalBenchmark.run).parameters.values()
    )
    assert [parameter.name for parameter in retrieval_run] == [
        "self",
        "retriever",
        "cases",
    ]

    model_run = list(
        inspect.signature(canonical_benchmark.ModelBenchmark.run).parameters.values()
    )
    assert [parameter.name for parameter in model_run] == ["self", "service", "cases"]

    validator_init = list(
        inspect.signature(canonical_benchmark.BenchmarkValidator).parameters.values()
    )
    assert [parameter.name for parameter in validator_init] == ["schema_path"]
    assert validator_init[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert validator_init[0].default is inspect.Parameter.empty

    validator_validate = list(
        inspect.signature(canonical_benchmark.BenchmarkValidator.validate).parameters.values()
    )
    assert [parameter.name for parameter in validator_validate] == ["self", "result"]


def test_benchmark_case_construction_is_identical_through_legacy_path():
    retrieval_case = legacy_benchmark.RetrievalBenchmarkCase(
        "case_one",
        "query",
        ("pack_one",),
        frozenset({"doc_one"}),
        "category",
    )
    assert type(retrieval_case) is canonical_benchmark.RetrievalBenchmarkCase
    assert retrieval_case == canonical_benchmark.RetrievalBenchmarkCase(
        "case_one",
        "query",
        ("pack_one",),
        frozenset({"doc_one"}),
        "category",
    )

    model_case = legacy_benchmark.ModelBenchmarkCase(
        "model_one",
        {"input": "value"},
        {"label": "expected"},
        "category",
    )
    assert type(model_case) is canonical_benchmark.ModelBenchmarkCase
    assert model_case == canonical_benchmark.ModelBenchmarkCase(
        "model_one",
        {"input": "value"},
        {"label": "expected"},
        "category",
    )
