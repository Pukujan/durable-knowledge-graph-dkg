from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fossil_core.trusted_local_broker import (
    MODEL_BY_ROLE,
    build_codex_command,
    build_codex_prompt,
    choose_unclaimed_task,
    codex_worker_environment,
    _git_in_worktree,
    make_work_order,
    parse_broker_ledger,
    parse_ready_local_tasks,
)
from fossil_core.trusted_local_runner import DispatchLedger, LedgerClaim


NOW = datetime(2026, 8, 12, 17, 0, tzinfo=UTC)
SHA = "a" * 40


def task_comment(*, login: str = "Pukujan", task: str = "CORTEX-05", role: str = "terra", sha: str = SHA):
    return {
        "id": 1,
        "user": {"login": login},
        "body": (
            f"TASK task={task}\n"
            "state=READY\n"
            "repo=Pukujan/cortex-v4\n"
            "access=CLOUD_SECRETLESS\n"
            f"starting_ref={sha}\n"
            f"local_role={role}\n"
            "purpose=bounded local code task"
        ),
    }


def test_ready_task_requires_trusted_author_exact_sha_and_explicit_role():
    parsed = parse_ready_local_tasks([task_comment()])
    assert len(parsed) == 1
    assert parsed[0].task_id == "CORTEX-05"
    assert parsed[0].role == "terra"
    assert parse_ready_local_tasks([task_comment(login="attacker")]) == []
    assert parse_ready_local_tasks([task_comment(sha="main")]) == []
    missing_role = task_comment()
    missing_role["body"] = missing_role["body"].replace("local_role=terra\n", "")
    assert parse_ready_local_tasks([missing_role]) == []


def test_broker_only_selects_unclaimed_task():
    tasks = parse_ready_local_tasks(
        [task_comment(task="CORTEX-05"), task_comment(task="CORTEX-06", role="luna")]
    )
    ledger = DispatchLedger(
        claims={
            "CORTEX-05": LedgerClaim("CORTEX-05", "other", NOW + timedelta(minutes=20))
        }
    )
    assert choose_unclaimed_task(tasks, ledger).task_id == "CORTEX-06"


def test_live_broker_ledger_tracks_generation_terminal_cancel_and_ignores_untrusted():
    comments = [
        {"user": {"login": "attacker"}, "body": "WORKORDER task=CORTEX-05 attempt_id=evil generation=99"},
        {"user": {"login": "Pukujan"}, "body": "WORKORDER task=CORTEX-05 attempt_id=a1 generation=2"},
        {"user": {"login": "Pukujan"}, "body": "WORKORDER_DONE task=CORTEX-05 attempt_id=a1 generation=2 status=PASS"},
        {"user": {"login": "Pukujan"}, "body": "WORKORDER_CANCEL task=CORTEX-05 attempt_id=a2 generation=3"},
    ]
    parsed = parse_broker_ledger(comments, now=NOW)
    assert parsed.latest_generation == {"CORTEX-05": 3}
    assert parsed.terminal_attempt_ids == frozenset({"a1"})
    assert parsed.cancelled_attempt_ids == frozenset({"a2"})


def test_workorder_generation_increments_from_live_ledger():
    task = parse_ready_local_tasks([task_comment()])[0]
    ledger = DispatchLedger(claims={}, latest_generation={"CORTEX-05": 7})
    order = make_work_order(task, ledger=ledger, now=NOW)
    assert order["generation"] == 8
    assert order["starting_ref"] == SHA
    assert order["role"] == "terra"


def test_codex_command_is_fresh_ephemeral_workspace_write_and_role_mapped():
    terra = build_codex_command("terra")
    luna = build_codex_command("luna")
    assert terra[:2] == ["codex", "exec"]
    assert "--ephemeral" in terra
    assert terra[terra.index("--sandbox") + 1] == "workspace-write"
    assert "--json" in terra
    assert "--ignore-user-config" in terra
    assert MODEL_BY_ROLE["terra"] in terra
    assert MODEL_BY_ROLE["luna"] in luna
    assert terra[-1] == "-"
    outer = build_codex_command("luna", sandbox="danger-full-access")
    assert outer[outer.index("--sandbox") + 1] == "danger-full-access"


def test_parent_git_command_trusts_only_the_exact_disposable_worktree(tmp_path):
    worktree = tmp_path / "worktree"
    assert _git_in_worktree(worktree, "status", "--porcelain") == [
        "git",
        "-c",
        f"safe.directory={worktree}",
        "-C",
        str(worktree),
        "status",
        "--porcelain",
    ]


def test_codex_worker_environment_drops_infra_secrets_and_interactive_home(tmp_path):
    worker_home = tmp_path / "worker"
    codex_home = worker_home / ".codex"
    environment = codex_worker_environment(
        worker_home=worker_home,
        codex_home=codex_home,
        source={
            "PATH": "fixture",
            "HOME": "/real/home",
            "GITHUB_TOKEN": "ghp_should_not_escape",
            "RAILWAY_API_KEY": "secret",
            "OPENAI_API_KEY": "secret",
            "TEMP": "tmp",
        },
    )
    assert environment["PATH"] == "fixture"
    assert environment["TEMP"] == "tmp"
    assert environment["HOME"] == str(worker_home)
    assert environment["USERPROFILE"] == str(worker_home)
    assert environment["CODEX_HOME"] == str(codex_home)
    assert "GITHUB_TOKEN" not in environment
    assert "RAILWAY_API_KEY" not in environment
    assert "OPENAI_API_KEY" not in environment


def test_codex_prompt_denies_secret_and_external_state_access():
    task = parse_ready_local_tasks([task_comment()])[0]
    order = make_work_order(task, ledger=DispatchLedger(claims={}), now=NOW)
    prompt = build_codex_prompt(task, order)
    assert "Do not access or search for local credentials" in prompt
    assert "Do not deploy" in prompt
    assert "Do not commit" in prompt
    assert task.spec in prompt
