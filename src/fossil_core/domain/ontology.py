from __future__ import annotations

from typing import Mapping


CORE_ONTOLOGY_REF = "dkg.core@1.0.0"

ENTITY_TYPES = frozenset(
    {
        "Artifact",
        "Episode",
        "Source",
        "Evidence",
        "Claim",
        "Assumption",
        "Argument",
        "Observation",
        "Experiment",
        "Decision",
        "Question",
        "Concept",
        "Methodology",
    }
)

# Runtime snapshot of ontology/core/v1.yaml. The canonical YAML remains the
# authoring source; tests/test_ontology_contracts.py requires this snapshot to
# match it exactly so lifecycle/commit code cannot drift independently.
RELATION_ENDPOINT_TYPES: Mapping[str, Mapping[str, frozenset[str]]] = {
    "SUPPORTS": {
        "source_types": frozenset({"Evidence", "Claim", "Observation", "Experiment"}),
        "target_types": frozenset({"Claim", "Assumption", "Decision"}),
    },
    "CHALLENGES": {
        "source_types": frozenset({"Evidence", "Claim", "Observation", "Argument"}),
        "target_types": frozenset({"Claim", "Assumption", "Decision"}),
    },
    "CONTRADICTS": {
        "source_types": frozenset({"Claim", "Evidence", "Observation"}),
        "target_types": frozenset({"Claim", "Assumption"}),
    },
    "REFINES": {
        "source_types": frozenset({"Claim", "Concept", "Methodology"}),
        "target_types": frozenset({"Claim", "Concept", "Methodology"}),
    },
    "DEPENDS_ON": {
        "source_types": frozenset({"Claim", "Decision", "Argument", "Methodology"}),
        "target_types": frozenset({"Claim", "Assumption", "Concept", "Source"}),
    },
    "ASSUMES": {
        "source_types": frozenset({"Claim", "Argument", "Decision", "Methodology"}),
        "target_types": frozenset({"Assumption", "Claim"}),
    },
    "DERIVED_FROM": {
        "source_types": frozenset({"Claim", "Concept", "Decision", "Evidence", "Methodology"}),
        "target_types": frozenset(
            {"Artifact", "Episode", "Source", "Evidence", "Claim", "Observation"}
        ),
    },
    "EXEMPLIFIES": {
        "source_types": frozenset({"Observation", "Evidence", "Episode"}),
        "target_types": frozenset({"Claim", "Concept", "Methodology"}),
    },
    "SUPERSEDES": {
        "source_types": frozenset({"Claim", "Concept", "Decision", "Methodology"}),
        "target_types": frozenset({"Claim", "Concept", "Decision", "Methodology"}),
    },
    "RELATED_TO": {
        "source_types": frozenset({"Claim", "Concept", "Source", "Methodology"}),
        "target_types": frozenset({"Claim", "Concept", "Source", "Methodology"}),
    },
    "BROADER_THAN": {
        "source_types": frozenset({"Concept"}),
        "target_types": frozenset({"Concept"}),
    },
    "NARROWER_THAN": {
        "source_types": frozenset({"Concept"}),
        "target_types": frozenset({"Concept"}),
    },
}

RELATION_TYPES = frozenset(RELATION_ENDPOINT_TYPES)


class OntologyConstraintError(ValueError):
    """A relation cannot satisfy the pinned ontology endpoint contract."""


def validate_relation_endpoints(
    *,
    relation_type: str,
    source_type: str,
    target_type: str,
    ontology_ref: str,
) -> None:
    """Fail closed unless one endpoint pair is legal in the pinned core ontology."""

    if ontology_ref != CORE_ONTOLOGY_REF:
        raise OntologyConstraintError(
            f"ontology_ref must resolve exactly to {CORE_ONTOLOGY_REF}; got {ontology_ref!r}"
        )

    try:
        constraints = RELATION_ENDPOINT_TYPES[relation_type]
    except KeyError as exc:
        raise OntologyConstraintError(
            f"unregistered relation type in {CORE_ONTOLOGY_REF}: {relation_type}"
        ) from exc

    if source_type not in constraints["source_types"]:
        raise OntologyConstraintError(
            f"source_type {source_type!r} is not valid for relation type {relation_type}"
        )
    if target_type not in constraints["target_types"]:
        raise OntologyConstraintError(
            f"target_type {target_type!r} is not valid for relation type {relation_type}"
        )


__all__ = [
    "CORE_ONTOLOGY_REF",
    "ENTITY_TYPES",
    "RELATION_ENDPOINT_TYPES",
    "RELATION_TYPES",
    "OntologyConstraintError",
    "validate_relation_endpoints",
]
