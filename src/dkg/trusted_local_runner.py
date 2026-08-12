"""Fail-closed trusted-local WorkOrder validation and execution helpers.

The module deliberately contains no GitHub token, credential loading, or webhook
server.  A default-branch workflow supplies a WorkOrder, and this module checks
the versioned contract before creating a short-lived worktree and process.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from urllib.request import Request, urlopen
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator, FormatChecker


WORK_ORDER_VERSION = "trusted-local-workorder-v1"
SECRETLESS_ACCESS_CLASS = "CLOUD_SECRETLESS"
PRIVILEGED_ACCESS_CLASSES = frozenset(
    {"LOCAL_INFRA", "TRUSTED_SECRET_WORKFLOW", "LIVE_STAGING", "OBJECT_STORE_LIVE"}
)
ACTIVE_LOCAL_ROLES = frozenset({"luna"})
TERMINAL_STATUSES = frozenset({"PASS", "FAILED", "BLOCKED"})
_SECRET_VALUE = re.compile(
    r"(?i)(?:gh[pousr]_[A-Za-z0-9_=-]{12,}|github_pat_[A-Za-z0-9_=-]{12,}|sk-[A-Za-z0-9_-]{12,}|(?:api[_-]?key|token|secret|password)\s*[:=]\s*[^\s'\"]+)"
)
_SECRET_NAME = re.compile(r"(?i)(?:token|secret|password|api[_-]?key|railway|credential)")


class WorkOrderError(ValueError):
    """A deterministic dispatch rejection with a stable machine-readable code."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(detail)


@dataclass(frozen=True)
class LedgerClaim:
    task_id: str
    agent: str
    lease_until: datetime
    released: bool = False

    def active_for(self, *, now: datetime) -> bool:
        return not self.released and self.lease_until > now


@dataclass
class DispatchLedger:
    """Small trusted view of #94, supplied by a default-branch reader.

    Parsing GitHub issue prose is intentionally outside this class: a caller must
    convert the append-only ledger into the winning, current claims before a
    WorkOrder is evaluated.  That keeps queue interpretation testable and makes a
    GitHub read failure a dispatch blocker rather than a silent fallback.
    """

    claims: Mapping[str, LedgerClaim]
    cancelled_attempt_ids: frozenset[str] = frozenset()
    terminal_attempt_ids: frozenset[str] = frozenset()
    latest_generation: Mapping[str, int] = field(default_factory=dict)
    available: bool = True


@dataclass(frozen=True)
class DispatchPolicy:
    repo_allowlist: frozenset[str]
    task_allowlist: frozenset[str]
    local_agent: str
    trusted_dispatch_refs: frozenset[str]
    allowed_roles: frozenset[str] = ACTIVE_LOCAL_ROLES
    now: Callable[[], datetime] = lambda: datetime.now(UTC)


_CLAIM_LINE = re.compile(r"^CLAIM\s+task=(?P<task>[^\s]+)", re.MULTILINE)
_AGENT_LINE = re.compile(r"^agent=(?P<agent>[^\s]+)", re.MULTILINE)
_LEASE_LINE = re.compile(r"^lease_until=(?P<lease>[^\s]+)", re.MULTILINE)
_RENEW_LINE = re.compile(r"^RENEW\s+task=(?P<task>[^\s]+)\s+agent=(?P<agent>[^\s]+).*?lease_until=(?P<lease>[^\s]+)", re.MULTILINE | re.DOTALL)
_RELEASE_LINE = re.compile(r"^RELEASE\s+task=(?P<task>[^\s]+)\s+agent=(?P<agent>[^\s]+)", re.MULTILINE)


def parse_claim_ledger(comments: Iterable[Mapping[str, Any]], *, now: datetime) -> DispatchLedger:
    """Derive the earliest still-active claim per task from append-only #94 comments.

    The trusted caller supplies comments in GitHub's chronological order.  Invalid
    claim syntax is ignored, while an unreadable GitHub response is represented by
    ``available=False`` by ``read_github_claim_ledger`` and blocks dispatch.
    """
    candidates: list[LedgerClaim] = []
    released: set[int] = set()
    for comment in comments:
        body = str(comment.get("body", ""))
        for match in _RELEASE_LINE.finditer(body):
            for index in range(len(candidates) - 1, -1, -1):
                claim = candidates[index]
                if index not in released and claim.task_id == match["task"] and claim.agent == match["agent"]:
                    released.add(index)
                    break
        for match in _RENEW_LINE.finditer(body):
            try:
                renewed_lease = _parse_deadline(match["lease"])
            except WorkOrderError:
                continue
            for index in range(len(candidates) - 1, -1, -1):
                claim = candidates[index]
                if index not in released and claim.task_id == match["task"] and claim.agent == match["agent"]:
                    candidates[index] = replace(claim, lease_until=renewed_lease)
                    break
        claim_match, agent_match, lease_match = _CLAIM_LINE.search(body), _AGENT_LINE.search(body), _LEASE_LINE.search(body)
        if not (claim_match and agent_match and lease_match):
            continue
        try:
            lease_until = _parse_deadline(lease_match["lease"])
        except WorkOrderError:
            continue
        candidates.append(LedgerClaim(claim_match["task"], agent_match["agent"], lease_until))
    claims: dict[str, LedgerClaim] = {}
    for index, claim in enumerate(candidates):
        if index in released or not claim.active_for(now=now):
            continue
        claims.setdefault(claim.task_id, claim)
    return DispatchLedger(claims=claims)


def read_github_claim_ledger(
    repository: str,
    *,
    issue_number: int = 94,
    token: str | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    fetch_json: Callable[[str, Mapping[str, str]], list[Mapping[str, Any]]] | None = None,
) -> DispatchLedger:
    """Read current #94 comments using the short-lived workflow token, then discard it.

    The token is used only by the default-branch dispatcher to read coordination
    metadata; it is never included in a secretless worker environment or receipt.
    """
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "fossil-trusted-local-dispatcher"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        comments: list[Mapping[str, Any]] = []
        for page in range(1, 101):  # 10,000 comments is a fail-closed practical ceiling.
            path = f"https://api.github.com/repos/{repository}/issues/{issue_number}/comments?per_page=100&page={page}"
            if fetch_json is not None:
                batch = fetch_json(path, headers)
            else:
                request = Request(path, headers=headers)
                with urlopen(request, timeout=10) as response:  # noqa: S310 - fixed GitHub API origin
                    batch = json.loads(response.read().decode("utf-8"))
            if not isinstance(batch, list):
                raise ValueError("GitHub comments response was not a list")
            comments.extend(batch)
            if len(batch) < 100:
                return parse_claim_ledger(comments, now=now())
        raise ValueError("GitHub comment ledger exceeded supported pagination limit")
    except Exception:
        return DispatchLedger(claims={}, available=False)


def _contract_schema() -> Mapping[str, Any]:
    root = Path(__file__).resolve().parents[2]
    return json.loads((root / "contracts" / "trusted-local-workorder-v1.schema.json").read_text(encoding="utf-8"))


def validate_work_order(work_order: Mapping[str, Any]) -> list[str]:
    """Return deterministic JSON-schema failures without touching the network."""
    errors = sorted(
        Draft202012Validator(_contract_schema(), format_checker=FormatChecker()).iter_errors(dict(work_order)),
        key=lambda error: (list(error.absolute_path), error.message),
    )
    return [error.message for error in errors]


def _parse_deadline(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WorkOrderError("MALFORMED", "deadline is not ISO-8601") from exc
    if parsed.tzinfo is None:
        raise WorkOrderError("MALFORMED", "deadline must include a timezone")
    return parsed.astimezone(UTC)


def lane_for(work_order: Mapping[str, Any]) -> str:
    return "secretless" if work_order["access_class"] == SECRETLESS_ACCESS_CLASS else "privileged"


def authorize_work_order(
    work_order: Mapping[str, Any], *, ledger: DispatchLedger, policy: DispatchPolicy
) -> str:
    """Fail closed before any checkout, worktree, agent, or credential action."""
    schema_errors = validate_work_order(work_order)
    if schema_errors:
        raise WorkOrderError("MALFORMED", "; ".join(schema_errors))
    now = policy.now()
    if not ledger.available:
        raise WorkOrderError("LEDGER_UNAVAILABLE", "current queue/claim ledger could not be verified")
    if work_order["repo"] not in policy.repo_allowlist:
        raise WorkOrderError("UNAUTHORIZED_REPOSITORY", "repository is not in the trusted-local allowlist")
    if work_order["task_id"] not in policy.task_allowlist:
        raise WorkOrderError("UNAUTHORIZED_TASK", "task is not in the trusted-local allowlist")
    if work_order["role"] not in policy.allowed_roles:
        raise WorkOrderError("BLOCKED_POLICY", "requested local role is not currently authorized")
    if _parse_deadline(work_order["deadline"]) <= now:
        raise WorkOrderError("DEADLINE_EXPIRED", "WorkOrder deadline has passed")
    claim = ledger.claims.get(work_order["task_id"])
    if claim is None or not claim.active_for(now=now) or claim.agent != policy.local_agent:
        raise WorkOrderError("CLAIM_INVALID", "task has no active winning claim for this dispatcher")
    if work_order["attempt_id"] in ledger.cancelled_attempt_ids:
        raise WorkOrderError("CANCELLED", "attempt is cancelled")
    if work_order["attempt_id"] in ledger.terminal_attempt_ids:
        raise WorkOrderError("DUPLICATE_ATTEMPT", "attempt already has a terminal closeout")
    latest_generation = ledger.latest_generation.get(work_order["task_id"])
    if latest_generation is not None and work_order["generation"] < latest_generation:
        raise WorkOrderError("STALE_GENERATION", "WorkOrder generation is older than the current task generation")
    lane = lane_for(work_order)
    if lane == "privileged":
        if work_order.get("reviewed_sha") != work_order["starting_ref"]:
            raise WorkOrderError("EXACT_SHA_REQUIRED", "privileged verification requires reviewed_sha equal to starting_ref")
        if work_order.get("trusted_dispatch_ref") not in policy.trusted_dispatch_refs:
            raise WorkOrderError("UNTRUSTED_DISPATCH", "privileged verification requires a reviewed dispatcher revision")
    return lane


def secretless_environment(source: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return a minimal process environment with credential-like variables removed."""
    source = source or os.environ
    permitted = {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP", "HOME", "USERPROFILE", "LANG", "LC_ALL"}
    return {key: value for key, value in source.items() if key.upper() in permitted and not _SECRET_NAME.search(key)}


def sanitize_text(value: str) -> str:
    """Remove credential-looking values from process output before receipt publication."""
    return _SECRET_VALUE.sub("[REDACTED]", value)


def sanitize_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively sanitize a compact receipt and reject non-terminal closeout."""
    terminal_status = receipt.get("terminal_status")
    if terminal_status not in TERMINAL_STATUSES:
        raise WorkOrderError("INVALID_CLOSEOUT", "terminal_status must be PASS, FAILED, or BLOCKED")

    def clean(value: Any) -> Any:
        if isinstance(value, str):
            return sanitize_text(value)
        if isinstance(value, Mapping):
            return {str(key): clean(item) for key, item in value.items()}
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value

    return clean(dict(receipt))


def isolated_worktree(repo_root: Path, *, work_order: Mapping[str, Any], base_dir: Path) -> Path:
    """Create a detached, disposable exact-SHA worktree for one attempt."""
    attempt_dir = base_dir / f"{work_order['work_order_id']}-{work_order['attempt_id']}"
    if attempt_dir.exists():
        raise WorkOrderError("DUPLICATE_ATTEMPT", "attempt worktree path already exists")
    base_dir.mkdir(parents=True, exist_ok=True)
    present = subprocess.run(
        ["git", "-C", str(repo_root), "cat-file", "-e", f"{work_order['starting_ref']}^{{commit}}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if present.returncode != 0:
        fetched = subprocess.run(
            ["git", "-C", str(repo_root), "fetch", "--no-tags", "origin", work_order["starting_ref"]],
            check=False,
            capture_output=True,
            text=True,
        )
        if fetched.returncode != 0:
            raise WorkOrderError("STARTING_REF_UNAVAILABLE", "reviewed starting_ref could not be fetched")
    try:
        subprocess.run(
            ["git", "-C", str(repo_root), "worktree", "add", "--detach", str(attempt_dir), work_order["starting_ref"]],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise WorkOrderError("WORKTREE_FAILED", "could not create isolated attempt worktree") from exc
    return attempt_dir


def destroy_worktree(repo_root: Path, worktree: Path) -> None:
    """Best-effort cleanup after a terminal closeout; never removes an arbitrary path."""
    subprocess.run(
        ["git", "-C", str(repo_root), "worktree", "remove", "--force", str(worktree)],
        check=False,
        capture_output=True,
        text=True,
    )
    if worktree.exists():
        shutil.rmtree(worktree)


def run_attempt(
    command: Sequence[str], *, worktree: Path, work_order: Mapping[str, Any], environment: Mapping[str, str], now: Callable[[], datetime] = lambda: datetime.now(UTC)
) -> dict[str, Any]:
    """Run one fresh agent/check command with the WorkOrder deadline as a hard bound."""
    remaining_seconds = (_parse_deadline(work_order["deadline"]) - now()).total_seconds()
    if remaining_seconds <= 0:
        raise WorkOrderError("DEADLINE_EXPIRED", "WorkOrder deadline passed before process launch")
    try:
        completed = subprocess.run(
            list(command), cwd=worktree, env=dict(environment), capture_output=True, text=True, timeout=remaining_seconds, check=False
        )
        status = "PASS" if completed.returncode == 0 else "FAILED"
        detail = sanitize_text((completed.stdout + "\n" + completed.stderr).strip())
    except subprocess.TimeoutExpired as exc:
        status, detail = "FAILED", sanitize_text(f"timeout after {remaining_seconds:.3f}s: {exc}")
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


def dispatch_secretless_attempt(
    work_order: Mapping[str, Any], *, ledger: DispatchLedger, policy: DispatchPolicy, repo_root: Path, base_dir: Path, command: Sequence[str]
) -> dict[str, Any]:
    """Authorize then execute one secretless attempt, always cleaning its worktree."""
    if authorize_work_order(work_order, ledger=ledger, policy=policy) != "secretless":
        raise WorkOrderError("ACCESS_CLASS_MISMATCH", "secretless worker cannot execute a privileged WorkOrder")
    worktree = isolated_worktree(repo_root, work_order=work_order, base_dir=base_dir)
    try:
        return run_attempt(command, worktree=worktree, work_order=work_order, environment=secretless_environment(), now=policy.now)
    finally:
        destroy_worktree(repo_root, worktree)


def dispatch_privileged_verifier(
    work_order: Mapping[str, Any], *, ledger: DispatchLedger, policy: DispatchPolicy, repo_root: Path, base_dir: Path,
    command: Sequence[str], credential_environment: Callable[[], Mapping[str, str]],
) -> dict[str, Any]:
    """Execute the isolated privileged lane only after exact-SHA authorization.

    ``credential_environment`` is an installation-local wrapper, not a repository
    file.  It may load the minimum required local credentials after all dispatcher
    checks pass.  Its values are never returned or copied into the receipt.
    """
    if authorize_work_order(work_order, ledger=ledger, policy=policy) != "privileged":
        raise WorkOrderError("ACCESS_CLASS_MISMATCH", "privileged verifier requires a privileged access class")
    worktree = isolated_worktree(repo_root, work_order=work_order, base_dir=base_dir)
    try:
        return run_attempt(command, worktree=worktree, work_order=work_order, environment=credential_environment(), now=policy.now)
    finally:
        destroy_worktree(repo_root, worktree)
