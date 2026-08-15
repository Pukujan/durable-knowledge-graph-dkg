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

# Exercise each required declaration independently so a mutant that drops one
# declaration cannot hide behind another missing field in the same receipt.
REQUIRED_PATHS = [
    ("schema_version",),
    ("host",),
    ("host", "node"),
    ("health",),
    ("health", "fossil_health_url"),
    ("health", "fossil_health_url", "url"),
    ("health", "fossil_health_url", "json_key"),
    ("health", "fossil_health_url", "outcome"),
    ("health", "gravebuster_health_url"),
    ("health", "gravebuster_health_url", "url"),
    ("health", "gravebuster_health_url", "json_key"),
    ("health", "gravebuster_health_url", "outcome"),
    ("tailscale",),
    ("tailscale", "host"),
    ("tailscale", "reachable"),
    ("variables",),
    ("variables", 0, "name"),
    ("variables", 0, "required"),
    ("variables", 0, "present"),
    ("correlation",),
    *(('correlation', key) for key in sorted(CORRELATION_KEYS)),
    ("status",),
    ("timestamp",),
]

CLOSED_ENUM_MUTATIONS = [
    (("schema_version",), "9.9.9"),
    (("status",), "unknown"),
    (("health", "fossil_health_url", "outcome"), "unknown"),
    (("health", "gravebuster_health_url", "outcome"), "unknown"),
]


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _set_path(document: dict, path: tuple[object, ...], value: object) -> None:
    target = document
    for part in path[:-1]:
        target = target[part]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]


def _remove_path(document: dict, path: tuple[object, ...]) -> None:
    target = document
    for part in path[:-1]:
        target = target[part]  # type: ignore[index]
    del target[path[-1]]  # type: ignore[index]


@pytest.fixture(scope="module")
def validator() -> "jsonschema.validators.Validator":
    schema = _load(SCHEMA)
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )


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


@pytest.mark.parametrize("path", REQUIRED_PATHS)
def test_each_required_field_rejects_independent_removal(validator, path) -> None:
    receipt = _load(VALID)
    _remove_path(receipt, path)

    assert list(validator.iter_errors(receipt))


@pytest.mark.parametrize(("path", "value"), CLOSED_ENUM_MUTATIONS)
def test_each_closed_enum_rejects_unknown_value(validator, path, value) -> None:
    receipt = _load(VALID)
    _set_path(receipt, path, value)

    assert list(validator.iter_errors(receipt))


def test_schema_version_is_exactly_v1(validator) -> None:
    receipt = _load(VALID)
    receipt["schema_version"] = "2.0.0"

    assert list(validator.iter_errors(receipt))


def test_timestamp_is_a_checked_date_time(validator) -> None:
    receipt = _load(VALID)
    receipt["timestamp"] = "not-a-date-time"

    assert validator.format_checker is not None
    assert list(validator.iter_errors(receipt))


def test_variables_are_explicit_per_variable_records(validator) -> None:
    receipt = _load(VALID)
    receipt["variables"] = [
        {"name": "FOSSIL_API_KEY", "required": True, "present": True},
        {"name": "DEBUG_LEVEL", "required": False, "present": False},
    ]

    assert list(validator.iter_errors(receipt)) == []


def test_parallel_variable_arrays_are_rejected(validator) -> None:
    receipt = _load(VALID)
    receipt["variables"] = {
        "names": ["FOSSIL_API_KEY", "GRAVEBUSTER_TOKEN"],
        "present": [True, True],
    }

    assert list(validator.iter_errors(receipt))


@pytest.mark.parametrize("record", ["fossil_health_url", "gravebuster_health_url"])
def test_each_health_record_requires_an_observed_outcome(validator, record) -> None:
    receipt = _load(VALID)
    receipt["health"][record].pop("outcome", None)

    assert list(validator.iter_errors(receipt))


@pytest.mark.parametrize(
    "path,value",
    [
        (("variables", 0, "present"), False),
        (("tailscale", "reachable"), False),
        (("health", "fossil_health_url", "outcome"), "failure"),
        (("health", "gravebuster_health_url", "outcome"), "unreachable"),
    ],
)
def test_operational_requires_successful_required_evidence(validator, path, value) -> None:
    receipt = _load(VALID)
    target = receipt
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value

    assert list(validator.iter_errors(receipt))


def test_operational_requires_a_declared_required_variable(validator) -> None:
    receipt = _load(VALID)
    for variable in receipt["variables"]:
        variable["required"] = False

    assert list(validator.iter_errors(receipt))


@pytest.mark.parametrize("status", ["degraded", "fail_closed"])
def test_non_operational_statuses_can_report_honest_negative_evidence(validator, status) -> None:
    receipt = _load(VALID)
    receipt["status"] = status
    receipt["tailscale"]["reachable"] = False
    receipt["health"]["fossil_health_url"]["outcome"] = "unreachable"

    assert list(validator.iter_errors(receipt)) == []


def test_closed_receipt_shape_rejects_unknown_fields(validator) -> None:
    receipt = _load(VALID)
    receipt["health"]["fossil_health_url"]["unchecked"] = "extra"

    assert list(validator.iter_errors(receipt))


@pytest.mark.parametrize("identifier", sorted(CORRELATION_KEYS))
def test_correlation_identifiers_must_be_nonempty(validator, identifier) -> None:
    receipt = _load(VALID)
    receipt["correlation"][identifier] = ""

    assert list(validator.iter_errors(receipt))


def test_valid_example_passes(validator) -> None:
    assert list(validator.iter_errors(_load(VALID))) == []


def test_invalid_example_rejected(validator) -> None:
    assert list(validator.iter_errors(_load(INVALID)))


def test_valid_example_has_complete_correlation_spine() -> None:
    correlation = _load(VALID)["correlation"]
    assert CORRELATION_KEYS <= set(correlation)


def test_examples_are_distinct() -> None:
    assert _load(VALID) != _load(INVALID)
