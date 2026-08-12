"""Explicit local WorkOrder harness for deterministic secretless checks.

The autonomous path is `run_trusted_local_broker.py`. This command remains a
small manual/debug harness and is not triggered by GitHub Actions.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dkg.trusted_local_runner import (
    DispatchPolicy,
    WorkOrderError,
    dispatch_secretless_attempt,
    read_github_claim_ledger,
    sanitize_receipt,
)

ALLOWED_REPOS = frozenset(
    {
        "Pukujan/fossil-core",
        "Pukujan/cortex-v4",
        "Pukujan/litellm-ckff-ops",
    }
)


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--work-order", help="JSON WorkOrder")
    source.add_argument("--work-order-env", help="environment variable holding the JSON WorkOrder")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--worktree-root", default=".trusted-local-worktrees")
    parser.add_argument("--agent", required=True, help="expected winning #94 claim owner")
    args = parser.parse_args()

    raw = args.work_order if args.work_order is not None else os.environ.get(args.work_order_env, "")
    try:
        work_order = json.loads(raw)
    except json.JSONDecodeError:
        print(json.dumps({"version": "trusted-local-receipt-v1", "terminal_status": "BLOCKED", "detail": "MALFORMED: WorkOrder is not valid JSON"}, sort_keys=True))
        return 1

    task_id = str(work_order.get("task_id", ""))
    repo = str(work_order.get("repo", ""))
    ledger = read_github_claim_ledger("Pukujan/fossil-core", token=os.environ.get("GITHUB_TOKEN"))
    policy = DispatchPolicy(
        repo_allowlist=ALLOWED_REPOS,
        task_allowlist=frozenset({task_id}) if task_id else frozenset(),
        local_agent=args.agent,
        allowed_roles=frozenset({"terra", "luna"}),
    )
    try:
        if repo not in ALLOWED_REPOS:
            raise WorkOrderError("UNAUTHORIZED_REPOSITORY", "repo is outside explicit local allowlist")
        receipt = dispatch_secretless_attempt(
            work_order,
            ledger=ledger,
            policy=policy,
            repo_root=Path(args.repo_root).resolve(),
            base_dir=Path(args.worktree_root).resolve(),
            command=["python", "-m", "pytest", "-q"],
        )
    except WorkOrderError as exc:
        receipt = sanitize_receipt(
            {
                "version": "trusted-local-receipt-v1",
                "terminal_status": "BLOCKED",
                "work_order_id": work_order.get("work_order_id", "unreadable"),
                "attempt_id": work_order.get("attempt_id", "unreadable"),
                "generation": work_order.get("generation", "unreadable"),
                "detail": f"{exc.code}: {exc}",
            }
        )
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["terminal_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
