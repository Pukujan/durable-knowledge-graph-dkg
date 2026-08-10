from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from dkg.temporal_benchmark import TemporalPhase, run_temporal_evolution_benchmark


def _git_head(root: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _load_plan(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("temporal benchmark plan must be a JSON object")
    if value.get("schema_version") != "fossil.temporal-benchmark-plan.v1":
        raise ValueError("unsupported temporal benchmark plan schema")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the post-Gate-2 evolving-corpus benchmark")
    parser.add_argument("--common-root", type=Path, required=True)
    parser.add_argument("--ai-root", type=Path, required=True)
    parser.add_argument(
        "--plan",
        type=Path,
        default=Path("benchmarks/post-gate2/evolving-corpus-temporal-v1.json"),
    )
    parser.add_argument("--schemas-root", type=Path, default=Path("schemas"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    plan = _load_plan(args.plan)
    expected_pins = dict(plan["pack_pins"])
    observed_pins = {
        "fossil-common": _git_head(args.common_root),
        "fossil-ai-systems": _git_head(args.ai_root),
    }
    if observed_pins != expected_pins:
        raise SystemExit(
            "pack pin mismatch: "
            + json.dumps({"expected": expected_pins, "observed": observed_pins}, sort_keys=True)
        )

    phases = [TemporalPhase.from_mapping(item) for item in plan["phases"]]
    report = run_temporal_evolution_benchmark(
        [args.common_root, args.ai_root],
        schemas_root=args.schemas_root,
        phases=phases,
        benchmark_id=str(plan["benchmark_id"]),
    )
    report["pack_pins"] = observed_pins
    report["plan_schema_version"] = plan["schema_version"]

    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
