from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "architecture_inventory.py"
PUBLIC_API_CONTRACT = ROOT / "contracts" / "python-public-api-v1.json"


def _load_inventory_module():
    spec = importlib.util.spec_from_file_location("architecture_inventory", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_architecture_inventory_is_import_free_and_tracks_storage_seams():
    module = _load_inventory_module()
    payload = module.inventory(ROOT)

    assert payload["schema"] == "fossil.architecture-inventory.v1"
    assert "fossil_core.storage_ports" in payload["modules"]
    assert "fossil_core.s3_storage" in payload["modules"]
    assert "fossil_core.artifact_store" in payload["modules"]
    assert "fossil_core.event_store" in payload["modules"]


def test_declared_package_root_api_matches_versioned_public_contract():
    module = _load_inventory_module()
    payload = module.inventory(ROOT)
    contract = json.loads(PUBLIC_API_CONTRACT.read_text(encoding="utf-8"))

    assert payload["declared_public_api"] == contract["surfaces"]["package_root"][
        "symbols"
    ]


def test_inventory_output_is_deterministic():
    module = _load_inventory_module()
    first = module.inventory(ROOT)
    second = module.inventory(ROOT)

    assert first == second
    assert first["internal_import_edges"] == sorted(
        first["internal_import_edges"], key=lambda edge: (edge["from"], edge["to"])
    )
