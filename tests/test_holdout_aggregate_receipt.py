from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.check_holdout_aggregate_receipt import evaluate


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "contracts/holdout/aggregate-receipt-v1.schema.json"
CATALOG_PATH = ROOT / "contracts/properties/fossil-properties-v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _pass_receipt() -> dict:
    return {
        "schema_version": "fossil.hidden-acceptance-aggregate.v1",
        "suite_id": "holdout_citation-integrity-v1",
        "software_commit": "a" * 40,
        "property_ids": ["FOSSIL-PROP-CITATION-INTEGRITY-001"],
        "result": "PASS",
        "counts": {"total": 12, "passed": 12, "failed": 0},
        "failure_classes": [],
        "sealed_material_disclosed": False,
        "private_oracle_disclosed": False,
        "credentials_disclosed": False,
        "public_run_ref": "github-run:example-public-ref",
    }


def test_holdout_aggregate_schema_is_valid_and_pass_receipt_is_accepted() -> None:
    schema = _load(SCHEMA_PATH)
    catalog = _load(CATALOG_PATH)

    Draft202012Validator.check_schema(schema)
    assert evaluate(_pass_receipt(), schema=schema, catalog=catalog) == []


def test_fail_receipt_allows_only_aggregate_failure_classes() -> None:
    schema = _load(SCHEMA_PATH)
    catalog = _load(CATALOG_PATH)
    receipt = _pass_receipt()
    receipt.update(
        result="FAIL",
        counts={"total": 12, "passed": 9, "failed": 3},
        failure_classes=[
            {"class_id": "property_violation", "count": 2},
            {"class_id": "missing_evidence", "count": 1},
        ],
    )

    assert evaluate(receipt, schema=schema, catalog=catalog) == []


def test_blocked_receipt_exposes_only_public_blocker_class() -> None:
    schema = _load(SCHEMA_PATH)
    catalog = _load(CATALOG_PATH)
    receipt = _pass_receipt()
    receipt.update(
        result="BLOCKED",
        counts={"total": 0, "passed": 0, "failed": 0},
        failure_classes=[],
        blocker_class="policy_not_approved",
    )

    assert evaluate(receipt, schema=schema, catalog=catalog) == []


def test_unknown_or_non_hidden_property_ids_are_rejected() -> None:
    schema = _load(SCHEMA_PATH)
    catalog = _load(CATALOG_PATH)

    unknown = _pass_receipt()
    unknown["property_ids"] = ["FOSSIL-PROP-NOT-REAL-001"]
    assert any("not active hidden-acceptance" in item for item in evaluate(unknown, schema=schema, catalog=catalog))

    public_only = _pass_receipt()
    public_only["property_ids"] = ["FOSSIL-PROP-IDEMPOTENCY-001"]
    assert any("not active hidden-acceptance" in item for item in evaluate(public_only, schema=schema, catalog=catalog))


def test_count_and_result_consistency_fail_closed() -> None:
    schema = _load(SCHEMA_PATH)
    catalog = _load(CATALOG_PATH)

    mismatch = _pass_receipt()
    mismatch["counts"] = {"total": 12, "passed": 10, "failed": 1}
    failures = evaluate(mismatch, schema=schema, catalog=catalog)
    assert any("must equal passed+failed" in item for item in failures)
    assert any("PASS requires failed=0 and passed=total" in item for item in failures)

    unclassified = _pass_receipt()
    unclassified.update(
        result="FAIL",
        counts={"total": 12, "passed": 10, "failed": 2},
        failure_classes=[{"class_id": "property_violation", "count": 1}],
    )
    assert any(
        "must equal counts.failed" in item
        for item in evaluate(unclassified, schema=schema, catalog=catalog)
    )


def test_private_case_oracle_credential_and_location_fields_are_rejected() -> None:
    schema = _load(SCHEMA_PATH)
    catalog = _load(CATALOG_PATH)

    forbidden_examples = {
        "case_ids": ["sealed-case-17"],
        "private_oracle": "exact expected answer",
        "credential_ref": "secret://holdout-token",
        "storage_location": "private://sealed-suite/path",
        "case_failures": [{"input": "secret adversarial fixture"}],
    }

    for field, value in forbidden_examples.items():
        receipt = deepcopy(_pass_receipt())
        receipt[field] = value
        failures = evaluate(receipt, schema=schema, catalog=catalog)
        assert failures, field
        assert any("schema <root>" in item for item in failures), field


def test_disclosure_flags_cannot_be_set_true() -> None:
    schema = _load(SCHEMA_PATH)
    catalog = _load(CATALOG_PATH)

    for field in (
        "sealed_material_disclosed",
        "private_oracle_disclosed",
        "credentials_disclosed",
    ):
        receipt = deepcopy(_pass_receipt())
        receipt[field] = True
        failures = evaluate(receipt, schema=schema, catalog=catalog)
        assert failures, field
