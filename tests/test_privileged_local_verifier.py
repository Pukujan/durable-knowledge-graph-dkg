from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fossil_core.privileged_local_verifier import (
    active_ready_privileged_tasks,
    parse_actions,
    read_selected_dotenv,
    verifier_environment,
)
from fossil_core.trusted_local_runner import WorkOrderError

SHA = "a" * 40


def comment(body: str, *, login: str = "Pukujan") -> dict:
    return {"id": 1, "user": {"login": login}, "body": body}


def ready(*, task: str = "INFRA-06", sha: str = SHA) -> dict:
    return comment(
        f"TASK task={task}\nstate=READY\nrepo=Pukujan/fossil-core\naccess=LIVE_STAGING\n"
        f"starting_ref={sha}\nreviewed_sha={sha}\ntrusted_dispatch_ref={SHA}\n"
        "local_role=luna\nverifier_action=staging-smoke\npurpose=reviewed staging check"
    )


def test_privileged_task_requires_exact_reviewed_sha_action_and_trusted_author():
    tasks = active_ready_privileged_tasks([ready()])
    assert len(tasks) == 1
    assert tasks[0].action == "staging-smoke"
    assert active_ready_privileged_tasks([comment(ready()["body"], login="attacker")]) == []
    invalid = ready()
    invalid["body"] = invalid["body"].replace(f"reviewed_sha={SHA}", "reviewed_sha=" + "b" * 40)
    assert active_ready_privileged_tasks([invalid]) == []


def test_terminal_record_prevents_reexecution_until_new_ready_directive():
    assert active_ready_privileged_tasks([ready(), comment("DONE task=INFRA-06\nresult=PASS")]) == []


def test_action_config_is_local_allowlist_and_rejects_production_or_shell(tmp_path):
    raw = {"actions": {"staging-smoke": {"access_class": "LIVE_STAGING", "secret_file": str(tmp_path / "ssc.env"), "required_env": ["STAGING_TOKEN"], "command": ["python", "-m", "pytest"]}}}
    parsed = parse_actions(raw)
    assert parsed["staging-smoke"].required_env == ("STAGING_TOKEN",)
    raw["actions"]["staging-smoke"]["production"] = True
    with pytest.raises(WorkOrderError, match="unauthorized"):
        parse_actions(raw)
    raw["actions"]["staging-smoke"].pop("production")
    raw["actions"]["staging-smoke"]["command"] = ["sh", "-c", "echo unsafe"]
    with pytest.raises(WorkOrderError, match="cannot use a shell"):
        parse_actions(raw)


def test_dotenv_loader_only_returns_approved_names_and_child_env_has_no_parent_secrets(tmp_path):
    env_file = tmp_path / "ssc.env"
    env_file.write_text("ALLOWED=ok\nUNRELATED=must-not-pass\n", encoding="utf-8")
    selected = read_selected_dotenv(env_file, ["ALLOWED"])
    assert selected == {"ALLOWED": "ok"}
    env = verifier_environment(selected)
    assert env["ALLOWED"] == "ok"
    assert "UNRELATED" not in env
    assert "GITHUB_TOKEN" not in env
    with pytest.raises(WorkOrderError, match="absent"):
        read_selected_dotenv(env_file, ["MISSING"])
