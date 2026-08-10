# Current Handoff

**Date:** 2026-08-10  
**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Durable substrate:** **DICS — Durable Intellectual Corpus System**  
**Repository:** `Pukujan/fossil-core`  
**Status:** **Gate 1 executable durability proof is complete (15/15). Issue #7 retrieval/model benchmark work is next.**

## Repository family

- `Pukujan/fossil-core` — architecture/contracts/core/projections/control plane;
- `Pukujan/fossil-common` — stable pack `pack_269099f7b2ba43b7a99b9427d64092de`;
- `Pukujan/fossil-ai-systems` — stable pack `pack_f024177f89a5442db84171c3dd7f58e5`, depending on common.

Repository, graph, and database placement are not knowledge identity. Never mint replacement pack IDs because placement changes.

## Fresh-session order

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/PROJECT_STATE.md`
4. this file
5. `docs/DECISION_LOG.md`
6. `docs/implementation/2026-08-09-gate1-core-proof.md`
7. `docs/implementation/2026-08-09-gate1-live-graphiti-proof.md`
8. `docs/implementation/2026-08-09-gate1-rebuild-blue-green-proof.md`
9. `docs/implementation/2026-08-09-gate1-conversation-lineage-proof.md`
10. `docs/implementation/2026-08-09-gate1-agent-boundary-proof.md`
11. `docs/implementation/2026-08-10-gate1-source-provenance-redaction-proof.md`
12. Issue #1 and active Issue #7

The chat UI is source material, not the control plane.

## Architecture that must not be casually changed

Canonical truth is immutable evidence + stable corpus IDs + append-only validated knowledge events + versioned pack/ontology contracts + provenance/history.

Graphiti/Neo4j, vector/lexical indexes, models, Skills, MCP, retrieval strategies, and future databases are replaceable projections/services.

A graph deletion must never delete irreplaceable intellectual history.

## Gate 1 completion summary

### #2 durable event/artifact store — complete
Atomic immutable publication, deterministic idempotency, content-addressed evidence, integrity/tamper checks, and exceptional audited artifact/event erasure paths.

### #3 pack boundaries/promotion — complete
Explicit read/write mounts and required dependencies. Cross-pack promotion is a new provenance-preserving target-pack event rather than source mutation.

### #6 lifecycle — complete
Replay preserves disagreement, disputed state, relation history, supersession, and stale dependent propagation.

### #4 real Graphiti/Neo4j — complete
Run `31338875226` proved Graphiti `0.29.3` + Neo4j `5.26.29`, durable-first materialization, stable pack/group namespaces, build metadata, projection-failure preservation, and idempotent retry. `json_schema` is the proven local structured-output mode.

### #5 destructive rebuild + blue/green — complete
Run `31339930551` proved a candidate graph can be destroyed and rebuilt from durable events with a fresh build-scoped ledger while current remains live; stable semantic digests drive comparison and activation, not graph UUID equality.

Critical invariant: **a physically new/rebuilt projection gets a fresh build identity/applied ledger**. Reusing an old applied ledger after deleting a graph can silently produce an empty rebuild because every event appears already applied.

### #9 conversation lineage — complete
Run `31340924480` / job `93314435997` proved immutable conversation source bytes/spans, stable message ordering/parentage, durable `verbatim` vs `reconstructed` status, derived lineage provenance, opposing-position retrieval, current conclusions, and historical path reconstruction.

The recovered path remains explicitly reconstructed:

`learning UX/parabola -> representation mismatch -> AI translation -> failure learning -> MAPE-K/KEDB -> truth maintenance -> temporal knowledge graph`

Never silently promote the recovery artifact to a verbatim transcript.

### #8 safe Agent Skills/API/MCP — complete
Run `31341456769` / job `93315824532`: **39 passed in 0.51s**.

Six Skills use progressive disclosure. `CorpusService` is protocol-independent and exposes only `search/read/lineage/propose/validate/commit/manage`. Normal agent mutation is pack- and Skill-gated, preserves actor/model/harness/skill provenance, commits durable events first, and exposes no arbitrary Cypher/Graphiti mutation escape hatch. MCP remains an adapter.

### #10 source snapshots/citations/redaction — complete
Final deterministic run `31345462801` / job `93326450028`: **51 passed in 1.40s**.

Real live redaction run `31346791333` / job `93330095684` used Graphiti `0.29.3`, Neo4j `5.26.29`, `qwen2.5:3b`, `nomic-embed-text`, and `json_schema`.

Event `evt_416e5c516581c8dea8c5c54025361960` first materialized under AI-systems pack `pack_f024177f89a5442db84171c3dd7f58e5` as one Graphiti episode and one entity. Exceptional redaction then:

- wrote a minimal non-sensitive durable event tombstone;
- physically removed canonical event bytes;
- blocked republication of the same deterministic event identity;
- used the projection applied ledger's episode UUID to remove the active Graphiti episode;
- reduced pack-local episode/entity/fact counts to `0/0/0`;
- survived a fresh projection rebuild without resurrection (`fresh_rebuild_receipts == []`).

Proof artifact ID: `9047631921`.

Evidence: `docs/implementation/2026-08-10-gate1-source-provenance-redaction-proof.md`.

## Redaction semantics now frozen

Ordinary revision stays append-only. Privacy/legal deletion is an explicit exceptional operation.

- artifact/event tombstone is persisted before sensitive bytes are physically removed;
- tombstones intentionally avoid copying sensitive payload content;
- erased content/event identities cannot be silently reintroduced;
- exports and projection rebuilds respect redaction;
- historical projection applied receipts remain audit history while a separate redaction receipt records purge;
- event redaction tombstones plus build-scoped applied ledgers allow active projection cleanup after a crash/restart;
- Graphiti episode UUID is an operational purge handle for one projection build, not canonical knowledge identity.

## Workflow note

During #10, the previously mysterious standalone live-workflow registration failure was traced to `${{ runner.temp }}` being used in job-level `env`. GitHub's runner context is not available there. The permanent `.github/workflows/graphiti-live.yml` now scopes runner-dependent proof paths to steps and includes both materialization and redaction/non-resurrection smoke scripts.

Normal `.github/workflows/ci.yml` has been restored to the fast contract suite. Disposable proof PRs were closed unmerged.

## Exact next task — Issue #7

**Pluggable retrieval/model services + local specialist benchmark contract.**

Do not build a model zoo. Make implementations compete behind existing interfaces.

Acceptance:

1. use/complete `ContextProvider`, `Retriever`, `EmbeddingProvider`, `Reranker`, `ModelService`, `VerificationService` interfaces;
2. add one initial implementation per capability needed for benchmark execution;
3. record model/provider/runtime versions in projection/review provenance;
4. make risk/uncertainty escalation policy explicit and testable;
5. define benchmark fixtures/metrics for retrieval quality, latency, cost/RAM, and domain-specific failure rates;
6. local/small models may propose candidates but may not gain truth-changing authority without policy/evidence;
7. compare long-context, lexical/vector/graph retrieval and specialist approaches by measured corpus behavior rather than architecture fashion.

Research references already exist in the evidence ledger. New research should be triggered by benchmark uncertainty or implementation contradictions, not by novelty alone.

## End-of-session rule

After substantial work, update this file, `docs/PROJECT_STATE.md`, Issue #1, the active child issue, durable benchmark/proof evidence, and `docs/DECISION_LOG.md` when a decision changes.
