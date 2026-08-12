from __future__ import annotations

import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dkg.trusted_local_runner import (
    DispatchLedger,
    DispatchPolicy,
    LedgerClaim,
    WorkOrderError,
    authorize_work_order,
    dispatch_secretless_attempt,
    lane_for,
    parse_claim_ledger,
    run_attempt,
    sanitize_receipt,
    secretless_environment,
    validate_work_order,
)


NOW = datetime(2026, 8, 12, 17, 0, tzinfo=UTC)
SHA = "a" * 40


def order(**changes: object) -> dict:
    result = {
        "version": "trusted-local-workorder-v1",
        "project_issue_id": 96,
        "work_order_id": "workorder-infra-03",
        "task_id": "INFRA-03",
        "attempt_id": "attempt-infra-03",
        "generation": 2,
        "repo": "Pukujan/fossil-core",
        "starting_ref": SHA,
        "role": "luna",
        "access_class": "CLOUD_SECRETLESS",
        "mutation_scope": ["tests"],
        "selected_checks": ["pytest"],
        "deadline": "2026-08-12T18:00:00Z",
        "closeout_contract": "trusted-local-receipt-v1",
    }
    result.update(changes)
    return result


def policy(**changes: object) -> DispatchPolicy:
    result = {
        "repo_allowlist": frozenset({"Pukujan/fossil-core"}),
        "task_allowlist": frozenset({"INFRA-03"}),
        "local_agent": "codex-trusted-local-runner-20260812",
        "trusted_dispatch_refs": frozenset({SHA}),
        "now": lambda: NOW,
    }
    result.update(changes)
    return DispatchPolicy(**result)


def ledger(**changes: object) -> DispatchLedger:
    result = {
        "claims": {
            "INFRA-03": LedgerClaim(
                "INFRA-03", "codex-trusted-local-runner-20260812", NOW + timedelta(minutes=10)
            )
        },
        "latest_generation": {"INFRA-03": 2},
    }
    result.update(changes)
    return DispatchLedger(**result)


def rejected(work_order: dict, *, expected: str, current_ledger: DispatchLedger | None = None) -> None:
    with pytest.raises(WorkOrderError) as raised:
        authorize_work_order(work_order, ledger=current_ledger or ledger(), policy=policy())
    assert raised.value.code == expected


def test_valid_secretless_luna_workorder_authorizes_and_schema_is_offline_valid():
    assert validate_work_order(order()) == []
    assert authorize_work_order(order(), ledger=ledger(), policy=policy()) == "secretless"
    assert lane_for(order()) == "secretless"


@pytest.mark.parametrize(
    ("work_order", "expected"),
    [
        (order(starting_ref="main"), "MALFORMED"),
        (order(repo="evil/repo"), "UNAUTHORIZED_REPOSITORY"),
        (order(task_id="OTHER-01"), "UNAUTHORIZED_TASK"),
        (order(role="terra"), "BLOCKED_POLICY"),
        (order(deadline="2026-08-12T16:00:00Z"), "DEADLINE_EXPIRED"),
        (order(generation=1), "STALE_GENERATION"),
    ],
)
def test_malformed_or_unauthorized_or_stale_workorders_fail_closed(work_order, expected):
    rejected(work_order, expected=expected)


def test_duplicate_cancelled_and_missing_claims_do_not_launch():
    rejected(
        order(), expected="DUPLICATE_ATTEMPT",
        current_ledger=ledger(terminal_attempt_ids=frozenset({"attempt-infra-03"})),
    )
    rejected(
        order(), expected="CANCELLED",
        current_ledger=ledger(cancelled_attempt_ids=frozenset({"attempt-infra-03"})),
    )
    rejected(order(), expected="CLAIM_INVALID", current_ledger=ledger(claims={}))


def test_privileged_lane_requires_exact_reviewed_sha_and_trusted_dispatcher():
    privileged = order(access_class="LIVE_STAGING")
    rejected(privileged, expected="EXACT_SHA_REQUIRED")
    privileged.update(reviewed_sha=SHA, trusted_dispatch_ref="b" * 40)
    rejected(privileged, expected="UNTRUSTED_DISPATCH")
    privileged["trusted_dispatch_ref"] = SHA
    assert authorize_work_order(privileged, ledger=ledger(), policy=policy()) == "privileged"


def test_ledger_uses_earliest_active_claim_and_honors_release():
    comments = [
        {"body": "CLAIM task=INFRA-03\nagent=winner\nlease_until=2026-08-12T18:00:00Z"},
        {"body": "CLAIM task=INFRA-03\nagent=later\nlease_until=2026-08-12T18:30:00Z"},
    ]
    parsed = parse_claim_ledger(comments, now=NOW)
    assert parsed.claims["INFRA-03"].agent == "winner"
    comments.append({"body": "RELEASE task=INFRA-03 agent=winner reason=done"})
    assert parse_claim_ledger(comments, now=NOW).claims["INFRA-03"].agent == "later"


def test_ledger_renewal_extends_only_the_active_claim_and_reclaim_survives_old_release():
    comments = [
        {"body": "CLAIM task=INFRA-03\nagent=winner\nlease_until=2026-08-12T16:30:00Z"},
        {"body": "RENEW task=INFRA-03 agent=winner lease_until=2026-08-12T18:00:00Z"},
        {"body": "RELEASE task=INFRA-03 agent=winner reason=done"},
        {"body": "CLAIM task=INFRA-03\nagent=winner\nlease_until=2026-08-12T18:30:00Z"},
    ]
    assert parse_claim_ledger(comments, now=NOW).claims["INFRA-03"].agent == "winner"


def test_secretless_environment_strips_token_and_credential_names():
    environment = secretless_environment(
        {"PATH": "fixture", "GITHUB_TOKEN": "ghp_should_not_escape", "RAILWAY_API_KEY": "secret", "TEMP": "tmp"}
    )
    assert environment == {"PATH": "fixture", "TEMP": "tmp"}


def test_receipt_sanitizer_redacts_credential_like_output_and_rejects_nonterminal_status():
    clean = sanitize_receipt(
        {"terminal_status": "FAILED", "detail": "GITHUB_TOKEN=ghp_abcdefghijklmnop"}
    )
    assert "ghp_" not in clean["detail"]
    with pytest.raises(WorkOrderError, match="terminal_status"):
        sanitize_receipt({"terminal_status": "agent says done"})


def test_timeout_and_killed_process_have_mechanical_failed_receipts(tmp_path):
    result = run_attempt(
        [sys.executable, "-c", "import time; time.sleep(1)"],
        worktree=tmp_path,
        work_order=order(deadline="2026-08-12T17:00:00.01Z"),
        environment={"PATH": os.environ["PATH"]},
        now=lambda: NOW,
    )
    assert result["terminal_status"] == "FAILED"
    killed = run_attempt(
        [sys.executable, "-c", "raise SystemExit(9)"],
        worktree=tmp_path,
        work_order=order(deadline="2026-08-12T18:00:00Z"),
        environment={"PATH": os.environ["PATH"]},
        now=lambda: NOW,
    )
    assert killed["terminal_status"] == "FAILED"


def test_secretless_attempt_uses_disposable_worktree_and_cleans_it(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    for command in (
        ["git", "init"],
        ["git", "config", "user.email", "runner@example.invalid"],
        ["git", "config", "user.name", "runner"],
        ["git", "commit", "--allow-empty", "-m", "fixture"],
    ):
        __import__("subprocess").run(command, cwd=repo, check=True, capture_output=True)
    sha = __import__("subprocess").check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    receipt = dispatch_secretless_attempt(
        order(starting_ref=sha),
        ledger=ledger(),
        policy=policy(),
        repo_root=repo,
        base_dir=tmp_path / "worktrees",
        command=[sys.executable, "-c", "print('ok')"],
    )
    assert receipt["terminal_status"] == "PASS"
    assert list((tmp_path / "worktrees").iterdir()) == []


def test_public_repo_has_no_self_hosted_workflow_trigger_for_local_pc():
    root = Path(__file__).resolve().parents[1]
    assert not (root / ".github" / "workflows" / "trusted-local-workorder.yml").exists()
    assert (root / "scripts" / "run_trusted_local_broker.py").exists()


def test_broker_image_supplies_bounded_secretless_cross_repo_check_runtime():
    root = Path(__file__).resolve().parents[1]
    dockerfile = (root / "docker" / "trusted-local-broker" / "Dockerfile").read_text(
        encoding="utf-8"
    )
    for requirement in ("fastapi>=0.115,<1", "httpx>=0.27,<1", "pyyaml"):
        assert requirement in dockerfile
    assert 'ENTRYPOINT ["/opt/fossil-venv/bin/python", "scripts/run_trusted_local_broker.py"]' in dockerfile


def test_independent_check_command_remains_literal_argv():
    root = Path(__file__).resolve().parents[1]
    broker = (root / "src" / "dkg" / "trusted_local_broker.py").read_text(encoding="utf-8")
    assert "list(command)" in broker
    assert "shell=True" not in broker
