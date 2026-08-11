#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


REQUIRED_ENDPOINTS = {
    ("GET", "/global/health"),
    ("POST", "/session"),
    ("POST", "/session/{session_id}/prompt_async"),
    ("GET", "/session/status"),
    ("GET", "/session/{session_id}/message"),
    ("GET", "/session/{session_id}/diff"),
    ("POST", "/session/{session_id}/abort"),
}


def main() -> int:
    path = Path("contracts/executor/opencode-persistent-v1.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema"] == "fossil.executor.contract.v1"
    assert data["session_lifetime_owner"] == "opencode_server"
    assert data["task_submission"]["blocking"] is False
    assert data["timeout_policy"]["whole_task_timeout"] == "caller_explicit_only"
    assert data["timeout_policy"]["default_whole_task_timeout_seconds"] is None
    assert data["runtime_dependencies"]["ssc_allowed"] is False
    assert data["orchestration"]["parent_process_must_not_own_agent_process_lifetime"] is True
    actual = {(row["method"], row["path"]) for row in data["required_endpoints"]}
    missing = REQUIRED_ENDPOINTS - actual
    if missing:
        raise SystemExit(f"executor contract missing endpoints: {sorted(missing)}")
    print(f"validated {data['id']} with {len(actual)} required endpoints")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
