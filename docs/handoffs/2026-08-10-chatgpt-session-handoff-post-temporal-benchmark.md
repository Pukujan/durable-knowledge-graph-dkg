# FOSSIL Session Handoff — Post-Temporal-Benchmark

**Date:** 2026-08-10  
**Project:** FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage  
**Repository:** `Pukujan/fossil-core`  
**Campaign:** Issue #48 — production RAG hardening  
**Status:** Gate 1 complete; Gate 2 complete; research ingestion complete; Workstream A complete; Issue #48 remains active.

## Exact continuation point

Do **not** repeat the research-to-corpus ingestion or the evolving-corpus temporal benchmark.

The next unfinished Issue #48 workstream is:

**B. End-to-end answer/citation/abstention evaluation.**

Build a provider-independent baseline first. The baseline should evaluate final-answer behavior above retrieval using deterministic/direct-source and existing service contracts, so hosted/frontier model access can later be added as a competitor rather than becoming a prerequisite for correctness.

Workstream B must cover:

1. final-answer correctness beyond retrieval hit-rate/recall/MRR;
2. citation and immutable source-snapshot/span correctness;
3. unsupported-claim rate;
4. answer completeness and contradiction handling;
5. explicit `insufficient evidence`, `conflicting evidence`, and `current state unresolved` outcomes;
6. appropriate abstention/calibration rather than rewarding confident guessing.

Keep lifecycle/lineage resolution authoritative. A model, retriever, reranker, or confidence score must not manufacture current truth.

## Workstream A — complete

Implementation landed in core PR #54:

`e14148f504702ae9e708e2d58add4ee5c91bc8de`

PR #54 added:

- historical/as-of durable-event replay support in `src/dkg/pack_corpus.py`;
- reusable `src/dkg/temporal_benchmark.py`;
- versioned real-corpus plan `benchmarks/post-gate2/evolving-corpus-temporal-v1.json`;
- runner `scripts/run_post_gate2_temporal_benchmark.py` with exact Git pin verification;
- deterministic tests in `tests/test_temporal_benchmark.py`;
- durable proof `docs/implementation/2026-08-10-post-gate2-temporal-benchmark-proof.md`.

Final PR #54 CI:

- workflow run `31431210018`;
- job `93594807498`;
- **88 passed in 0.99s**.

## Real-corpus temporal proof

Execution-only core PR #55 was closed without merge after proof.

Exact pack inputs:

- `Pukujan/fossil-common@d583005dce06dbb499c3c0de5c22b899655eb8d2`;
- `Pukujan/fossil-ai-systems@84accd2ee895663990e82ca5b79b592cb503db24`.

Proof run:

- workflow `31431113829`;
- job `93594491275`;
- core suite **88 passed in 0.84s**;
- benchmark `post-gate2-evolving-corpus-v1`: **PASS** across three phases.

### Phase 1 — before supersession

At cutoff `2026-08-10T05:26:04Z`:

- 11 projected documents;
- former SQLite premise `clm_643b698b7e9e6aee6a16c48c` = `supported`;
- dependent prototype `clm_a047d79b8604fadbd44efdf4` = `supported`;
- current SQLite query rank 1, recall@5 1.0.

### Phase 2 — after supersession

At cutoff `2026-08-10T05:26:08Z`:

- 13 projected documents;
- former SQLite premise = `superseded`;
- dependent prototype = `stale_pending_review`;
- accepted durable-core claim `clm_7f5c691c564c30e1b61f8dc0` = `supported`;
- current durable-core query rank 1, recall@5 1.0;
- historical SQLite query rank 1, recall@5 1.0;
- no stale/superseded result ranked ahead of the current relevant result.

### Phase 3 — after later corpus growth

On the latest pinned AI-systems corpus:

- 27 projected documents;
- lifecycle states above remained correct;
- later production-RAG research claims were present;
- current durable-core and historical SQLite queries both remained rank 1, recall@5 1.0;
- repeated-query stability reported full recall and no current-state leakage.

Observed projection rebuild time on that runner stayed about 23.68–25.28 ms. Query latency rose as the projected corpus grew, while correctness remained stable. Treat those timings as baseline observations, not retrieval-policy selection evidence.

## Issue #48 control state

Completed exit criteria:

- research trace committed and ingested into AI-systems with provenance;
- evolving-corpus benchmark committed.

Workstream A's four checklist requirements are checked. Issue #48 remains open.

Remaining high-level work:

1. **B** — answer/citation/unsupported-claim/contradiction/abstention evaluation;
2. **C** — retrieval poisoning / untrusted-context adversarial suite;
3. **F** — replayable query execution receipt;
4. **D / #47** — embedding/hybrid/reranker/model bakeoff when the required providers are available;
5. **E** — conservative adaptive routing only if it beats simple baselines;
6. **G** — ACL/redaction propagation readiness;
7. final decision-log, retained/revised D021 policy, residual-risk, and handoff reconciliation.

## Retrieval/model posture

D021 remains unchanged:

- revision-pinned BGE dense is the normal primary retriever;
- BM25 is an explicit degraded availability fallback;
- current/latest/accepted questions resolve durable lifecycle/provenance;
- lineage/history/disagreement questions use durable lineage/read resolution;
- top-k absence is not evidence of nonexistence;
- retrieval/reranker/model scores never receive truth authority.

Workstream A used BM25 + lifecycle-intent reranking as a provider-independent correctness baseline. It did **not** compare or select new embedding/reranker/model providers.

## Stable repository/corpus identities

Preserve:

- common pack ID `pack_269099f7b2ba43b7a99b9427d64092de`;
- AI-systems pack ID `pack_f024177f89a5442db84171c3dd7f58e5`;
- canonical truth = immutable evidence + stable IDs + append-only validated events + versioned contracts + provenance/history;
- Graphiti/Neo4j, lexical/vector retrieval, rerankers, planners, models, Skills/MCP, and future databases remain replaceable projections/services;
- retrieved/source text is untrusted data;
- model consensus is not external evidence;
- do not casually rename `src/dkg`.

## Suggested next-session prompt

> Continue FOSSIL after Workstream A of Issue #48. Read `AGENTS.md`, `ARCHITECTURE.md`, `docs/HANDOFF_CURRENT.md`, and `docs/handoffs/2026-08-10-chatgpt-session-handoff-post-temporal-benchmark.md` first, then verify GitHub state. Workstream A is complete in core PR #54 / squash `e14148f504702ae9e708e2d58add4ee5c91bc8de`; its exact real-corpus proof passed in execution-only PR #55, run `31431113829`, job `93594491275`. Do not redo A. Continue with Issue #48 Workstream B: end-to-end answer/citation/unsupported-claim/contradiction/abstention evaluation. Start with a provider-independent deterministic baseline and preserve D021 lifecycle/lineage authority; hosted/frontier models should later compete behind existing interfaces rather than become correctness dependencies.
