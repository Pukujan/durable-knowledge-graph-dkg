# FOSSIL Project State

**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Durable substrate:** **DICS — Durable Intellectual Corpus System**  
**Current phase:** **Milestone 0 / Gate 1 complete; Gate 2 active under Issue #33**  
**Active work:** **#34 representative real corpus + versioned gold/adversarial benchmark set; draft PR #38**  
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
5. Gate 2 control Issue #33 and active children #34–#37
6. `docs/DECISION_LOG.md`
7. proof docs under `docs/implementation/`
8. closed Milestone 0 Issue #1 and child Issues #2–#10 when detailed history is useful

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
- **#7 cognitive-service contract:** run `31347744797`, job `93332738616` — **56 passed in 0.70s**; versioned replaceable cognitive-service interfaces and `fossil.benchmark.v1` result contract.

## Gate 2 — active

Control issue: **#33 — Real Corpus + Retrieval/Model Bakeoff**.

Children:

- [ ] #34 representative corpus fixtures + gold/adversarial benchmark set
- [ ] #35 real retrieval/context adapters behind existing interfaces
- [ ] #36 reproducible comparative bakeoff + failure taxonomy
- [ ] #37 evidence-based default retrieval/routing policy

### Current #34 checkpoint

Initial repository inspection found both physical pack repositories are still scaffolds:

- `fossil-common` initial commit `94fd576286ee359f1929b31bbba99e0ca54d4b41` contains the stable manifest/policy pointers plus empty event/artifact payloads;
- `fossil-ai-systems` initial commit `cfd03e08c36f00a5eb25c8de4c1463d06877e015` likewise contains only the stable pack scaffold.

Therefore Gate 2A must seed representative canonical evidence/events into the existing stable packs before deriving a benchmark and calling it a real corpus.

Draft PR **#38 — `Gate 2: persist benchmark case sets`** adds the missing portable case-set layer:

- `fossil.benchmark-case-set.v1`;
- exact repository commit pins for each participating pack;
- persistent retrieval/model cases converted into the existing Gate 1 benchmark case types;
- exact citation span/hash gold metadata plus source snapshot references;
- semantic rejection of duplicate case IDs, unpinned retrieval pack scopes, and citation gold that references undeclared source snapshots.

First trusted PR run `31356440481`, job `93356916077`: **60 passed in 0.69s**. The branch received follow-up exact-citation validation changes after that run; re-check current PR CI before merging.

### Gate 2 exit target

- representative real corpus fixtures from both stable packs;
- versioned gold/adversarial benchmark set;
- at least two materially different real retrieval strategies compared against controls;
- reproducible benchmark evidence for quality, latency, memory, estimated cost, and failure categories;
- documented failure taxonomy;
- one evidence-based default retrieval/routing policy;
- no canonical identity/durability change merely to suit a benchmark winner.

## Current cognitive-service controls

- `BM25Retriever`
- `HashEmbeddingProvider`
- `EmbeddingRetriever`
- `TokenOverlapReranker`
- `BudgetedContextProvider`
- `CallableCandidateModelService`
- `RiskEscalationPolicy`
- `PolicyVerificationService`

These remain **baselines/controls, not chosen production winners**. Small/local model output remains `candidate_only`; truth-changing eligibility comes from the separate evidence/risk policy.

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

GitHub currently has active Gate 2 Issues #33–#37 and draft PR #38. Do not use the old "zero open issues/PRs" Milestone 0 checkpoint as current state.
