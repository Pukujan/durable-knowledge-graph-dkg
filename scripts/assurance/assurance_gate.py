"""Issue #88 reusable engineering-assurance checks.

These are deliberately small, deterministic, offline, and secretless helpers that
back the reusable GitHub Actions workflows in ``.github/workflows``. They never
turn a 2xx transport response, a process exit code, or a receipt string into
product truth on their own.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ASSURANCE_VERSION = "assurance-v1"
REQUIRED_CORRELATION_FIELDS = (
    "project_issue_id",
    "work_order_id",
    "task_id",
    "attempt_id",
    "request_id",
    "trace_id",
    "checkpoint_id",
    "commit_sha",
    "deployment_id",
)
CURRENT_AUTHORITY_STATUSES = frozenset({"CURRENT_AUTHORITY", "ACCEPTED"})
NONCURRENT_STATUSES = frozenset(
    {"SUPERSEDED_OR_HISTORICAL", "STALE", "CANDIDATE_UNDER_TEST", "UNDECIDED"}
)


def _contract_schema(name: str) -> Mapping[str, Any]:
    root = Path(__file__).resolve().parents[2]
    return json.loads((root / "contracts" / "engineering" / name).read_text(encoding="utf-8"))


def validate_assurance_receipt(receipt: Mapping[str, Any]) -> list[str]:
    """Validate the correlated assurance-v1 receipt.

    Enforces the schema plus the issue #88 semantic gates:
    - explicit risk facets require a ``not_applicable_rationale`` when none apply;
    - stale/historical sources may not be presented as current authority;
    - explicit semantic-success criteria are required;
    - the shared correlation spine is preserved.
    """
    errors = sorted(
        Draft202012Validator(_contract_schema("assurance-v1.schema.json")).iter_errors(receipt),
        key=str,
    )
    errors = [error.message for error in errors]

    risk_facets = list(receipt.get("risk_facets", ()))
    rationale = str(receipt.get("not_applicable_rationale", "")).strip()
    if not risk_facets and not rationale:
        errors.append("risk_facets is empty but not_applicable_rationale is missing")
    if not risk_facets and rationale:
        errors.append("not_applicable_rationale requires an explicit risk_facets entry")
    if "not_applicable" in {str(f).lower() for f in risk_facets} and not rationale:
        errors.append("a not_applicable risk facet requires a rationale")

    semantic_success = str(receipt.get("semantic_success", "")).strip()
    if not semantic_success:
        errors.append("semantic_success criteria are required")

    for source in receipt.get("sources", ()):
        status = str(source.get("status", ""))
        if status in NONCURRENT_STATUSES and status not in CURRENT_AUTHORITY_STATUSES:
            if "authority" in str(source.get("role", "")).lower():
                errors.append(f"stale/historical source {source.get('stable_id')} is presented as current authority")

    return sorted(set(errors))


def validate_correlation_spine(correlation: Mapping[str, Any]) -> list[str]:
    """Preserve and validate the shared Fossil/Cortex/LiteLLM correlation spine."""
    errors: list[str] = []
    missing = [field for field in REQUIRED_CORRELATION_FIELDS if field not in correlation]
    if missing:
        errors.append(f"correlation spine missing fields: {', '.join(missing)}")
    return errors


def semantic_acceptance(*, status_code: int, body: bytes) -> list[str]:
    """Reject transport-only success when the semantic payload is absent or malformed."""
    if not 200 <= status_code < 300:
        return ["non-success HTTP status"]
    if not body:
        return ["2xx response has an empty body"]
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ["2xx response has malformed JSON"]
    if isinstance(parsed, Mapping) and not parsed:
        return ["2xx response has no usable JSON object"]
    return []


def scan_for_secrets(text: str) -> list[str]:
    """Best-effort heuristic scan for secret-bearing values in logs/receipts/artifacts."""
    findings: list[str] = []
    if not text:
        return findings
    patterns = {
        "bearer-token": re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{20,}"),
        "aws-access-key": re.compile(r"(?i)\bAKIA[0-9A-Z]{16}\b"),
        "private-key": re.compile(r"(?i)-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "api-key-assignment": re.compile(r"(?i)(api[_-]?key|password|secret|token)\s*[:=]\s*\S{8,}"),
    }
    for name, pattern in patterns.items():
        if pattern.search(text):
            findings.append(f"possible {name}")
    return sorted(set(findings))


def load_pyproject(path: Path) -> dict[str, Any]:
    """Parse pyproject.toml into a dict; return {} on missing file."""
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}