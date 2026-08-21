from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NETWORK = ROOT / "src" / "fossil_core" / "runtime" / "network.py"


@dataclass(frozen=True)
class Mutant:
    name: str
    replacements: tuple[tuple[str, str], ...]
    rationale: str


MUTANTS = (
    Mutant(
        "bypass_bearer_rejection",
        (("        if not valid:\n", "        if False:\n"),),
        "Missing, malformed, and incorrect bearer credentials must fail closed.",
    ),
    Mutant(
        "accept_duplicate_authorization",
        (("        if len(authorization_values) == 1:\n", "        if authorization_values:\n"),),
        "Duplicate Authorization headers must never be accepted by selecting one value.",
    ),
    Mutant(
        "accept_any_presented_token",
        (("                and hmac.compare_digest(presented, self.token)\n", "                and True\n"),),
        "The presented bearer value must exactly match the configured secret.",
    ),
    Mutant(
        "make_mcp_public_without_auth",
        (
            (
                '        public_paths=frozenset({"/healthz", "/readyz"}),\n',
                '        public_paths=frozenset({"/healthz", "/readyz", "/mcp"}),\n',
            ),
        ),
        "The MCP route must never bypass bearer authentication.",
    ),
    Mutant(
        "make_ingest_public_without_auth",
        (
            (
                '        public_paths=frozenset({"/healthz", "/readyz"}),\n',
                '        public_paths=frozenset({"/healthz", "/readyz", "/ingest"}),\n',
            ),
        ),
        "Reviewed ingestion must not become unauthenticated through route widening.",
    ),
    Mutant(
        "remove_mcp_body_limit",
        (
            (
                "        max_request_body_size=max_mcp_request_body_size,\n",
                "        max_request_body_size=1024 * 1024 * 1024,\n",
            ),
        ),
        "Authenticated MCP requests must remain bounded.",
    ),
    Mutant(
        "disable_mcp_transport_security",
        (
            (
                "        transport_security=transport_security,\n",
                "        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),\n",
            ),
        ),
        "The explicit public Host/Origin allowlist must reach the MCP transport unchanged.",
    ),
    Mutant(
        "reflect_token_in_auth_error",
        (
            (
                '                        "detail": "Bearer authentication required",\n',
                '                        "detail": "Bearer authentication required: " + self.token,\n',
            ),
        ),
        "Authentication errors must never reflect the configured bearer token.",
    ),
)


TEST_COMMAND = [
    sys.executable,
    "-m",
    "pytest",
    "-q",
    "tests/holdout/test_public_mcp_holdout.py",
    "tests/test_fossil_node_network.py",
]


def apply_mutant(mutant: Mutant) -> str:
    original = NETWORK.read_text(encoding="utf-8")
    mutated = original
    for old, new in mutant.replacements:
        if old not in mutated:
            raise RuntimeError(f"mutant {mutant.name}: anchor not found: {old!r}")
        mutated = mutated.replace(old, new, 1)
    NETWORK.write_text(mutated, encoding="utf-8")
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
            NETWORK.write_text(original, encoding="utf-8")

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
