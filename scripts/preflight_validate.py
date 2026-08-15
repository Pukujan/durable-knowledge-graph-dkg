"""Offline validator and CLI for engineering preflight/closeout v1 receipts.

Loads the JSON Schemas from ``contracts/engineering`` and validates a receipt.
Runs offline with no network, no model, and no secrets. Adds the fail-closed
semantic checks that generic JSON Schema cannot express, most importantly that
stale or historical material is never silently treated as current authority.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "contracts" / "engineering"

PREFLIGHT_VERSION = "preflight-v1"
CLOSEOUT_VERSION = "closeout-v1"

CURRENT_STATUSES = frozenset({"CURRENT_AUTHORITY", "ACCEPTED"})
STALE_KINDS = frozenset({"stale_or_unverified", "historical"})
STALE_STATUSES = frozenset({"STALE", "SUPERSEDED_OR_HISTORICAL"})


def load_receipt(path: str | Path) -> Mapping[str, Any]:
    """Load a JSON receipt from disk and require a JSON object."""
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("receipt must be a JSON object")
    return value


def load_schema(name: str) -> Mapping[str, Any]:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _schema_errors(receipt: Mapping[str, Any]) -> list[str]:
    version = receipt.get("version")
    if version == PREFLIGHT_VERSION:
        validator = Draft202012Validator(load_schema("preflight-v1.schema.json"))
    elif version == CLOSEOUT_VERSION:
        validator = Draft202012Validator(load_schema("closeout-v1.schema.json"))
    else:
        return [f"unsupported receipt version: {version!r}"]
    return sorted((error.message for error in validator.iter_errors(receipt)), key=str)


def semantic_source_errors(receipt: Mapping[str, Any]) -> list[str]:
    """Reject receipts that silently treat stale/historical material as current authority.

    A source that is kind ``stale_or_unverified``/``historical``, has status
    ``STALE``/``SUPERSEDED_OR_HISTORICAL``, or reports stale freshness may remain
    as lineage, but it must never be classified as current authority.
    """
    errors: list[str] = []
    for source in receipt.get("sources", []):
        stable_id = source.get("stable_id", "?")
        kind = source.get("kind")
        status = source.get("status")
        freshness = source.get("freshness")
        stale = kind in STALE_KINDS or status in STALE_STATUSES or freshness == "stale"
        if not stale:
            continue
        misclassified_as_current = status in CURRENT_STATUSES or kind == "approved_current_standard"
        if misclassified_as_current:
            errors.append(
                f"stale or historical source {stable_id!r} is misclassified as current authority"
            )
        elif status not in {"STALE", "SUPERSEDED_OR_HISTORICAL"}:
            errors.append(f"stale or historical source {stable_id!r} must be marked unverified")
    return errors


def validate_receipt(receipt: Mapping[str, Any]) -> list[str]:
    """Return all schema and semantic errors; empty means the receipt is valid."""
    errors = _schema_errors(receipt)
    if not errors and receipt.get("version") == PREFLIGHT_VERSION:
        errors.extend(semantic_source_errors(receipt))
    return sorted(set(errors))


def validate_file(path: str | Path) -> list[str]:
    return validate_receipt(load_receipt(path))


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args:
        print("usage: python scripts/preflight_validate.py <receipt.json> [...]", file=sys.stderr)
        return 2
    failed = False
    for path in args:
        try:
            errors = validate_file(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"{path}: error loading receipt: {exc}", file=sys.stderr)
            failed = True
            continue
        if errors:
            failed = True
            print(f"{path}: INVALID", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
        else:
            print(f"{path}: valid")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())