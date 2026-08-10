# FOSSIL Project State

**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Durable substrate:** **DICS — Durable Intellectual Corpus System**  
**Completed:** **Milestone 0 / Gate 1; Gate 2; Issue #48 research ingestion; Issue #48 Workstream A**  
**Active work:** **Issue #48 Workstream B — end-to-end answer/citation/abstention evaluation**  
**Related workstream:** **Issue #47 — embedding/reranker/model-scale bakeoff**  
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
4. `docs/handoffs/2026-08-10-chatgpt-session-handoff-post-temporal-benchmark.md`
5. this file
6. `docs/research/2026-08-10-production-rag-hardening-research-trace.md`
7. Issue #48
8. Issue #47
9. `docs/DECISION_LOG.md`
10. completed proof/policy docs under `docs/implementation/`

The chat UI is source material, not the control plane.

## Frozen architecture

Canonical FOSSIL knowledge is **immutable evidence + stable corpus IDs + append-only validated knowledge events + versioned pack/ontology contracts + provenance/history**.

Graphiti/Neo4j, lexical/vector indexes, embedding models, rerankers, context construction, planners, model services, Skills, MCP, and future databases remain replaceable projections/services.

A graph deletion or embedding replacement must never delete irreplaceable intellectual history.

## Completed foundation

### Gate 1

Gate 1 is complete: durable events/artifacts, pack boundaries, lifecycle/disagreement/supersession, replaceable graph projection, rebuild/migration, conversation lineage, exact source/citation integrity, redaction/non-resurrection, cognitive-service contracts, and safe Agent Skill/API/MCP boundaries were proven.

Final cleaned Gate 1 run `31347457485`, job `93331933728`: **51 passed in 0.82s**. Cognitive-service contract run `31347744797`, job `93332738616`: **56 passed in 0.70s**.

### Gate 2

Gate 2 control #33 and children #34–#37 are closed/completed.

Evidence anchors:

- Gate 2A core commit `a028f9e328c2cbcde0185930e90b5eeb4c4efcb8`;
- Gate 2B core commit `2affde923acf196319d90bfa63f206e4a5e2f25f`;
- Gate 2C PR #44 / squash `38aac6325cdb5b738c8a6ac5e55959affb3acfb5`;
- Gate 2C final CI run `31366259213`, job `93385174741` — **86 passed in 1.25s**;
- semantic proof run `31364039745`, artifact `9053475462`, digest `sha256:23c95b46f47cec5a16e0a8c0926a4f13532f283d8f4fbcc0de12ceb63db63c41`;
- Gate 2D PR #45 / squash `2d22dee9e6b176956d30005f4d7877baf68b0a3c`;
- Gate 2D CI run `31366800697`, job `93386832166` — **86 passed in 1.02s**;
- closed-state reconciliation PR #46 / squash `a614936249ff0ab201756fa54a1e89699d7b924f`.

The 21-case history-rich corpus compared BM25, a hash embedding control, revision-pinned BGE dense, and BM25+BGE hybrid/lifecycle reranking. BGE dense was the only compared strategy with zero full retrieval misses and had mean recall@5 `0.98413`. It still showed current-state ranking leakage and incomplete multi-target lineage recall.

Decision D021 therefore selects revision-pinned `BAAI/bge-small-en-v1.5@5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` as the normal primary retriever and BM25 as an explicit degraded availability fallback.

Mandatory D021 safeguards remain:

- current/latest/accepted questions resolve lifecycle/provenance;
- lineage/history/disagreement questions use durable lineage/read resolution;
- top-k absence is not evidence of nonexistence;
- citation-bearing answers resolve immutable source snapshot/span/hash identity;
- retrieval/model output does not receive truth authority from score, confidence, or agreement.

Policy proof: `docs/implementation/2026-08-10-gate2-default-retrieval-policy.md`.

## Active campaign #48 — production RAG hardening

Research basis:

`docs/research/2026-08-10-production-rag-hardening-research-trace.md`

The campaign conclusion remains **harden, do not redesign the durable core**.

### Workstream state

1. **A — evolving-corpus temporal/update benchmark: COMPLETE**
2. **B — end-to-end answer/citation/unsupported-claim/abstention evaluation: ACTIVE NEXT**
3. **C — poisoning/untrusted-context adversarial suite: pending**
4. **F — replayable query execution receipt: pending**
5. **D / #47 — embedding/hybrid/reranker/model bakeoff: pending provider-backed comparison**
6. **E — conservative adaptive routing: pending evidence**
7. **G — ACL/redaction propagation readiness: pending**
8. final retrieval-policy/decision-log/residual-risk reconciliation: pending

### Workstream A — landed evidence

Core PR #54 / squash:

`e14148f504702ae9e708e2d58add4ee5c91bc8de`

Final CI:

- run `31431210018`;
- job `93594807498`;
- **88 passed in 0.99s**.

The implementation adds:

- historical/as-of durable-event replay for pack search projections;
- reusable phased temporal benchmark machinery;
- a versioned real-corpus benchmark plan;
- exact Git pin verification in the runner;
- deterministic lifecycle/current/history tests;
- durable proof at `docs/implementation/2026-08-10-post-gate2-temporal-benchmark-proof.md`.

Execution-only proof PR #55 ran the exact plan against:

- `fossil-common@d583005dce06dbb499c3c0de5c22b899655eb8d2`;
- `fossil-ai-systems@84accd2ee895663990e82ca5b79b592cb503db24`.

Proof run `31431113829`, job `93594491275`:

- **88 tests passed in 0.84s**;
- temporal benchmark **PASS** across three phases;
- former SQLite premise changed `supported -> superseded`;
- its dependent prototype changed `supported -> stale_pending_review`;
- accepted durable-core claim remained `supported`;
- current and historical queries were rank 1 / recall@5 1.0;
- after projected corpus growth from 13 to 27 documents, both repeated queries remained rank 1 / recall@5 1.0 with no current-state leakage;
- projection rebuilds were roughly 23.68–25.28 ms on that runner.

The timing observations are baseline measurements, not evidence to replace D021.

Issue #48 now has all four Workstream A checklist items checked and the `Evolving-corpus benchmark committed` exit criterion checked.

### Workstream B — exact next target

Extend evaluation above retrieval to answer-level reliability. The first committed baseline should be provider-independent and should measure:

- final-answer correctness;
- citation/source-snapshot/span correctness;
- unsupported-claim rate;
- answer completeness;
- contradiction handling;
- explicit insufficient/conflicting/unresolved outcomes;
- appropriate abstention/calibration.

Use deterministic/direct-source/read paths and existing `ModelService` / `VerificationService` contracts first. Hosted/frontier models may later be evaluated behind those interfaces; they should not become correctness dependencies.

### Hardening principles under test

- retrieved/source text is untrusted data, not executable policy;
- uncertainty/abstention is explicit answer behavior when evidence is insufficient/conflicting/unresolved;
- simple direct-source/read and fixed retrieval baselines remain mandatory competitors;
- a reranker can improve candidate ordering but cannot decide lifecycle truth;
- adaptive planners must expose route/execution metadata and earn their cost/complexity;
- important benchmark queries should be replayable after provider/model/projection changes.

These are campaign hypotheses/requirements, not silent changes to `ARCHITECTURE.md`.

## Research-to-corpus state

The 2026-08-10 production-RAG research synthesis is ingested into `fossil-ai-systems` as a **local derived research artifact** with stable artifact/source identity, exact citations, deterministic event identity, and claim provenance.

Exact landed pack state:

- `fossil-common@d583005dce06dbb499c3c0de5c22b899655eb8d2`;
- `fossil-ai-systems@84accd2ee895663990e82ca5b79b592cb503db24` via PR #3;
- research artifact `art_b030642ff65f883ff467529c73cbb6e5`;
- SHA-256 `b030642ff65f883ff467529c73cbb6e502deca28f4c3dece0c2879bf690d3b15`;
- source snapshot `snap_9c0e088ab2d7d8e1b21db563`;
- source core commit `6799b2db743d91b004b1e16b5129285a582f8847`.

Cross-pack validation proof ran in execution-only core PR #51, workflow `31415053398`, job `93541977670`: **86 core tests passed** and `PackFixtureAudit` reported **6 artifacts, 6 snapshots, 51 events, 47 citations, 23 claims, 4 relations — PASS**.

Original external papers and production documentation must still be captured as distinct source snapshots when full research-source ingestion is implemented. The synthesis or chat transcript must not be presented as verbatim external evidence.

## Cognitive-service posture

Current approved retrieval profile remains D021 until new committed benchmark evidence says otherwise.

Existing replaceable service contracts include:

- `Retriever`;
- `EmbeddingProvider`;
- `Reranker`;
- `ContextProvider`;
- `ModelService`;
- `VerificationService`.

This allows later #48/#47 work to test new embeddings, rerankers, routing/context strategies, and model services without coupling canonical knowledge to them.

## Frozen invariants

- stable pack identity is independent of repository/database placement;
- durable commit precedes replaceable projection;
- new physical projection build => fresh build-scoped applied ledger;
- rebuild order => `(recorded_at, event_id)`;
- migration compares stable FOSSIL semantics, not graph-native UUIDs;
- reconstructed evidence cannot silently become verbatim;
- exact citations resolve to immutable observed bytes/spans;
- source quality is multidimensional and derivation is explicit;
- ordinary intellectual revision is append-only;
- privacy/legal erasure is exceptional tombstone-before-delete with non-resurrection;
- active projections/exports respect redaction;
- Skills contain methodology, not canonical truth;
- protocol adapters cannot become the durable knowledge model;
- cognitive services expose provider/version metadata and compete behind interfaces;
- model agreement is not evidence; model output remains bounded by evidence/risk policy.

## Workflow state

`.github/workflows/ci.yml` remains the normal fast contract suite.

`.github/workflows/graphiti-live.yml` contains reusable live materialization plus redaction/non-resurrection smoke coverage.

Execution-only PRs #51 and #55 were closed without merge after their proofs. Issue #48 remains active; do not extend closed Gate 2 issues to implement it.
