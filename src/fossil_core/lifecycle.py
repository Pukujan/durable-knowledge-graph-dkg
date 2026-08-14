from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

CLAIM_STATES = frozenset({
    "proposed",
    "open",
    "supported",
    "disputed",
    "rejected",
    "superseded",
    "retracted",
    "stale_pending_review",
})
RELATION_STATES = frozenset({"proposed", "active", "disputed", "superseded", "invalidated"})
RELATION_TYPES = frozenset({
    "SUPPORTS",
    "CHALLENGES",
    "CONTRADICTS",
    "REFINES",
    "DEPENDS_ON",
    "ASSUMES",
    "DERIVED_FROM",
    "EXEMPLIFIES",
    "SUPERSEDES",
    "RELATED_TO",
    "BROADER_THAN",
    "NARROWER_THAN",
})


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
    """Deterministic current-state projection built by replaying durable events.

    Histories are retained as state sequences for convenient inspection, while
    the immutable event store remains the authoritative historical record.
    """

    claims: dict[str, str] = field(default_factory=dict)
    claim_history: dict[str, list[str]] = field(default_factory=dict)
    relations: dict[str, RelationRecord] = field(default_factory=dict)
    relation_history: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def replay(cls, events: Iterable[dict[str, Any]]) -> "KnowledgeState":
        state = cls()
        for event in events:
            state.apply(event)
        return state

    def apply(self, event: dict[str, Any]) -> None:
        kind = event["event_type"]
        payload = event["payload"]
        subject = event["subject_refs"][0]

        if kind == "claim.proposed":
            if subject in self.claims:
                raise LifecycleError(f"claim already exists: {subject}")
            self.claims[subject] = "proposed"
            self.claim_history[subject] = ["proposed"]
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
            relation_type = payload["relation_type"]
            if relation_type not in RELATION_TYPES:
                raise LifecycleError(f"invalid relation type: {relation_type}")
            state = payload.get("state", "proposed")
            if state not in RELATION_STATES:
                raise LifecycleError(f"invalid relation state: {state}")
            self.relations[relation_id] = RelationRecord(
                relation_id=relation_id,
                relation_type=relation_type,
                source_ref=payload["source_ref"],
                target_ref=payload["target_ref"],
                state=state,
            )
            self.relation_history[relation_id] = [state]
            return

        if kind in {"relation.state_changed", "relation.superseded"}:
            relation = self.relations[payload["relation_id"]]
            expected = payload.get("from_state")
            if expected is not None and relation.state != expected:
                raise LifecycleError("relation from_state does not match current state")
            target = "superseded" if kind == "relation.superseded" else payload["to_state"]
            if target not in RELATION_STATES:
                raise LifecycleError(f"invalid relation state: {target}")
            relation.state = target
            self.relation_history[relation.relation_id].append(target)

    def change_claim(self, claim_id: str, target: str, expected: str | None = None) -> None:
        if claim_id not in self.claims:
            raise LifecycleError(f"unknown claim: {claim_id}")
        if target not in CLAIM_STATES:
            raise LifecycleError(f"invalid claim state: {target}")
        if expected is not None and self.claims[claim_id] != expected:
            raise LifecycleError("claim from_state does not match current state")
        self.claims[claim_id] = target
        self.claim_history[claim_id].append(target)

    def mark_dependents_stale(self, premise_id: str) -> None:
        terminal = {"superseded", "retracted", "rejected"}
        for relation in self.relations.values():
            if relation.relation_type != "DEPENDS_ON" or relation.state != "active":
                continue
            if relation.target_ref != premise_id or relation.source_ref not in self.claims:
                continue
            if self.claims[relation.source_ref] not in terminal:
                self.change_claim(relation.source_ref, "stale_pending_review")
