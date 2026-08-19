from __future__ import annotations

from collections.abc import Callable
from typing import Mapping


CORE_ONTOLOGY_REF = "dkg.core@1.0.0"
EndpointTypeResolver = Callable[[str], str | None]

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
    """Fail closed unless one endpoint-kind pair is legal in the pinned ontology."""

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


def _resolve_endpoint(
    endpoint_ref: str,
    *,
    role: str,
    resolver: EndpointTypeResolver | None,
) -> str:
    if resolver is None:
        raise OntologyConstraintError(
            "accepted relation endpoint identity cannot be resolved without an endpoint type resolver"
        )
    try:
        endpoint_type = resolver(endpoint_ref)
    except Exception as exc:
        raise OntologyConstraintError(
            f"{role} endpoint identity {endpoint_ref!r} could not be resolved"
        ) from exc
    if not endpoint_type:
        raise OntologyConstraintError(
            f"{role} endpoint identity {endpoint_ref!r} could not be resolved"
        )
    if endpoint_type not in ENTITY_TYPES:
        raise OntologyConstraintError(
            f"{role} endpoint identity {endpoint_ref!r} resolved to unknown entity type {endpoint_type!r}"
        )
    return endpoint_type


def validate_resolved_relation_endpoints(
    *,
    relation_type: str,
    source_ref: str,
    source_type: str,
    target_ref: str,
    target_type: str,
    ontology_ref: str,
    resolver: EndpointTypeResolver | None,
) -> None:
    """Resolve endpoint identities independently, then enforce the ontology pair."""

    resolved_source_type = _resolve_endpoint(source_ref, role="source", resolver=resolver)
    resolved_target_type = _resolve_endpoint(target_ref, role="target", resolver=resolver)
    if source_type != resolved_source_type:
        raise OntologyConstraintError(
            f"source_type {source_type!r} does not match resolved endpoint type {resolved_source_type!r}"
        )
    if target_type != resolved_target_type:
        raise OntologyConstraintError(
            f"target_type {target_type!r} does not match resolved endpoint type {resolved_target_type!r}"
        )
    validate_relation_endpoints(
        relation_type=relation_type,
        source_type=resolved_source_type,
        target_type=resolved_target_type,
        ontology_ref=ontology_ref,
    )


__all__ = [
    "CORE_ONTOLOGY_REF",
    "ENTITY_TYPES",
    "EndpointTypeResolver",
    "RELATION_ENDPOINT_TYPES",
    "RELATION_TYPES",
    "OntologyConstraintError",
    "validate_relation_endpoints",
    "validate_resolved_relation_endpoints",
]
