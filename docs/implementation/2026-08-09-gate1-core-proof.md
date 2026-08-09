# Gate 1 Core Proof — Event, Artifact, and Pack Boundaries

Date: 2026-08-09

This checkpoint records the first implementation proof after the research freeze. It is intended to become ingestible project provenance later, not merely a release note.

> **Later status note:** the `Still not proven` section below records what was genuinely unproven **at the time of this checkpoint**. It is preserved as historical project evidence rather than rewritten. Later durable checkpoints supersede that status: claim/relation lifecycle work completed in Issue #6, live Graphiti/Neo4j proof is recorded in `docs/implementation/2026-08-09-gate1-live-graphiti-proof.md`, and destructive rebuild/blue-green proof is recorded in `docs/implementation/2026-08-09-gate1-rebuild-blue-green-proof.md`. Conversation lineage (#9) remains the active next gate at the time of this note.

## What changed

- Added an atomic immutable-file publication primitive. Data is written and fsynced to a temporary file, then published without replacing an existing durable path.
- Hardened the durable event store so an idempotency key deterministically fixes the event identity. A caller cannot reuse an idempotency key while supplying a different event ID.
- Added a content-addressed artifact store using SHA-256 blobs and immutable manifests. Artifact integrity can be re-verified from bytes.
- Added explicit pack read/write boundary objects and validation of required pack dependencies.
- Added explicit cross-pack promotion events. Promotion creates a new event in the target pack and points back to the source pack rather than mutating shared knowledge silently.

## Why

These changes directly implement the durable architecture invariants: evidence exists independently of projections, retrying agents cannot silently fork history, shared/domain/project libraries have explicit logical boundaries, and moving knowledge upward is a provenance-preserving action.

## Verification performed

The implementation was reconstructed in an isolated local test fixture and exercised with tests for:

- idempotent retries;
- conflicting retry identity;
- malformed event rejection;
- content-addressed artifact retry;
- artifact tamper detection;
- pack read/write gates;
- missing required pack dependencies;
- explicit promotion provenance.

The local fixture passed all exercised checks before the corresponding repository changes were committed. GitHub-hosted CI should remain the independent repository-level check; this document does not claim a remote CI result unless one is separately observed.

## Still not proven

The following list is intentionally historical: these items were not yet proven when this checkpoint was written.

- Claim/relation lifecycle replay and stale-dependency propagation (#6).
- Graphiti/Neo4j projection behavior (#4).
- Destructive rebuild and blue/green migration (#5).
- Conversation lineage reconstruction (#9).
- Agent Skills/API/MCP layer (#8).

## Trace links

- Issue #2 — durable event + artifact store.
- Issue #3 — knowledge-pack boundaries and promotion.
- Architecture contract — `ARCHITECTURE.md`.
- Research trace contract — `docs/research/RESEARCH_TRACE_CONTRACT.md`.

This proof is deliberately written as project evidence so the future knowledge graph can answer not only *what the current system does*, but *which engineering evidence caused the project state to advance*.
