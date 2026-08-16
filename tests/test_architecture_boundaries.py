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


def test_first_party_import_cycles_fail_closed():
    payload = deepcopy(_synthetic_clean_payload())
    payload["modules"]["fossil_core.ports.artifact_store"]["internal_imports"] = [
        "fossil_core.ports.event_store"
    ]
    payload["modules"]["fossil_core.ports.event_store"]["internal_imports"] = [
        "fossil_core.ports.artifact_store"
    ]
    payload["internal_import_edges"].extend(
        [
            {
                "from": "fossil_core.ports.artifact_store",
                "to": "fossil_core.ports.event_store",
            },
            {
                "from": "fossil_core.ports.event_store",
                "to": "fossil_core.ports.artifact_store",
            },
        ]
    )

    problems = boundaries.violations(payload)

    assert any("first-party import cycle" in problem for problem in problems)


def test_inventory_remains_the_single_source_of_import_edges():
    payload = inventory(ROOT)

    assert payload["schema"] == "fossil.architecture-inventory.v1"
    assert payload["internal_import_edges"] == sorted(
        payload["internal_import_edges"], key=lambda edge: (edge["from"], edge["to"])
    )
