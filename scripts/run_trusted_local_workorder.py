"""Entry point for the trusted default-branch local-worker workflow.

This intentionally supports only the secretless worker.  The privileged verifier
is a separately installed local command that injects its reviewed credential
loader after exact-SHA authorization; it is never called by this workflow.
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
    sanitize_receipt,
    read_github_claim_ledger,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--work-order", help="JSON WorkOrder supplied by trusted workflow_dispatch")
    source.add_argument("--work-order-env", help="environment variable holding the JSON WorkOrder")
    parser.add_argument("--check-profile", choices=["pytest"], default="pytest")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--worktree-root", default=".trusted-local-worktrees")
    parser.add_argument("--agent", required=True, help="expected winning #94 claim owner")
    parser.add_argument("--trusted-dispatch-ref", required=True, help="immutable reviewed SHA of this dispatcher")
    args = parser.parse_args()
    work_order_json = args.work_order if args.work_order is not None else os.environ.get(args.work_order_env, "")
    try:
        work_order = json.loads(work_order_json)
    except json.JSONDecodeError:
        print(json.dumps({"version": "trusted-local-receipt-v1", "terminal_status": "BLOCKED", "detail": "MALFORMED: WorkOrder is not valid JSON"}, sort_keys=True))
        return 1
    ledger = read_github_claim_ledger("Pukujan/fossil-core", token=os.environ.get("GITHUB_TOKEN"))
    policy = DispatchPolicy(
        repo_allowlist=frozenset({"Pukujan/fossil-core"}),
        task_allowlist=frozenset({"INFRA-03"}),
        local_agent=args.agent,
        trusted_dispatch_refs=frozenset({args.trusted_dispatch_ref}),
    )
    try:
        receipt = dispatch_secretless_attempt(
            work_order,
            ledger=ledger,
            policy=policy,
            repo_root=Path(args.repo_root).resolve(),
            base_dir=Path(args.worktree_root).resolve(),
            command=["python", "-m", "pytest", "-q"] if args.check_profile == "pytest" else [],
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
