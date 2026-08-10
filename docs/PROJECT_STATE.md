# FOSSIL Project State

**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Durable substrate:** **DICS — Durable Intellectual Corpus System**  
**Current phase:** **Milestone 0 complete; Gate 1 = 15/15; Issues #1–#10 closed completed**  
**Next phase:** not yet opened; natural next campaign is corpus-scale comparison of real retrieval/model providers behind the benchmark interfaces  
**Control plane:** GitHub issues + durable repository docs  
**Last updated:** 2026-08-10

## Repository family

- `Pukujan/fossil-core` — architecture/contracts/durable core/projections/benchmarks;
- `Pukujan/fossil-common` — stable pack `pack_269099f7b2ba43b7a99b9427d64092de`;
- `Pukujan/fossil-ai-systems` — stable pack `pack_f024177f89a5442db84171c3dd7f58e5`, depending on common.

Repository/database/graph placement is physical placement, not knowledge identity.

## Continuation order

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/HANDOFF_CURRENT.md`
4. this file
5. `docs/DECISION_LOG.md`
6. proof docs under `docs/implementation/`
7. closed Milestone #1 and child Issues #2–#10

The chat UI is source material, not the control plane.

## Frozen architecture

Canonical FOSSIL knowledge is **immutable evidence + stable corpus IDs + append-only validated knowledge events + versioned pack/ontology contracts + provenance/history**.

Graphiti/Neo4j, lexical/vector indexes, context construction, models, Skills, MCP, and future databases remain replaceable projections/services.

A graph deletion must never delete irreplaceable intellectual history.

## Gate 1 — complete (15/15)

1. [x] immutable validated events
2. [x] deterministic invalid/duplicate rejection
3. [x] content-addressed immutable artifacts
4. [x] knowledge-pack boundaries/dependencies
5. [x] provenance-preserving cross-pack promotion
6. [x] claim/relation lifecycle, disagreement, supersession, staleness
7. [x] replaceable Graphiti adapter
8. [x] projection retry/failure ledger
9. [x] projection build metadata
10. [x] live Graphiti + Neo4j materialization
11. [x] destructive rebuild from durable data
12. [x] second projection comparison + guarded blue/green switch
13. [x] conversation ingestion + intellectual-lineage reconstruction
14. [x] source snapshots, exact citations, quality/lifecycle/redaction integrity
15. [x] safe Agent Skill/API/MCP boundary

Final cleaned Gate 1 run `31347457485`, job `93331933728`: **51 passed in 0.82s**.

## Major Gate 1 proof checkpoints

- **#4 live projection:** run `31338875226` — Graphiti `0.29.3` + Neo4j `5.26.29`, stable pack namespace, durable-first projection, failure preservation, idempotent replay.
- **#5 rebuild/migration:** run `31339930551` — candidate destroy/rebuild with fresh build ledger, semantic comparison, guarded blue/green switch.
- **#9 conversation lineage:** run `31340924480`, job `93314435997` — exact source spans, durable `verbatim` vs `reconstructed`, opposing/current/historical lineage queries.
- **#8 agent boundary:** run `31341456769`, job `93315824532` — progressive-disclosure Skills, protocol-independent corpus service, no arbitrary graph mutation.
- **#10 provenance/redaction:** deterministic run `31345462801`, job `93326450028`; live run `31346791333`, job `93330095684` — tombstone-before-delete, active Graphiti purge, zero-state fresh rebuild/non-resurrection.

## #7 cognitive-service benchmark contract — complete

Trusted run `31347744797`, job `93332738616`: **56 passed in 0.70s**.

Versioned interfaces: `Retriever`, `EmbeddingProvider`, `Reranker`, `ContextProvider`, `ModelService`, `VerificationService`.

Initial inspectable controls:

- `BM25Retriever`
- `HashEmbeddingProvider`
- `EmbeddingRetriever`
- `TokenOverlapReranker`
- `BudgetedContextProvider`
- `CallableCandidateModelService`
- `RiskEscalationPolicy`
- `PolicyVerificationService`

`schemas/benchmark/v1.schema.json` + `src/dkg/benchmark.py` measure retrieval/model quality, mean/p95 latency, peak Python allocation bytes, estimated provider cost, and failures by domain category. Provider/model/runtime/benchmark identity can be persisted in review event provenance.

These implementations are **baselines/controls, not chosen production winners**. Future semantic/vector/graph/long-context/model candidates must compete behind the interfaces.

Small/local model output is `candidate_only`. Truth-changing commit eligibility comes from a separate evidence/risk policy, not model consensus.

Evidence: `docs/implementation/2026-08-10-retrieval-model-benchmark-contract-proof.md`.

## Closed issue map

- #1 Milestone 0 control — **complete**
- #2 durable event + artifact store — **complete**
- #3 pack boundaries/mounts/promotion — **complete**
- #4 Graphiti + Neo4j projection — **complete**
- #5 destructive rebuild + blue/green — **complete**
- #6 lifecycle/disagreement/supersession/staleness — **complete**
- #7 pluggable retrieval/model services + benchmark contract — **complete**
- #8 Agent Skills + thin corpus API/MCP — **complete**
- #9 conversation ingestion + intellectual lineage — **complete**
- #10 source snapshots/citation/redaction — **complete**

## Frozen invariants from Milestone 0

- stable pack identity is independent of repository/database placement;
- durable commit precedes replaceable projection;
- new physical projection build => fresh build-scoped applied ledger;
- rebuild order => `(recorded_at, event_id)`;
- migration compares stable FOSSIL semantics, not graph-native UUIDs;
- reconstructed evidence cannot silently become verbatim;
- exact citations resolve to immutable observed bytes/spans;
- source quality is multidimensional and source derivation is explicit;
- ordinary intellectual revision is append-only;
- privacy/legal erasure is exceptional tombstone-before-delete with non-resurrection;
- active projections/exports respect redaction;
- Skills contain methodology, not canonical truth;
- protocol adapters cannot become the durable knowledge model;
- cognitive services expose provider/version metadata and compete behind interfaces;
- model agreement is not evidence; local/small models remain candidate-only until evidence/policy permits downstream authority.

## Workflow state

`.github/workflows/ci.yml` is the normal fast contract suite.

`.github/workflows/graphiti-live.yml` contains reusable live materialization plus redaction/non-resurrection smoke coverage. Runner-dependent proof paths are step-scoped; the invalid job-level `runner.temp` usage found during Gate 1 is fixed.

There are no open Issues or pull requests in `Pukujan/fossil-core` at this checkpoint.

## Natural next phase — not yet opened

Use representative `fossil-common` and `fossil-ai-systems` material to compare the current controls against selected real semantic/vector/graph/long-context providers under the existing benchmark contract. Open a new tracked gate before materially expanding that campaign.
