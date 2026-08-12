from __future__ import annotations

from pathlib import Path

from dkg.engineering_assurance import (
    load_control_plane_contract,
    semantic_http_errors,
    validate_control_plane_contract,
)


ROOT = Path(__file__).resolve().parents[1]


def test_semantic_false_success_fixtures_are_rejected():
    assert semantic_http_errors(status_code=200, body=b"") == ["2xx response has an empty body"]
    assert semantic_http_errors(status_code=200, body=b"{") == ["2xx response has malformed JSON"]
    assert semantic_http_errors(status_code=200, body=b"{}") == ["2xx response has no usable JSON object"]
    assert semantic_http_errors(status_code=200, body=b"   ", expected="stream") == [
        "completed stream has zero usable payload"
    ]


def test_usable_json_and_non_success_have_explicit_outcomes():
    assert semantic_http_errors(status_code=200, body=b'{"id":"fixture"}') == []
    assert semantic_http_errors(status_code=503, body=b"unavailable") == ["non-success HTTP status"]


def test_shared_control_plane_contract_preserves_owner_and_correlation_boundary():
    assert validate_control_plane_contract(load_control_plane_contract(ROOT)) == []


def test_assurance_workflow_is_path_scoped_and_secretless():
    workflow = (ROOT / ".github" / "workflows" / "engineering-assurance.yml").read_text(
        encoding="utf-8"
    )
    assert "pull_request_target" not in workflow
    assert "secrets." not in workflow
    assert "contents: read" in workflow
    assert "paths:" in workflow
