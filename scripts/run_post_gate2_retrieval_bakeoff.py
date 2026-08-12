from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path
from typing import Any

from dkg.answer_eval import (
    AnswerReliabilityCase,
    DeterministicEvidenceAnswerService,
    evaluate_answer_candidate,
)
from dkg.answer_pipeline import LineageResolvedModelService
from dkg.benchmark import RetrievalBenchmark
from dkg.benchmark_cases import load_benchmark_case_set, retrieval_cases_from_case_set
from dkg.context_security import UntrustedContextModelService
from dkg.execution_receipt import execute_query_with_receipt
from dkg.pack_corpus import retrieval_documents_from_pack_fixtures
from dkg.real_retrieval import (
    DEFAULT_BGE_MODEL,
    DEFAULT_BGE_REVISION,
    DEFAULT_CROSS_ENCODER_MODEL,
    DEFAULT_CROSS_ENCODER_REVISION,
    LifecycleIntentReranker,
    ReciprocalRankFusionRetriever,
    RerankedRetriever,
    SentenceTransformerCrossEncoderReranker,
    SentenceTransformerEmbeddingProvider,
)
from dkg.semantic_retriever import SemanticEmbeddingRetriever
from dkg.services import BM25Retriever

try:
    import resource
except ModuleNotFoundError:  # Windows has no POSIX resource module.
    resource = None

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN = ROOT / "benchmarks" / "post-gate2" / "retrieval-bakeoff-v1.json"
CASE_SCHEMA = ROOT / "schemas" / "benchmark-case-set" / "v1.schema.json"

CURRENT_QUERY_TOP1_LEAKAGE = {
    "current_architecture_after_reconsideration": {"clm_643b698b7e9e6aee6a16c48c"},
    "graphiti_current_role": {"clm_bdf2ed41fb11e6b1808d3df4"},
}


def _git_head(root: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        text=True,
    ).strip()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _projection_build_id(pack_mounts: dict[str, str]) -> str:
    payload = json.dumps(pack_mounts, sort_keys=True, separators=(",", ":"))
    return "packfix_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _answer_metrics(observations: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(observations)
    abstention = [item for item in observations if item["expected_outcome"] != "answer"]
    return {
        "final_answer_correctness_rate": sum(bool(item["case_correct"]) for item in observations)
        / count,
        "outcome_accuracy": sum(bool(item["outcome_match"]) for item in observations) / count,
        "citation_correctness_rate": sum(
            bool(item["citation_correct"]) for item in observations
        )
        / count,
        "mean_unsupported_claim_rate": sum(
            float(item["unsupported_claim_rate"]) for item in observations
        )
        / count,
        "completeness_rate": sum(float(item["completeness"]) == 1.0 for item in observations)
        / count,
        "appropriate_abstention_rate": (
            sum(bool(item["appropriate_abstention"]) for item in abstention) / len(abstention)
            if abstention
            else None
        ),
        "overabstention_rate": sum(bool(item["overabstention"]) for item in observations)
        / count,
        "high_confidence_error_rate": sum(
            float(item["confidence"]) >= 0.8 and not bool(item["case_correct"])
            for item in observations
        )
        / count,
    }


def _model_service(documents: list[dict[str, Any]]):
    return UntrustedContextModelService(
        LineageResolvedModelService(
            DeterministicEvidenceAnswerService(),
            documents=documents,
        ),
        documents=documents,
    )


def _build_routes(documents: list[dict[str, Any]], plan: dict[str, Any]) -> dict[str, Any]:
    models = dict(plan["models"])
    incumbent = dict(models["incumbent_embedding"])
    cross_encoder_config = dict(models["cross_encoder"])
    if incumbent != {"model": DEFAULT_BGE_MODEL, "revision": DEFAULT_BGE_REVISION}:
        raise ValueError("plan incumbent embedding pin does not match committed D021 constants")
    if cross_encoder_config["model"] != DEFAULT_CROSS_ENCODER_MODEL or cross_encoder_config[
        "revision"
    ] != DEFAULT_CROSS_ENCODER_REVISION:
        raise ValueError("plan cross-encoder pin does not match committed reranker constants")

    multiplier = int(plan["candidate_multiplier"])
    embedder = SentenceTransformerEmbeddingProvider(
        model_name=incumbent["model"],
        revision=incumbent["revision"],
        device="cpu",
    )
    dense = SemanticEmbeddingRetriever(
        documents,
        embedder,
        version="workstream-d-d021-bge-v1",
    )
    lexical = BM25Retriever(documents, version="workstream-d-bm25-v1")
    hybrid = ReciprocalRankFusionRetriever(
        [lexical, dense],
        rrf_k=int(plan["rrf_k"]),
        candidate_multiplier=multiplier,
        version="workstream-d-bge-bm25-rrf-v1",
    )
    lifecycle = RerankedRetriever(
        hybrid,
        LifecycleIntentReranker(version="workstream-d-lifecycle-v1"),
        candidate_multiplier=multiplier,
        version="workstream-d-bge-bm25-rrf-lifecycle-v1",
    )
    cross_encoder = SentenceTransformerCrossEncoderReranker(
        model_name=cross_encoder_config["model"],
        revision=cross_encoder_config["revision"],
        device="cpu",
        batch_size=int(cross_encoder_config.get("batch_size", 16)),
        max_length=(
            int(cross_encoder_config["max_length"])
            if cross_encoder_config.get("max_length") is not None
            else None
        ),
        implementation_version="workstream-d-v1",
    )
    dense_cross_encoder = RerankedRetriever(
        dense,
        cross_encoder,
        candidate_multiplier=multiplier,
        version="workstream-d-bge-dense-crossencoder-v1",
    )
    hybrid_cross_encoder = RerankedRetriever(
        hybrid,
        cross_encoder,
        candidate_multiplier=multiplier,
        version="workstream-d-bge-bm25-rrf-crossencoder-v1",
    )
    return {
        "bm25": lexical,
        "bge-dense": dense,
        "bge-bm25-rrf": hybrid,
        "bge-bm25-rrf-lifecycle": lifecycle,
        "bge-dense-crossencoder": dense_cross_encoder,
        "bge-bm25-rrf-crossencoder": hybrid_cross_encoder,
    }


def _route_specs(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["name"]): dict(item) for item in plan["routes"]}


def _audit_route(retriever: Any, retrieval_cases: list[Any], *, limit: int) -> dict[str, Any]:
    pack_violations: list[dict[str, Any]] = []
    top1_leakage: list[dict[str, Any]] = []
    for case in retrieval_cases:
        results = retriever.search(case.query, pack_ids=list(case.pack_ids), limit=limit)
        allowed = set(case.pack_ids)
        foreign = [
            str(item["id"])
            for item in results
            if str(item.get("pack_id", "")) not in allowed
        ]
        if foreign:
            pack_violations.append({"case_id": case.case_id, "foreign_ids": foreign})
        forbidden_top1 = CURRENT_QUERY_TOP1_LEAKAGE.get(case.case_id, set())
        if results and str(results[0]["id"]) in forbidden_top1:
            top1_leakage.append(
                {
                    "case_id": case.case_id,
                    "top1_id": str(results[0]["id"]),
                    "forbidden_ids": sorted(forbidden_top1),
                }
            )
    return {
        "pack_isolation_preserved": not pack_violations,
        "pack_isolation_violations": pack_violations,
        "current_query_top1_superseded_leakage_count": len(top1_leakage),
        "current_query_top1_superseded_leakage": top1_leakage,
    }


def _route_eligibility(
    *,
    route_name: str,
    route_spec: dict[str, Any],
    answer_report: dict[str, Any],
    audit: dict[str, Any],
) -> dict[str, Any]:
    """Keep candidate disqualification evidence explicit and mechanically stable.

    This is intentionally stricter than a transport/process result. A candidate
    may be useful evaluation evidence while still being ineligible to replace
    D021. Current-query leakage remains distinct from end-to-end answer safety
    so the report neither hides the leak nor falsely calls it a safe promotion.
    """
    metrics = dict(answer_report.get("metrics", {}))
    reasons: list[str] = []
    if metrics.get("final_answer_correctness_rate") != 1.0:
        reasons.append("final_answer_correctness_below_1.0")
    if metrics.get("citation_correctness_rate") != 1.0:
        reasons.append("citation_correctness_below_1.0")
    if metrics.get("mean_unsupported_claim_rate") != 0.0:
        reasons.append("unsupported_claim_rate_above_0.0")
    pack_safe = bool(audit.get("pack_isolation_preserved"))
    if not pack_safe:
        reasons.append("pack_isolation_violation")
    leakage_free = int(audit.get("current_query_top1_superseded_leakage_count", 0)) == 0
    if not leakage_free:
        reasons.append("current_query_top1_superseded_leakage")
    end_to_end_guardrails_pass = all(
        reason not in {"final_answer_correctness_below_1.0", "citation_correctness_below_1.0", "unsupported_claim_rate_above_0.0", "pack_isolation_violation"}
        for reason in reasons
    )
    return {
        "route_name": route_name,
        "route_role": str(route_spec.get("role", "unknown")),
        "end_to_end_guardrails_pass": end_to_end_guardrails_pass,
        "pack_isolation_preserved": pack_safe,
        "retrieval_leakage_free": leakage_free,
        "eligible_for_promotion": end_to_end_guardrails_pass and leakage_free,
        "disqualifying_reasons": reasons,
    }


def _answer_receipts(
    *,
    route_name: str,
    route_spec: dict[str, Any],
    retriever: Any,
    answer_cases: list[AnswerReliabilityCase],
    documents: list[dict[str, Any]],
    pack_mounts: dict[str, str],
    projection: dict[str, str],
    run_ref: str,
) -> dict[str, Any]:
    observations: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    service = _model_service(documents)
    for case in answer_cases:
        response, receipt = execute_query_with_receipt(
            query=case.query,
            pack_mounts=pack_mounts,
            query_pack_ids=list(case.pack_ids),
            projection=projection,
            policy={
                "route_id": str(route_spec["route_id"]),
                "retrieval_policy_id": "D021-evaluation-boundary",
                "mode": "workstream-d-bakeoff",
            },
            retriever=retriever,
            model_service=service,
            limit=case.limit,
            trace_ref=f"trace://workstream-d/{route_name}/{case.case_id}",
            run_ref=run_ref,
            query_id=case.case_id,
            requested_model={
                "provider": "fossil",
                "model_id": None,
                "implementation": "deterministic-evidence-answerer",
            },
        )
        evaluation = evaluate_answer_candidate(
            response["output"],
            case=case,
            documents=documents,
        )
        observations.append(
            {
                **evaluation,
                "case_id": case.case_id,
                "receipt_id": receipt["receipt_id"],
                "execution_identity_sha256": receipt["execution_identity_sha256"],
                "result_sha256": receipt["result_sha256"],
            }
        )
        receipts.append(receipt)
    return {
        "metrics": _answer_metrics(observations),
        "observations": observations,
        "receipts": receipts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Issue #48 Workstream D matched incumbent/hybrid/reranker bakeoff."
    )
    parser.add_argument("--common-root", type=Path, required=True)
    parser.add_argument("--ai-root", type=Path, required=True)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--run-ref", default="post-gate2-retrieval-bakeoff")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    plan = _load_json(args.plan)
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

    stable_ids = dict(plan["stable_pack_ids"])
    pack_mounts = {
        str(stable_ids["fossil-common"]): observed_repo_pins["fossil-common"],
        str(stable_ids["fossil-ai-systems"]): observed_repo_pins["fossil-ai-systems"],
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

    retrieval_case_path = ROOT / str(plan["retrieval_case_set"])
    retrieval_case_set = load_benchmark_case_set(retrieval_case_path, CASE_SCHEMA)
    retrieval_cases = retrieval_cases_from_case_set(retrieval_case_set)
    answer_plan = _load_json(ROOT / str(plan["answer_case_set"]))
    answer_cases = [AnswerReliabilityCase.from_mapping(item) for item in answer_plan["cases"]]
    routes = _build_routes(documents, plan)
    specs = _route_specs(plan)
    if set(routes) != set(specs):
        raise ValueError("implemented routes do not match the versioned Workstream D plan")

    retrieval_benchmark = RetrievalBenchmark(limit=int(plan["retrieval_limit"]))
    route_reports: dict[str, Any] = {}
    for route_name in [str(item["name"]) for item in plan["routes"]]:
        retriever = routes[route_name]
        retrieval_report = retrieval_benchmark.run(retriever, retrieval_cases)
        audit = _audit_route(
            retriever,
            retrieval_cases,
            limit=int(plan["retrieval_limit"]),
        )
        answer_report = _answer_receipts(
            route_name=route_name,
            route_spec=specs[route_name],
            retriever=retriever,
            answer_cases=answer_cases,
            documents=documents,
            pack_mounts=pack_mounts,
            projection=projection,
            run_ref=args.run_ref,
        )
        eligibility = _route_eligibility(
            route_name=route_name,
            route_spec=specs[route_name],
            answer_report=answer_report,
            audit=audit,
        )
        route_reports[route_name] = {
            "role": str(specs[route_name]["role"]),
            "retrieval": retrieval_report,
            "safety_audit": audit,
            "answer_reliability": answer_report,
            "promotion_eligibility": eligibility,
        }

    max_rss_kib = (
        int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        if resource is not None
        else None
    )
    all_pack_safe = all(
        bool(report["safety_audit"]["pack_isolation_preserved"])
        for report in route_reports.values()
    )
    all_answers_safe = all(
        bool(report["promotion_eligibility"]["end_to_end_guardrails_pass"])
        for report in route_reports.values()
    )
    report = {
        "schema_version": "fossil.retrieval-bakeoff-proof.v1",
        "benchmark_id": str(plan["benchmark_id"]),
        "authority": (
            "candidate retrieval/reranker scores and Workstream-F receipts are evaluation "
            "evidence only; D021 durable lifecycle/lineage/citation authority is unchanged"
        ),
        "repo_pack_pins": observed_repo_pins,
        "pack_mounts": pack_mounts,
        "projection": projection,
        "corpus_document_count": len(documents),
        "retrieval_case_count": len(retrieval_cases),
        "answer_case_count": len(answer_cases),
        "route_count": len(route_reports),
        "receipt_count": len(route_reports) * len(answer_cases),
        "environment": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "process_max_rss_kib": max_rss_kib,
        },
        "routes": route_reports,
        "stage_gate": {
            "pack_isolation_preserved_all_routes": all_pack_safe,
            "answer_citation_unsupported_guardrails_all_routes": all_answers_safe,
            "d021_replacement_decision": "not_authorized_by_first_stage",
            "embedding_scale_progression": "pending_after_baseline_reranker_evidence",
        },
        "passed": all_pack_safe and all_answers_safe,
    }

    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
