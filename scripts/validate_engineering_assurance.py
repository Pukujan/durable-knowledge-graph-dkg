"""Run deterministic engineering-assurance checks without network or secrets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dkg.engineering_assurance import load_control_plane_contract, validate_control_plane_contract
from dkg.engineering_preflight import validate_closeout, validate_preflight


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    example = json.loads(
        (ROOT / "contracts" / "engineering" / "examples" / "trivial-edit.json").read_text(encoding="utf-8")
    )
    closeout = json.loads(
        (ROOT / "contracts" / "engineering" / "examples" / "trivial-edit-closeout.json").read_text(
            encoding="utf-8"
        )
    )
    errors = validate_preflight(example)
    errors.extend(validate_closeout(closeout))
    errors.extend(validate_control_plane_contract(load_control_plane_contract(ROOT)))
    if errors:
        print("engineering assurance validation failed:", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    print("engineering assurance validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
