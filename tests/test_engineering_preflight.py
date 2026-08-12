from __future__ import annotations

from dkg.engineering_preflight import (
    build_context_packet,
    preflight_from_packet,
    resolve_live_github_state,
    selected_risk_packs,
    validate_build_context_packet,
    validate_closeout,
    validate_preflight,
)


def task():
    return {
        "outcome": "Add a bounded context packet.",
        "behavior_owner": "FOSSIL engineering preflight",
        "state_classification": "versioned source contract",
        "public_contract_impact": "new opt-in contract",
        "semantic_success": "stale material cannot silently select current authority",
        "mechanical_success_and_failure": "validator passes or blocks dispatch",
        "evidence_and_tests": ["unit tests"],
        "recovery_and_rollback": "revert the isolated commit",
    }


def current_source(stable_id="fossil:issue:84"):
    return {"stable_id": stable_id, "status": "CURRENT_AUTHORITY", "provenance": "fixture", "material": True}


def github_source():
    return {"stable_id": "github:Pukujan/fossil-core:issue:84", "status": "CURRENT_AUTHORITY", "provenance": "live-github-read", "material": True}


def test_trivial_task_selects_no_distributed_systems_pack():
    assert selected_risk_packs([]) == []


def test_packet_keeps_history_but_allows_bounded_work_when_current_authority_is_known():
    packet = build_context_packet(
        task=task(),
        fossil_material=[current_source(), {"stable_id": "fossil:old", "status": "SUPERSEDED_OR_HISTORICAL", "provenance": "fixture"}],
        github_state=[github_source()],
        required_closeout_evidence=["targeted tests"],
    )
    assert packet["dispatch_status"] == "READY_FOR_BOUNDED_WORKORDER"
    assert packet["superseded_or_historical"][0]["stable_id"] == "fossil:old"
    assert validate_build_context_packet(packet) == []
    assert validate_preflight(preflight_from_packet(packet)) == []


def test_material_unresolved_state_fails_closed():
    packet = build_context_packet(
        task=task(),
        fossil_material=[current_source(), {"stable_id": "fossil:conflict", "status": "CURRENT_STATE_UNRESOLVED", "provenance": "fixture", "material": True}],
        github_state=[github_source()],
    )
    assert packet["current_state_unresolved"] is True
    assert packet["dispatch_status"] == "BLOCKED"
    assert validate_build_context_packet(packet) == []


def test_live_github_read_is_injectable_and_secretless():
    paths = []

    def fetch(path):
        paths.append(path)
        return {"html_url": "https://example.invalid/84", "updated_at": "2026-08-12T00:00:00Z", "state": "open"}

    state = resolve_live_github_state("Pukujan/fossil-core", [{"kind": "issue", "number": 84}], fetch_json=fetch)
    assert paths == ["repos/Pukujan/fossil-core/issues/84"]
    assert state[0]["status"] == "CURRENT_AUTHORITY"
    assert state[0]["provenance"] == "live-github-read"


def test_branch_names_are_url_encoded_and_generators_are_not_lost():
    paths = []

    def fetch(path):
        paths.append(path)
        return {"commit": {"sha": "abc"}, "state": "active"}

    state = resolve_live_github_state("Pukujan/fossil-core", [{"kind": "branch", "name": "agent/context packet"}], fetch_json=fetch)
    packet = build_context_packet(task=task(), fossil_material=(item for item in [current_source()]), github_state=(item for item in state))
    assert paths == ["repos/Pukujan/fossil-core/branches/agent%2Fcontext%20packet"]
    assert packet["current_implementation_state"][0]["head_sha"] == "abc"


def test_live_github_failure_is_packet_blocking_evidence():
    def unavailable(_):
        raise TimeoutError("fixture timeout")

    state = resolve_live_github_state("Pukujan/fossil-core", [{"kind": "pull", "number": 90}], fetch_json=unavailable)
    packet = build_context_packet(task=task(), fossil_material=[current_source()], github_state=state)
    assert packet["dispatch_status"] == "BLOCKED"
    assert packet["contradictions"][0]["error_class"] == "TimeoutError"


def test_closeout_requires_mechanical_evidence_and_terminal_status():
    assert validate_closeout({"version": "closeout-v1", "outcome": "done", "changed_files": [], "tests": [], "terminal_status": "PASS", "evidence": [{"kind": "test"}]}) == []
    assert validate_closeout({"version": "closeout-v1", "outcome": "done", "changed_files": [], "tests": [], "terminal_status": "PASS", "evidence": []})
