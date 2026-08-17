"""Offline-validatable engineering preflight and build-context packet v1.

This module deliberately treats GitHub and FOSSIL retrieval as evidence inputs.  A
retrieval score, a GitHub HTTP response, or a model-written summary does not by
itself establish current authority.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import quote
from urllib.request import Request, urlopen

from jsonschema import Draft202012Validator


PREFLIGHT_VERSION = "preflight-v1"
BUILD_CONTEXT_VERSION = "build-context-packet-v1"
CURRENT_STATUSES = frozenset({"CURRENT_AUTHORITY", "ACCEPTED"})
NONCURRENT_STATUSES = frozenset(
    {"CANDIDATE_UNDER_TEST", "UNDECIDED", "SUPERSEDED_OR_HISTORICAL", "STALE"}
)
KNOWN_STATUSES = CURRENT_STATUSES | NONCURRENT_STATUSES | {"CURRENT_STATE_UNRESOLVED"}

RISK_PACKS = {
    "new-service": ("api-service", "deployment-release", "observability"),
    "cross-service-call": ("api-service", "timeout-retry", "observability"),
    "durable-write": ("durability", "timeout-retry", "recovery"),
    "database-or-schema-change": ("durability", "migration", "recovery"),
    "async-or-background-work": ("async-delivery", "timeout-retry", "recovery"),
    "queue-or-event-stream": ("async-delivery", "timeout-retry", "recovery"),
    "external-dependency": ("dependency-provider", "timeout-retry"),
    "auth-security-sensitive": ("security",),
    "ai-agent-or-model-call": ("ai-semantic-success", "timeout-retry", "observability"),
    "deployment-or-infrastructure": ("deployment-release", "security", "observability"),
    "migration-or-backfill": ("migration", "durability", "recovery"),
    "performance-or-capacity": ("performance-capacity",),
    "observability-change": ("observability",),
    "cross-repo-contract-change": ("cross-repo-contract",),
}


def selected_risk_packs(risk_facets: Iterable[str]) -> list[str]:
    """Return ordered, de-duplicated packs; a trivial task remains empty."""
    return list(dict.fromkeys(pack for facet in risk_facets for pack in RISK_PACKS.get(facet, ())))


def _contract_schema(name: str) -> Mapping[str, Any]:
    root = Path(__file__).resolve().parents[4]
    return json.loads((root / "contracts" / "engineering" / name).read_text(encoding="utf-8"))


def validate_preflight(receipt: Mapping[str, Any]) -> list[str]:
    """Validate the small offline preflight contract and return deterministic errors."""
    errors = sorted(Draft202012Validator(_contract_schema("preflight-v1.schema.json")).iter_errors(receipt), key=str)
    return [error.message for error in errors]


def validate_closeout(receipt: Mapping[str, Any]) -> list[str]:
    errors = sorted(Draft202012Validator(_contract_schema("closeout-v1.schema.json")).iter_errors(receipt), key=str)
    return [error.message for error in errors]


def _default_fetch_json(path: str) -> Mapping[str, Any]:
    """Read public GitHub metadata without reading or requiring any secret."""
    request = Request(
        f"https://api.github.com/{path.lstrip('/')}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "fossil-build-context-v1"},
    )
    with urlopen(request, timeout=10) as response:  # noqa: S310 - fixed GitHub API origin
        return json.loads(response.read().decode("utf-8"))


def resolve_live_github_state(
    repository: str,
    refs: Iterable[Mapping[str, Any]],
    *,
    fetch_json: Callable[[str], Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Resolve issue/PR/branch state into bounded evidence records.

    Callers can inject an authenticated transport from a trusted path.  This
    secretless default deliberately never reads environment credentials.
    """
    fetch = fetch_json or _default_fetch_json
    resolved: list[dict[str, Any]] = []
    for ref in refs:
        kind, number, name = str(ref.get("kind", "")), ref.get("number"), ref.get("name")
        if kind not in {"issue", "pull", "branch"}:
            raise ValueError(f"unsupported GitHub ref kind: {kind}")
        if kind in {"issue", "pull"} and not isinstance(number, int):
            raise ValueError(f"{kind} ref requires integer number")
        if kind == "branch" and not isinstance(name, str):
            raise ValueError("branch ref requires name")
        value = number if kind != "branch" else quote(name, safe="")
        path = f"repos/{repository}/{'issues' if kind == 'issue' else 'pulls' if kind == 'pull' else 'branches'}/{value}"
        stable_id = f"github:{repository}:{kind}:{number if kind != 'branch' else name}"
        try:
            payload = fetch(path)
        except Exception as exc:  # network/permission failures are blockable evidence, never silently ignored
            resolved.append(
                {
                    "stable_id": stable_id,
                    "provenance": "live-github-read",
                    "status": "CURRENT_STATE_UNRESOLVED",
                    "error_class": type(exc).__name__,
                    "material": True,
                }
            )
            continue
        resolved.append(
            {
                "stable_id": stable_id,
                "provenance": "live-github-read",
                "status": "CURRENT_AUTHORITY",
                "url": payload.get("html_url"),
                "updated_at": payload.get("updated_at"),
                "state": payload.get("state"),
                "head_sha": payload.get("head", {}).get("sha") if isinstance(payload.get("head"), Mapping) else payload.get("commit", {}).get("sha"),
                "freshness": "live-read",
                "material": True,
            }
        )
    return resolved


def build_context_packet(
    *,
    task: Mapping[str, Any],
    fossil_material: Iterable[Mapping[str, Any]],
    github_state: Iterable[Mapping[str, Any]],
    risk_facets: Iterable[str] = (),
    unresolved_assumptions: Iterable[Mapping[str, Any]] = (),
    required_closeout_evidence: Iterable[str] = (),
) -> dict[str, Any]:
    """Build a task-scoped packet and fail closed on unresolved material state."""
    fossil = [dict(item) for item in fossil_material]
    github = [dict(item) for item in github_state]
    material = fossil + github
    unknown_statuses = [item for item in material if item.get("status") not in KNOWN_STATUSES]
    unresolved = [dict(item) for item in unresolved_assumptions]
    conflicts = [
        item
        for item in material
        if item.get("status") == "CURRENT_STATE_UNRESOLVED" or (item.get("material") and item.get("conflict"))
    ]
    if unknown_statuses:
        conflicts.extend({"stable_id": item.get("stable_id"), "reason": "unknown source status", "material": True} for item in unknown_statuses)
    conflicts.extend(item for item in unresolved if item.get("material") and item.get("status") != "resolved")
    current = [item for item in material if item.get("status") in CURRENT_STATUSES]
    packet = {
        "version": BUILD_CONTEXT_VERSION,
        "task": dict(task),
        "current_authority": current,
        "current_implementation_state": github,
        "candidates_under_test": [item for item in material if item.get("status") == "CANDIDATE_UNDER_TEST"],
        "undecided": [item for item in material if item.get("status") == "UNDECIDED"],
        "superseded_or_historical": [item for item in material if item.get("status") in {"SUPERSEDED_OR_HISTORICAL", "STALE"}],
        "contradictions": conflicts,
        "current_state_unresolved": bool(conflicts),
        "risk_facets": list(dict.fromkeys(risk_facets)),
        "selected_risk_packs": selected_risk_packs(risk_facets),
        "sources": material,
        "freshness": {"github": "live-read" if github_state else "not-requested", "fossil": "caller-supplied"},
        "unresolved_assumptions": unresolved,
        "required_tests_fault_probes_closeout": list(required_closeout_evidence),
        "dispatch_status": "BLOCKED" if conflicts else "READY_FOR_BOUNDED_WORKORDER",
    }
    return packet


def preflight_from_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Create a v1 receipt whose validator remains offline and network-free."""
    task = dict(packet["task"])
    receipt = {
        "version": PREFLIGHT_VERSION,
        "task": task,
        "risk_facets": list(packet.get("risk_facets", [])),
        "kernel": {
            key: task.get(key)
            for key in (
                "outcome", "behavior_owner", "state_classification", "public_contract_impact",
                "semantic_success", "mechanical_success_and_failure", "evidence_and_tests", "recovery_and_rollback",
            )
        },
        "sources": list(packet.get("sources", [])),
        "unresolved_assumptions": list(packet.get("unresolved_assumptions", [])),
        "required_closeout_evidence": list(packet.get("required_tests_fault_probes_closeout", [])),
        "build_context_version": packet.get("version"),
        "dispatch_status": packet.get("dispatch_status"),
    }
    return receipt


def validate_build_context_packet(packet: Mapping[str, Any]) -> list[str]:
    """Enforce the additional safety semantics not expressed by generic JSON Schema."""
    errors: list[str] = []
    if packet.get("version") != BUILD_CONTEXT_VERSION:
        errors.append("unsupported build-context packet version")
    required_task_keys = {
        "outcome", "behavior_owner", "state_classification", "public_contract_impact", "semantic_success",
        "mechanical_success_and_failure", "evidence_and_tests", "recovery_and_rollback",
    }
    missing = required_task_keys - set(packet.get("task", {}))
    if missing:
        errors.append(f"task is missing universal-kernel fields: {', '.join(sorted(missing))}")
    if not packet.get("current_authority"):
        errors.append("no CURRENT_AUTHORITY source is present")
    if not packet.get("current_implementation_state"):
        errors.append("live GitHub implementation state is required")
    blocked = bool(packet.get("current_state_unresolved"))
    if blocked and packet.get("dispatch_status") != "BLOCKED":
        errors.append("unresolved material state must block dispatch")
    if not blocked and packet.get("dispatch_status") != "READY_FOR_BOUNDED_WORKORDER":
        errors.append("resolved packet must have bounded-workorder dispatch status")
    errors.extend(f"preflight: {error}" for error in validate_preflight(preflight_from_packet(packet)))
    return errors
