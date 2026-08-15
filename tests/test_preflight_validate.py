from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from preflight_validate import (  # noqa: E402
    semantic_source_errors,
    validate_file,
    validate_receipt,
)

EXAMPLES = ROOT / "contracts" / "engineering" / "examples"


def test_three_scope_differentiated_examples_all_pass():
    for name in ("trivial-edit.json", "new-api.json", "durable-cross-service-write.json"):
        assert validate_file(EXAMPLES / name) == [], name


def test_malformed_receipt_is_rejected():
    malformed = {
        "version": "preflight-v1",
        "task": {},
        "risk_facets": [],
        "kernel": {},
        "sources": [],
        "unresolved_assumptions": [],
    }
    errors = validate_receipt(malformed)
    assert errors
    assert any("task" in error or "required" in error.lower() for error in errors)


def test_unknown_version_is_rejected():
    assert validate_receipt({"version": "not-a-receipt"}) != []


def test_stale_source_misclassified_as_current_authority_is_rejected():
    receipt = {
        "version": "preflight-v1",
        "task": {
            "outcome": "x",
            "behavior_owner": "x",
            "state_classification": "x",
            "public_contract_impact": "x",
            "semantic_success": "x",
            "mechanical_success_and_failure": "x",
            "evidence_and_tests": [],
            "recovery_and_rollback": "x",
        },
        "risk_facets": [],
        "kernel": {},
        "sources": [
            {
                "stable_id": "fossil:stale-doc",
                "status": "CURRENT_AUTHORITY",
                "provenance": "corpus-history",
                "kind": "stale_or_unverified",
                "freshness": "stale",
            }
        ],
        "unresolved_assumptions": [],
        "required_closeout_evidence": [],
    }
    assert semantic_source_errors(receipt)
    assert validate_receipt(receipt)


def test_historical_source_kept_as_lineage_is_marked_unverified_not_current():
    receipt = {
        "version": "preflight-v1",
        "task": {
            "outcome": "x",
            "behavior_owner": "x",
            "state_classification": "x",
            "public_contract_impact": "x",
            "semantic_success": "x",
            "mechanical_success_and_failure": "x",
            "evidence_and_tests": [],
            "recovery_and_rollback": "x",
        },
        "risk_facets": [],
        "kernel": {},
        "sources": [
            {
                "stable_id": "fossil:old-doc",
                "status": "SUPERSEDED_OR_HISTORICAL",
                "provenance": "corpus-history",
                "kind": "historical",
            }
        ],
        "unresolved_assumptions": [],
        "required_closeout_evidence": [],
    }
    assert semantic_source_errors(receipt) == []
    assert validate_receipt(receipt) == []


def test_closeout_example_passes_and_closeout_without_evidence_fails():
    assert validate_file(EXAMPLES / "trivial-edit-closeout.json") == []
    bad = json.loads((EXAMPLES / "trivial-edit-closeout.json").read_text(encoding="utf-8"))
    bad["evidence"] = []
    assert validate_receipt(bad) != []