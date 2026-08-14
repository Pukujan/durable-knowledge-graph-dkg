"""Exact-SHA, model-free local verifier helpers.

This is deliberately not an extension of the Codex broker.  The only executable
input is a locally administered argv allowlist; queue text selects an action name
but never supplies a command or an environment-variable name.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from uuid import uuid4

from fossil_core.trusted_local_broker import QueueTask, choose_unclaimed_task, claim_text, make_work_order, parse_broker_ledger, terminal_text
from fossil_core.trusted_local_runner import (
    PRIVILEGED_ACCESS_CLASSES,
    DispatchLedger,
    DispatchPolicy,
    WorkOrderError,
    authorize_work_order,
    destroy_worktree,
    isolated_worktree,
    sanitize_receipt,
)

_TASK = re.compile(r"^TASK\s+task=(?P<task>[^\s]+)$", re.MULTILINE)
_FIELD = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_-]*)=(?P<value>.*)$", re.MULTILINE)
_TERMINAL = re.compile(r"^(?:DONE|BLOCKED)\s+task=(?P<task>[^\s]+)", re.MULTILINE)
_SHA = re.compile(r"^[0-9a-f]{40}$")
_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_TRUSTED_AUTHORS = frozenset({"Pukujan"})


@dataclass(frozen=True)
class VerifierTask:
    task_id: str
    repo: str
    access: str
    starting_ref: str
    reviewed_sha: str
    trusted_dispatch_ref: str
    action: str
    spec: str
    comment_id: int | None = None

    def queue_task(self) -> QueueTask:
        # WorkOrder v1 has a role field.  This schema compatibility value never
        # launches a model; the verifier has no Codex executable or model auth.
        return QueueTask(self.task_id, self.repo, self.access, self.starting_ref, "luna", self.spec, self.comment_id)


@dataclass(frozen=True)
class VerifierAction:
    name: str
    access_class: str
    secret_file: Path
    required_env: tuple[str, ...]
    command: tuple[str, ...]


def _trusted(comment: Mapping[str, Any], trusted_authors: frozenset[str]) -> bool:
    user = comment.get("user")
    return isinstance(user, Mapping) and user.get("login") in trusted_authors


def _parse_task(comment: Mapping[str, Any]) -> VerifierTask | None:
    body = str(comment.get("body", ""))
    start = _TASK.search(body)
    if start is None:
        return None
    fields = {item["key"]: item["value"].strip() for item in _FIELD.finditer(body)}
    access = fields.get("access", "")
    starting_ref = fields.get("starting_ref", "")
    reviewed_sha = fields.get("reviewed_sha", "")
    dispatch_ref = fields.get("trusted_dispatch_ref", "")
    action = fields.get("verifier_action", "")
    if (
        fields.get("state") != "READY"
        or access not in PRIVILEGED_ACCESS_CLASSES
        or not all(_SHA.fullmatch(value) for value in (starting_ref, reviewed_sha, dispatch_ref))
        or reviewed_sha != starting_ref
        or fields.get("local_role") != "luna"
        or not action
        or not fields.get("repo")
    ):
        return None
    return VerifierTask(
        task_id=start["task"], repo=fields["repo"], access=access,
        starting_ref=starting_ref, reviewed_sha=reviewed_sha,
        trusted_dispatch_ref=dispatch_ref, action=action, spec=body,
        comment_id=comment.get("id") if isinstance(comment.get("id"), int) else None,
    )


def active_ready_privileged_tasks(
    comments: Iterable[Mapping[str, Any]], *, trusted_authors: frozenset[str] = _TRUSTED_AUTHORS
) -> list[VerifierTask]:
    """Return current trusted privileged tasks, never resurrecting terminal work."""
    active: dict[str, VerifierTask] = {}
    order: list[str] = []
    for comment in comments:
        if not _trusted(comment, trusted_authors):
            continue
        body = str(comment.get("body", ""))
        directive = _TASK.search(body)
        if directive:
            task_id = directive["task"]
            task = _parse_task(comment)
            if task is None:
                active.pop(task_id, None)
                if task_id in order:
                    order.remove(task_id)
            else:
                active[task_id] = task
                if task_id in order:
                    order.remove(task_id)
                order.append(task_id)
            continue
        terminal = _TERMINAL.search(body)
        if terminal:
            active.pop(terminal["task"], None)
            if terminal["task"] in order:
                order.remove(terminal["task"])
    return [active[task_id] for task_id in order if task_id in active]


def parse_actions(raw: Mapping[str, Any]) -> dict[str, VerifierAction]:
    """Validate a local-only action allowlist without reading any secret values."""
    actions_raw = raw.get("actions")
    if not isinstance(actions_raw, Mapping):
        raise WorkOrderError("MALFORMED_CONFIG", "local actions must be a mapping")
    actions: dict[str, VerifierAction] = {}
    for name, value in actions_raw.items():
        if not isinstance(name, str) or not name or not isinstance(value, Mapping):
            raise WorkOrderError("MALFORMED_CONFIG", "each verifier action must have a name and object")
        access = str(value.get("access_class", ""))
        secret_file = Path(str(value.get("secret_file", "")))
        required = value.get("required_env", [])
        command = value.get("command")
        if access not in PRIVILEGED_ACCESS_CLASSES or value.get("production") is True:
            raise WorkOrderError("MALFORMED_CONFIG", f"action {name} has an unauthorized access class or production flag")
        if not secret_file.is_absolute() or not isinstance(required, list) or not all(isinstance(key, str) and _ENV_NAME.fullmatch(key) for key in required):
            raise WorkOrderError("MALFORMED_CONFIG", f"action {name} has invalid secret_file or required_env")
        if not isinstance(command, list) or not command or not all(isinstance(part, str) and part for part in command):
            raise WorkOrderError("MALFORMED_CONFIG", f"action {name} command must be a non-empty argv list")
        if any(part in {"sh", "bash", "cmd", "powershell", "pwsh"} for part in command):
            raise WorkOrderError("MALFORMED_CONFIG", f"action {name} cannot use a shell")
        actions[name] = VerifierAction(name, access, secret_file, tuple(required), tuple(command))
    return actions


def read_selected_dotenv(path: Path, required_env: Sequence[str]) -> dict[str, str]:
    """Read only a named allowlist from an owner-controlled, root-only dotenv file."""
    if not path.is_file():
        raise WorkOrderError("SECRET_SOURCE_UNAVAILABLE", "configured local secret file is unavailable")
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in line:
            raise WorkOrderError("SECRET_SOURCE_MALFORMED", "secret file has an unsupported dotenv line")
        key, value = line.split("=", 1)
        key = key.strip()
        if key in required_env:
            values[key] = value
    missing = [key for key in required_env if not values.get(key)]
    if missing:
        raise WorkOrderError("REQUIRED_SECRET_MISSING", "configured required secret is absent or empty")
    return values


def verifier_environment(selected: Mapping[str, str], *, home: Path = Path("/verifier/home")) -> dict[str, str]:
    """No inherited GitHub/user profile; only a minimal OS env plus selected keys."""
    result = {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL", "TZ") if key in os.environ}
    result.update({"HOME": str(home), "USERPROFILE": str(home), "GIT_CONFIG_NOSYSTEM": "1"})
    result.update(selected)
    return result


def _drop_to_verifier_user() -> None:
    """Demote reviewed-code execution away from the coordinator/root credentials."""
    geteuid = getattr(os, "geteuid", None)
    if os.name != "posix" or geteuid is None or geteuid() != 0:
        return
    try:
        import pwd

        account = getattr(pwd, "getpwnam")("verifier")
    except KeyError as exc:
        raise WorkOrderError("VERIFIER_IDENTITY_UNAVAILABLE", "dedicated verifier account is required") from exc
    setgroups = getattr(os, "setgroups")
    setgid = getattr(os, "setgid")
    setuid = getattr(os, "setuid")
    setgroups([])
    setgid(account.pw_gid)
    setuid(account.pw_uid)


def make_privileged_work_order(task: VerifierTask, *, ledger: DispatchLedger, now: datetime) -> dict[str, Any]:
    order = make_work_order(task.queue_task(), ledger=ledger, now=now, duration=timedelta(minutes=30))
    order.update({"reviewed_sha": task.reviewed_sha, "trusted_dispatch_ref": task.trusted_dispatch_ref, "selected_checks": [task.action]})
    return order


def run_verified_action(
    work_order: Mapping[str, Any], *, ledger: DispatchLedger, policy: DispatchPolicy,
    repo_root: Path, worktree_root: Path, action: VerifierAction,
) -> dict[str, Any]:
    """Run reviewed code with allowlisted credentials and deliberately discard output."""
    if authorize_work_order(work_order, ledger=ledger, policy=policy) != "privileged":
        raise WorkOrderError("ACCESS_CLASS_MISMATCH", "verifier requires a privileged WorkOrder")
    selected = read_selected_dotenv(action.secret_file, action.required_env)
    worktree = isolated_worktree(repo_root, work_order=work_order, base_dir=worktree_root)
    try:
        remaining = (datetime.fromisoformat(str(work_order["deadline"]).replace("Z", "+00:00")) - datetime.now(UTC)).total_seconds()
        if remaining <= 0:
            raise WorkOrderError("DEADLINE_EXPIRED", "WorkOrder deadline passed before verifier launch")
        command = [part.replace("{worktree}", str(worktree)) for part in action.command]
        completed = subprocess.run(
            command, cwd=worktree, env=verifier_environment(selected),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=remaining,
            check=False, preexec_fn=_drop_to_verifier_user if os.name == "posix" else None,
        )
        return sanitize_receipt({
            "version": "trusted-local-receipt-v1", "terminal_status": "PASS" if completed.returncode == 0 else "FAILED",
            "work_order_id": work_order["work_order_id"], "attempt_id": work_order["attempt_id"],
            "generation": work_order["generation"], "starting_ref": work_order["starting_ref"],
            "detail": f"privileged verifier action {action.name} completed; process output was discarded",
        })
    except subprocess.TimeoutExpired:
        return sanitize_receipt({
            "version": "trusted-local-receipt-v1", "terminal_status": "FAILED",
            "work_order_id": work_order["work_order_id"], "attempt_id": work_order["attempt_id"],
            "generation": work_order["generation"], "starting_ref": work_order["starting_ref"],
            "detail": "privileged verifier timed out; process output was discarded",
        })
    finally:
        destroy_worktree(repo_root, worktree)
