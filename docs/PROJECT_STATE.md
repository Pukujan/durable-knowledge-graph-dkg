# FOSSIL Project State

**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Durable substrate:** **DICS — Durable Intellectual Corpus System**  
**Current phase:** **Gate 1 executable durability proof complete (15/15)**  
**Next engineering gate:** **Issue #7 — pluggable retrieval/model services + specialist benchmark contract**  
**Control plane:** GitHub issues + durable repository docs  
**Last updated:** 2026-08-10

## Repository family

- `Pukujan/fossil-core` — architecture, contracts, durable core, projections, control plane;
- `Pukujan/fossil-common` — stable pack `pack_269099f7b2ba43b7a99b9427d64092de`;
- `Pukujan/fossil-ai-systems` — stable pack `pack_f024177f89a5442db84171c3dd7f58e5`, with a required dependency on common.

Repository/database/graph placement is physical placement, not knowledge identity. Stable `pack_id` values remain authoritative.

## Fresh-session continuation

Read in this order:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/HANDOFF_CURRENT.md`
4. this file
5. `docs/DECISION_LOG.md`
6. `docs/implementation/2026-08-09-gate1-core-proof.md`
7. `docs/implementation/2026-08-09-gate1-live-graphiti-proof.md`
8. `docs/implementation/2026-08-09-gate1-rebuild-blue-green-proof.md`
9. `docs/implementation/2026-08-09-gate1-conversation-lineage-proof.md`
10. `docs/implementation/2026-08-09-gate1-agent-boundary-proof.md`
11. `docs/implementation/2026-08-10-gate1-source-provenance-redaction-proof.md`
12. Issue #1 and active Issue #7

The chat UI is source material, not the project control plane.

## Frozen architecture

Canonical FOSSIL knowledge is:

**immutable evidence + stable corpus IDs + append-only validated knowledge events + versioned pack/ontology contracts + provenance/history**.

Graphiti/Neo4j, vector/lexical indexes, models, Skills, MCP, retrieval strategies, and future databases remain replaceable projections/services.

A graph deletion must never delete irreplaceable intellectual history.

## Gate 1 — complete

1. [x] immutable validated events;
2. [x] deterministic invalid/duplicate rejection;
3. [x] content-addressed immutable artifacts;
4. [x] knowledge-pack boundaries and required dependencies;
5. [x] provenance-preserving cross-pack promotion;
6. [x] claim/relation lifecycle, disagreement, supersession, staleness;
7. [x] replaceable Graphiti adapter;
8. [x] projection retry/failure ledger;
9. [x] projection build metadata;
10. [x] live Graphiti + Neo4j materialization;
11. [x] destructive rebuild from durable data;
12. [x] second candidate projection comparison + guarded blue/green switch;
13. [x] conversation ingestion + intellectual-lineage reconstruction benchmark;
14. [x] source snapshots, exact citation provenance, quality dimensions, lifecycle, and redaction integrity;
15. [x] safe Agent Skill/API/MCP boundary.

## Proof checkpoints

### Durable core / packs / lifecycle

Issues #2, #3, and #6 established deterministic event/artifact durability, pack read/write boundaries and explicit promotion, plus replayable disagreement/supersession/staleness semantics.

### #4 — real Graphiti/Neo4j

Trusted CI run `31338875226` proved Graphiti `0.29.3` + Neo4j `5.26.29`, durable-first materialization into the stable pack/group namespace, runtime build metadata, projection failure preservation, and idempotent replay. See `docs/implementation/2026-08-09-gate1-live-graphiti-proof.md`.

### #5 — destructive rebuild + blue/green

Trusted live run `31339930551` destroyed the green candidate to zero nodes, replayed the same durable source with fresh build identity `green-rebuild-1`, kept blue live, matched projection-independent semantic digest exactly, and switched `blue -> green` only after checks passed. See `docs/implementation/2026-08-09-gate1-rebuild-blue-green-proof.md`.

### #9 — conversation lineage

Trusted CI run `31340924480`, job `93314435997`, passed 31 tests. Conversation evidence has immutable source bytes/spans, stable message order/parentage, actor metadata, explicit `verbatim` vs `reconstructed` status, and derived lineage with source provenance. The recovered path remains reconstructable without pretending recovery text is a verbatim lost transcript. See `docs/implementation/2026-08-09-gate1-conversation-lineage-proof.md`.

### #8 — safe Agent Skills/API/MCP boundary

Trusted CI run `31341456769`, job `93315824532`, passed **39 tests in 0.51s**. Six progressive-disclosure Skills feed a protocol-independent `CorpusService`; the thin adapter exposes only `search/read/lineage/propose/validate/commit/manage`. Agent mutation is pack- and skill-gated, preserves actor/model/harness/skill provenance, and provides no arbitrary graph/Cypher mutation path. See `docs/implementation/2026-08-09-gate1-agent-boundary-proof.md`.

### #10 — source provenance + redaction

Final deterministic run `31345462801`, job `93326450028`, passed **51 tests in 1.40s**.

Real redaction run `31346791333`, live job `93330095684`, used Graphiti `0.29.3`, Neo4j `5.26.29`, `qwen2.5:3b`, `nomic-embed-text`, and `json_schema` structured output.

Event `evt_416e5c516581c8dea8c5c54025361960` materialized under stable AI-systems pack `pack_f024177f89a5442db84171c3dd7f58e5` as one episode + one entity. Exceptional durable redaction wrote a minimal non-sensitive tombstone, deleted canonical event bytes, blocked same-ID republication, purged the active Graphiti episode, and left episode/entity/fact counts at zero. A fresh projection rebuild produced zero receipts and did not resurrect the erased knowledge. Proof artifact ID: `9047631921`.

See `docs/implementation/2026-08-10-gate1-source-provenance-redaction-proof.md`.

## Current issue map

- #1 milestone/control — open
- #2 durable event + artifact store — **complete**
- #3 pack boundaries/mounts/promotion — **complete**
- #4 Graphiti + Neo4j adapter/queue — **complete**
- #5 destructive rebuild + blue/green — **complete**
- #6 lifecycle/disagreement/supersession/staleness — **complete**
- #7 pluggable retrieval/model services + specialist benchmark contract — **active / next**
- #8 Agent Skills + thin corpus API/MCP — **complete**
- #9 conversation ingestion + intellectual lineage — **complete**
- #10 source snapshots/citation quality/redaction — **complete**

## Exact next task — Issue #7

Do not build a model zoo. Prove replaceability and benchmark authority boundaries.

Acceptance target:

1. retain interfaces for `ContextProvider`, `Retriever`, `EmbeddingProvider`, `Reranker`, `ModelService`, `VerificationService`;
2. provide one initial implementation per capability needed by the benchmark;
3. record model/provider/runtime versions in review/projection provenance;
4. represent risk/uncertainty escalation policy explicitly;
5. benchmark retrieval quality, latency, cost/RAM, and corpus-specific failure rates;
6. allow small/local models to propose candidates without granting truth-changing authority unless evidence/policy permits it;
7. compare alternatives behind the existing interfaces rather than changing canonical knowledge contracts.

Research references already exist in the evidence ledger for Kimi-style context, contextual retrieval, Model2Vec/Potion/FastEmbed/BGE-M3/ColBERT, GraphRAG/HippoRAG/LightRAG, and related approaches. New research should be benchmark-driven, not restart the architecture.

## Frozen invariants added during Gate 1

- new physical projection build => fresh build-scoped applied ledger;
- rebuild order => `(recorded_at, event_id)`;
- migration equality => stable FOSSIL semantics, not graph-native UUIDs;
- active projection changes => append-only switch records after checks pass;
- reconstructed conversation evidence cannot silently become verbatim evidence;
- verbatim conversation text resolves to immutable source bytes/spans;
- source quality is multidimensional, not one universal tier;
- derived/reconstructed source snapshots retain explicit parent provenance;
- normal intellectual revision remains append-only;
- privacy/legal erasure is an exceptional tombstone-before-delete path;
- erased artifact/event identities cannot silently resurrect;
- active projections and exports must respect redaction;
- event-redaction tombstones + projection ledgers must support crash/restart cleanup;
- Skills contain methodology, not canonical truth;
- protocol adapters cannot become the durable knowledge model.

## Workflow state

`.github/workflows/ci.yml` is restored to the normal fast contract suite.

`.github/workflows/graphiti-live.yml` contains reusable real Graphiti/Neo4j materialization plus redaction/non-resurrection smoke coverage. A Gate 1 debugging pass found that `runner.temp` cannot be used in job-level `env`; runner-dependent proof paths are now scoped to steps so the permanent workflow definition remains valid.

## End-of-session rule

After substantial work, update this file, `docs/HANDOFF_CURRENT.md`, Issue #1, the active child issue, durable benchmark/proof docs, and `docs/DECISION_LOG.md` when architecture/policy changes.
