# Project State

**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Durable substrate:** **DICS — Durable Intellectual Corpus System**  
**Current phase:** Gate 1 executable durability proof — 13/15 core checklist items complete; safe Agent Skill/API boundary active  
**Control plane:** GitHub issues + durable repository docs  
**Last updated:** 2026-08-09

## Repository family

- `Pukujan/fossil-core` — architecture, contracts, durable core, projections, control plane;
- `Pukujan/fossil-common` — stable pack `pack_269099f7b2ba43b7a99b9427d64092de`;
- `Pukujan/fossil-ai-systems` — stable pack `pack_f024177f89a5442db84171c3dd7f58e5`, depending on common.

Repository location and graph/database placement are physical details, not knowledge identity.

## Fresh-session continuation

Read:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/HANDOFF_CURRENT.md`
4. this file
5. `docs/DECISION_LOG.md`
6. `docs/implementation/2026-08-09-gate1-live-graphiti-proof.md`
7. `docs/implementation/2026-08-09-gate1-rebuild-blue-green-proof.md`
8. `docs/implementation/2026-08-09-gate1-conversation-lineage-proof.md`
9. Issue #1 and active Issue #8

The chat UI is not the project record.

## Gate 1 checklist

1. [x] immutable validated events;
2. [x] deterministic invalid/duplicate rejection;
3. [x] content-addressed immutable artifacts;
4. [x] pack boundaries/dependencies;
5. [x] provenance-preserving promotion;
6. [x] claim/relation lifecycle, disagreement, supersession, staleness;
7. [x] replaceable Graphiti adapter;
8. [x] projection retry/failure ledger;
9. [x] projection build metadata;
10. [x] live Graphiti + Neo4j materialization;
11. [x] destructive rebuild from durable data;
12. [x] blue/green candidate comparison and guarded switch;
13. [x] conversation ingestion + intellectual-lineage reconstruction benchmark;
14. [ ] general citation/source-snapshot quality + redaction integrity (#10);
15. [ ] safe Agent Skill/API/MCP boundary (#8).

## Completed proof checkpoints

### #4 — live Graphiti/Neo4j

Trusted CI run #70 (`31338875226`, job `93309155019`) proved Graphiti `0.29.3` + Neo4j `5.26.29`, stable pack/group namespace, durable-first materialization, runtime build metadata, and idempotent replay. Evidence: `docs/implementation/2026-08-09-gate1-live-graphiti-proof.md`.

### #5 — destructive rebuild + blue/green

Trusted live run #81 (`31339930551`, job `93311926075`) destroyed the green candidate graph to zero nodes, retained durable event `evt_aadf683e9aa41443f95be71c211cd2c4`, rebuilt green with fresh build ledger `green-rebuild-1`, kept blue live beside it, matched durable/blue/green semantic digest `c8d790b3a1d6741a86e280db44595b463347e6c47a4d933274e1c829696e4696`, and recorded `blue -> green` only after checks passed. Final migration guardrails passed CI run #84: 26 tests. Evidence: `docs/implementation/2026-08-09-gate1-rebuild-blue-green-proof.md`.

### #9 — conversation lineage

Trusted CI run #97 (`31340924480`, job `93314435997`) passed **31 tests in 0.37s**. FOSSIL now has immutable source artifacts + byte spans + conversation envelopes with durable `verbatim`/`reconstructed` evidence status, derived lineage with source-message/span provenance, opposing-position queries, current/historical queries, and the recovered benchmark path:

`learning UX / parabola -> representation mismatch -> AI translation layer -> failure learning -> MAPE-K / KEDB -> truth maintenance -> temporal knowledge graph`

The recovery benchmark remains explicitly reconstructed and is not presented as a verbatim lost transcript. Evidence: `docs/implementation/2026-08-09-gate1-conversation-lineage-proof.md`.

## Current issue map

- #1 milestone/control — open
- #2 durable event + artifact store — **complete**
- #3 pack boundaries/mounts/promotion — **complete**
- #4 Graphiti + Neo4j adapter/queue — **complete**
- #5 destructive rebuild + blue/green — **complete**
- #6 lifecycle/disagreement/supersession/staleness — **complete**
- #7 pluggable retrieval/model services + specialist benchmarks — pending
- #8 Agent Skills + thin corpus API/MCP — **active**
- #9 conversation ingestion + intellectual lineage — **complete**
- #10 source snapshots/citation quality/redaction — cross-cutting/pending

## Active task — Issue #8

Implement the agent-facing boundary without coupling durable knowledge to one agent/protocol:

1. protocol-independent corpus domain service;
2. thin capabilities around search/read/lineage/propose/validate/commit/manage;
3. no arbitrary graph mutation capability;
4. mutation proposals preserve actor/model/harness/skill provenance;
5. durable commit remains authoritative and precedes any projection work;
6. Agent Skills describe lazily loaded methodology/workflows rather than storing truth;
7. initial Skills: corpus search, research ingestion, citation audit, contradiction review, stale-assumption review, knowledge promotion;
8. MCP representation is a thin adapter over the domain service, not a foundational storage contract.

## Frozen invariants added during recent gates

- new physical projection build => fresh build-scoped applied ledger;
- rebuild replay order => `(recorded_at, event_id)`;
- graph-native UUID equality is not a migration requirement;
- active projection switch is append-only and requires passed semantic/benchmark checks;
- reconstructed conversation evidence cannot silently become verbatim evidence;
- verbatim conversation text must resolve exactly to immutable source bytes/spans.

## Execution order after #8

`#8 Skills/API/MCP -> #7 retrieval/model benchmarks`, while completing #10 source-snapshot/citation/redaction work cross-cutting.

## Current implementation evidence

Core: `src/dkg/event_store.py`, `artifact_store.py`, `pack.py`, `promotion.py`, `lifecycle.py`.  
Projection: `src/dkg/projection/graphiti.py`, `ledger.py`, `migration.py`.  
Conversation: `src/dkg/conversation.py`, `schemas/conversation/`, `schemas/conversation-lineage/`, `tests/test_conversation_lineage.py`.  
Proofs: `docs/implementation/2026-08-09-gate1-*.md`.

## End-of-session rule

Update `docs/HANDOFF_CURRENT.md`, this file, Issue #1, active child issue(s), material benchmark evidence, and `docs/DECISION_LOG.md` after substantial changes.
