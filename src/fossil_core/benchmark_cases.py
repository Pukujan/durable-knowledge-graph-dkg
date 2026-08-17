from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker

from .application.evaluation.benchmark import ModelBenchmarkCase, RetrievalBenchmarkCase


class BenchmarkCaseSetError(ValueError):
    pass


def load_benchmark_case_set(
    path: Path,
    schema_path: Path,
) -> dict[str, Any]:
    """Load and validate a persistent benchmark case set.

    JSON Schema owns the portable data shape. These semantic checks cover the
    relationships JSON Schema cannot express compactly: case IDs are unique,
    retrieval cases may only mount packs pinned by the case-set corpus, and
    exact citation gold must resolve to source snapshots declared by the case.
    """

    candidate = json.loads(Path(path).read_text(encoding="utf-8"))
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(candidate)

    case_ids = [str(case["case_id"]) for case in candidate["cases"]]
    if len(case_ids) != len(set(case_ids)):
        raise BenchmarkCaseSetError("benchmark case IDs must be unique within a case set")

    corpus_pack_ids = {str(entry["pack_id"]) for entry in candidate["corpus"]}
    for case in candidate["cases"]:
        if case["kind"] == "retrieval":
            requested = {str(pack_id) for pack_id in case["pack_ids"]}
            unavailable = requested - corpus_pack_ids
            if unavailable:
                raise BenchmarkCaseSetError(
                    "retrieval case references packs not pinned by the case-set corpus: "
                    + ", ".join(sorted(unavailable))
                )

        gold = dict(case.get("gold", {}))
        citations = list(gold.get("citations", []))
        citation_ids = [str(citation["citation_id"]) for citation in citations]
        if len(citation_ids) != len(set(citation_ids)):
            raise BenchmarkCaseSetError(
                f"benchmark case {case['case_id']} contains duplicate citation IDs"
            )
        declared_snapshots = {
            str(snapshot_id) for snapshot_id in gold.get("source_snapshot_ids", [])
        }
        cited_snapshots = {str(citation["snapshot_id"]) for citation in citations}
        undeclared = cited_snapshots - declared_snapshots
        if undeclared:
            raise BenchmarkCaseSetError(
                f"benchmark case {case['case_id']} citations reference undeclared source snapshots: "
                + ", ".join(sorted(undeclared))
            )

    return copy.deepcopy(candidate)


def retrieval_cases_from_case_set(
    case_set: Mapping[str, Any],
) -> list[RetrievalBenchmarkCase]:
    return [
        RetrievalBenchmarkCase(
            case_id=str(case["case_id"]),
            query=str(case["query"]),
            pack_ids=tuple(str(pack_id) for pack_id in case["pack_ids"]),
            relevant_ids=frozenset(str(identifier) for identifier in case["relevant_ids"]),
            category=str(case["category"]),
        )
        for case in case_set["cases"]
        if case["kind"] == "retrieval"
    ]


def model_cases_from_case_set(
    case_set: Mapping[str, Any],
) -> list[ModelBenchmarkCase]:
    return [
        ModelBenchmarkCase(
            case_id=str(case["case_id"]),
            task=copy.deepcopy(dict(case["task"])),
            expected_output=copy.deepcopy(dict(case["expected_output"])),
            category=str(case["category"]),
        )
        for case in case_set["cases"]
        if case["kind"] == "model"
    ]
