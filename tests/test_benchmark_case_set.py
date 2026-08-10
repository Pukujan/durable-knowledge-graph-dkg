from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import ValidationError

from dkg.benchmark_cases import (
    BenchmarkCaseSetError,
    load_benchmark_case_set,
    model_cases_from_case_set,
    retrieval_cases_from_case_set,
)


COMMON = "pack_269099f7b2ba43b7a99b9427d64092de"
AI = "pack_f024177f89a5442db84171c3dd7f58e5"
OTHER = "pack_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def root() -> Path:
    return Path(__file__).resolve().parents[1]


def schema() -> Path:
    return root() / "schemas" / "benchmark" / "case-set-v1.schema.json"


def fixture_citation() -> dict:
    return {
        "schema_version": "fossil.citation.v1",
        "citation_id": "cite_fixture_source_quality_001",
        "snapshot_id": "snap_fixture_source_quality_001",
        "artifact_id": "art_fixture_source_quality_00000001",
        "byte_start": 12,
        "byte_end": 36,
        "passage_hash": {
            "algorithm": "sha256",
            "digest": "a" * 64,
        },
    }


def fixture() -> dict:
    return {
        "schema_version": "fossil.benchmark-case-set.v1",
        "case_set_id": "caseset_gate2_fixture_001",
        "title": "Gate 2 fixture contract",
        "description": "Persistent gold cases pin their corpus commits and exact evidence targets.",
        "created_at": "2026-08-10T04:45:00Z",
        "corpus": [
            {
                "pack_id": COMMON,
                "repository": "Pukujan/fossil-common",
                "commit_sha": "94fd576286ee359f1929b31bbba99e0ca54d4b41",
            },
            {
                "pack_id": AI,
                "repository": "Pukujan/fossil-ai-systems",
                "commit_sha": "cfd03e08c36f00a5eb25c8de4c1463d06877e015",
            },
        ],
        "cases": [
            {
                "kind": "retrieval",
                "case_id": "source_quality_dimensions",
                "category": "source-citation-recovery",
                "query": "Why must source quality dimensions remain separate?",
                "pack_ids": [COMMON],
                "relevant_ids": ["doc_common_source_quality"],
                "gold": {
                    "answerable": True,
                    "expected_answer": "Source usefulness is claim-specific and dimensions remain canonical.",
                    "citations": [fixture_citation()],
                    "source_snapshot_ids": ["snap_fixture_source_quality_001"],
                    "notes": "IDs are fixture-shaped here; Gate 2 corpus seeding will replace them with generated stable IDs.",
                },
                "tags": ["exact-citation", "common-pack"],
            },
            {
                "kind": "model",
                "case_id": "insufficient_evidence_negative",
                "category": "insufficient-evidence",
                "task": {
                    "query": "Which permanent semantic retriever has FOSSIL selected?",
                    "pack_ids": [COMMON, AI],
                },
                "expected_output": {"answerable": False},
                "gold": {
                    "answerable": False,
                    "expected_answer": None,
                    "citations": [],
                    "source_snapshot_ids": [],
                    "notes": "The benchmark baseline explicitly does not select a production winner.",
                },
                "tags": ["negative", "authority-boundary"],
            },
        ],
    }


def write_case_set(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "case-set.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_case_set_pins_corpus_and_loads_existing_benchmark_case_types(tmp_path):
    loaded = load_benchmark_case_set(write_case_set(tmp_path, fixture()), schema())

    assert loaded["corpus"][0]["pack_id"] == COMMON
    assert loaded["corpus"][1]["pack_id"] == AI
    citation = loaded["cases"][0]["gold"]["citations"][0]
    assert citation["citation_id"] == "cite_fixture_source_quality_001"
    assert citation["byte_start"] == 12
    assert citation["passage_hash"]["digest"] == "a" * 64

    retrieval = retrieval_cases_from_case_set(loaded)
    assert len(retrieval) == 1
    assert retrieval[0].case_id == "source_quality_dimensions"
    assert retrieval[0].pack_ids == (COMMON,)
    assert retrieval[0].relevant_ids == frozenset({"doc_common_source_quality"})

    model = model_cases_from_case_set(loaded)
    assert len(model) == 1
    assert model[0].case_id == "insufficient_evidence_negative"
    assert model[0].task["pack_ids"] == [COMMON, AI]
    assert model[0].expected_output == {"answerable": False}


def test_case_set_rejects_duplicate_case_ids(tmp_path):
    payload = fixture()
    payload["cases"][1]["case_id"] = payload["cases"][0]["case_id"]

    with pytest.raises(BenchmarkCaseSetError, match="case IDs must be unique"):
        load_benchmark_case_set(write_case_set(tmp_path, payload), schema())


def test_case_set_rejects_retrieval_pack_not_pinned_by_corpus(tmp_path):
    payload = fixture()
    payload["cases"][0]["pack_ids"] = [OTHER]

    with pytest.raises(BenchmarkCaseSetError, match="not pinned by the case-set corpus"):
        load_benchmark_case_set(write_case_set(tmp_path, payload), schema())


def test_case_set_rejects_citation_snapshot_not_declared_by_gold(tmp_path):
    payload = fixture()
    payload["cases"][0]["gold"]["source_snapshot_ids"] = [
        "snap_different_source_snapshot_001"
    ]

    with pytest.raises(BenchmarkCaseSetError, match="undeclared source snapshots"):
        load_benchmark_case_set(write_case_set(tmp_path, payload), schema())


def test_case_set_schema_rejects_unpinned_corpus_commit_format(tmp_path):
    payload = copy.deepcopy(fixture())
    payload["corpus"][0]["commit_sha"] = "main"

    with pytest.raises(ValidationError):
        load_benchmark_case_set(write_case_set(tmp_path, payload), schema())
