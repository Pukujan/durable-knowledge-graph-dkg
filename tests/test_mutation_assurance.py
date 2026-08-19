from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_mutation_assurance.py"
spec = importlib.util.spec_from_file_location("check_mutation_assurance", SCRIPT)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
evaluate = module.evaluate


def stats(**overrides: int | bool) -> dict[str, int | bool]:
    baseline: dict[str, int | bool] = {
        "killed": 8,
        "survived": 2,
        "total": 10,
        "no_tests": 0,
        "skipped": 0,
        "suspicious": 0,
        "timeout": 0,
        "check_was_interrupted_by_user": False,
        "segfault": 0,
    }
    baseline.update(overrides)
    return baseline


def test_mutation_score_matches_upstream_killed_plus_timeout_semantics() -> None:
    receipt, failures = evaluate(
        stats(killed=7, timeout=1, survived=2),
        scope="lifecycle-pack",
        minimum_score=80.0,
    )

    assert failures == []
    assert receipt["score_percent"] == 80.0
    assert receipt["killed_equivalent"] == 8
    assert receipt["tested_mutants"] == 10
    assert receipt["passed"] is True


def test_mutation_thresholds_fail_loudly_without_hiding_raw_counts() -> None:
    receipt, failures = evaluate(
        stats(killed=6, survived=3, no_tests=1),
        scope="lifecycle-pack",
        minimum_score=70.0,
        maximum_survivors=2,
        maximum_no_tests=0,
    )

    assert len(failures) == 3
    assert receipt["score_percent"] == 60.0
    assert receipt["counts"]["survived"] == 3
    assert receipt["counts"]["no_tests"] == 1
    assert receipt["passed"] is False


def test_mutation_infrastructure_anomalies_are_gate_failures() -> None:
    receipt, failures = evaluate(
        stats(suspicious=1, segfault=1, check_was_interrupted_by_user=True),
        scope="lifecycle-pack",
        minimum_score=0.0,
    )

    assert len(failures) == 3
    assert receipt["passed"] is False
