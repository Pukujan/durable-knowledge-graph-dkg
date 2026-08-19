from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_COUNTS = (
    "killed",
    "survived",
    "total",
    "no_tests",
    "skipped",
    "suspicious",
    "timeout",
    "segfault",
)


def evaluate(
    stats: dict[str, Any],
    *,
    scope: str,
    minimum_score: float,
    maximum_survivors: int | None = None,
    maximum_no_tests: int | None = None,
) -> tuple[dict[str, Any], list[str]]:
    counts = {name: int(stats[name]) for name in REQUIRED_COUNTS}
    interrupted = bool(stats.get("check_was_interrupted_by_user", False))
    tested = counts["total"] - counts["skipped"]
    killed_equivalent = counts["killed"] + counts["timeout"]
    score = 0.0 if tested <= 0 else (killed_equivalent / tested) * 100.0

    failures: list[str] = []
    if counts["total"] <= 0:
        failures.append("mutation run produced no mutants")
    if interrupted:
        failures.append("mutation run was interrupted")
    if counts["segfault"]:
        failures.append(f"mutation run had {counts['segfault']} segfault mutant(s)")
    if counts["suspicious"]:
        failures.append(f"mutation run had {counts['suspicious']} suspicious mutant(s)")
    if score + 1e-9 < minimum_score:
        failures.append(
            f"mutation score {score:.2f}% is below minimum {minimum_score:.2f}%"
        )
    if maximum_survivors is not None and counts["survived"] > maximum_survivors:
        failures.append(
            f"survived mutants {counts['survived']} exceed maximum {maximum_survivors}"
        )
    if maximum_no_tests is not None and counts["no_tests"] > maximum_no_tests:
        failures.append(
            f"mutants with no associated tests {counts['no_tests']} exceed maximum {maximum_no_tests}"
        )

    receipt = {
        "schema_version": "fossil.mutation-assurance.v1",
        "scope": scope,
        "score_percent": round(score, 2),
        "minimum_score_percent": minimum_score,
        "maximum_survivors": maximum_survivors,
        "maximum_no_tests": maximum_no_tests,
        "tested_mutants": tested,
        "killed_equivalent": killed_equivalent,
        "counts": counts,
        "interrupted": interrupted,
        "passed": not failures,
        "failures": failures,
    }
    return receipt, failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stats", type=Path)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--minimum-score", type=float, required=True)
    parser.add_argument("--maximum-survivors", type=int)
    parser.add_argument("--maximum-no-tests", type=int)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    stats = json.loads(args.stats.read_text(encoding="utf-8"))
    missing = [name for name in REQUIRED_COUNTS if name not in stats]
    if missing:
        raise SystemExit(f"mutation stats missing fields: {', '.join(missing)}")

    receipt, failures = evaluate(
        stats,
        scope=args.scope,
        minimum_score=args.minimum_score,
        maximum_survivors=args.maximum_survivors,
        maximum_no_tests=args.maximum_no_tests,
    )
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
