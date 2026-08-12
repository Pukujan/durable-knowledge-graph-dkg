from __future__ import annotations

from dkg.trusted_local_queue import active_ready_local_tasks


SHA = "a" * 40


def comment(body: str, *, login: str = "Pukujan") -> dict:
    return {"user": {"login": login}, "body": body}


def ready(task: str = "CORTEX-05", *, role: str = "terra", sha: str = SHA) -> dict:
    return comment(
        f"TASK task={task}\n"
        "state=READY\n"
        "repo=Pukujan/cortex-v4\n"
        "access=CLOUD_SECRETLESS\n"
        f"starting_ref={sha}\n"
        f"local_role={role}\n"
        "purpose=bounded local task"
    )


def test_done_task_does_not_resurrect_after_release():
    comments = [
        ready(),
        comment("CLAIM task=CORTEX-05\nagent=broker\nlease_until=2026-08-12T20:00:00Z"),
        comment("DONE task=CORTEX-05\nagent=broker\nresult=LOCAL_CODEX_PASS"),
        comment("RELEASE task=CORTEX-05 agent=broker reason=done"),
    ]
    assert active_ready_local_tasks(comments) == []


def test_blocked_task_stays_inactive_until_explicit_new_ready_directive():
    comments = [ready(), comment("BLOCKED task=CORTEX-05\nagent=broker\nclass=LOCAL_CODEX_FAILED")]
    assert active_ready_local_tasks(comments) == []
    comments.append(ready(sha="b" * 40, role="luna"))
    active = active_ready_local_tasks(comments)
    assert len(active) == 1
    assert active[0].starting_ref == "b" * 40
    assert active[0].role == "luna"


def test_later_non_machine_ready_task_directive_revokes_old_local_authority():
    comments = [
        ready(),
        comment(
            "TASK task=CORTEX-05\n"
            "state=READY\n"
            "repo=Pukujan/cortex-v4\n"
            "access=CLOUD_SECRETLESS\n"
            "starting_ref=main\n"
            "purpose=human-only task now"
        ),
    ]
    assert active_ready_local_tasks(comments) == []


def test_untrusted_terminal_comment_cannot_cancel_trusted_ready_task():
    comments = [ready(), comment("DONE task=CORTEX-05 result=fake", login="attacker")]
    active = active_ready_local_tasks(comments)
    assert [task.task_id for task in active] == ["CORTEX-05"]


def test_trusted_task_cancel_deactivates_ready_task():
    comments = [ready(), comment("CANCEL task=CORTEX-05 reason=owner-cancel")]
    assert active_ready_local_tasks(comments) == []


def test_trusted_task_cancel_only_deactivates_named_task():
    comments = [
        ready("CORTEX-05"),
        ready("CORTEX-06", role="luna"),
        comment("CANCEL task=CORTEX-05 reason=owner-cancel"),
    ]
    assert [task.task_id for task in active_ready_local_tasks(comments)] == ["CORTEX-06"]


def test_new_ready_explicitly_reactivates_cancelled_task():
    comments = [
        ready(),
        comment("CANCEL task=CORTEX-05 reason=owner-cancel"),
        ready(sha="b" * 40, role="luna"),
    ]
    active = active_ready_local_tasks(comments)
    assert [task.task_id for task in active] == ["CORTEX-05"]
    assert active[0].starting_ref == "b" * 40


def test_untrusted_task_cancel_cannot_deactivate_trusted_ready_task():
    comments = [ready(), comment("CANCEL task=CORTEX-05 reason=fake", login="attacker")]
    assert [task.task_id for task in active_ready_local_tasks(comments)] == ["CORTEX-05"]


def test_latest_trusted_ready_order_drives_fifo_selection_order():
    comments = [ready("CORTEX-05"), ready("CORTEX-06", role="luna"), ready("CORTEX-05", sha="c" * 40)]
    active = active_ready_local_tasks(comments)
    assert [task.task_id for task in active] == ["CORTEX-06", "CORTEX-05"]
    assert active[-1].starting_ref == "c" * 40
