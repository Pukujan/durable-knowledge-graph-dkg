# Current Handoff

**Date:** 2026-08-10  
**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Durable substrate:** **DICS — Durable Intellectual Corpus System**  
**Repository:** `Pukujan/fossil-core`  
**Status:** **Milestone 0 complete. Gate 1 = 15/15. Issues #1–#10 are closed completed. No PRs are open.**

## Repository family

- `Pukujan/fossil-core` — architecture/contracts/core/projections/benchmark/control plane;
- `Pukujan/fossil-common` — stable pack `pack_269099f7b2ba43b7a99b9427d64092de`;
- `Pukujan/fossil-ai-systems` — stable pack `pack_f024177f89a5442db84171c3dd7f58e5`, depending on common.

Repository/database/graph placement is not knowledge identity. Never mint replacement pack IDs because placement changes.

## Fresh-session order

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/PROJECT_STATE.md`
4. this file
5. `docs/DECISION_LOG.md`
6. proof docs under `docs/implementation/`
7. closed Milestone #1 and child Issues #2–#10

The chat UI is source material, not the control plane.

## Architecture that must not be casually changed

Canonical truth is immutable evidence + stable corpus IDs + append-only validated knowledge events + versioned pack/ontology contracts + provenance/history.

Graphiti/Neo4j, lexical/vector indexes, context construction, models, Skills, MCP, and future databases remain replaceable projections/services.

A graph deletion must never delete irreplaceable intellectual history.

## Completed proof stack

### Durable core / packs / lifecycle
Issues #2, #3, #6: atomic immutable publication, deterministic idempotency, content-addressed evidence, pack read/write boundaries/dependencies, provenance-preserving promotion, disagreement/supersession/staleness replay.

### #4 live Graphiti/Neo4j
Run `31338875226`: Graphiti `0.29.3` + Neo4j `5.26.29`, stable pack namespace, durable-first materialization, build metadata, projection-failure preservation, idempotent retry.

### #5 destructive rebuild + blue/green
Run `31339930551`: candidate destroyed to zero, rebuilt from the same durable source with a fresh build-scoped ledger, semantic comparison matched, active switch recorded only after checks.

Critical invariant: **new/rebuilt physical projection => fresh build-scoped applied ledger**.

### #9 conversation lineage
Run `31340924480` / job `93314435997`: immutable source bytes/spans, stable message ordering/parentage, explicit `verbatim` vs `reconstructed`, derived intellectual lineage with exact provenance, opposing/current/historical queries.

Recovered chat-loss material remains reconstructed, never a verbatim transcript.

### #8 Agent Skills/API/MCP
Run `31341456769` / job `93315824532`: **39 passed in 0.51s**. Six progressive-disclosure Skills, protocol-independent `CorpusService`, pack/Skill-gated mutations, actor/model/harness/skill provenance, no arbitrary Cypher/Graphiti mutation path.

### #10 source provenance + redaction
Deterministic run `31345462801` / job `93326450028`: **51 passed in 1.40s**.

Live run `31346791333` / job `93330095684`: event `evt_416e5c516581c8dea8c5c54025361960` materialized under stable AI-systems pack, then exceptional tombstone-before-delete removed canonical event bytes, blocked same-ID resurrection, purged active Graphiti episode/entity state to zero, and remained absent on a fresh rebuild. Proof artifact `9047631921`.

Normal intellectual revision remains append-only. Privacy/legal erasure is an explicit exceptional path.

### #7 retrieval/model benchmark contract
Run `31347744797` / job `93332738616`: **56 passed in 0.70s**.

Versioned service controls:

- `BM25Retriever`
- `HashEmbeddingProvider`
- `EmbeddingRetriever`
- `TokenOverlapReranker`
- `BudgetedContextProvider`
- `CallableCandidateModelService`
- `RiskEscalationPolicy`
- `PolicyVerificationService`

The benchmark schema/harness measures retrieval/model quality, mean/p95 latency, peak Python allocation memory, estimated provider cost, and category-specific failure rates. Provider/model/runtime/benchmark provenance can be committed to review events.

These are **controls, not production winners**. Future providers must compete behind the interfaces.

Small/local model output remains `candidate_only`; evidence/risk policy controls downstream truth-changing eligibility.

Evidence: `docs/implementation/2026-08-10-retrieval-model-benchmark-contract-proof.md`.

## CI / workflow state

Final clean Gate 1 run `31347457485` / job `93331933728`: **51 passed in 0.82s**.

Expanded post-#7 run `31347744797` / job `93332738616`: **56 passed in 0.70s**.

`.github/workflows/ci.yml` is restored to the normal fast suite. Disposable proof PRs were closed unmerged.

`.github/workflows/graphiti-live.yml` contains reusable materialization + redaction/non-resurrection smoke coverage. Runner-dependent proof paths are step-scoped; the earlier invalid job-level `runner.temp` usage is fixed.

## Milestone closure

All original children #2–#10 and control Issue #1 are closed completed. There are no open Issues or PRs at this checkpoint.

## Natural next phase — intentionally not opened automatically

The next useful campaign is corpus-scale provider benchmarking:

1. derive representative cases from `fossil-common` and `fossil-ai-systems`;
2. compare current controls with selected real semantic/vector/graph/long-context providers;
3. record quality, latency, memory, cost, and failure categories under `fossil.benchmark.v1`;
4. preserve candidate-only model authority unless independent evidence/risk policy permits downstream changes;
5. let measured corpus performance choose adapters.

Open a new tracked gate before materially expanding this work rather than silently extending the closed milestone.
