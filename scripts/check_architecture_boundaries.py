from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

from architecture_inventory import inventory


PACKAGE = "fossil_core"
CANONICAL_MODULES = {
    "fossil_core.application",
    "fossil_core.application.evaluation",
    "fossil_core.application.evaluation.benchmark",
    "fossil_core.application.evaluation.cases",
    "fossil_core.application.evaluation.context_probe",
    "fossil_core.application.ingest",
    "fossil_core.application.ingest.pack_validation",
    "fossil_core.application.query",
    "fossil_core.application.query.lineage",
    "fossil_core.application.rebuild",
    "fossil_core.application.rebuild.pack_corpus",
    "fossil_core.domain",
    "fossil_core.domain.evidence",
    "fossil_core.domain.identity",
    "fossil_core.domain.lifecycle",
    "fossil_core.domain.pack",
    "fossil_core.domain.promotion",
    "fossil_core.domain.provenance",
    "fossil_core.ports",
    "fossil_core.ports.artifact_store",
    "fossil_core.ports.cognitive_service",
    "fossil_core.ports.context_provider",
    "fossil_core.ports.embedding_provider",
    "fossil_core.ports.event_store",
    "fossil_core.ports.model_service",
    "fossil_core.ports.projection",
    "fossil_core.ports.reranker",
    "fossil_core.ports.retriever",
    "fossil_core.ports.verification_service",
    "fossil_core.adapters",
    "fossil_core.adapters.filesystem",
    "fossil_core.adapters.filesystem.artifact_store",
    "fossil_core.adapters.filesystem.event_store",
    "fossil_core.adapters.filesystem.io",
    "fossil_core.adapters.litellm",
    "fossil_core.adapters.litellm.embedding",
    "fossil_core.adapters.litellm.reranker",
    "fossil_core.adapters.s3",
    "fossil_core.adapters.s3.storage",
    "fossil_core.adapters.vector",
    "fossil_core.adapters.vector.semantic_retriever",
}

COMPATIBILITY_IMPORTS = {
    "fossil_core.answer_pipeline": {"fossil_core.application.query"},
    "fossil_core.benchmark": {"fossil_core.application.evaluation.benchmark"},
    "fossil_core.benchmark_cases": {"fossil_core.application.evaluation.cases"},
    "fossil_core.contracts": {"fossil_core.ports"},
    "fossil_core.ids": {"fossil_core.domain.identity"},
    "fossil_core.io": {"fossil_core.adapters.filesystem.io"},
    "fossil_core.lifecycle": {"fossil_core.domain.lifecycle"},
    "fossil_core.pack_corpus": {"fossil_core.application.rebuild.pack_corpus"},
    "fossil_core.promotion": {"fossil_core.domain.promotion"},
    "fossil_core.semantic_retriever": {"fossil_core.adapters.vector.semantic_retriever"},
    "fossil_core.storage_ports": {"fossil_core.ports"},
    "fossil_core.artifact_store": {
        "fossil_core.adapters.filesystem.artifact_store"
    },
    "fossil_core.event_store": {"fossil_core.adapters.filesystem.event_store"},
    "fossil_core.s3_storage": {"fossil_core.adapters.s3"},
}

PORT_FORBIDDEN_PREFIXES = (
    "fossil_core.adapters",
    "fossil_core.artifact_store",
    "fossil_core.event_store",
    "fossil_core.s3_storage",
)

DOMAIN_FORBIDDEN_PREFIXES = (
    "fossil_core.ports",
    "fossil_core.adapters",
    "fossil_core.storage_ports",
    "fossil_core.artifact_store",
    "fossil_core.event_store",
    "fossil_core.s3_storage",
)

APPLICATION_FORBIDDEN_PREFIXES = (
    "fossil_core.adapters",
    "fossil_core.artifact_store",
    "fossil_core.event_store",
    "fossil_core.s3_storage",
)

ADAPTER_SELF_SHIMS = {
    "fossil_core.adapters.filesystem": {
        "fossil_core.artifact_store",
        "fossil_core.event_store",
    },
    "fossil_core.adapters.s3": {"fossil_core.s3_storage"},
}


def _matches_prefix(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(f"{prefix}.")


def _edges(payload: dict[str, Any]) -> dict[str, set[str]]:
    modules = set(payload["modules"])
    graph: dict[str, set[str]] = {module: set() for module in modules}
    for edge in payload["internal_import_edges"]:
        source = str(edge["from"])
        target = str(edge["to"])
        if source in modules and target in modules:
            graph[source].add(target)
    return graph


def _strongly_connected_components(
    graph: dict[str, set[str]],
) -> list[tuple[str, ...]]:
    """Return deterministic first-party cycles as strongly connected components."""

    index = 0
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[tuple[str, ...]] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for target in sorted(graph[node]):
            if target not in indices:
                visit(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif target in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[target])

        if lowlinks[node] != indices[node]:
            return

        component: list[str] = []
        while True:
            member = stack.pop()
            on_stack.remove(member)
            component.append(member)
            if member == node:
                break

        ordered = tuple(sorted(component))
        if len(ordered) > 1 or node in graph[node]:
            components.append(ordered)

    for node in sorted(graph):
        if node not in indices:
            visit(node)

    return sorted(components)


def violations(payload: dict[str, Any]) -> list[str]:
    modules = payload["modules"]
    violations: list[str] = []

    missing = sorted(CANONICAL_MODULES - set(modules))
    for module in missing:
        violations.append(f"missing canonical architecture module: {module}")

    for module, expected in sorted(COMPATIBILITY_IMPORTS.items()):
        details = modules.get(module)
        if details is None:
            violations.append(f"missing compatibility module: {module}")
            continue
        actual = set(details["internal_imports"])
        if actual != expected:
            violations.append(
                f"compatibility module {module} must stay thin: "
                f"expected imports {sorted(expected)}, got {sorted(actual)}"
            )

    for module, details in sorted(modules.items()):
        internal_imports = set(details["internal_imports"])

        if _matches_prefix(module, "fossil_core.domain"):
            for imported in sorted(internal_imports):
                if any(
                    _matches_prefix(imported, prefix)
                    for prefix in DOMAIN_FORBIDDEN_PREFIXES
                ):
                    violations.append(
                        f"domain boundary violation: {module} imports {imported}"
                    )

        if _matches_prefix(module, "fossil_core.application"):
            for imported in sorted(internal_imports):
                if any(
                    _matches_prefix(imported, prefix)
                    for prefix in APPLICATION_FORBIDDEN_PREFIXES
                ):
                    violations.append(
                        f"application boundary violation: {module} imports {imported}"
                    )

        if _matches_prefix(module, "fossil_core.ports"):
            for imported in sorted(internal_imports):
                if any(
                    _matches_prefix(imported, prefix)
                    for prefix in PORT_FORBIDDEN_PREFIXES
                ):
                    violations.append(
                        f"ports boundary violation: {module} imports {imported}"
                    )

        for adapter_prefix, forbidden_shims in ADAPTER_SELF_SHIMS.items():
            if not _matches_prefix(module, adapter_prefix):
                continue
            for imported in sorted(internal_imports):
                if any(
                    _matches_prefix(imported, shim) for shim in forbidden_shims
                ):
                    violations.append(
                        f"adapter compatibility-cycle risk: {module} imports {imported}"
                    )

    for component in _strongly_connected_components(_edges(payload)):
        violations.append(
            "first-party import cycle: " + " -> ".join(component)
        )

    return sorted(set(violations))


def check(repo_root: Path) -> list[str]:
    return violations(inventory(repo_root))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail closed on established FOSSIL package-boundary drift."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (defaults to the parent of scripts/)",
    )
    args = parser.parse_args()

    problems = check(args.repo_root.resolve())
    if problems:
        print("Architecture boundary check FAILED:")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print("Architecture boundary check PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
