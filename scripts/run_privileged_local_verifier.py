"""Outbound, model-free privileged verifier service for exact reviewed SHAs."""
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

_SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))

from dkg.privileged_local_verifier import (active_ready_privileged_tasks, make_privileged_work_order, parse_actions, run_verified_action)
from dkg.trusted_local_broker import GitHubQueueClient, claim_text, terminal_text
from dkg.trusted_local_runner import DispatchPolicy, WorkOrderError, sanitize_receipt


def load_token() -> str:
    token = os.environ.get("FOSSIL_BROKER_GITHUB_TOKEN", "").strip()
    if token:
        return token
    completed = subprocess.run(["gh", "auth", "token"], check=False, capture_output=True, text=True)
    if completed.returncode != 0 or not completed.stdout.strip():
        raise WorkOrderError("GITHUB_AUTH_REQUIRED", "authenticate GitHub CLI for the verifier coordinator")
    return completed.stdout.strip()


def load_config(path: Path) -> tuple[str, dict[str, Path], frozenset[str], dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise WorkOrderError("MALFORMED_CONFIG", "verifier config must be a JSON object")
    agent = str(raw.get("agent", "")).strip()
    repos_raw = raw.get("repos")
    refs = raw.get("trusted_dispatch_refs")
    if not agent or not isinstance(repos_raw, Mapping) or not isinstance(refs, list):
        raise WorkOrderError("MALFORMED_CONFIG", "agent, repos, and trusted_dispatch_refs are required")
    repos = {str(repo): Path(str(value)).expanduser().resolve() for repo, value in repos_raw.items()}
    trusted = frozenset(str(ref) for ref in refs)
    if not repos or not trusted:
        raise WorkOrderError("MALFORMED_CONFIG", "repos and trusted_dispatch_refs cannot be empty")
    return agent, repos, trusted, parse_actions(raw)


def closeout(client: GitHubQueueClient, *, task: Any, order: Mapping[str, Any], receipt: Mapping[str, Any], agent: str) -> None:
    client.comment(terminal_text(order, receipt))
    status = str(receipt["terminal_status"])
    if status == "PASS":
        client.comment(f"DONE task={task.task_id}\nagent={agent}\nresult=PRIVILEGED_VERIFIER_PASS\nrefs=reviewed_sha:{task.reviewed_sha}\ntests={receipt['detail']}")
    else:
        client.comment(f"BLOCKED task={task.task_id}\nagent={agent}\nclass=PRIVILEGED_VERIFIER_{status}\nevidence={receipt['detail']}")
    client.comment(f"RELEASE task={task.task_id} agent={agent} reason=privileged-verifier-terminal-{status.lower()}")


def run_once(*, client: GitHubQueueClient, agent: str, repos: Mapping[str, Path], trusted_refs: frozenset[str], actions: Mapping[str, Any], worktree_root: Path) -> bool:
    comments = client.comments()
    from dkg.trusted_local_broker import parse_broker_ledger
    ledger = parse_broker_ledger(comments, now=datetime.now(UTC))
    candidates = [task for task in active_ready_privileged_tasks(comments) if task.repo in repos and task.action in actions and actions[task.action].access_class == task.access]
    task = next((item for item in candidates if item.task_id not in ledger.claims), None)
    if task is None:
        return False
    client.comment(claim_text(task.queue_task(), agent=agent, now=datetime.now(UTC)))
    ledger = parse_broker_ledger(client.comments(), now=datetime.now(UTC))
    if ledger.claims.get(task.task_id) is None or ledger.claims[task.task_id].agent != agent:
        return False
    order = make_privileged_work_order(task, ledger=ledger, now=datetime.now(UTC))
    client.comment(f"WORKORDER task={order['task_id']} attempt_id={order['attempt_id']} generation={order['generation']}\nrepo={order['repo']}\nstarting_ref={order['starting_ref']}\nrole=luna access={order['access_class']}\nreviewed_sha={task.reviewed_sha}\ntrusted_dispatch_ref={task.trusted_dispatch_ref}\nverifier_action={task.action}")
    ledger = parse_broker_ledger(client.comments(), now=datetime.now(UTC))
    policy = DispatchPolicy(repo_allowlist=frozenset(repos), task_allowlist=frozenset({task.task_id}), local_agent=agent, trusted_dispatch_refs=trusted_refs, now=lambda: datetime.now(UTC))
    try:
        receipt = run_verified_action(order, ledger=ledger, policy=policy, repo_root=repos[task.repo], worktree_root=worktree_root, action=actions[task.action])
    except WorkOrderError as exc:
        receipt = sanitize_receipt({"version": "trusted-local-receipt-v1", "terminal_status": "BLOCKED", "work_order_id": order["work_order_id"], "attempt_id": order["attempt_id"], "generation": order["generation"], "starting_ref": order["starting_ref"], "detail": f"{exc.code}: privileged verifier blocked"})
    closeout(client, task=task, order=order, receipt=receipt, agent=agent)
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--worktree-root", type=Path, default=Path(".privileged-verifier-worktrees"))
    args = parser.parse_args()
    if args.poll_seconds < 15:
        raise SystemExit("--poll-seconds must be >= 15")
    agent, repos, refs, actions = load_config(args.config)
    client = GitHubQueueClient(load_token())
    while True:
        try:
            did_work = run_once(client=client, agent=agent, repos=repos, trusted_refs=refs, actions=actions, worktree_root=args.worktree_root.resolve())
        except WorkOrderError as exc:
            print(json.dumps({"terminal_status": "BLOCKED", "code": exc.code, "detail": "privileged verifier blocked"}))
            did_work = False
        if args.once:
            return 0 if did_work else 2
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
