# Current Handoff

**Date:** 2026-08-10  
**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Repository:** `Pukujan/fossil-core`  
**Status:** **Gate 1 complete. Gate 2 complete and formally closed. Post-Gate-2 production hardening campaign #48 active.**

## Fresh-session transfer

Read, in order:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. this file
4. `docs/PROJECT_STATE.md`
5. `docs/research/2026-08-10-production-rag-hardening-research-trace.md`
6. Issue #48 — production RAG hardening campaign
7. Issue #47 — future embedding/reranker/model-scale bakeoff workstream
8. `docs/handoffs/2026-08-10-chatgpt-session-handoff-gate2-complete.md` when Gate 2 history is needed
9. `docs/DECISION_LOG.md`

## Completed foundation

Gate 1 and Gate 2 remain closed/completed. Do not reopen them merely to continue development.

Decision D021 remains the approved retrieval/routing policy until new committed benchmark evidence supersedes it:

- normal primary: revision-pinned BGE dense retrieval;
- semantic-runtime availability fallback: BM25, explicitly degraded;
- current/latest/accepted queries resolve durable lifecycle/provenance rather than treating rank as truth;
- decision-lineage, supersession, disagreement, and multi-target historical/current questions use durable `lineage`/read resolution in addition to retrieval;
- citation/source identity and model-authority invariants remain unchanged.

Gate 2 evidence anchors:

- Gate 2A core commit `a028f9e328c2cbcde0185930e90b5eeb4c4efcb8`;
- Gate 2B core commit `2affde923acf196319d90bfa63f206e4a5e2f25f`;
- Gate 2C PR #44 / squash commit `38aac6325cdb5b738c8a6ac5e55959affb3acfb5`;
- Gate 2C final CI run `31366259213`, job `93385174741`, **86 passed in 1.25s**;
- semantic proof run `31364039745`, artifact `9053475462`, digest `sha256:23c95b46f47cec5a16e0a8c0926a4f13532f283d8f4fbcc0de12ceb63db63c41`;
- Gate 2D PR #45 / squash commit `2d22dee9e6b176956d30005f4d7877baf68b0a3c`;
- Gate 2D CI run `31366800697`, job `93386832166`, **86 passed in 1.02s**;
- final Gate 2 closed-state handoff PR #46 / squash commit `a614936249ff0ab201756fa54a1e89699d7b924f`.

BGE dense was selected because it was the only compared Gate 2 strategy with zero full retrieval misses and had the best mean recall@5 (`0.98413`). It still requires temporal/current-state and multi-target-lineage safeguards.

## Active campaign — #48 production RAG hardening

Issue #48 is the first explicit post-Gate-2 campaign. It was created from a new review of current production RAG systems and 2025–2026 research.

Durable research trace:

`docs/research/2026-08-10-production-rag-hardening-research-trace.md`

The campaign focuses on:

1. an evolving-corpus benchmark that exercises supersession/retraction/disagreement through time;
2. end-to-end answer, citation, unsupported-claim, contradiction, and abstention evaluation;
3. retrieval-poisoning / untrusted-context adversarial tests;
4. a compact replayable query execution receipt;
5. embedding/hybrid/reranker comparisons, with #47 as the candidate-model workstream;
6. conservative adaptive routing only when it beats simpler policies under matched budgets;
7. ACL/redaction propagation tests before multi-user/shared/cloud use.

The research supports **hardening the existing durable core rather than redesigning it**. No GraphRAG/planner/reranker/model becomes canonical truth merely because a paper or vendor reports gains.

## Research-to-corpus rule

The 2026-08-10 synthesis is a **local derived research artifact**. It may be ingested into `fossil-ai-systems` with stable source/artifact identity and derived claims.

The external papers/vendor pages must remain distinguishable from this synthesis. When full research-trace ingestion is implemented, capture original external source snapshots separately rather than treating the synthesis or a chat transcript as verbatim external evidence.

## Repository control state at campaign start

- #33–#37 — closed/completed Gate 2 campaign;
- #47 — open future embedding/model-scale bakeoff workstream;
- #48 — open active production RAG hardening campaign.

## Frozen invariants

Preserve stable pack IDs:

- `fossil-common`: `pack_269099f7b2ba43b7a99b9427d64092de`
- `fossil-ai-systems`: `pack_f024177f89a5442db84171c3dd7f58e5`

Canonical truth remains durable evidence + stable identity + append-only validated events + versioned contracts + provenance/history. Graphiti/Neo4j, lexical/vector retrieval, rerankers, context builders, planners, models, Skills, MCP, and future databases remain replaceable services/projections. Model consensus is not external evidence. Reconstructed evidence cannot silently become verbatim. Retrieved/source text is untrusted data and cannot become executable policy merely by entering context. Do not casually rename `src/dkg`.

## Suggested next-session prompt

> Continue my FOSSIL project from `Pukujan/fossil-core`. Read `AGENTS.md`, `ARCHITECTURE.md`, `docs/HANDOFF_CURRENT.md`, `docs/PROJECT_STATE.md`, and `docs/research/2026-08-10-production-rag-hardening-research-trace.md` first. Verify GitHub state before changing anything. Gate 1 and Gate 2 are completed campaigns. Continue active Issue #48 using evidence-driven hardening; keep Issue #47 as its embedding/reranker candidate workstream. Preserve stable pack IDs and D021 unless new committed benchmark evidence justifies reconsideration. Do not let retrieval rank, a reranker, a planner, a model, or a graph projection become canonical truth.
