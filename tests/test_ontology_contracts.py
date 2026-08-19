from __future__ import annotations

import re
from pathlib import Path

import pytest

from fossil_core.domain.lifecycle import RELATION_TYPES
from fossil_core.domain.ontology import (
    CORE_ONTOLOGY_REF,
    ENTITY_TYPES,
    RELATION_ENDPOINT_TYPES,
    OntologyConstraintError,
    validate_relation_endpoints,
)


ROOT = Path(__file__).parents[1]
ONTOLOGY = ROOT / "ontology/core/v1.yaml"


def _inline_list(value: str) -> tuple[str, ...]:
    match = re.fullmatch(r"\[(.*)\]", value.strip())
    assert match is not None
    body = match.group(1).strip()
    return tuple(item.strip() for item in body.split(",") if item.strip())


def _parse_core_ontology(path: Path) -> tuple[str, set[str], dict[str, dict[str, tuple[str, ...]]]]:
    ontology_id = ""
    version = ""
    entity_types: set[str] = set()
    relations: dict[str, dict[str, tuple[str, ...]]] = {}
    section: str | None = None
    relation: str | None = None

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" "):
            relation = None
            if line.startswith("ontology_id:"):
                ontology_id = line.split(":", 1)[1].strip()
                section = None
            elif line.startswith("version:"):
                version = line.split(":", 1)[1].strip()
                section = None
            elif line == "entity_types:":
                section = "entity_types"
            elif line == "relation_types:":
                section = "relation_types"
            else:
                section = None
            continue

        if section == "entity_types" and line.startswith("  ") and not line.startswith("    "):
            entity_types.add(line.strip().removesuffix(":"))
            continue

        if section == "relation_types":
            if line.startswith("  ") and not line.startswith("    "):
                relation = line.strip().removesuffix(":")
                relations[relation] = {}
                continue
            if relation is not None and line.startswith("    "):
                key, value = line.strip().split(":", 1)
                relations[relation][key] = _inline_list(value)

    assert ontology_id and version
    return f"{ontology_id}@{version}", entity_types, relations


def test_runtime_ontology_snapshot_exactly_matches_canonical_yaml():
    ontology_ref, entity_types, relations = _parse_core_ontology(ONTOLOGY)

    assert CORE_ONTOLOGY_REF == ontology_ref
    assert ENTITY_TYPES == frozenset(entity_types)
    assert RELATION_ENDPOINT_TYPES == {
        relation_type: {
            "source_types": frozenset(values["source_types"]),
            "target_types": frozenset(values["target_types"]),
        }
        for relation_type, values in relations.items()
    }
    assert RELATION_TYPES == frozenset(relations)


def test_ontology_endpoint_validator_accepts_declared_pair():
    validate_relation_endpoints(
        relation_type="DEPENDS_ON",
        source_type="Claim",
        target_type="Claim",
        ontology_ref=CORE_ONTOLOGY_REF,
    )


def test_ontology_endpoint_validator_rejects_wrong_pinned_ontology():
    with pytest.raises(OntologyConstraintError, match="ontology_ref"):
        validate_relation_endpoints(
            relation_type="DEPENDS_ON",
            source_type="Claim",
            target_type="Claim",
            ontology_ref="dkg.core@0.9.0",
        )


def test_ontology_endpoint_validator_rejects_invalid_source_kind():
    with pytest.raises(OntologyConstraintError, match="source_type"):
        validate_relation_endpoints(
            relation_type="DEPENDS_ON",
            source_type="Evidence",
            target_type="Claim",
            ontology_ref=CORE_ONTOLOGY_REF,
        )


def test_ontology_endpoint_validator_rejects_unregistered_relation_type():
    with pytest.raises(OntologyConstraintError, match="relation type"):
        validate_relation_endpoints(
            relation_type="MENTIONS",
            source_type="Claim",
            target_type="Claim",
            ontology_ref=CORE_ONTOLOGY_REF,
        )
