# Current Handoff

**Date:** 2026-08-10  
**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Repository:** `Pukujan/fossil-core`  
**Status:** **Gate 1 complete. Gate 2 complete and formally closed. Post-Gate-2 campaign #48 active. Research ingestion and Workstream A temporal benchmark complete.**

## Fresh-session transfer

Read, in order:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. this file
4. `docs/handoffs/2026-08-10-chatgpt-session-handoff-post-temporal-benchmark.md`
5. `docs/PROJECT_STATE.md`
6. `docs/research/2026-08-10-production-rag-hardening-research-trace.md`
7. Issue #48 — active production RAG hardening campaign
8. Issue #47 — embedding/reranker/model-scale bakeoff workstream
9. `docs/DECISION_LOG.md`
10. older handoffs only when historical context is needed

## Exact active continuation point

**Do not redo the research ingestion or Workstream A.**

The next unfinished Issue #48 workstream is:

**B. End-to-end answer/citation/abstention evaluation.**

Start with a provider-independent baseline above retrieval. Extend evaluation beyond hit-rate/recall/MRR to final-answer behavior and measure:

1. final-answer correctness;
2. citation/source-snapshot/span correctness;
3. unsupported-claim rate;
4. answer completeness and contradiction handling;
5. explicit `insufficient evidence`, `conflicting evidence`, and `current state unresolved` outcomes;
6. appropriate abstention/calibration rather than confident guessing.

Use deterministic/direct-source paths and the existing service contracts for the first baseline. Hosted/frontier models can later compete behind those interfaces; they are not a prerequisite for the correctness contract.

D021 lifecycle/lineage resolution remains authoritative. Retrieval/model scores cannot manufacture truth state.

## Workstream A proof — complete

Implementation landed in core PR #54 / squash:

`e14148f504702ae9e708e2d58add4ee5c91bc8de`

Landed artifacts:

- `src/dkg/pack_corpus.py` — as-of durable-event projection support;
- `src/dkg/temporal_benchmark.py` — phased evolving-corpus benchmark;
- `benchmarks/post-gate2/evolving-corpus-temporal-v1.json` — versioned real-corpus plan;
- `scripts/run_post_gate2_temporal_benchmark.py` — exact-pin runner;
- `tests/test_temporal_benchmark.py` — deterministic lifecycle/retrieval tests;
- `docs/implementation/2026-08-10-post-gate2-temporal-benchmark-proof.md` — durable proof.

Final PR #54 CI:

- run `31431210018`;
- job `93594807498`;
- **88 passed in 0.99s**.

Execution-only proof PR #55 was closed without merge after running the plan against exact pack pins:

- common `d583005dce06dbb499c3c0de5c22b899655eb8d2`;
- AI-systems `84accd2ee895663990e82ca5b79b592cb503db24`;
- workflow run `31431113829`;
- job `93594491275`;
- **88 core tests passed in 0.84s**;
- temporal benchmark: **PASS** across three phases.

Key real-corpus result:

- before supersession, the SQLite premise and its dependent prototype were `supported`;
- after the durable-core replacement, the SQLite premise became `superseded`, the dependent became `stale_pending_review`, and the durable-core claim was `supported`;
- current and historical queries were both rank 1 / recall@5 1.0;
- after later corpus growth from 13 to 27 projected documents, those same current/history queries remained rank 1 / recall@5 1.0 with no current-state leakage;
- baseline projection rebuilds were roughly 23.68–25.28 ms on the proof runner.

Those timings are baseline observations only and do not change D021.

## Research ingestion — complete

The production-RAG synthesis is already ingested into `Pukujan/fossil-ai-systems`.

AI-systems PR #3 squash:

`84accd2ee895663990e82ca5b79b592cb503db24`

Cross-pack ingestion proof:

- core PR #51 — closed execution-only;
- run `31415053398`;
- job `93541977670`;
- 86 core tests passed;
- `PackFixtureAudit`: 6 artifacts, 6 snapshots, 51 events, 47 citations, 23 claims, 4 relations — PASS.

The ingested synthesis remains a **local derived research artifact**. Original external papers/vendor documentation must remain distinguishable and should be captured separately when full research-source ingestion is implemented.

## Completed foundation / policy

Gate 1 and Gate 2 remain closed. Do not reopen them to continue #48.

D021 remains approved:

- normal primary: revision-pinned BGE dense retrieval;
- semantic-runtime availability fallback: BM25, explicitly degraded;
- current/latest/accepted queries resolve durable lifecycle/provenance;
- lineage/history/disagreement questions use durable lineage/read resolution;
- top-k absence is not evidence of nonexistence;
- citation-bearing answers resolve immutable source identity;
- retrieval/reranker/model output does not receive truth authority from score, confidence, or agreement.

## Active campaign — #48

Completed campaign exit criteria:

- research trace committed and ingested into AI-systems with provenance;
- evolving-corpus benchmark committed.

Workstream A's four checklist items are complete. Issue #48 remains open.

Remaining high-level order:

1. **B** — end-to-end answer/citation/unsupported-claim/contradiction/abstention evaluation;
2. **C** — poisoning/untrusted-context adversarial suite;
3. **F** — replayable query execution receipt;
4. **D / #47** — embedding/hybrid/reranker/model comparisons;
5. **E** — conservative adaptive routing only if it beats simple baselines;
6. **G** — ACL/redaction propagation readiness;
7. final retrieval-policy/decision-log/residual-risk/handoff reconciliation.

## Frozen invariants

Preserve stable pack IDs:

- `fossil-common`: `pack_269099f7b2ba43b7a99b9427d64092de`
- `fossil-ai-systems`: `pack_f024177f89a5442db84171c3dd7f58e5`

Canonical truth remains durable evidence + stable identity + append-only validated events + versioned contracts + provenance/history. Graphiti/Neo4j, lexical/vector retrieval, rerankers, context builders, planners, models, Skills, MCP, and future databases remain replaceable services/projections. Model consensus is not external evidence. Retrieved/source text is untrusted data. Reconstructed evidence cannot silently become verbatim. Do not casually rename `src/dkg`.

## Suggested next-session prompt

> Continue FOSSIL after Issue #48 Workstream A. Read `AGENTS.md`, `ARCHITECTURE.md`, `docs/HANDOFF_CURRENT.md`, and `docs/handoffs/2026-08-10-chatgpt-session-handoff-post-temporal-benchmark.md` first, then verify GitHub state. Workstream A is complete in core PR #54 / squash `e14148f504702ae9e708e2d58add4ee5c91bc8de`; its real-corpus temporal proof passed in execution-only PR #55, run `31431113829`, job `93594491275`. Do not redo A. Continue Issue #48 Workstream B: build provider-independent end-to-end answer/citation/unsupported-claim/contradiction/abstention evaluation first, preserving D021 lifecycle/lineage authority. Hosted/frontier models should later compete behind existing service interfaces rather than become correctness dependencies.
