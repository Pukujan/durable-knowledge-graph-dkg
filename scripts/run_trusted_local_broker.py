"""Outbound trusted-local broker service.

Run this under a dedicated local account/profile. It polls #94, claims only
explicitly local-auto secretless tasks, launches fresh Codex processes, runs
independent checks, publishes a draft PR, and posts sanitized closeout evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

# Keep the documented direct invocation usable from a clean source checkout.
_SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))

from dkg.trusted_local_broker import (
    GitHubQueueClient,
    QueueTask,
    RepoPolicy,
    choose_unclaimed_task,
    claim_text,
    make_work_order,
    parse_broker_ledger,
    run_local_codex_task,
    terminal_text,
    workorder_text,
)
from dkg.trusted_local_queue import active_ready_local_tasks
from dkg.trusted_local_runner import WorkOrderError, sanitize_receipt


def load_token() -> str:
    token = os.environ.get("FOSSIL_BROKER_GITHUB_TOKEN", "").strip()
    if token:
        return token
    completed = subprocess.run(
        ["gh", "auth", "token"], check=False, capture_output=True, text=True
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        raise WorkOrderError(
            "GITHUB_AUTH_REQUIRED",
            "set FOSSIL_BROKER_GITHUB_TOKEN or authenticate GitHub CLI for the broker account",
        )
    return completed.stdout.strip()


def load_config(path: Path) -> tuple[str, Path, Path, dict[str, RepoPolicy], str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise WorkOrderError("MALFORMED_CONFIG", "broker config must be a JSON object")
    agent = str(raw.get("agent", "")).strip()
    worker_home = Path(str(raw.get("worker_home", ""))).expanduser().resolve()
    codex_home = Path(str(raw.get("codex_home", ""))).expanduser().resolve()
    codex_executable = str(raw.get("codex_executable", "codex")).strip() or "codex"
    repos_raw = raw.get("repos")
    if not agent or not isinstance(repos_raw, Mapping):
        raise WorkOrderError("MALFORMED_CONFIG", "agent and repos mapping are required")

    repos: dict[str, RepoPolicy] = {}
    for repo, value in repos_raw.items():
        if isinstance(value, str):
            repos[str(repo)] = RepoPolicy(str(repo), Path(value).expanduser().resolve())
            continue
        if not isinstance(value, Mapping):
            raise WorkOrderError("MALFORMED_CONFIG", f"repo config for {repo} must be path or object")
        check = value.get("check_command", ["python", "-m", "pytest", "-q"])
        if not isinstance(check, list) or not check or not all(isinstance(item, str) and item for item in check):
            raise WorkOrderError("MALFORMED_CONFIG", f"check_command for {repo} must be a non-empty string list")
        repos[str(repo)] = RepoPolicy(
            str(repo),
            Path(str(value.get("path", ""))).expanduser().resolve(),
            tuple(check),
        )
    return agent, worker_home, codex_home, repos, codex_executable


def closeout(
    client: GitHubQueueClient,
    *,
    task: QueueTask,
    work_order: Mapping[str, Any] | None,
    receipt: Mapping[str, Any],
    agent: str,
    pr_url: str | None = None,
) -> None:
    if work_order is not None:
        client.comment(terminal_text(work_order, receipt, pr_url=pr_url))
    status = str(receipt.get("terminal_status", "BLOCKED"))
    detail = str(receipt.get("detail", "")).replace("\n", " ")[:1200]
    if status == "PASS":
        client.comment(
            f"DONE task={task.task_id}\nagent={agent}\nresult=LOCAL_CODEX_PASS\n"
            f"refs={pr_url or 'no-pr'}\ntests=parent-broker independent checks PASS; detail={detail}"
        )
    else:
        client.comment(
            f"BLOCKED task={task.task_id}\nagent={agent}\nclass=LOCAL_CODEX_{status}\n"
            f"evidence={detail}"
        )
    client.comment(
        f"RELEASE task={task.task_id} agent={agent} reason=local-broker-terminal-{status.lower()}"
    )


def run_once(
    *,
    client: GitHubQueueClient,
    agent: str,
    worker_home: Path,
    codex_home: Path,
    repos: Mapping[str, RepoPolicy],
    codex_executable: str,
    worktree_root: Path,
) -> bool:
    comments = client.comments()
    now = datetime.now(UTC)
    ledger = parse_broker_ledger(comments, now=now)
    candidates = [
        task
        for task in active_ready_local_tasks(comments)
        if task.repo in repos and task.access == "CLOUD_SECRETLESS"
    ]
    task = choose_unclaimed_task(candidates, ledger)
    if task is None:
        return False

    client.comment(claim_text(task, agent=agent, now=now))
    comments = client.comments()
    ledger = parse_broker_ledger(comments, now=datetime.now(UTC))
    winning = ledger.claims.get(task.task_id)
    if winning is None or winning.agent != agent:
        return False

    work_order = make_work_order(task, ledger=ledger, now=datetime.now(UTC))
    client.comment(workorder_text(work_order))
    comments = client.comments()
    ledger = parse_broker_ledger(comments, now=datetime.now(UTC))

    try:
        receipt, pr_url = run_local_codex_task(
            task,
            work_order,
            ledger=ledger,
            agent=agent,
            repo_policy=repos[task.repo],
            worktree_root=worktree_root,
            worker_home=worker_home,
            codex_home=codex_home,
            github=client,
            codex_executable=codex_executable,
        )
    except WorkOrderError as exc:
        receipt = sanitize_receipt(
            {
                "version": "trusted-local-receipt-v1",
                "terminal_status": "BLOCKED",
                "work_order_id": work_order["work_order_id"],
                "attempt_id": work_order["attempt_id"],
                "generation": work_order["generation"],
                "starting_ref": work_order["starting_ref"],
                "detail": f"{exc.code}: {exc}",
            }
        )
        pr_url = None
    closeout(
        client,
        task=task,
        work_order=work_order,
        receipt=receipt,
        agent=agent,
        pr_url=pr_url,
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--worktree-root", type=Path, default=Path(".trusted-local-worktrees"))
    args = parser.parse_args()
    if args.poll_seconds < 15:
        raise SystemExit("--poll-seconds must be >= 15")

    agent, worker_home, codex_home, repos, codex_executable = load_config(args.config)
    client = GitHubQueueClient(load_token())
    worktree_root = args.worktree_root.expanduser().resolve()

    while True:
        try:
            did_work = run_once(
                client=client,
                agent=agent,
                worker_home=worker_home,
                codex_home=codex_home,
                repos=repos,
                codex_executable=codex_executable,
                worktree_root=worktree_root,
            )
        except WorkOrderError as exc:
            print(json.dumps({"terminal_status": "BLOCKED", "code": exc.code, "detail": str(exc)}))
            did_work = False
        if args.once:
            return 0 if did_work else 2
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
