from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

PACKAGE = "fossil_core"


def _module_name(path: Path, source_root: Path) -> str:
    relative = path.relative_to(source_root)
    parts = list(relative.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _package_for(module: str, path: Path) -> str:
    if path.name == "__init__.py":
        return module
    return module.rpartition(".")[0]


def _resolve_from(module: str | None, level: int, package: str) -> str | None:
    if level == 0:
        return module

    package_parts = package.split(".") if package else []
    trim = level - 1
    if trim > len(package_parts):
        return None
    base = package_parts[: len(package_parts) - trim]
    if module:
        base.extend(module.split("."))
    return ".".join(base)


def _declared_exports(init_path: Path) -> list[str]:
    tree = ast.parse(init_path.read_text(encoding="utf-8"), filename=str(init_path))
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and target.id == "__all__" for target in targets):
            continue
        value = node.value
        if value is None:
            break
        exports = ast.literal_eval(value)
        if not isinstance(exports, (list, tuple)) or not all(
            isinstance(item, str) for item in exports
        ):
            raise ValueError("fossil_core.__all__ must be a literal list/tuple of strings")
        return list(exports)
    return []


def inventory(repo_root: Path) -> dict[str, Any]:
    source_root = repo_root / "src"
    package_root = source_root / PACKAGE
    if not package_root.is_dir():
        raise FileNotFoundError(f"missing package root: {package_root}")

    modules: dict[str, dict[str, Any]] = {}
    edges: set[tuple[str, str]] = set()

    for path in sorted(package_root.rglob("*.py")):
        module = _module_name(path, source_root)
        package = _package_for(module, path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == PACKAGE or alias.name.startswith(f"{PACKAGE}."):
                        imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                resolved = _resolve_from(node.module, node.level, package)
                if resolved and (
                    resolved == PACKAGE or resolved.startswith(f"{PACKAGE}.")
                ):
                    imports.add(resolved)

        for imported in imports:
            edges.add((module, imported))

        modules[module] = {
            "path": path.relative_to(repo_root).as_posix(),
            "internal_imports": sorted(imports),
        }

    declared_public_api = _declared_exports(package_root / "__init__.py")
    return {
        "schema": "fossil.architecture-inventory.v1",
        "package": PACKAGE,
        "declared_public_api": declared_public_api,
        "modules": dict(sorted(modules.items())),
        "internal_import_edges": [
            {"from": source, "to": target} for source, target in sorted(edges)
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit a deterministic, import-free inventory of fossil_core."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (defaults to the parent of scripts/)",
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    payload = inventory(args.repo_root.resolve())
    if args.pretty:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
