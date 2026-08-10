# FOSSIL Session Handoff — Post-Retrieval-Bakeoff Stage 1

**Date:** 2026-08-10  
**Repository:** `Pukujan/fossil-core`  
**Campaign:** Issue #48 — production RAG hardening  
**State:** Gate 1 complete; Gate 2 complete/formally closed; Workstreams A/B/C/F complete; Workstream D active. **D stage 1 is complete; Qwen3-Embedding 0.6B is the exact next step.**

## Read first

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/HANDOFF_CURRENT.md`
4. this file
5. `docs/PROJECT_STATE.md`
6. `docs/implementation/2026-08-10-post-gate2-retrieval-bakeoff-stage1-proof.md`
7. `docs/implementation/2026-08-10-post-gate2-query-execution-receipt-proof.md`
8. `docs/implementation/2026-08-10-post-gate2-retrieval-poisoning-proof.md`
9. `docs/implementation/2026-08-10-post-gate2-answer-reliability-proof.md`
10. `docs/operations/LITELLM-GATEWAY.md`
11. Issue #48
12. Issue #47
13. `docs/DECISION_LOG.md`

Verify GitHub state before changing anything.

## Do not redo

- production-RAG research ingestion;
- Workstream A — temporal/evolving corpus;
- Workstream B — answer/citation/abstention reliability;
- Workstream C — retrieval poisoning/untrusted context;
- Workstream F — query execution receipts;
- Workstream D stage 1 — incumbent/hybrid/real-reranker matched bakeoff.

## D stage 1 landed

Core PR #67 landed the stage-1 comparison surface.

Execution-only PR #68 was a failed-first probe and was closed unmerged. It showed that the original bakeoff exit semantics incorrectly treated a weak challenger as benchmark infrastructure failure and also exposed a hidden-artifact upload issue. The benchmark expectations were not relaxed.

Execution-only PR #69 was the corrected final real-semantic proof and was closed unmerged after PASS.

Stage-1 proof inputs:

- common pack revision `d583005dce06dbb499c3c0de5c22b899655eb8d2`;
- AI-systems pack revision `84accd2ee895663990e82ca5b79b592cb503db24`;
- 27 projected documents;
- 21 history-rich retrieval cases;
- 6 Workstream-B answer cases;
- 6 routes;
- 36 Workstream-F receipts;
- real D021 `BAAI/bge-small-en-v1.5@5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` on CPU;
- real `cross-encoder/ms-marco-MiniLM-L6-v2@ce0834f22110de6d9222af7a7a03628121708969` on CPU, batch 16, max length 512.

The final stage gate passed with pack isolation intact and the incumbent D021 downstream answer/citation/unsupported-claim guardrails intact. Challenger routes have explicit `eligible_for_promotion` and `disqualifying_reasons` evidence. Stage 1 does **not** authorize replacing D021.

See `docs/implementation/2026-08-10-post-gate2-retrieval-bakeoff-stage1-proof.md`.

## Exact next task — Qwen3-Embedding 0.6B

Start D stage 2 with the Qwen3-Embedding 0.6B class candidate.

Before committing benchmark code or executing the candidate:

- verify the official model repository;
- pin an immutable model revision;
- pin runtime/library versions;
- record precision/quantization/device/hardware;
- record embedding dimensionality/normalization configuration;
- keep corpus pack revisions identical to the stage-1 matched comparison unless a versioned benchmark change is explicitly justified.

Reuse:

- the stage-1 21-case retrieval benchmark;
- the six Workstream-B answer cases;
- `fossil-untrusted-context-v1`;
- `fossil-lineage-context-v1`;
- `fossil.query-execution-receipt.v1`;
- matched route/candidate budgets when comparison claims require them.

Evaluate retrieval metrics, decision-critical misses, current-vs-superseded leakage, downstream answer/citation/unsupported claims, pack isolation, latency, memory/resources, and exact execution identity.

Do not automatically proceed to 4B or 8B. The 0.6B result and runner/resource evidence must justify continuing.

## D021 remains frozen

- pinned BGE dense remains the normal primary retriever;
- BM25 remains explicit degraded fallback;
- lifecycle/provenance and lineage/read-state resolution remain deterministic authority;
- top-k absence is not evidence of nonexistence;
- exact citations resolve immutable source identity;
- retrieved text is untrusted data;
- retrieval/reranker/model/consensus scores are not truth;
- receipts are observability evidence, not truth or mutation authority;
- agents propose and deterministic gates commit.

Stable pack IDs:

- common `pack_269099f7b2ba43b7a99b9427d64092de`;
- AI systems `pack_f024177f89a5442db84171c3dd7f58e5`.

Do not casually rename `src/dkg`.

## Remaining campaign order

1. D stage 2 — Qwen3-Embedding 0.6B;
2. D 4B / 8B only if justified;
3. E — conservative adaptive routing only if benchmark justified;
4. G — ACL/redaction propagation readiness;
5. final D021/retrieval-policy reconciliation;
6. decision log + residual risks + final handoff.
