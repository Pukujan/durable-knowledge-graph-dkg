from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from fossil_core.answer_eval import (
    AnswerReliabilityCase,
    DeterministicEvidenceAnswerService,
    evaluate_answer_candidate,
)
from fossil_core.answer_pipeline import LineageResolvedModelService
from fossil_core.context_security import UntrustedContextModelService
from fossil_core.execution_receipt import (
    compare_query_execution_receipts,
    execute_query_with_receipt,
)
from fossil_core.pack_corpus import retrieval_documents_from_pack_fixtures
from fossil_core.real_retrieval import LifecycleIntentReranker, RerankedRetriever
from fossil_core.services import BM25Retriever

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN = ROOT / "benchmarks" / "post-gate2" / "answer-reliability-v1.json"
COMMON_PACK = "pack_269099f7b2ba43b7a99b9427d64092de"
AI_PACK = "pack_f024177f89a5442db84171c3dd7f58e5"


def _git_head(root: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        text=True,
    ).strip()


def _load_plan(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("answer reliability plan must be a JSON object")
    return value


def _projection_build_id(pack_mounts: dict[str, str]) -> str:
    payload = json.dumps(pack_mounts, sort_keys=True, separators=(",", ":"))
    return "packfix_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _model(documents):
    return UntrustedContextModelService(
        LineageResolvedModelService(
            DeterministicEvidenceAnswerService(),
            documents=documents,
        ),
        documents=documents,
    )


def _retriever(documents, *, version: str):
    return RerankedRetriever(
        BM25Retriever(documents),
        LifecycleIntentReranker(),
        candidate_multiplier=4,
        version=version,
    )


def _run_one(
    *,
    case: AnswerReliabilityCase,
    documents,
    pack_mounts: dict[str, str],
    projection: dict,
    route_id: str,
    retriever_version: str,
    trace_ref: str,
    run_ref: str,
):
    return execute_query_with_receipt(
        query=case.query,
        pack_mounts=pack_mounts,
        query_pack_ids=list(case.pack_ids),
        projection=projection,
        policy={
            "route_id": route_id,
            "retrieval_policy_id": "D021",
            "mode": "receipt-replay-proof",
        },
        retriever=_retriever(documents, version=retriever_version),
        model_service=_model(documents),
        limit=case.limit,
        trace_ref=trace_ref,
        run_ref=run_ref,
        query_id=case.case_id,
        requested_model={
            "provider": "fossil",
            "model_id": None,
            "implementation": "deterministic-evidence-answerer",
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the post-Gate-2 reproducible query execution receipt replay proof."
    )
    parser.add_argument("--common-root", type=Path, required=True)
    parser.add_argument("--ai-root", type=Path, required=True)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--run-ref", default="post-gate2-query-receipt-proof")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    plan = _load_plan(args.plan)
    expected_repo_pins = {
        "fossil-common": str(plan["pack_pins"]["fossil-common"]),
        "fossil-ai-systems": str(plan["pack_pins"]["fossil-ai-systems"]),
    }
    observed_repo_pins = {
        "fossil-common": _git_head(args.common_root),
        "fossil-ai-systems": _git_head(args.ai_root),
    }
    if observed_repo_pins != expected_repo_pins:
        raise SystemExit(
            "pack pin mismatch: "
            + json.dumps(
                {"expected": expected_repo_pins, "observed": observed_repo_pins},
                sort_keys=True,
            )
        )

    pack_mounts = {
        COMMON_PACK: observed_repo_pins["fossil-common"],
        AI_PACK: observed_repo_pins["fossil-ai-systems"],
    }
    projection = {
        "name": "pack-fixture-retrieval-documents",
        "version": "1",
        "build_id": _projection_build_id(pack_mounts),
    }
    documents = retrieval_documents_from_pack_fixtures(
        [args.common_root, args.ai_root],
        schemas_root=ROOT / "schemas",
    )
    cases = [AnswerReliabilityCase.from_mapping(item) for item in plan["cases"]]

    observations: list[dict] = []
    exact_matches = 0
    variant_visible = 0
    stable_semantic_results = 0
    all_answers_correct = True
    all_security_resolvers_recorded = True

    for case in cases:
        baseline_response, baseline = _run_one(
            case=case,
            documents=documents,
            pack_mounts=pack_mounts,
            projection=projection,
            route_id="d021-answer-baseline-v1",
            retriever_version="answer-reliability-baseline-v1",
            trace_ref=f"trace://query-receipt/{case.case_id}/baseline",
            run_ref=args.run_ref,
        )
        replay_response, replay = _run_one(
            case=case,
            documents=documents,
            pack_mounts=pack_mounts,
            projection=projection,
            route_id="d021-answer-baseline-v1",
            retriever_version="answer-reliability-baseline-v1",
            trace_ref=f"trace://query-receipt/{case.case_id}/exact-replay",
            run_ref=args.run_ref,
        )
        variant_response, variant = _run_one(
            case=case,
            documents=documents,
            pack_mounts=pack_mounts,
            projection=projection,
            route_id="workstream-f-service-version-probe",
            retriever_version="query-receipt-replay-probe-v2",
            trace_ref=f"trace://query-receipt/{case.case_id}/service-variant",
            run_ref=args.run_ref,
        )

        baseline_eval = evaluate_answer_candidate(
            baseline_response["output"], case=case, documents=documents
        )
        replay_eval = evaluate_answer_candidate(
            replay_response["output"], case=case, documents=documents
        )
        variant_eval = evaluate_answer_candidate(
            variant_response["output"], case=case, documents=documents
        )
        case_answers_correct = all(
            bool(item["case_correct"])
            for item in (baseline_eval, replay_eval, variant_eval)
        )
        all_answers_correct = all_answers_correct and case_answers_correct

        exact_comparison = compare_query_execution_receipts(baseline, replay)
        variant_comparison = compare_query_execution_receipts(baseline, variant)
        exact_ok = (
            exact_comparison["same_logical_query"]
            and exact_comparison["same_corpus_revision"]
            and exact_comparison["same_pack_scope"]
            and exact_comparison["execution_identity_match"]
            and exact_comparison["result_identity_match"]
            and exact_comparison["changed_dimensions"] == []
        )
        if exact_ok:
            exact_matches += 1

        variant_change_visible = (
            variant_comparison["same_logical_query"]
            and variant_comparison["same_corpus_revision"]
            and variant_comparison["same_pack_scope"]
            and not variant_comparison["execution_identity_match"]
            and {"policy", "services"}
            <= set(variant_comparison["changed_dimensions"])
        )
        if variant_change_visible:
            variant_visible += 1

        semantic_result_stable = baseline["result"] == variant["result"]
        if semantic_result_stable:
            stable_semantic_results += 1

        required_resolvers = {
            "fossil-untrusted-context-v1",
            "fossil-lineage-context-v1",
        }
        resolver_sets = [
            {item["resolver"] for item in receipt["resolvers"]}
            for receipt in (baseline, replay, variant)
        ]
        resolvers_recorded = all(required_resolvers <= values for values in resolver_sets)
        all_security_resolvers_recorded = all_security_resolvers_recorded and resolvers_recorded

        observations.append(
            {
                "case_id": case.case_id,
                "category": case.category,
                "expected_outcome": case.expected_outcome,
                "baseline_evaluation": baseline_eval,
                "replay_evaluation": replay_eval,
                "variant_evaluation": variant_eval,
                "exact_replay_comparison": exact_comparison,
                "variant_comparison": variant_comparison,
                "semantic_result_stable_across_service_version_change": semantic_result_stable,
                "required_resolvers_recorded": resolvers_recorded,
                "receipts": {
                    "baseline": baseline,
                    "exact_replay": replay,
                    "service_version_variant": variant,
                },
            }
        )

    count = len(cases)
    report = {
        "schema_version": "fossil.query-execution-replay-proof.v1",
        "benchmark_id": "post-gate2-query-execution-receipt-v1",
        "authority": "execution receipts are observability/replay evidence, not truth authority",
        "repo_pack_pins": observed_repo_pins,
        "pack_mounts": pack_mounts,
        "projection": projection,
        "corpus_document_count": len(documents),
        "case_count": count,
        "receipt_count": count * 3,
        "metrics": {
            "answer_correctness_rate": 1.0 if all_answers_correct else sum(
                all(
                    bool(item[name]["case_correct"])
                    for name in (
                        "baseline_evaluation",
                        "replay_evaluation",
                        "variant_evaluation",
                    )
                )
                for item in observations
            )
            / count,
            "exact_replay_identity_rate": exact_matches / count,
            "service_change_visibility_rate": variant_visible / count,
            "semantic_result_stability_rate": stable_semantic_results / count,
            "resolver_recording_rate": sum(
                bool(item["required_resolvers_recorded"]) for item in observations
            )
            / count,
        },
        "observations": observations,
        "passed": (
            all_answers_correct
            and exact_matches == count
            and variant_visible == count
            and stable_semantic_results == count
            and all_security_resolvers_recorded
        ),
        "residual_note": (
            "This proof demonstrates receipt/replay identity and change visibility for the "
            "committed deterministic baseline. It does not establish provider determinism, "
            "and latency/cost remain telemetry rather than replay identity."
        ),
    }

    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
