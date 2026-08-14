"""Task-lifecycle filtering for the trusted local autonomous broker.

A historical READY task must not become executable again merely because its claim
was released.  This module derives the currently executable local-auto task set
from the append-only queue in chronological order.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

from fossil_core.trusted_local_broker import QueueTask, parse_ready_local_tasks

_TERMINAL_TASK = re.compile(r"^(?:DONE|BLOCKED)\s+task=(?P<task>[^\s]+)", re.MULTILINE)
_TASK_DIRECTIVE = re.compile(r"^TASK\s+task=(?P<task>[^\s]+)$", re.MULTILINE)
_CANCEL_TASK = re.compile(r"^CANCEL\s+task=(?P<task>[^\s]+)", re.MULTILINE)
_TRUSTED_AUTHORS = frozenset({"Pukujan"})


def _trusted(comment: Mapping[str, Any], trusted_authors: frozenset[str]) -> bool:
    user = comment.get("user")
    login = user.get("login") if isinstance(user, Mapping) else None
    return login in trusted_authors


def active_ready_local_tasks(
    comments: Iterable[Mapping[str, Any]],
    *,
    trusted_authors: frozenset[str] = _TRUSTED_AUTHORS,
) -> list[QueueTask]:
    """Return only local-auto tasks whose latest lifecycle directive is READY.

    Rules are deliberately conservative:
    - only trusted-author comments affect executable lifecycle state;
    - a machine-valid `TASK ... state=READY` activates/replaces that task;
    - a later trusted task-level `CANCEL task=...` deactivates that task;
    - any later trusted `DONE` or `BLOCKED` deactivates it;
    - a later `TASK` directive that is not machine-valid local-auto also deactivates
      the prior local-auto version rather than silently retaining stale authority;
    - `RELEASE` affects claim ownership, not task readiness.
    """
    active: dict[str, QueueTask] = {}
    order: list[str] = []

    for comment in comments:
        if not _trusted(comment, trusted_authors):
            continue
        body = str(comment.get("body", ""))

        directive = _TASK_DIRECTIVE.search(body)
        if directive:
            task_id = directive["task"]
            parsed = parse_ready_local_tasks([comment], trusted_authors=trusted_authors)
            candidate = next((task for task in parsed if task.task_id == task_id), None)
            if candidate is None:
                active.pop(task_id, None)
            else:
                active[task_id] = candidate
                if task_id in order:
                    order.remove(task_id)
                order.append(task_id)
            continue

        cancellation = _CANCEL_TASK.search(body)
        if cancellation:
            task_id = cancellation["task"]
            active.pop(task_id, None)
            if task_id in order:
                order.remove(task_id)
            continue

        terminal = _TERMINAL_TASK.search(body)
        if terminal:
            task_id = terminal["task"]
            active.pop(task_id, None)
            if task_id in order:
                order.remove(task_id)

    return [active[task_id] for task_id in order if task_id in active]
