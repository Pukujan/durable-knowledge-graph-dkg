from __future__ import annotations

import inspect

import fossil_core.application.evaluation.cases as canonical_cases
import fossil_core.benchmark_cases as legacy_cases


EXPECTED_IMPLICIT_NAMESPACE = {
    "Any",
    "BenchmarkCaseSetError",
    "Draft202012Validator",
    "FormatChecker",
    "Mapping",
    "ModelBenchmarkCase",
    "Path",
    "RetrievalBenchmarkCase",
    "annotations",
    "copy",
    "json",
    "load_benchmark_case_set",
    "model_cases_from_case_set",
    "retrieval_cases_from_case_set",
}

SEMANTIC_SYMBOLS = (
    "BenchmarkCaseSetError",
    "load_benchmark_case_set",
    "retrieval_cases_from_case_set",
    "model_cases_from_case_set",
)


def test_benchmark_cases_legacy_namespace_and_identity_are_frozen():
    assert not hasattr(legacy_cases, "__all__")
    assert {
        name for name in vars(legacy_cases) if not name.startswith("_")
    } == EXPECTED_IMPLICIT_NAMESPACE

    for name in SEMANTIC_SYMBOLS:
        assert getattr(legacy_cases, name) is getattr(canonical_cases, name)

    assert legacy_cases.RetrievalBenchmarkCase is canonical_cases.RetrievalBenchmarkCase
    assert legacy_cases.ModelBenchmarkCase is canonical_cases.ModelBenchmarkCase


def test_benchmark_case_set_call_shapes_are_unchanged():
    load_parameters = list(
        inspect.signature(canonical_cases.load_benchmark_case_set).parameters.values()
    )
    assert [parameter.name for parameter in load_parameters] == ["path", "schema_path"]
    assert all(
        parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and parameter.default is inspect.Parameter.empty
        for parameter in load_parameters
    )

    retrieval_parameters = list(
        inspect.signature(canonical_cases.retrieval_cases_from_case_set).parameters.values()
    )
    assert [parameter.name for parameter in retrieval_parameters] == ["case_set"]

    model_parameters = list(
        inspect.signature(canonical_cases.model_cases_from_case_set).parameters.values()
    )
    assert [parameter.name for parameter in model_parameters] == ["case_set"]


def test_case_conversion_matches_through_legacy_and_canonical_paths():
    case_set = {
        "cases": [
            {
                "kind": "retrieval",
                "case_id": "retrieval-one",
                "query": "query",
                "pack_ids": ["pack-one"],
                "relevant_ids": ["doc-one"],
                "category": "retrieval-category",
            },
            {
                "kind": "model",
                "case_id": "model-one",
                "task": {"query": "question"},
                "expected_output": {"answerable": True},
                "category": "model-category",
            },
        ]
    }

    legacy_retrieval = legacy_cases.retrieval_cases_from_case_set(case_set)
    canonical_retrieval = canonical_cases.retrieval_cases_from_case_set(case_set)
    assert legacy_retrieval == canonical_retrieval
    assert type(legacy_retrieval[0]) is canonical_cases.RetrievalBenchmarkCase

    legacy_model = legacy_cases.model_cases_from_case_set(case_set)
    canonical_model = canonical_cases.model_cases_from_case_set(case_set)
    assert legacy_model == canonical_model
    assert type(legacy_model[0]) is canonical_cases.ModelBenchmarkCase

    case_set["cases"][1]["task"]["query"] = "mutated after conversion"
    assert legacy_model[0].task == {"query": "question"}
