from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "contracts/properties/property-catalog-v1.schema.json"
CATALOG_PATH = ROOT / "contracts/properties/fossil-properties-v1.json"
LEAN_TOOLCHAIN_PATH = ROOT / "lean-toolchain"
PINNED_LEAN_TOOLCHAIN = "leanprover/lean4:v4.30.0"


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

        # Existing Phase 5 Lean kernels use concrete theorem refs. File-only
        # refs remain valid only for intentionally future formal targets whose
        # source file has not landed yet (for example Promotion while #111 is
        # unresolved and the optional lower-priority Identity proof).
        for ref in item["lean_refs"]:
            assert ref.startswith("formal/lean/"), f"{item['property_id']}: invalid Lean ref {ref}"
            path_ref, separator, theorem = ref.partition("::")
            path = ROOT / path_ref
            if path.exists():
                assert separator and theorem, (
                    f"{item['property_id']}: landed Lean ref must name a theorem: {ref}"
                )
                source = path.read_text(encoding="utf-8")
                assert f"theorem {theorem}" in source, (
                    f"{item['property_id']}: missing Lean theorem {theorem} in {path_ref}"
                )
                assert "Lean 4.30.0" in item.get("notes", ""), (
                    f"{item['property_id']}: landed Lean evidence must record toolchain identity"
                )
            else:
                assert not separator, (
                    f"{item['property_id']}: future Lean ref cannot claim an absent theorem: {ref}"
                )

        # Hidden acceptance cases remain outside this public repository. The
        # catalog records only whether sealed acceptance is required.
        if item["hidden_acceptance_required"]:
            assert not any(
                "hidden" in ref.lower() or "holdout" in ref.lower()
                for ref in [*item["deterministic_oracles"], *item["property_oracles"]]
            )


def test_landed_lean_evidence_uses_pinned_toolchain() -> None:
    assert LEAN_TOOLCHAIN_PATH.read_text(encoding="utf-8").strip() == PINNED_LEAN_TOOLCHAIN
