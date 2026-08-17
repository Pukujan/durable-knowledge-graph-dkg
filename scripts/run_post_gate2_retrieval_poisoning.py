from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from fossil_core.answer_eval import DeterministicEvidenceAnswerService
from fossil_core.answer_pipeline import LineageResolvedModelService
from fossil_core.application.query.security import UntrustedContextModelService
from fossil_core.application.query.poisoning_eval import (
    RetrievalPoisoningCase,
    run_retrieval_poisoning_benchmark,
)
from fossil_core.application.rebuild import retrieval_documents_from_pack_fixtures

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN = ROOT / "benchmarks" / "post-gate2" / "retrieval-poisoning-v1.json"


def _git_head(root: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        text=True,
    ).strip()


def _load_plan(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("retrieval poisoning plan must be a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the post-Gate-2 retrieval poisoning / untrusted-context benchmark."
    )
    parser.add_argument("--common-root", type=Path, required=True)
    parser.add_argument("--ai-root", type=Path, required=True)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    plan = _load_plan(args.plan)
    expected_pins = {str(key): str(value) for key, value in plan["pack_pins"].items()}
    observed_pins = {
        "fossil-common": _git_head(args.common_root),
        "fossil-ai-systems": _git_head(args.ai_root),
    }
    if observed_pins != expected_pins:
        raise SystemExit(
            "pack pin mismatch: "
            + json.dumps({"expected": expected_pins, "observed": observed_pins}, sort_keys=True)
        )

    documents = retrieval_documents_from_pack_fixtures(
        [args.common_root, args.ai_root],
        schemas_root=ROOT / "schemas",
    )
    cases = [RetrievalPoisoningCase.from_mapping(item) for item in plan["cases"]]
    service = UntrustedContextModelService(
        LineageResolvedModelService(
            DeterministicEvidenceAnswerService(),
            documents=documents,
        ),
        documents=documents,
    )
    report = run_retrieval_poisoning_benchmark(
        service,
        documents=documents,
        cases=cases,
        benchmark_id=str(plan["benchmark_id"]),
    )
    report["plan_schema_version"] = str(plan["schema_version"])
    report["pack_pins"] = observed_pins
    report["corpus_document_count"] = len(documents)
    report["baseline"] = (
        "BM25+lifecycle retrieval -> untrusted-context authority resolution -> durable "
        "relation-endpoint resolution -> deterministic durable-evidence answerer -> "
        "candidate-only output containment"
    )
    report["residual_risk_boundary"] = (
        "This suite proves bounded structural defenses for the committed attacks; it does "
        "not establish universal prompt-injection or retrieval-poisoning resistance."
    )

    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
