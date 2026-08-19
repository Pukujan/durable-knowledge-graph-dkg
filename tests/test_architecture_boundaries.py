from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import check_architecture_boundaries as boundaries  # noqa: E402
from architecture_inventory import inventory  # noqa: E402


def _synthetic_clean_payload() -> dict:
    modules = {
        module: {"path": f"src/{module.replace('.', '/')}.py", "internal_imports": []}
        for module in boundaries.CANONICAL_MODULES
    }
    for module, expected in boundaries.COMPATIBILITY_IMPORTS.items():
        modules[module] = {
            "path": f"src/{module.replace('.', '/')}.py",
            "internal_imports": sorted(expected),
        }
    return {
        "schema": "fossil.architecture-inventory.v1",
        "package": "fossil_core",
        "declared_public_api": [],
        "modules": modules,
        "internal_import_edges": [
            {"from": source, "to": target}
            for source, expected in sorted(boundaries.COMPATIBILITY_IMPORTS.items())
            for target in sorted(expected)
        ],
    }


def test_current_repository_satisfies_enforced_boundaries():
    assert boundaries.check(ROOT) == []


def test_edges_ignore_imports_with_unknown_endpoints():
    payload = _synthetic_clean_payload()
    known = "fossil_core.ports.artifact_store"
    unknown = "fossil_core.not_a_real_module"
    payload["internal_import_edges"].extend(
        [
            {"from": known, "to": unknown},
            {"from": unknown, "to": known},
        ]
    )

    graph = boundaries._edges(payload)

    assert unknown not in graph
    assert unknown not in graph[known]


def test_missing_canonical_module_reports_exact_module():
    payload = _synthetic_clean_payload()
    missing = "fossil_core.domain.provenance"
    payload["modules"].pop(missing)

    problems = boundaries.violations(payload)

    assert f"missing canonical architecture module: {missing}" in problems


def test_all_missing_compatibility_modules_are_reported():
    payload = _synthetic_clean_payload()
    missing = ["fossil_core.event_store", "fossil_core.ids"]
    for module in missing:
        payload["modules"].pop(module)

    problems = boundaries.violations(payload)

    assert {f"missing compatibility module: {module}" for module in missing}.issubset(
        problems
    )


def test_domain_cannot_depend_on_ports_or_concrete_adapters():
    payload = _synthetic_clean_payload()
    payload["modules"]["fossil_core.domain.lifecycle"]["internal_imports"] = [
        "fossil_core.ports",
        "fossil_core.adapters.s3",
    ]

    problems = boundaries.violations(payload)

    assert sum("domain boundary violation" in problem for problem in problems) == 2


def test_application_cannot_depend_on_concrete_adapters():
    payload = _synthetic_clean_payload()
    payload["modules"]["fossil_core.application.query.lineage"]["internal_imports"] = [
        "fossil_core.adapters.s3"
    ]

    problems = boundaries.violations(payload)

    assert any("application boundary violation" in problem for problem in problems)


def test_ports_cannot_depend_on_concrete_adapters():
    payload = _synthetic_clean_payload()
    payload["modules"]["fossil_core.ports.artifact_store"]["internal_imports"] = [
        "fossil_core.adapters.s3"
    ]

    problems = boundaries.violations(payload)

    assert any("ports boundary violation" in problem for problem in problems)


def test_compatibility_modules_must_remain_thin():
    payload = _synthetic_clean_payload()
    payload["modules"]["fossil_core.s3_storage"]["internal_imports"].append(
        "fossil_core.ids"
    )

    problems = boundaries.violations(payload)

    assert any(
        "compatibility module fossil_core.s3_storage must stay thin" in problem
        for problem in problems
    )


def test_adapter_cannot_import_its_own_legacy_shim():
    payload = _synthetic_clean_payload()
    payload["modules"]["fossil_core.adapters.s3.storage"]["internal_imports"] = [
        "fossil_core.s3_storage"
    ]

    problems = boundaries.violations(payload)

    assert any("adapter compatibility-cycle risk" in problem for problem in problems)


def test_first_party_import_cycles_fail_closed_with_exact_diagnostic():
    payload = deepcopy(_synthetic_clean_payload())
    left = "fossil_core.ports.artifact_store"
    right = "fossil_core.ports.event_store"
    payload["modules"][left]["internal_imports"] = [right]
    payload["modules"][right]["internal_imports"] = [left]
    payload["internal_import_edges"].extend(
        [
            {"from": left, "to": right},
            {"from": right, "to": left},
        ]
    )

    problems = boundaries.violations(payload)

    assert f"first-party import cycle: {left} -> {right}" in problems


def test_main_uses_explicit_repo_root_and_reports_pass(monkeypatch, capsys, tmp_path):
    seen: list[Path] = []
    monkeypatch.setattr(
        sys,
        "argv",
        ["check_architecture_boundaries.py", "--repo-root", str(tmp_path)],
    )
    monkeypatch.setattr(boundaries, "check", lambda root: seen.append(root) or [])

    assert boundaries.main() == 0
    assert seen == [tmp_path.resolve()]
    assert capsys.readouterr().out == "Architecture boundary check PASS\n"


def test_main_uses_checker_parent_as_default_repo_root(monkeypatch, capsys):
    seen: list[Path] = []
    monkeypatch.setattr(sys, "argv", ["check_architecture_boundaries.py"])
    monkeypatch.setattr(boundaries, "check", lambda root: seen.append(root) or [])

    assert boundaries.main() == 0
    assert seen == [Path(boundaries.__file__).resolve().parents[1]]
    assert capsys.readouterr().out == "Architecture boundary check PASS\n"


def test_main_fails_closed_and_reports_each_problem(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(
        sys,
        "argv",
        ["check_architecture_boundaries.py", "--repo-root", str(tmp_path)],
    )
    monkeypatch.setattr(boundaries, "check", lambda root: ["alpha", "beta"])

    assert boundaries.main() == 1
    assert capsys.readouterr().out == (
        "Architecture boundary check FAILED:\n- alpha\n- beta\n"
    )


def test_inventory_remains_the_single_source_of_import_edges():
    payload = inventory(ROOT)

    assert payload["schema"] == "fossil.architecture-inventory.v1"
    assert payload["internal_import_edges"] == sorted(
        payload["internal_import_edges"], key=lambda edge: (edge["from"], edge["to"])
    )
