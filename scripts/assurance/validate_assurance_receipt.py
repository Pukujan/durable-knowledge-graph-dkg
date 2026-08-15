"""Issue #88 CLI runner for the reusable assurance gate.

Reads a receipt JSON and prints deterministic errors. Exit 0 when valid, 1 when
the gate rejects. Intended to be called from the reusable workflows.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from assurance_gate import validate_assurance_receipt, validate_correlation_spine


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an assurance-v1 receipt.")
    parser.add_argument("receipt", help="Path to the assurance-v1 receipt JSON.")
    args = parser.parse_args(argv)

    path = Path(args.receipt)
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"unreadable or malformed receipt: {exc}", file=sys.stderr)
        return 1
    if not isinstance(receipt, dict):
        print("receipt must be a JSON object", file=sys.stderr)
        return 1

    errors = validate_assurance_receipt(receipt)
    errors.extend(validate_correlation_spine(receipt.get("correlation", {})))
    if errors:
        print("assurance gate rejected:", file=sys.stderr)
        for error in sorted(set(errors)):
            print(f"- {error}", file=sys.stderr)
        return 1
    print("assurance gate accepted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())