from __future__ import annotations

import importlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts" / "python-public-api-v1.json"


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _resolve_symbol(path: str):
    module_name, symbol = path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, symbol)


def test_supported_surfaces_match_declared_exports():
    contract = _contract()

    assert contract["schema"] == "fossil.python-public-api.v1"
    for surface in contract["surfaces"].values():
        module = importlib.import_module(surface["module"])
        symbols = surface["symbols"]

        assert len(symbols) == len(set(symbols))
        assert module.__all__ == symbols
        for symbol in symbols:
            assert getattr(module, symbol) is not None


def test_compatibility_modules_preserve_identity_and_star_exports():
    contract = _contract()

    for module_name, compatibility in contract["compatibility_modules"].items():
        legacy = importlib.import_module(module_name)
        replacement = importlib.import_module(compatibility["replacement"])

        assert legacy.__all__ == compatibility["star_exported_symbols"]
        for symbol in compatibility["symbols"]:
            assert getattr(legacy, symbol) is getattr(replacement, symbol)


def test_explicit_root_aliases_preserve_canonical_object_identity():
    contract = _contract()

    for alias in contract["identity_aliases"]:
        assert _resolve_symbol(alias["source"]) is _resolve_symbol(alias["target"])


def test_contract_policy_keeps_compatibility_non_behavioral():
    policy = _contract()["policy"]

    assert policy == {
        "unlisted_modules": "internal_until_explicitly_promoted",
        "compatibility_modules": "temporary_until_explicit_cleanup_phase",
        "runtime_deprecation_warnings": False,
    }
