# Current Handoff

**Date:** 2026-08-09  
**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Repository:** `Pukujan/fossil-core`  
**Status:** durable core, pack boundaries, lifecycle, live Graphiti/Neo4j, destructive rebuild/blue-green, and conversation lineage are complete. Issue #8 safe agent-facing boundary is active.

## Repository family

- `fossil-core` — architecture/contracts/core/projections/control plane;
- `fossil-common` — stable pack `pack_269099f7b2ba43b7a99b9427d64092de`;
- `fossil-ai-systems` — stable pack `pack_f024177f89a5442db84171c3dd7f58e5`, depending on common.

Repository/database/graph placement is not pack identity.

## Fresh-session order

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/PROJECT_STATE.md`
4. this file
5. `docs/DECISION_LOG.md`
6. `docs/implementation/2026-08-09-gate1-live-graphiti-proof.md`
7. `docs/implementation/2026-08-09-gate1-rebuild-blue-green-proof.md`
8. `docs/implementation/2026-08-09-gate1-conversation-lineage-proof.md`
9. Issue #1 and active Issue #8

The chat UI is source material, not the control plane.

## Frozen architecture

Canonical truth is immutable evidence + stable corpus IDs + append-only validated knowledge events + versioned pack/ontology contracts + provenance/history. Graphiti/Neo4j, vector indexes, models, Skills, MCP, retrieval strategies, and future databases are replaceable projections/services.

A graph deletion must never delete irreplaceable intellectual history.

## Completed gates

### #2 durable event/artifact store
Atomic immutable publication, deterministic idempotency, content-addressed artifacts, integrity checks.

### #3 pack boundaries/promotion
Explicit read/write boundaries and dependencies; promotion creates new provenance-preserving events.

### #6 lifecycle
Claims/relations preserve disagreement, disputed state, supersession, and stale dependency propagation.

### #4 live Graphiti/Neo4j
Trusted CI run #70 (`31338875226`, job `93309155019`) proved real Graphiti `0.29.3` + Neo4j `5.26.29`, stable pack/group namespace, durable-first materialization, build metadata, and idempotent replay. `json_schema` is the proven local structured-output mode. Evidence: `docs/implementation/2026-08-09-gate1-live-graphiti-proof.md`.

### #5 destructive rebuild + blue/green
Trusted live run #81 (`31339930551`, job `93311926075`) proved a candidate graph can be destroyed to zero nodes, rebuilt from the same durable event source using a fresh projection-build ledger, coexist beside the current projection, compare by stable semantic invariants, and become active only after checks pass. Final guardrails passed run #84. Evidence: `docs/implementation/2026-08-09-gate1-rebuild-blue-green-proof.md`.

Critical invariant: a physically new projection gets a fresh build identity/applied ledger; otherwise stale `already applied` records can suppress a rebuild.

### #9 conversation ingestion + intellectual lineage
Trusted CI run #97 (`31340924480`, job `93314435997`) passed 31 tests. The corpus now preserves immutable conversation source artifacts, byte spans, stable message/parent ordering, actor metadata, durable `verbatim` vs `reconstructed` status, derived lineage with exact source provenance, opposing positions, current conclusions, and historical paths.

Recovered benchmark path:

`learning UX / parabola -> representation mismatch -> AI translation layer -> failure learning -> MAPE-K / KEDB -> truth maintenance -> temporal knowledge graph`

The recovery source is explicitly **reconstructed, not a verbatim transcript**. Never silently upgrade it. If primary transcript evidence appears later, ingest it separately as verbatim evidence. Evidence: `docs/implementation/2026-08-09-gate1-conversation-lineage-proof.md`.

## Exact next task — Issue #8

Create the agent-facing layer without coupling durable knowledge to any one agent protocol.

Issue #8 acceptance:

- Skills for corpus search, research ingestion, citation audit, contradiction review, stale-assumption review, knowledge promotion;
- progressive disclosure: methodology loaded only when relevant;
- protocol-independent internal domain service;
- thin external surface around search/read/lineage/propose/validate/commit/manage;
- MCP is an adapter only; Graphiti experimental MCP is not foundational;
- agents cannot perform arbitrary graph mutation through the normal interface;
- proposals carry actor/model/harness/skill provenance.

Implementation rule: an agent-facing mutation must produce/validate/commit canonical durable data first. Projection work is downstream. Do not expose Cypher or graph-native mutation as a normal capability.

## Recent durable decisions

- D018: physical projection builds have separate operational identity and build-scoped ledgers; migration activation uses semantic comparison + append-only switch history.
- D019: conversation evidence status (`verbatim` vs `reconstructed`) is durable provenance; exact verbatim text resolves to immutable byte spans.

## Gate state

13 of the 15 executable Gate 1 checklist items are complete. Remaining:

1. general citation/source-snapshot quality + redaction integrity (#10);
2. safe Agent Skill/API/MCP boundary (#8).

After #8: execute #7 retrieval/model benchmarks while continuing #10 cross-cutting provenance work.

## End-of-session rule

Update this file, `docs/PROJECT_STATE.md`, Issue #1, active child issues, durable benchmark/proof docs, and `docs/DECISION_LOG.md` after substantial changes.
