"""Outbound trusted-local broker helpers for autonomous Codex WorkOrders.

The broker is intentionally outbound-only: it polls the trusted GitHub queue from
local infrastructure. Public repository workflow code never schedules the local
machine directly, and GitHub/infra credentials are never passed to the Codex child.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

from dkg.trusted_local_runner import (
    DispatchLedger,
    DispatchPolicy,
    WorkOrderError,
    authorize_work_order,
    destroy_worktree,
    isolated_worktree,
    parse_claim_ledger,
    sanitize_receipt,
    sanitize_text,
)

TRUSTED_QUEUE_AUTHORS = frozenset({"Pukujan"})
DEFAULT_REPOS = frozenset(
    {
        "Pukujan/fossil-core",
        "Pukujan/cortex-v4",
        "Pukujan/litellm-ckff-ops",
    }
)
MODEL_BY_ROLE = {"terra": "gpt-5.6-terra", "luna": "gpt-5.6-luna"}
CODEX_SANDBOXES = frozenset({"workspace-write", "danger-full-access"})
_TASK_START = re.compile(r"^TASK\s+task=(?P<task>[^\s]+)$", re.MULTILINE)
_FIELD = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_-]*)=(?P<value>.*)$", re.MULTILINE)
_WORKORDER = re.compile(
    r"^WORKORDER\s+task=(?P<task>[^\s]+)\s+attempt_id=(?P<attempt>[^\s]+)\s+generation=(?P<generation>\d+)",
    re.MULTILINE,
)
_WORKORDER_DONE = re.compile(
    r"^WORKORDER_DONE\s+task=(?P<task>[^\s]+)\s+attempt_id=(?P<attempt>[^\s]+)\s+generation=(?P<generation>\d+)",
    re.MULTILINE,
)
_WORKORDER_CANCEL = re.compile(
    r"^WORKORDER_CANCEL\s+task=(?P<task>[^\s]+)\s+attempt_id=(?P<attempt>[^\s]+)\s+generation=(?P<generation>\d+)",
    re.MULTILINE,
)
_SHA = re.compile(r"^[0-9a-f]{40}$")
_SAFE_BRANCH = re.compile(r"[^a-z0-9._-]+")
_SECRET_ENV_NAME = re.compile(
    r"(?i)(?:token|secret|password|api[_-]?key|railway|credential|aws_|azure_|gcp_|anthropic|openai_api)"
)


@dataclass(frozen=True)
class QueueTask:
    task_id: str
    repo: str
    access: str
    starting_ref: str
    role: str
    spec: str
    comment_id: int | None = None


@dataclass(frozen=True)
class RepoPolicy:
    repo: str
    path: Path
    check_command: tuple[str, ...] = ("python", "-m", "pytest", "-q")


def _trusted_comments(
    comments: Iterable[Mapping[str, Any]],
    trusted_authors: frozenset[str] = TRUSTED_QUEUE_AUTHORS,
) -> list[Mapping[str, Any]]:
    result: list[Mapping[str, Any]] = []
    for comment in comments:
        user = comment.get("user")
        login = user.get("login") if isinstance(user, Mapping) else None
        if login in trusted_authors:
            result.append(comment)
    return result


def parse_broker_ledger(
    comments: Iterable[Mapping[str, Any]],
    *,
    now: datetime,
    trusted_authors: frozenset[str] = TRUSTED_QUEUE_AUTHORS,
) -> DispatchLedger:
    """Build claim + generation/terminal/cancel state from live trusted #94 comments."""
    trusted = _trusted_comments(comments, trusted_authors)
    ledger = parse_claim_ledger(trusted, now=now)
    latest: dict[str, int] = {}
    terminal: set[str] = set()
    cancelled: set[str] = set()
    for comment in trusted:
        body = str(comment.get("body", ""))
        for match in _WORKORDER.finditer(body):
            generation = int(match["generation"])
            latest[match["task"]] = max(latest.get(match["task"], -1), generation)
        for match in _WORKORDER_DONE.finditer(body):
            generation = int(match["generation"])
            latest[match["task"]] = max(latest.get(match["task"], -1), generation)
            terminal.add(match["attempt"])
        for match in _WORKORDER_CANCEL.finditer(body):
            generation = int(match["generation"])
            latest[match["task"]] = max(latest.get(match["task"], -1), generation)
            cancelled.add(match["attempt"])
    ledger.latest_generation = latest
    ledger.terminal_attempt_ids = frozenset(terminal)
    ledger.cancelled_attempt_ids = frozenset(cancelled)
    return ledger


def parse_ready_local_tasks(
    comments: Iterable[Mapping[str, Any]],
    *,
    trusted_authors: frozenset[str] = TRUSTED_QUEUE_AUTHORS,
) -> list[QueueTask]:
    """Parse explicit machine-ready local tasks from trusted queue authors."""
    tasks: list[QueueTask] = []
    for comment in _trusted_comments(comments, trusted_authors):
        body = str(comment.get("body", ""))
        start = _TASK_START.search(body)
        if not start:
            continue
        fields = {match["key"]: match["value"].strip() for match in _FIELD.finditer(body)}
        if fields.get("state") != "READY":
            continue
        role = fields.get("local_role")
        repo = fields.get("repo", "")
        starting_ref = fields.get("starting_ref", "")
        if role not in MODEL_BY_ROLE:
            continue
        if repo not in DEFAULT_REPOS or not _SHA.fullmatch(starting_ref):
            continue
        tasks.append(
            QueueTask(
                task_id=start["task"],
                repo=repo,
                access=fields.get("access", "CLOUD_SECRETLESS"),
                starting_ref=starting_ref,
                role=role,
                spec=body,
                comment_id=comment.get("id") if isinstance(comment.get("id"), int) else None,
            )
        )
    return tasks


def choose_unclaimed_task(tasks: Sequence[QueueTask], ledger: DispatchLedger) -> QueueTask | None:
    for task in tasks:
        if task.task_id not in ledger.claims:
            return task
    return None


def next_generation(task_id: str, ledger: DispatchLedger) -> int:
    current = ledger.latest_generation.get(task_id)
    return 0 if current is None else current + 1


def make_work_order(
    task: QueueTask,
    *,
    ledger: DispatchLedger,
    now: datetime,
    duration: timedelta = timedelta(minutes=60),
) -> dict[str, Any]:
    attempt_id = f"{task.task_id.lower()}-{uuid4().hex[:12]}"
    return {
        "version": "trusted-local-workorder-v1",
        "project_issue_id": 94,
        "work_order_id": f"wo-{attempt_id}",
        "task_id": task.task_id,
        "attempt_id": attempt_id,
        "generation": next_generation(task.task_id, ledger),
        "repo": task.repo,
        "starting_ref": task.starting_ref,
        "role": task.role,
        "access_class": task.access,
        "mutation_scope": ["repository-worktree"],
        "selected_checks": ["pytest"],
        "deadline": (now + duration).astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "closeout_contract": "trusted-local-receipt-v1",
    }


def build_codex_prompt(task: QueueTask, work_order: Mapping[str, Any]) -> str:
    return (
        f"You are the {task.role} local coding worker for {task.task_id}.\n"
        "Execute only the bounded task below in the current isolated Git worktree.\n"
        "Do not access or search for local credentials, .env files, browser/session data, "
        "GitHub auth, Railway/provider credentials, or files outside this worktree.\n"
        "Do not deploy, promote production, push, open PRs, or change external state.\n"
        "Do not commit: the parent broker owns publication after mechanical checks.\n"
        "Make the smallest in-scope code/test/doc changes and run relevant local tests.\n"
        "A zero exit from your run is not final acceptance; the parent broker runs independent checks.\n"
        f"WorkOrder: {json.dumps(dict(work_order), sort_keys=True)}\n\n"
        "Authoritative queue task:\n"
        f"{task.spec}\n"
    )


def build_codex_command(
    role: str, *, executable: str = "codex", sandbox: str = "workspace-write"
) -> list[str]:
    if role not in MODEL_BY_ROLE:
        raise WorkOrderError("BLOCKED_POLICY", f"unsupported local role: {role}")
    if sandbox not in CODEX_SANDBOXES:
        raise WorkOrderError("BLOCKED_POLICY", f"unsupported Codex sandbox: {sandbox}")
    return [
        executable,
        "exec",
        "--ephemeral",
        "--sandbox",
        sandbox,
        "--json",
        "--ignore-user-config",
        "-m",
        MODEL_BY_ROLE[role],
        "-",
    ]


def codex_worker_environment(
    *, worker_home: Path, codex_home: Path, source: Mapping[str, str] | None = None
) -> dict[str, str]:
    """Create a Codex-only environment, excluding the interactive user's home/secrets."""
    source = source or os.environ
    permitted = {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP", "LANG", "LC_ALL"}
    result = {
        key: value
        for key, value in source.items()
        if key.upper() in permitted and not _SECRET_ENV_NAME.search(key)
    }
    result["HOME"] = str(worker_home)
    result["USERPROFILE"] = str(worker_home)
    result["CODEX_HOME"] = str(codex_home)
    return result


class GitHubQueueClient:
    """Parent-only GitHub client. Its token is never passed to Codex."""

    def __init__(self, token: str, *, queue_repo: str = "Pukujan/fossil-core", queue_issue: int = 94) -> None:
        if not token:
            raise WorkOrderError("GITHUB_AUTH_REQUIRED", "broker GitHub token is empty")
        self.token = token
        self.queue_repo = queue_repo
        self.queue_issue = queue_issue

    def _request(self, method: str, url: str, payload: Mapping[str, Any] | None = None) -> Any:
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "fossil-trusted-local-broker",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        data = None if payload is None else json.dumps(dict(payload)).encode("utf-8")
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=15) as response:  # noqa: S310 - fixed GitHub API origin
                raw = response.read()
        except HTTPError as exc:
            raise WorkOrderError("GITHUB_API_FAILED", f"{method} GitHub API -> HTTP {exc.code}") from exc
        return None if not raw else json.loads(raw.decode("utf-8"))

    def comments(self) -> list[Mapping[str, Any]]:
        comments: list[Mapping[str, Any]] = []
        for page in range(1, 101):
            url = (
                f"https://api.github.com/repos/{self.queue_repo}/issues/{self.queue_issue}/comments"
                f"?per_page=100&page={page}"
            )
            batch = self._request("GET", url)
            if not isinstance(batch, list):
                raise WorkOrderError("GITHUB_API_FAILED", "issue comments response was not a list")
            comments.extend(batch)
            if len(batch) < 100:
                return comments
        raise WorkOrderError("GITHUB_API_FAILED", "queue exceeded supported pagination ceiling")

    def comment(self, body: str) -> None:
        self._request(
            "POST",
            f"https://api.github.com/repos/{self.queue_repo}/issues/{self.queue_issue}/comments",
            {"body": body},
        )

    def default_branch(self, repo: str) -> str:
        result = self._request("GET", f"https://api.github.com/repos/{repo}")
        branch = result.get("default_branch") if isinstance(result, Mapping) else None
        if not isinstance(branch, str) or not branch:
            raise WorkOrderError("GITHUB_API_FAILED", f"could not resolve default branch for {repo}")
        return branch

    def create_pull_request(self, repo: str, *, branch: str, title: str, body: str) -> str:
        result = self._request(
            "POST",
            f"https://api.github.com/repos/{repo}/pulls",
            {"title": title, "head": branch, "base": self.default_branch(repo), "body": body, "draft": True},
        )
        url = result.get("html_url") if isinstance(result, Mapping) else None
        if not isinstance(url, str):
            raise WorkOrderError("GITHUB_API_FAILED", "pull request response had no html_url")
        return url


def claim_text(task: QueueTask, *, agent: str, now: datetime, lease: timedelta = timedelta(minutes=120)) -> str:
    lease_until = (now + lease).astimezone(UTC).isoformat().replace("+00:00", "Z")
    return (
        f"CLAIM task={task.task_id}\nagent={agent}\nmode=LOCAL_CODEX\n"
        f"lease_until={lease_until}\nrepo={task.repo}\nstarting_ref={task.starting_ref}"
    )


def workorder_text(work_order: Mapping[str, Any]) -> str:
    return (
        f"WORKORDER task={work_order['task_id']} attempt_id={work_order['attempt_id']} "
        f"generation={work_order['generation']}\nrepo={work_order['repo']}\n"
        f"starting_ref={work_order['starting_ref']}\nrole={work_order['role']} access={work_order['access_class']}"
    )


def terminal_text(work_order: Mapping[str, Any], receipt: Mapping[str, Any], *, pr_url: str | None = None) -> str:
    ref = f" pr={pr_url}" if pr_url else ""
    return (
        f"WORKORDER_DONE task={work_order['task_id']} attempt_id={work_order['attempt_id']} "
        f"generation={work_order['generation']} status={receipt['terminal_status']}{ref}"
    )


def _remaining_seconds(work_order: Mapping[str, Any], now: datetime) -> float:
    deadline = datetime.fromisoformat(str(work_order["deadline"]).replace("Z", "+00:00")).astimezone(UTC)
    return (deadline - now).total_seconds()


def run_bounded_process(
    command: Sequence[str],
    *,
    worktree: Path,
    work_order: Mapping[str, Any],
    environment: Mapping[str, str],
    stdin_text: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    remaining = _remaining_seconds(work_order, now or datetime.now(UTC))
    if remaining <= 0:
        raise WorkOrderError("DEADLINE_EXPIRED", "WorkOrder deadline passed before process launch")
    try:
        completed = subprocess.run(
            list(command),
            cwd=worktree,
            env=dict(environment),
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=remaining,
            check=False,
        )
        status = "PASS" if completed.returncode == 0 else "FAILED"
        detail = sanitize_text((completed.stdout + "\n" + completed.stderr).strip())
    except subprocess.TimeoutExpired as exc:
        status = "FAILED"
        detail = sanitize_text(f"timeout after {remaining:.3f}s: {exc}")
    return sanitize_receipt(
        {
            "version": "trusted-local-receipt-v1",
            "terminal_status": status,
            "work_order_id": work_order["work_order_id"],
            "attempt_id": work_order["attempt_id"],
            "generation": work_order["generation"],
            "starting_ref": work_order["starting_ref"],
            "detail": detail,
        }
    )


def _safe_branch(task_id: str, attempt_id: str) -> str:
    tail = _SAFE_BRANCH.sub("-", attempt_id.lower()).strip("-")
    return f"agent/{task_id.lower()}-{tail}"[:120]


def _git_in_worktree(worktree: Path, *arguments: str) -> list[str]:
    """Build a parent Git command for this exact unprivileged worktree only."""
    return ["git", "-c", f"safe.directory={worktree}", "-C", str(worktree), *arguments]


def publish_checked_changes(
    repo_policy: RepoPolicy,
    *,
    worktree: Path,
    task: QueueTask,
    work_order: Mapping[str, Any],
    github: GitHubQueueClient,
) -> str:
    status = subprocess.run(
        _git_in_worktree(worktree, "status", "--porcelain"),
        check=False,
        capture_output=True,
        text=True,
    )
    if status.returncode != 0:
        raise WorkOrderError("GIT_FAILED", "could not inspect Codex worktree")
    if not status.stdout.strip():
        raise WorkOrderError("NO_CHANGES", "Codex completed but produced no repository changes")

    branch = _safe_branch(task.task_id, str(work_order["attempt_id"]))
    empty_hooks = worktree / ".broker-empty-hooks"
    empty_hooks.mkdir(exist_ok=True)
    commands = [
        _git_in_worktree(worktree, "switch", "-c", branch),
        _git_in_worktree(worktree, "add", "-A"),
        _git_in_worktree(
            worktree,
            "-c", f"core.hooksPath={empty_hooks}",
            "-c", "user.name=trusted-local-broker",
            "-c", "user.email=trusted-local-broker@users.noreply.github.com",
            "commit", "-m", f"{task.task_id}: autonomous local WorkOrder",
        ),
        _git_in_worktree(
            worktree,
            "-c", f"core.hooksPath={empty_hooks}",
            "-c", f"remote.origin.url=https://github.com/{task.repo}.git",
            "push", "origin", f"HEAD:refs/heads/{branch}",
        ),
    ]
    for command in commands:
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        if completed.returncode != 0:
            raise WorkOrderError("GIT_FAILED", f"publication command failed: {command[-1]}")
    return github.create_pull_request(
        task.repo,
        branch=branch,
        title=f"{task.task_id}: autonomous local WorkOrder",
        body=(
            f"Autonomous local Codex WorkOrder for `{task.task_id}`.\n\n"
            f"Starting SHA: `{work_order['starting_ref']}`\nRole: `{task.role}`\n"
            "Publication occurred only after the secretless Codex process exited, the parent "
            "broker's independent check command passed, and live queue state was reconciled."
        ),
    )


def reconcile_before_publication(
    task: QueueTask,
    work_order: Mapping[str, Any],
    *,
    agent: str,
    github: GitHubQueueClient,
    now: datetime | None = None,
) -> DispatchLedger:
    """Re-read live queue immediately before any GitHub publication.

    This rejects cancellation, a newer generation, terminal/duplicate attempt state,
    claim loss/expiry, or queue read failure that happened while Codex/tests ran.
    """
    current = now or datetime.now(UTC)
    live_ledger = parse_broker_ledger(github.comments(), now=current)
    policy = DispatchPolicy(
        repo_allowlist=DEFAULT_REPOS,
        task_allowlist=frozenset({task.task_id}),
        local_agent=agent,
        trusted_dispatch_refs=frozenset(),
        allowed_roles=frozenset(MODEL_BY_ROLE),
        now=lambda: current,
    )
    if authorize_work_order(work_order, ledger=live_ledger, policy=policy) != "secretless":
        raise WorkOrderError("ACCESS_CLASS_MISMATCH", "publication reconciliation requires secretless WorkOrder")
    return live_ledger


def run_local_codex_task(
    task: QueueTask,
    work_order: Mapping[str, Any],
    *,
    ledger: DispatchLedger,
    agent: str,
    repo_policy: RepoPolicy,
    worktree_root: Path,
    worker_home: Path,
    codex_home: Path,
    github: GitHubQueueClient,
    codex_executable: str = "codex",
    codex_sandbox: str = "workspace-write",
) -> tuple[dict[str, Any], str | None]:
    """Run fresh Codex, independent checks, reconcile live state, then publish."""
    policy = DispatchPolicy(
        repo_allowlist=DEFAULT_REPOS,
        task_allowlist=frozenset({task.task_id}),
        local_agent=agent,
        trusted_dispatch_refs=frozenset(),
        allowed_roles=frozenset(MODEL_BY_ROLE),
    )
    if authorize_work_order(work_order, ledger=ledger, policy=policy) != "secretless":
        raise WorkOrderError("ACCESS_CLASS_MISMATCH", "Codex worker only accepts CLOUD_SECRETLESS")

    worktree = isolated_worktree(repo_policy.path, work_order=work_order, base_dir=worktree_root)
    environment = codex_worker_environment(worker_home=worker_home, codex_home=codex_home)
    try:
        codex_receipt = run_bounded_process(
            build_codex_command(
                task.role, executable=codex_executable, sandbox=codex_sandbox
            ),
            worktree=worktree,
            work_order=work_order,
            environment=environment,
            stdin_text=build_codex_prompt(task, work_order),
        )
        if codex_receipt["terminal_status"] != "PASS":
            return codex_receipt, None

        check_receipt = run_bounded_process(
            repo_policy.check_command,
            worktree=worktree,
            work_order=work_order,
            environment=environment,
        )
        if check_receipt["terminal_status"] != "PASS":
            check_receipt["detail"] = "independent check failed\n" + str(check_receipt.get("detail", ""))
            return sanitize_receipt(check_receipt), None

        reconcile_before_publication(task, work_order, agent=agent, github=github)

        pr_url = publish_checked_changes(
            repo_policy,
            worktree=worktree,
            task=task,
            work_order=work_order,
            github=github,
        )
        return sanitize_receipt(
            {
                **check_receipt,
                "terminal_status": "PASS",
                "detail": "Codex, independent checks, and live pre-publication reconciliation passed; parent broker published draft PR.",
                "pr_url": pr_url,
            }
        ), pr_url
    finally:
        destroy_worktree(repo_policy.path, worktree)
