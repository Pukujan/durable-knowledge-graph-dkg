from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / "src" / "fossil_core" / "runtime" / "chatgpt_action.py"
SERVER = ROOT / "src" / "fossil_core" / "runtime" / "chatgpt_action_server.py"
DOCKERFILE = ROOT / "docker" / "chatgpt-action" / "Dockerfile"
WORKFLOW = ROOT / ".github" / "workflows" / "chatgpt-action-container.yml"


@dataclass(frozen=True)
class Mutant:
    name: str
    path: Path
    replacements: tuple[tuple[str, str], ...]
    rationale: str


MUTANTS = (
    Mutant(
        "bypass_bearer_check",
        ACTION,
        (("if not self._authorized(request):", "if False:"),),
        "Missing/incorrect bearer authentication must fail closed.",
    ),
    Mutant(
        "widen_route_allowlist",
        ACTION,
        (("if path not in _ACTION_ROUTE_ALLOWLIST:", "if False:"),),
        "Unknown and prohibited paths must remain 404.",
    ),
    Mutant(
        "enable_commit_route",
        ACTION,
        (
            (
                '    "/actions/lineage": "fossil.lineage",',
                '    "/actions/lineage": "fossil.lineage",\n    "/actions/commit": "fossil.commit",',
            ),
        ),
        "Authenticated callers must never gain a durable commit route.",
    ),
    Mutant(
        "remove_body_size_guards",
        ACTION,
        (
            ("if declared > self.max_request_body_size:", "if False:"),
            ("if len(raw) > self.max_request_body_size:", "if False:"),
        ),
        "Oversized bodies must be rejected before adapter invocation.",
    ),
    Mutant(
        "weaken_search_limit_validation",
        ACTION,
        (("or limit > 100", "or limit > 1000"),),
        "Out-of-range search limits must fail closed.",
    ),
    Mutant(
        "allow_extra_capability_fields",
        ACTION,
        (("return set(payload).issubset(allowed)", "return True"),),
        "Extra fields must not smuggle graph/write/filesystem capabilities.",
    ),
    Mutant(
        "trust_forwarded_headers_from_any_peer",
        ACTION,
        (
            (
                "if not any(peer in network for network in self.trusted_proxy_networks):\n            return None",
                "if False:\n            return None",
            ),
        ),
        "Forwarded origin metadata must be trusted only from configured proxy CIDRs.",
    ),
    Mutant(
        "remove_trusted_proxy_origin_support",
        ACTION,
        (("return self._trusted_proxy_origin(request)", "return None"),),
        "A correctly configured trusted proxy must produce the HTTPS schema origin.",
    ),
    Mutant(
        "publish_http_schema_origin",
        ACTION,
        (("return self.public_base_url", 'return "http://internal.invalid:8787"'),),
        "The generated public server URL must never regress to HTTP.",
    ),
    Mutant(
        "remove_components_schemas",
        ACTION,
        (("\"schemas\": schemas,", "\"x-disabled-schemas\": schemas,"),),
        "Custom GPT/OpenAPI compatibility requires components.schemas.",
    ),
    Mutant(
        "erase_search_response_properties",
        ACTION,
        (
            (
                '"SearchResult": {\n            "type": "object",\n            "additionalProperties": True,\n            "required": ["event_id", "event_type", "pack_id", "recorded_at"],\n            "properties": {',
                '"SearchResult": {\n            "type": "object",\n            "additionalProperties": True,\n            "required": ["event_id", "event_type", "pack_id", "recorded_at"],\n            "properties": {},\n            "x-original-properties": {',
            ),
        ),
        "Successful response objects must retain declared properties.",
    ),
    Mutant(
        "enable_uvicorn_global_proxy_headers",
        SERVER,
        (("proxy_headers=False,", "proxy_headers=True,"),),
        "Uvicorn must not globally trust caller-controlled forwarded headers.",
    ),
    Mutant(
        "add_write_method_to_read_store",
        SERVER,
        (
            (
                "    def iter_events(self) -> Iterator[dict[str, Any]]:",
                "    def commit(self, event: dict[str, Any]) -> dict[str, Any]:\n        return event\n\n    def iter_events(self) -> Iterator[dict[str, Any]]:",
            ),
        ),
        "The Action event-store view must expose no mutation API.",
    ),
    Mutant(
        "run_container_as_root",
        DOCKERFILE,
        (("USER fossil", "USER root"),),
        "The production image must execute as non-root.",
    ),
    Mutant(
        "make_canonical_mount_writable",
        WORKFLOW,
        ((":/var/lib/fossil:ro", ":/var/lib/fossil:rw"),),
        "The container/deployment contract must preserve a read-only canonical mount.",
    ),
    Mutant(
        "remove_loopback_host_binding",
        WORKFLOW,
        (("-p 127.0.0.1:8787:8787", "-p 8787:8787"),),
        "Docker Desktop must publish the Action port only on Windows loopback.",
    ),
)


TEST_COMMAND = [
    sys.executable,
    "-m",
    "pytest",
    "-q",
    "tests/holdout/test_chatgpt_action_holdout.py",
    "tests/test_chatgpt_action_architecture.py",
]


def apply_mutant(mutant: Mutant) -> str:
    original = mutant.path.read_text(encoding="utf-8")
    mutated = original
    for old, new in mutant.replacements:
        if old not in mutated:
            raise RuntimeError(f"mutant {mutant.name}: anchor not found: {old!r}")
        mutated = mutated.replace(old, new, 1)
    mutant.path.write_text(mutated, encoding="utf-8")
    return original


def main() -> int:
    survivors: list[str] = []
    killed: list[str] = []
    harness_errors: list[str] = []
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

    for mutant in MUTANTS:
        try:
            original = apply_mutant(mutant)
        except RuntimeError as exc:
            harness_errors.append(mutant.name)
            print(f"HARNESS_ERROR: {exc}")
            continue

        try:
            completed = subprocess.run(
                TEST_COMMAND,
                cwd=ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
        finally:
            mutant.path.write_text(original, encoding="utf-8")

        if completed.returncode == 0:
            survivors.append(mutant.name)
            status = "SURVIVED"
            print(completed.stdout)
        else:
            killed.append(mutant.name)
            status = "KILLED"
        print(f"{status}: {mutant.name} — {mutant.rationale}")

    print(
        "mutation summary: "
        f"killed={len(killed)} survived={len(survivors)} "
        f"harness_errors={len(harness_errors)} total={len(MUTANTS)}"
    )
    if harness_errors:
        print("harness errors: " + ", ".join(harness_errors))
    if survivors:
        print("surviving mutants: " + ", ".join(survivors))
    if harness_errors or survivors:
        return 1
    print("surviving mutants: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
