from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

CLAIM_STATES = frozenset({"proposed", "open", "supported", "disputed", "rejected", "superseded", "retracted", "stale_pending_review"})
RELATION_STATES = frozenset({"proposed", "active", "disputed", "superseded", "invalidated"})


class LifecycleError(ValueError):
    pass


@dataclass
class RelationRecord:
    relation_id: str
    relation_type: str
    source_ref: str
    target_ref: str
    state: str = "proposed"


@dataclass
class KnowledgeState:
    """Deterministic in-memory projection of lifecycle events."""

    claims: dict[str, str] = field(default_factory=dict)
    relations: dict[str, RelationRecord] = field(default_factory=dict)

    def apply(self, event: dict[str, Any]) -> None:
        kind = event["event_type"]
        payload = event["payload"]
        subject = event["subject_refs"][0]

        if kind == "claim.proposed":
            if subject in self.claims:
                raise LifecycleError(f"claim already exists: {subject}")
            self.claims[subject] = "proposed"
            return

        if kind == "claim.state_changed":
            self.change_claim(subject, payload["to_state"], payload.get("from_state"))
            return

        if kind == "claim.superseded":
            self.change_claim(subject, "superseded", payload.get("from_state"))
            self.mark_dependents_stale(subject)
            return

        if kind == "relation.proposed":
            relation_id = payload["relation_id"]
            if relation_id in self.relations:
                raise LifecycleError(f"relation already exists: {relation_id}")
            state = payload.get("state", "proposed")
            if state not in RELATION_STATES:
                raise LifecycleError(f"invalid relation state: {state}")
            self.relations[relation_id] = RelationRecord(
                relation_id=relation_id,
                relation_type=payload["relation_type"],
                source_ref=payload["source_ref"],
                target_ref=payload["target_ref"],
                state=state,
            )
            return

        if kind == "relation.state_changed":
            relation = self.relations[payload["relation_id"]]
            expected = payload.get("from_state")
            if expected is not None and relation.state != expected:
                raise LifecycleError("relation from_state does not match current state")
            target = payload["to_state"]
            if target not in RELATION_STATES:
                raise LifecycleError(f"invalid relation state: {target}")
            relation.state = target

    def change_claim(self, claim_id: str, target: str, expected: str | None = None) -> None:
        if claim_id not in self.claims:
            raise LifecycleError(f"unknown claim: {claim_id}")
        if target not in CLAIM_STATES:
            raise LifecycleError(f"invalid claim state: {target}")
        if expected is not None and self.claims[claim_id] != expected:
            raise LifecycleError("claim from_state does not match current state")
        self.claims[claim_id] = target

    def mark_dependents_stale(self, premise_id: str) -> None:
        terminal = {"superseded", "retracted", "rejected"}
        for relation in self.relations.values():
            if relation.relation_type != "DEPENDS_ON" or relation.state != "active":
                continue
            if relation.target_ref != premise_id or relation.source_ref not in self.claims:
                continue
            if self.claims[relation.source_ref] not in terminal:
                self.claims[relation.source_ref] = "stale_pending_review"
