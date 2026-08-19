from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "contracts/holdout/aggregate-receipt-v1.schema.json"
DEFAULT_CATALOG = ROOT / "contracts/properties/fossil-properties-v1.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(
    receipt: dict[str, Any],
    *,
    schema: dict[str, Any],
    catalog: dict[str, Any],
) -> list[str]:
    failures: list[str] = []

    validator = Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(receipt), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.path) or "<root>"
        failures.append(f"schema {location}: {error.message}")

    if failures:
        return failures

    hidden_properties = {
        item["property_id"]
        for item in catalog["properties"]
        if item.get("status") == "active"
        and item.get("hidden_acceptance_required") is True
    }
    unknown = sorted(set(receipt["property_ids"]) - hidden_properties)
    if unknown:
        failures.append(
            "receipt property_ids are not active hidden-acceptance properties: "
            + ", ".join(unknown)
        )

    counts = receipt["counts"]
    total = counts["total"]
    passed = counts["passed"]
    failed = counts["failed"]
    if total != passed + failed:
        failures.append(
            f"counts total {total} must equal passed+failed ({passed + failed})"
        )

    classified_failures = sum(item["count"] for item in receipt["failure_classes"])
    if classified_failures != failed:
        failures.append(
            "failure_classes count total "
            f"{classified_failures} must equal counts.failed {failed}"
        )

    result = receipt["result"]
    if result == "PASS":
        if total <= 0:
            failures.append("PASS requires at least one evaluated holdout case")
        if failed != 0 or passed != total:
            failures.append("PASS requires failed=0 and passed=total")
    elif result == "FAIL":
        if failed <= 0:
            failures.append("FAIL requires at least one failed holdout case")
    elif result == "BLOCKED":
        if total != 0 or passed != 0 or failed != 0:
            failures.append("BLOCKED requires zero evaluated cases")
        if receipt["failure_classes"]:
            failures.append("BLOCKED cannot report case failure classes")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    args = parser.parse_args()

    schema = _load(args.schema)
    Draft202012Validator.check_schema(schema)
    catalog = _load(args.catalog)
    receipt = _load(args.receipt)

    failures = evaluate(receipt, schema=schema, catalog=catalog)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print(
        json.dumps(
            {
                "schema_version": receipt["schema_version"],
                "suite_id": receipt["suite_id"],
                "software_commit": receipt["software_commit"],
                "property_ids": receipt["property_ids"],
                "result": receipt["result"],
                "counts": receipt["counts"],
                "failure_classes": receipt["failure_classes"],
                "blocker_class": receipt.get("blocker_class"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
