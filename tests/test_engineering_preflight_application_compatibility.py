from __future__ import annotations

import inspect

import fossil_core.application.engineering.preflight as canonical_preflight
import fossil_core.engineering_preflight as legacy_preflight


EXPECTED_IMPLICIT_NAMESPACE = {
    "Any",
    "BUILD_CONTEXT_VERSION",
    "CURRENT_STATUSES",
    "Callable",
    "Draft202012Validator",
    "Iterable",
    "KNOWN_STATUSES",
    "Mapping",
    "NONCURRENT_STATUSES",
    "PREFLIGHT_VERSION",
    "Path",
    "RISK_PACKS",
    "Request",
    "annotations",
    "build_context_packet",
    "json",
    "preflight_from_packet",
    "quote",
    "resolve_live_github_state",
    "selected_risk_packs",
    "urlopen",
    "validate_build_context_packet",
    "validate_closeout",
    "validate_preflight",
}

SEMANTIC_SYMBOLS = (
    "PREFLIGHT_VERSION",
    "BUILD_CONTEXT_VERSION",
    "CURRENT_STATUSES",
    "NONCURRENT_STATUSES",
    "KNOWN_STATUSES",
    "RISK_PACKS",
    "selected_risk_packs",
    "validate_preflight",
    "validate_closeout",
    "resolve_live_github_state",
    "build_context_packet",
    "preflight_from_packet",
    "validate_build_context_packet",
)


def _task() -> dict:
    return {
        "outcome": "bounded work",
        "behavior_owner": "test",
        "state_classification": "test",
        "public_contract_impact": "none",
        "semantic_success": "bounded",
        "mechanical_success_and_failure": "tests",
        "evidence_and_tests": ["tests"],
        "recovery_and_rollback": "revert",
    }


def test_engineering_preflight_legacy_namespace_and_identity_are_frozen():
    assert not hasattr(legacy_preflight, "__all__")
    assert {
        name for name in vars(legacy_preflight) if not name.startswith("_")
    } == EXPECTED_IMPLICIT_NAMESPACE

    for name in SEMANTIC_SYMBOLS:
        assert getattr(legacy_preflight, name) is getattr(canonical_preflight, name)
    assert legacy_preflight._contract_schema is canonical_preflight._contract_schema
    assert legacy_preflight._default_fetch_json is canonical_preflight._default_fetch_json


def test_engineering_preflight_call_shapes_are_unchanged():
    selected = list(
        inspect.signature(canonical_preflight.selected_risk_packs).parameters.values()
    )
    assert [parameter.name for parameter in selected] == ["risk_facets"]

    live = list(
        inspect.signature(canonical_preflight.resolve_live_github_state).parameters.values()
    )
    assert [parameter.name for parameter in live] == ["repository", "refs", "fetch_json"]
    assert live[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert live[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert live[2].kind is inspect.Parameter.KEYWORD_ONLY
    assert live[2].default is None

    packet = list(
        inspect.signature(canonical_preflight.build_context_packet).parameters.values()
    )
    assert [parameter.name for parameter in packet] == [
        "task",
        "fossil_material",
        "github_state",
        "risk_facets",
        "unresolved_assumptions",
        "required_closeout_evidence",
    ]
    assert all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in packet)


def test_engineering_preflight_fail_closed_behavior_matches_legacy_path():
    current = {
        "stable_id": "fossil:current",
        "status": "CURRENT_AUTHORITY",
        "provenance": "fixture",
        "material": True,
    }
    unresolved = {
        "stable_id": "github:unresolved",
        "status": "CURRENT_STATE_UNRESOLVED",
        "provenance": "fixture",
        "material": True,
    }

    canonical = canonical_preflight.build_context_packet(
        task=_task(),
        fossil_material=[current],
        github_state=[unresolved],
        risk_facets=["external-dependency", "external-dependency"],
        required_closeout_evidence=["targeted tests"],
    )
    legacy = legacy_preflight.build_context_packet(
        task=_task(),
        fossil_material=[current],
        github_state=[unresolved],
        risk_facets=["external-dependency", "external-dependency"],
        required_closeout_evidence=["targeted tests"],
    )

    assert legacy == canonical
    assert canonical["dispatch_status"] == "BLOCKED"
    assert canonical["current_state_unresolved"] is True
    assert canonical["selected_risk_packs"] == ["dependency-provider", "timeout-retry"]
    assert canonical_preflight.validate_build_context_packet(canonical) == []


def test_engineering_preflight_live_failure_and_contract_resolution_are_preserved():
    def unavailable(_path):
        raise TimeoutError("fixture timeout")

    canonical = canonical_preflight.resolve_live_github_state(
        "Pukujan/fossil-core",
        [{"kind": "pull", "number": 171}],
        fetch_json=unavailable,
    )
    legacy = legacy_preflight.resolve_live_github_state(
        "Pukujan/fossil-core",
        [{"kind": "pull", "number": 171}],
        fetch_json=unavailable,
    )
    assert legacy == canonical
    assert canonical[0]["status"] == "CURRENT_STATE_UNRESOLVED"
    assert canonical[0]["error_class"] == "TimeoutError"

    valid_closeout = {
        "version": "closeout-v1",
        "outcome": "done",
        "changed_files": [],
        "tests": [],
        "terminal_status": "PASS",
        "evidence": [{"kind": "test"}],
    }
    assert canonical_preflight.validate_closeout(valid_closeout) == []
    assert legacy_preflight.validate_closeout(valid_closeout) == []
