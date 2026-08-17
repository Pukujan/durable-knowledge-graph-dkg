"""Small deterministic assurance checks for engineering contracts.

These helpers intentionally validate a bounded semantic surface. They do not
turn a 2xx response, a process exit, or a workflow success into product truth.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


CONTROL_PLANE_VERSION = "control-plane-contract-v1"
REQUIRED_CORRELATION_FIELDS = (
    "project_issue_id",
    "work_order_id",
    "task_id",
    "attempt_id",
    "generation",
    "request_id",
    "trace_id",
    "checkpoint_id",
    "commit_sha",
    "deployment_id",
)


def semantic_http_errors(*, status_code: int, body: bytes, expected: str = "json") -> list[str]:
    """Reject transport-only success when the requested semantic payload is absent."""
    errors: list[str] = []
    if not 200 <= status_code < 300:
        errors.append("non-success HTTP status")
        return errors
    if not body:
        return ["2xx response has an empty body"]
    if expected == "json":
        try:
            parsed = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return ["2xx response has malformed JSON"]
        if not isinstance(parsed, Mapping) or not parsed:
            return ["2xx response has no usable JSON object"]
    elif expected == "stream" and not body.strip():
        return ["completed stream has zero usable payload"]
    elif expected not in {"json", "stream", "bytes"}:
        return [f"unsupported semantic expectation: {expected}"]
    return errors


def validate_control_plane_contract(contract: Mapping[str, Any]) -> list[str]:
    """Validate the small, versioned FOSSIL/Cortex/LiteLLM compatibility seam."""
    errors: list[str] = []
    if contract.get("version") != CONTROL_PLANE_VERSION:
        errors.append("unsupported control-plane contract version")
    owners = contract.get("owners")
    if not isinstance(owners, Mapping) or set(owners) != {"fossil", "cortex", "litellm_ckff_ops"}:
        errors.append("control-plane owners must name fossil, cortex, and litellm_ckff_ops")
    if contract.get("routing_policy_owner") != "caller":
        errors.append("routing policy owner must remain caller")
    shared = contract.get("shared_contracts")
    required_shared = {
        "build_context": "build-context-packet-v1",
        "preflight": "preflight-v1",
        "closeout": "closeout-v1",
    }
    if shared != required_shared:
        errors.append("shared contract versions do not match v1 control-plane boundary")
    if tuple(contract.get("correlation_fields", ())) != REQUIRED_CORRELATION_FIELDS:
        errors.append("correlation fields do not match the shared receipt spine")
    return errors


def load_control_plane_contract(root: Path) -> dict[str, Any]:
    path = root / "contracts" / "engineering" / "control-plane-contract-v1.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("control-plane contract must be a JSON object")
    return value
