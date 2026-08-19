from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SCHEMA_PATH = ROOT / "contracts/holdout/public-suite-manifest-v1.schema.json"
MANIFEST_PATH = ROOT / "contracts/holdout/fossil-holdout-suites-v1.json"
RECEIPT_SCHEMA_PATH = ROOT / "contracts/holdout/aggregate-receipt-v1.schema.json"
CATALOG_PATH = ROOT / "contracts/properties/fossil-properties-v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_public_holdout_manifest_validates_and_matches_receipt_version() -> None:
    schema = _load(MANIFEST_SCHEMA_PATH)
    manifest = _load(MANIFEST_PATH)
    receipt_schema = _load(RECEIPT_SCHEMA_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(manifest)
    assert manifest["receipt_schema_version"] == receipt_schema["properties"][
        "schema_version"
    ]["const"]


def test_public_holdout_manifest_suite_ids_are_unique_and_location_free() -> None:
    manifest = _load(MANIFEST_PATH)
    suite_ids = [item["suite_id"] for item in manifest["suites"]]

    assert len(suite_ids) == len(set(suite_ids))
    assert manifest["sealed_material_in_public_repo"] is False
    assert manifest["private_placement_disclosed"] is False
    assert manifest["credentials_disclosed"] is False
    assert all(item["status"] == "planned" for item in manifest["suites"])


def test_manifest_references_only_active_hidden_acceptance_properties() -> None:
    manifest = _load(MANIFEST_PATH)
    catalog = _load(CATALOG_PATH)
    allowed = {
        item["property_id"]
        for item in catalog["properties"]
        if item.get("status") == "active"
        and item.get("hidden_acceptance_required") is True
    }

    referenced = {
        property_id
        for suite in manifest["suites"]
        for property_id in suite["property_ids"]
    }
    assert referenced
    assert referenced <= allowed


def test_manifest_schema_rejects_private_case_execution_and_location_fields() -> None:
    schema = _load(MANIFEST_SCHEMA_PATH)
    manifest = _load(MANIFEST_PATH)
    validator = Draft202012Validator(schema)

    forbidden_top_level = {
        "case_count": 12,
        "storage_location": "private://sealed-suite/path",
        "executor": "private-runner",
        "credential_ref": "secret://holdout-token",
        "notes": "free-form text is intentionally absent",
    }
    for field, value in forbidden_top_level.items():
        candidate = deepcopy(manifest)
        candidate[field] = value
        assert list(validator.iter_errors(candidate)), field

    forbidden_suite_fields = {
        "case_ids": ["sealed-case-1"],
        "case_count": 12,
        "oracle": "private expected answer",
        "endpoint": "https://private.invalid",
        "runner": "private-runner",
    }
    for field, value in forbidden_suite_fields.items():
        candidate = deepcopy(manifest)
        candidate["suites"][0][field] = value
        assert list(validator.iter_errors(candidate)), field
