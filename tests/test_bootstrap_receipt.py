"""Tests for the v5-authored FOSSIL bootstrap/deployment receipt contract.

Verifies the bootstrap-receipt-v1 schema is well-formed, that the valid example
passes, and that the invalid example is rejected (fail-closed). Authored by a
Cortex V5 task and mechanically verified; adapted here as an offline pytest.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = REPO_ROOT / "contracts" / "engineering" / "bootstrap-receipt-v1.schema.json"
EXAMPLES = REPO_ROOT / "contracts" / "engineering" / "examples"
VALID = EXAMPLES / "bootstrap-receipt-valid.json"
INVALID = EXAMPLES / "bootstrap-receipt-invalid.json"

CORRELATION_KEYS = {
    "project_issue_id",
    "work_order_id",
    "task_id",
    "attempt_id",
    "request_id",
    "trace_id",
    "checkpoint_id",
    "commit_sha",
    "deployment_id",
}


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def validator() -> "jsonschema.validators.Validator":
    schema = _load(SCHEMA)
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


def test_schema_requires_deployment_proof_facts(validator) -> None:
    schema = _load(SCHEMA)
    required = set(schema["required"])
    assert {
        "host",
        "health",
        "tailscale",
        "variables",
        "correlation",
        "status",
        "timestamp",
    } <= required


def test_valid_example_passes(validator) -> None:
    assert list(validator.iter_errors(_load(VALID))) == []


def test_invalid_example_rejected(validator) -> None:
    assert list(validator.iter_errors(_load(INVALID)))


def test_valid_example_has_complete_correlation_spine() -> None:
    correlation = _load(VALID)["correlation"]
    assert CORRELATION_KEYS <= set(correlation)


def test_examples_are_distinct() -> None:
    assert _load(VALID) != _load(INVALID)