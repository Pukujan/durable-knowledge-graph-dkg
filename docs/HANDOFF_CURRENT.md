# Current Handoff

**Date:** 2026-08-10  
**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Durable substrate:** **DICS — Durable Intellectual Corpus System**  
**Repository:** `Pukujan/fossil-core`  
**Status:** **Milestone 0 is complete: Gate 1 = 15/15 and every child Issue #2–#10 is complete.**

## Repository family

- `Pukujan/fossil-core` — architecture/contracts/core/projections/benchmark/control plane;
- `Pukujan/fossil-common` — stable pack `pack_269099f7b2ba43b7a99b9427d64092de`;
- `Pukujan/fossil-ai-systems` — stable pack `pack_f024177f89a5442db84171c3dd7f58e5`, depending on common.

Repository/database/graph placement is not knowledge identity. Stable `pack_id` values survive moves and future physical sharding.

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
12. `docs/implementation/2026-08-10-retrieval-model-benchmark-contract-proof.md`
13. closed Milestone #1 and child Issues #2–#10

The chat UI is source material, not the control plane.

## Frozen architecture

Canonical FOSSIL knowledge is immutable evidence + stable corpus IDs + append-only validated knowledge events + versioned pack/ontology contracts + provenance/history.

Graphiti/Neo4j, lexical/vector indexes, context construction, models, Skills, MCP, and future databases remain replaceable projections/services.

A graph deletion must never delete irreplaceable intellectual history.

## Completed executable proofs

### Durable core / packs / lifecycle
Issues #2, #3, and #6 cover atomic immutable publication, deterministic idempotency, content-addressed artifacts, pack read/write boundaries and dependencies, provenance-preserving promotion, disagreement, supersession, and stale dependency propagation.

### #4 live Graphiti/Neo4j
Run `31338875226`: Graphiti `0.29.3` + Neo4j `5.26.29`, stable pack namespace, durable-first materialization, build metadata, failure preservation, idempotent replay.

### #5 destructive rebuild + blue/green
Run `31339930551`: candidate graph destroyed to zero, rebuilt from the same durable source with fresh build identity, semantic compare matched, active switch recorded only after checks.

Critical invariant: **new/rebuilt physical projection => fresh build-scoped applied ledger**.

### #9 conversation lineage
Run `31340924480` / job `93314435997`: immutable source bytes/spans, stable message ordering/parentage, explicit `verbatim` vs `reconstructed`, derived intellectual lineage with exact provenance, opposing/current/historical queries.

The recovered chat-loss material remains reconstructed, never a verbatim transcript.

### #8 Agent Skills/API/MCP
Run `31341456769` / job `93315824532`: **39 passed in 0.51s**. Six progressive-disclosure Skills, protocol-independent `CorpusService`, pack/Skill-gated mutations, actor/model/harness/skill provenance, no arbitrary Cypher/Graphiti mutation path.

### #10 source provenance + redaction
Deterministic run `31345462801` / job `93326450028`: **51 passed in 1.40s**.

Live run `31346791333` / job `93330095684`: event `evt_416e5c516581c8dea8c5c54025361960` materialized under stable AI-systems pack, then exceptional tombstone-before-delete erased canonical event bytes, blocked same-ID resurrection, purged active Graphiti episode/entity state to zero, and stayed absent on a fresh rebuild. Proof artifact `9047631921`.

Redaction is exceptional; normal intellectual revision remains append-only.

### #7 retrieval/model service benchmark contract
Run `31347744797` / job `93332738616`: **56 passed in 0.70s**.

Versioned cognitive interfaces now have executable controls:

- `BM25Retriever`
- `HashEmbeddingProvider`
- `EmbeddingRetriever`
- `TokenOverlapReranker`
- `BudgetedContextProvider`
- `CallableCandidateModelService`
- `RiskEscalationPolicy`
- `PolicyVerificationService`

`schemas/benchmark/v1.schema.json` + `src/dkg/benchmark.py` measure retrieval/model quality, latency, peak Python memory, estimated cost, and failure rates by category. Provider/model/runtime/benchmark identity can be persisted in review event provenance.

These implementations are **baselines/controls, not production winners**. Future real providers must compete behind the interfaces.

A local/small model remains `candidate_only`. Truth-changing commit eligibility comes from independent evidence + risk/uncertainty policy, not model consensus.

Evidence: `docs/implementation/2026-08-10-retrieval-model-benchmark-contract-proof.md`.

## Final clean-state CI

Before #7, Gate 1's cleaned repository passed run `31347457485` / job `93331933728`: **51 passed in 0.82s**.

After #7 implementation, trusted run `31347744797` / job `93332738616` passed the expanded suite: **56 passed in 0.70s**.

Normal `.github/workflows/ci.yml` is restored. Disposable proof branches/PRs are never merged.

`.github/workflows/graphiti-live.yml` contains reusable materialization + redaction/non-resurrection smoke coverage. Runner-dependent proof paths are step-scoped; the earlier invalid job-level `runner.temp` usage is fixed.

## Milestone result

All original child issues are complete:

- #2 durable event/artifact store
- #3 pack boundaries/promotion
- #4 live Graphiti projection
- #5 destructive rebuild/blue-green
- #6 lifecycle/disagreement/staleness
- #7 pluggable cognitive services + benchmark contract
- #8 safe Skills/API/MCP boundary
- #9 conversation lineage
- #10 source snapshots/citation/redaction

Issue #1 can be closed as completed.

## Natural next phase — not yet opened

The next useful campaign is **corpus-scale provider benchmarking**, not more architecture invention:

1. build representative benchmark fixtures from `fossil-common` and `fossil-ai-systems`;
2. compare current lexical/hash controls against selected real semantic/vector/graph/long-context providers;
3. record quality, latency, memory, cost, and failure categories under the existing schema;
4. keep model output candidate-only unless evidence/risk policy supports downstream authority;
5. let measured corpus performance choose adapters.

Open a new tracked gate before materially expanding this work.
