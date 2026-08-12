from __future__ import annotations

from datetime import UTC, datetime

import pytest

from dkg.trusted_local_broker import QueueTask, reconcile_before_publication
from dkg.trusted_local_runner import WorkOrderError


NOW = datetime(2026, 8, 12, 17, 0, tzinfo=UTC)
SHA = "a" * 40
AGENT = "trusted-local-broker-test"
ATTEMPT = "cortex-05-attempt"


class FakeGitHub:
    def __init__(self, comments: list[dict]):
        self._comments = comments

    def comments(self):
        return list(self._comments)


def trusted(body: str) -> dict:
    return {"user": {"login": "Pukujan"}, "body": body}


def base_comments() -> list[dict]:
    return [
        trusted(
            "CLAIM task=CORTEX-05\n"
            f"agent={AGENT}\n"
            "mode=LOCAL_CODEX\n"
            "lease_until=2026-08-12T18:00:00Z\n"
            "repo=Pukujan/cortex-v4\n"
            f"starting_ref={SHA}"
        ),
        trusted(
            f"WORKORDER task=CORTEX-05 attempt_id={ATTEMPT} generation=2\n"
            "repo=Pukujan/cortex-v4\n"
            f"starting_ref={SHA}\n"
            "role=terra access=CLOUD_SECRETLESS"
        ),
    ]


def task() -> QueueTask:
    return QueueTask(
        task_id="CORTEX-05",
        repo="Pukujan/cortex-v4",
        access="CLOUD_SECRETLESS",
        starting_ref=SHA,
        role="terra",
        spec="fixture",
    )


def work_order() -> dict:
    return {
        "version": "trusted-local-workorder-v1",
        "project_issue_id": 94,
        "work_order_id": "wo-cortex-05-attempt",
        "task_id": "CORTEX-05",
        "attempt_id": ATTEMPT,
        "generation": 2,
        "repo": "Pukujan/cortex-v4",
        "starting_ref": SHA,
        "role": "terra",
        "access_class": "CLOUD_SECRETLESS",
        "mutation_scope": ["repository-worktree"],
        "selected_checks": ["pytest"],
        "deadline": "2026-08-12T18:00:00Z",
        "closeout_contract": "trusted-local-receipt-v1",
    }


def test_reconciliation_allows_unchanged_live_authority():
    ledger = reconcile_before_publication(
        task(), work_order(), agent=AGENT, github=FakeGitHub(base_comments()), now=NOW
    )
    assert ledger.latest_generation["CORTEX-05"] == 2


def test_cancellation_during_model_run_blocks_publication():
    comments = base_comments() + [
        trusted(f"WORKORDER_CANCEL task=CORTEX-05 attempt_id={ATTEMPT} generation=2 reason=owner-cancel")
    ]
    with pytest.raises(WorkOrderError) as raised:
        reconcile_before_publication(
            task(), work_order(), agent=AGENT, github=FakeGitHub(comments), now=NOW
        )
    assert raised.value.code == "CANCELLED"


def test_newer_generation_during_model_run_blocks_late_publication():
    comments = base_comments() + [
        trusted("WORKORDER task=CORTEX-05 attempt_id=new-attempt generation=3")
    ]
    with pytest.raises(WorkOrderError) as raised:
        reconcile_before_publication(
            task(), work_order(), agent=AGENT, github=FakeGitHub(comments), now=NOW
        )
    assert raised.value.code == "STALE_GENERATION"


def test_claim_release_or_loss_during_model_run_blocks_publication():
    comments = base_comments() + [
        trusted(f"RELEASE task=CORTEX-05 agent={AGENT} reason=cancelled")
    ]
    with pytest.raises(WorkOrderError) as raised:
        reconcile_before_publication(
            task(), work_order(), agent=AGENT, github=FakeGitHub(comments), now=NOW
        )
    assert raised.value.code == "CLAIM_INVALID"


def test_terminal_attempt_during_model_run_blocks_duplicate_publication():
    comments = base_comments() + [
        trusted(
            f"WORKORDER_DONE task=CORTEX-05 attempt_id={ATTEMPT} generation=2 status=BLOCKED"
        )
    ]
    with pytest.raises(WorkOrderError) as raised:
        reconcile_before_publication(
            task(), work_order(), agent=AGENT, github=FakeGitHub(comments), now=NOW
        )
    assert raised.value.code == "DUPLICATE_ATTEMPT"
