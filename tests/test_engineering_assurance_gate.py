from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
ASSURANCE_DIR = ROOT / "scripts" / "assurance"


def _load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, ASSURANCE_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ag = _load_module("assurance_gate")


def valid_receipt() -> dict:
    return {
        "version": "assurance-v1",
        "task": {"outcome": "x", "behavior_owner": "b", "state_classification": "c"},
        "risk_facets": ["not_applicable"],
        "not_applicable_rationale": "no risk surface touched",
        "semantic_success": "validates offline",
        "sources": [{"stable_id": "fossil:issue:88", "status": "CURRENT_AUTHORITY", "provenance": "caller"}],
        "correlation": {
            "project_issue_id": "#88", "work_order_id": "w", "task_id": "t",
            "attempt_id": "a", "request_id": "r", "trace_id": "tr",
            "checkpoint_id": "c", "commit_sha": "s", "deployment_id": "d",
        },
    }


def test_valid_receipt_passes():
    assert ag.validate_assurance_receipt(valid_receipt()) == []


def test_empty_risk_facets_requires_rationale():
    receipt = valid_receipt()
    receipt["risk_facets"] = []
    receipt["not_applicable_rationale"] = ""
    assert "risk_facets is empty but not_applicable_rationale is missing" in ag.validate_assurance_receipt(receipt)


def test_not_applicable_facet_requires_rationale():
    receipt = valid_receipt()
    receipt["not_applicable_rationale"] = ""
    errors = ag.validate_assurance_receipt(receipt)
    assert any("rationale" in e for e in errors)


def test_stale_source_cannot_be_current_authority():
    receipt = valid_receipt()
    receipt["sources"] = [
        {"stable_id": "fossil:old", "status": "SUPERSEDED_OR_HISTORICAL", "provenance": "lineage", "role": "current_authority"}
    ]
    assert any("current authority" in e for e in ag.validate_assurance_receipt(receipt))


def test_semantic_success_required():
    receipt = valid_receipt()
    receipt["semantic_success"] = ""
    assert "semantic_success criteria are required" in ag.validate_assurance_receipt(receipt)


def test_correlation_spine_preserved_and_complete():
    assert ag.validate_correlation_spine(valid_receipt()["correlation"]) == []


def test_correlation_spine_missing_field_rejected():
    correlation = valid_receipt()["correlation"].copy()
    correlation.pop("trace_id")
    errors = ag.validate_correlation_spine(correlation)
    assert "trace_id" in errors[0]


def test_2xx_empty_body_fails_semantic_acceptance():
    assert ag.semantic_acceptance(status_code=200, body=b"") == ["2xx response has an empty body"]


def test_2xx_malformed_json_fails_semantic_acceptance():
    assert ag.semantic_acceptance(status_code=200, body=b"{") == ["2xx response has malformed JSON"]


def test_2xx_empty_object_fails_semantic_acceptance():
    assert ag.semantic_acceptance(status_code=200, body=b"{}") == ["2xx response has no usable JSON object"]


def test_2xx_usable_json_passes():
    assert ag.semantic_acceptance(status_code=200, body=b'{"id":"x"}') == []


def test_secret_scan_flags_bearer_and_key_values():
    assert ag.scan_for_secrets("Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456") == ["possible bearer-token"]


def test_secret_scan_clean_text_returns_empty():
    assert ag.scan_for_secrets("no secrets here, just code") == []


def test_receipt_cli_accepts_valid_fixture():
    runner = _load_module("validate_assurance_receipt")
    assert runner.main([str(ROOT / "contracts" / "engineering" / "examples" / "assurance-receipt.json")]) == 0


def test_receipt_cli_rejects_missing_rationale(tmp_path):
    runner = _load_module("validate_assurance_receipt")
    bad = tmp_path / "bad.json"
    receipt = valid_receipt()
    receipt["not_applicable_rationale"] = ""
    bad.write_text(__import__("json").dumps(receipt), encoding="utf-8")
    assert runner.main([str(bad)]) == 1