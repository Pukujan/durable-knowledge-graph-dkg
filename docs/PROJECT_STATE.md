# FOSSIL Project State

**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Durable substrate:** **DICS — Durable Intellectual Corpus System**  
**Current phase:** **Milestone 0 / Gate 1 complete; Gate 2 complete**  
**Active work:** **none after Gate 2 closure; open a new evidence-backed campaign rather than extending closed Gate 2 issues**  
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
6. Gate 2 proof/policy documents under `docs/implementation/`
7. closed Gate 2 control Issue #33 and children #34–#37 when detailed campaign history is useful
8. closed Milestone 0 Issue #1 and child Issues #2–#10 when detailed Gate 1 history is useful

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

## Gate 2 — complete

Control issue: **#33 — Real Corpus + Retrieval/Model Bakeoff**.

Children:

- [x] #34 representative corpus fixtures + gold/adversarial benchmark set
- [x] #35 real retrieval/context adapters behind existing interfaces
- [x] #36 reproducible comparative bakeoff + failure taxonomy
- [x] #37 evidence-based default retrieval/routing policy

### Gate 2A — real history-rich corpus

Pinned source pack commits:

- `Pukujan/fossil-common` — `d583005dce06dbb499c3c0de5c22b899655eb8d2`;
- `Pukujan/fossil-ai-systems` — `cf7cf4087bde543cb247a978de2a7252b1b8e4de`.

`benchmarks/gate2/real-corpus-history-v2.json` contains 21 cases covering exact lookup, source/citation recovery, decision lineage, current/history, disagreement, stale/superseded state, cross-pack isolation, deep evidence, conversation lineage, and insufficient-evidence negatives.

Gate 2A landed at core commit `a028f9e328c2cbcde0185930e90b5eeb4c4efcb8`.

### Gate 2B — real retrieval adapters

Core commit `2affde923acf196319d90bfa63f206e4a5e2f25f` added:

- revision-pinned BGE dense retrieval;
- BM25+BGE reciprocal-rank fusion;
- lifecycle-intent reranking;
- context integration;
- optional semantic runtime behavior with provider/model/runtime provenance.

Approved semantic identity tested in Gate 2:

- model `BAAI/bge-small-en-v1.5`;
- revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`;
- Sentence Transformers `5.2.2`;
- Torch `2.13.0`;
- Transformers `5.14.1`;
- normalized embeddings enabled.

### Gate 2C — comparative evidence

PR #44 landed as squash commit `38aac6325cdb5b738c8a6ac5e55959affb3acfb5`.

Final branch-independent CI before landing: run `31366259213`, job `93385174741` — **86 passed in 1.25s**.

Exact-head semantic proof:

- run `31364039745`;
- artifact `9053475462` (`gate2-comparative-results`);
- digest `sha256:23c95b46f47cec5a16e0a8c0926a4f13532f283d8f4fbcc0de12ceb63db63c41`.

Exact-head comparison:

| Strategy | Hit rate | Recall@5 | MRR | Mean latency | p95 | Peak Python alloc |
|---|---:|---:|---:|---:|---:|---:|
| BM25 | 0.95238 | 0.95238 | 0.81746 | 3.270 ms | 4.566 ms | 58,844 B |
| Hash control | 0.95238 | 0.92063 | 0.83730 | 1.283 ms | 1.558 ms | 34,100 B |
| **BGE dense** | **1.00000** | **0.98413** | 0.85873 | 36.201 ms | 38.535 ms | 81,779 B |
| Hybrid | 0.95238 | 0.95238 | **0.86667** | 58.658 ms | 66.023 ms | 183,065 B |

All estimated provider cost was `$0` in the local proof. No strategy violated pack isolation, and the tested context probes stayed below the 4,000-character reference budget without truncation/overload.

Important stable failures:

- BM25, hash, and hybrid fully miss `current_architecture_after_reconsideration`;
- BGE dense is the only strategy with zero full retrieval misses, but the current architecture is only rank 5 behind rejected/history material;
- BGE retrieves 2/3 targets for `historical_current_supersession_bundle` at `k=5`;
- hybrid has the best MRR but its decision-critical current-architecture full miss disqualifies it as the Gate 2 default.

Durable evidence:

- `benchmarks/gate2/results/2026-08-10-comparative/comparison-summary.json`;
- `docs/implementation/2026-08-10-gate2-comparative-bakeoff-proof.md`.

### Gate 2D — selected retrieval/routing policy

Decision D021 selects **revision-pinned BGE dense as the normal primary retriever** because it is the only compared strategy with zero full misses and has the best mean recall.

**Explicit availability fallback:** BM25, marked degraded. The hash control is not the fallback. BM25 is not quality-equivalent to BGE; quality/configuration rollback returns to the last known benchmark-passing BGE profile.

Mandatory safeguards:

- current/latest/accepted queries resolve durable lifecycle/provenance before presenting a current conclusion;
- rejected/superseded/retracted/stale/disputed history cannot become current because of retrieval rank;
- decision-lineage, disagreement, supersession, and multi-target historical/current tasks use durable `lineage`/read resolution in addition to retrieval;
- top-k absence is not evidence of nonexistence;
- citation-bearing answers still resolve immutable source snapshot/span/hash identity;
- retrieval/model output does not receive truth-changing authority merely from confidence or agreement.

Policy proof: `docs/implementation/2026-08-10-gate2-default-retrieval-policy.md`.

## Current cognitive-service posture

Normal primary retrieval profile:

- BGE dense behind the existing replaceable semantic retriever interface;
- `BudgetedContextProvider` remains the replaceable context builder;
- Gate 2's 4,000-character context budget is a benchmark reference profile, not a frozen universal limit.

Availability fallback:

- `BM25Retriever`, explicitly degraded when the semantic runtime is unavailable.

Controls retained for future comparison:

- `HashEmbeddingProvider` / `EmbeddingRetriever`;
- `TokenOverlapReranker`;
- BM25 remains both a control and the availability fallback.

`CallableCandidateModelService`, `RiskEscalationPolicy`, and `PolicyVerificationService` retain the separate model-authority boundary. Small/local model output remains `candidate_only`; truth-changing eligibility comes from independent evidence/risk policy.

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

`.github/workflows/graphiti-live.yml` contains reusable live materialization plus redaction/non-resurrection smoke coverage.

Gate 2 temporary proof workflows were removed before their PRs landed. After #37/#33 close, there are no active Gate 2 issues. Future work should start a new issue/campaign and preserve the completed Gate 2 evidence rather than rewriting it.
