from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_post_gate2_retrieval_bakeoff.py"
SPEC = importlib.util.spec_from_file_location("workstream_d_bakeoff", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _answer_report(*, correct: float = 1.0, citation: float = 1.0, unsupported: float = 0.0):
    return {
        "metrics": {
            "final_answer_correctness_rate": correct,
            "citation_correctness_rate": citation,
            "mean_unsupported_claim_rate": unsupported,
        }
    }


def _audit(*, pack_safe: bool = True, leakage: int = 0):
    return {
        "pack_isolation_preserved": pack_safe,
        "current_query_top1_superseded_leakage_count": leakage,
    }


def test_route_eligibility_keeps_candidate_failures_as_disqualification_evidence():
    result = MODULE._route_eligibility(
        route_name="challenger",
        route_spec={"role": "real-reranker-candidate"},
        answer_report=_answer_report(correct=5 / 6),
        audit=_audit(),
    )

    assert result["end_to_end_guardrails_pass"] is False
    assert result["eligible_for_promotion"] is False
    assert result["disqualifying_reasons"] == ["final_answer_correctness_below_1.0"]


def test_route_eligibility_records_retrieval_leakage_without_hiding_end_to_end_safety():
    result = MODULE._route_eligibility(
        route_name="challenger",
        route_spec={"role": "hybrid-candidate"},
        answer_report=_answer_report(),
        audit=_audit(leakage=1),
    )

    assert result["end_to_end_guardrails_pass"] is True
    assert result["retrieval_leakage_free"] is False
    assert result["eligible_for_promotion"] is False
    assert result["disqualifying_reasons"] == ["current_query_top1_superseded_leakage"]


def test_route_eligibility_requires_pack_isolation_for_end_to_end_guardrails():
    result = MODULE._route_eligibility(
        route_name="challenger",
        route_spec={"role": "hybrid-candidate"},
        answer_report=_answer_report(),
        audit=_audit(pack_safe=False),
    )

    assert result["end_to_end_guardrails_pass"] is False
    assert result["eligible_for_promotion"] is False
    assert result["disqualifying_reasons"] == ["pack_isolation_violation"]


def test_route_eligibility_accepts_only_fully_clean_candidate():
    result = MODULE._route_eligibility(
        route_name="challenger",
        route_spec={"role": "hybrid-candidate"},
        answer_report=_answer_report(),
        audit=_audit(),
    )

    assert result["end_to_end_guardrails_pass"] is True
    assert result["retrieval_leakage_free"] is True
    assert result["eligible_for_promotion"] is True
    assert result["disqualifying_reasons"] == []
