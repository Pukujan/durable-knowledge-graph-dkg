# Issue #111 Semantic Freeze Proposal

**Status:** owner-approved proposal for review, 2026-08-19
**Authority:** [FOSSIL issue #111](https://github.com/Pukujan/fossil-core/issues/111), under the current architecture boundary in [issue #86](https://github.com/Pukujan/fossil-core/issues/86)
**Related assurance:** [issue #176](https://github.com/Pukujan/fossil-core/issues/176)

## Purpose

This document turns the semantic portions of #111 into a bounded, reviewable
freeze candidate. It freezes laws and sequencing; it does not claim that the
implementation work is complete.

The proposal covers:

1. semantic commit enforcement;
2. reproducible mounted-pack sets;
3. provenance-preserving cross-pack promotion; and
4. the boundary for reviewed evidence ingestion.

Longitudinal benchmarking remains a separately implemented proof campaign.
Private holdout execution remains outside this repository and is not changed
by this proposal.

## Non-goals and boundaries

- No database, graph, vector-index, or storage-provider rewrite.
- No change to the durable-truth rule: immutable evidence and validated events
  remain authoritative; projections remain rebuildable.
- No silent alteration of existing event identity, redaction, lifecycle, or
  source-citation semantics.
- No production promotion authorization.
- No public sealed cases, private oracles, credentials, private locations, or
  verifier identities.
- No claim that Lean proves the Python implementation. Formal models and
  conformance tests remain separate evidence layers under #176.

## Proposed frozen laws

### 1. Proposal and accepted-commit states are different

An agent or importer may produce a cheap proposal, but a proposal is not
accepted durable knowledge merely because it is syntactically valid or has
been projected into a graph or index.

An accepted commit must pass all applicable deterministic gates before the
durable event is written:

- event envelope and event-type payload validation;
- pack read/write authorization;
- actor and provenance continuity;
- evidence/reference policy for the event type and risk tier; and
- ontology constraints for entity and relation payloads.

Unknown consequential event types may be preserved as explicitly proposal-only
material, but cannot enter the accepted knowledge path until their contract and
policy are registered. A transport success, model agreement, retrieval score,
or projection success cannot substitute for these gates.

### 2. Event-type contracts are explicit and fail closed

Every consequential event type has a versioned payload contract and an
associated evidence policy. The registry is the source for validation; callers
must not rely on scattered hard-coded required-field lists.

The registry must make it possible to answer mechanically:

- which payload schema applies;
- whether an event is proposal-only or eligible for accepted commit;
- which evidence or source references are required;
- which provenance fields are required;
- which ontology entity/relation constraints apply; and
- which property IDs and tests are the executable oracle.

Existing `dkg.event.v1` envelope compatibility remains intact. Adding the
registry is an acceptance gate around the envelope, not permission to change
historical event identity or silently reinterpret old events.

### 3. Ontology definitions own relation endpoint validity

For relation events, the declared relation type is resolved from the pinned
ontology version. The source and target entities must satisfy that relation's
declared endpoint kinds. Lifecycle relation sets must not drift independently
between ontology files, domain code, and projection adapters.

If the required ontology definition or endpoint identity cannot be resolved,
the accepted commit fails closed. The event may remain a proposal requiring
resolution; it must not be accepted by falling back to a permissive generic
relation.

### 4. A mounted pack set is an exact, portable revision set

`pack_id` is the stable logical identity. A mounted pack set additionally has
an exact immutable revision for each mounted pack. Physical repository,
database, graph namespace, bucket, and filesystem paths are not pack identity.

The proposed `dkg.packset-lock.v1` representation is canonical JSON with:

- a contract version;
- one record per mounted `pack_id`, sorted by `pack_id`;
- an opaque immutable `revision` for each pack;
- a manifest/content digest sufficient to detect manifest drift; and
- the resolved dependency edges, including required versus optional status.

The lock digest is computed from the canonical lock content; it is not a
self-referential field inside that content. A lock is invalid when it has
duplicate pack IDs, duplicate revisions for one pack, missing required
dependencies, unresolved referenced packs, or dependency metadata that differs
from the validated manifests.

The default dependency layering is **common -> domain -> project**: a domain
may depend on common, and a project may depend on domain/common. No dependency
edge may point downstream or create a cycle. Personal and experimental packs
may exist, but they do not weaken cycle detection or exact-revision locking.

The existing query-receipt rule that every mounted pack has one non-empty exact
revision is the compatible observability surface. A query receipt is evidence
of what ran; the packset lock is the portable semantic input that can be
replayed.

### 5. Promotion pins source meaning without mutating the source

Promotion is an explicit new event in the target pack. It never edits or
rewrites the source pack.

For a newly accepted promotion, the target event must durably retain:

- the source `pack_id`;
- the exact source pack `revision` from the mounted pack set;
- the stable source `event_id` containing the promoted knowledge;
- the target `pack_id`, which must equal the event's durable `pack_id`;
- the stable subject references; and
- evidence and review/provenance references explaining acceptance.

The source event must be resolvable at the pinned source revision when the
promotion is accepted. If it is missing, redacted, or otherwise not resolvable,
the promotion fails closed rather than creating a dangling target meaning.
Historical promotions without the new source pin remain historical data; they
must not be treated as proof that a new promotion is safe. New accepted
promotions use the pinned form after its versioned payload contract lands.

Promotion therefore preserves both portability and provenance: a target pack
can explain exactly which source revision and source event caused the new
knowledge, while the source remains unchanged.

### 6. Reviewed evidence ingestion is provenance-first

The reviewed-ingest boundary is:

1. preserve source bytes/artifacts first when available;
2. keep source evidence separate from derived synthesis;
3. emit proposed knowledge by default;
4. validate the pack, event, provenance, evidence, and ontology contracts;
5. require explicit review/promotion for accepted architecture or shared-domain
   knowledge;
6. exclude raw CI/log noise from wholesale ingestion; and
7. emit a compact validation/ingestion receipt.

An ingest receipt records what was validated and what was proposed or accepted;
it does not turn a receipt, summary, model output, or projection into evidence.

## Implementation sequence after semantic acceptance

The smallest safe implementation order is:

1. add the event-type contract/evidence-policy registry and deterministic
   commit-gate oracles;
2. add `dkg.packset-lock.v1`, cycle detection, layer validation, and replay/
   portability tests;
3. version the promotion payload with the source revision/event pin and add
   source-resolvability tests;
4. build the longitudinal benchmark against the frozen laws; and
5. implement reviewed evidence ingestion and its compact receipt.

Promotion mutation testing and Lean proof work begin only after the promotion
law above is accepted and implemented. #176 may test these laws, but it must
not weaken them or publish private holdout material.

## Acceptance criteria for this freeze proposal

The semantic freeze is ready for acceptance when reviewers agree that:

- the six laws above are the intended current authority for #111;
- the implementation sequence does not authorize a database rewrite or
  production promotion;
- the exact pack revision and source-event pin are sufficient to prevent
  dangling promotion meaning;
- old events remain replayable without being silently upgraded; and
- the remaining #111 checkboxes are implementation/evidence work against
  these laws, not unresolved semantic alternatives.

After acceptance, implementation PRs should reference the affected
`FOSSIL-PROP-*` IDs and state whether each law is preserved, strengthened, or
changed. A changed law requires a new reviewed decision rather than a silent
contract drift.
