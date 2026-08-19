from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "contracts/properties/property-catalog-v1.schema.json"
CATALOG_PATH = ROOT / "contracts/properties/fossil-properties-v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _repo_path(ref: str) -> Path:
    return ROOT / ref.split("::", 1)[0]


def test_property_catalog_schema_and_instance_validate() -> None:
    schema = _load(SCHEMA_PATH)
    catalog = _load(CATALOG_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(catalog)


def test_property_catalog_is_unique_sorted_and_grounded_in_public_oracles() -> None:
    catalog = _load(CATALOG_PATH)
    properties = catalog["properties"]
    property_ids = [item["property_id"] for item in properties]

    assert property_ids == sorted(property_ids)
    assert len(property_ids) == len(set(property_ids))

    for item in properties:
        if item["status"] == "active" and item["criticality"] in {"critical", "high"}:
            assert item["deterministic_oracles"], item["property_id"]

        for field in (
            "modules",
            "deterministic_oracles",
            "property_oracles",
            "mutation_scope",
            "source_refs",
        ):
            for ref in item[field]:
                assert _repo_path(ref).exists(), f"{item['property_id']}: missing {field} ref {ref}"

        # Phase 4 TLA+ references are executable traceability links: every ref
        # names both a checked spec file and a concrete model operator/invariant.
        for ref in item["tla_refs"]:
            assert ref.startswith("formal/tla/"), f"{item['property_id']}: invalid TLA+ ref {ref}"
            path_ref, separator, symbol = ref.partition("::")
            assert separator and symbol, f"{item['property_id']}: TLA+ ref must name a symbol: {ref}"
            path = ROOT / path_ref
            assert path.exists(), f"{item['property_id']}: missing TLA+ spec {path_ref}"
            spec = path.read_text(encoding="utf-8")
            assert f"{symbol} ==" in spec, f"{item['property_id']}: missing TLA+ symbol {symbol} in {path_ref}"

        # Landed Phase 5 Lean references are executable traceability links too.
        # Bare refs remain valid only for genuinely future theorem files whose
        # semantic law is intentionally deferred (for example Promotion while
        # #111 remains unresolved, or the optional Identity proof).
        for ref in item["lean_refs"]:
            assert ref.startswith("formal/lean/"), f"{item['property_id']}: invalid Lean ref {ref}"
            path_ref, separator, theorem = ref.partition("::")
            path = ROOT / path_ref
            if separator:
                assert theorem, f"{item['property_id']}: Lean ref must name a theorem: {ref}"
                assert path.exists(), f"{item['property_id']}: missing Lean file {path_ref}"
                source = path.read_text(encoding="utf-8")
                assert f"theorem {theorem}" in source, (
                    f"{item['property_id']}: missing Lean theorem {theorem} in {path_ref}"
                )
            else:
                assert not path.exists(), (
                    f"{item['property_id']}: landed Lean ref must name a theorem: {ref}"
                )

        # Hidden acceptance cases remain outside this public repository. The
        # catalog records only whether sealed acceptance is required.
        if item["hidden_acceptance_required"]:
            assert not any(
                "hidden" in ref.lower() or "holdout" in ref.lower()
                for ref in [*item["deterministic_oracles"], *item["property_oracles"]]
            )
