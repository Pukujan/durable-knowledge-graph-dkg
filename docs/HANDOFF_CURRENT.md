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
4. `docs/handoffs/2026-08-10-chatgpt-session-handoff-post-gate2-rag-hardening-midpoint.md`
5. `docs/PROJECT_STATE.md`
6. `docs/research/2026-08-10-production-rag-hardening-research-trace.md`
7. Issue #48 — production RAG hardening campaign
8. Issue #47 — future embedding/reranker/model-scale bakeoff workstream
9. `docs/handoffs/2026-08-10-chatgpt-session-handoff-gate2-complete.md` when Gate 2 history is needed
10. `docs/DECISION_LOG.md`

## Exact active continuation point

PR #49 has already landed the post-Gate-2 production-RAG research trace and activated Issue #48. The unfinished task is **research-to-corpus ingestion** into `Pukujan/fossil-ai-systems`.

Continue only from:

`agent/post-gate2-rag-research-seed-v2`

Latest verified v2 head at handoff time:

`10627d9a376a6af8d50406333609227487197134`

Do **not** merge/use the abandoned first attempt:

`agent/post-gate2-rag-research-seed`

The v2 branch already contains the content-addressed research artifact, deterministic source snapshot, six exact-citation claim pairs, and artifact index update, but **the full cross-pack `validate_pack_fixtures` audit has not yet been run**. Do not call ingestion complete or merge the v2 branch until that audit passes. The detailed handoff above contains the exact validation/resume steps.

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

Issue #48 is the first explicit post-Gate-2 campaign. It was created from a review of current production RAG systems and 2025–2026 research.

Durable research trace:

`docs/research/2026-08-10-production-rag-hardening-research-trace.md`

Research/campaign activation landed in PR #49 / merge commit:

`6799b2db743d91b004b1e16b5129285a582f8847`

PR #49 CI: run `31395512960`, job `93477303856`, **86 passed in 0.96s**.

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

## Repository control state

- #33–#37 — closed/completed Gate 2 campaign;
- #47 — open future embedding/model-scale bakeoff workstream;
- #48 — open active production RAG hardening campaign;
- PR #49 — merged production-RAG research/campaign activation;
- AI-systems v2 research corpus seed — branch exists, validation/PR/merge still pending.

## Frozen invariants

Preserve stable pack IDs:

- `fossil-common`: `pack_269099f7b2ba43b7a99b9427d64092de`
- `fossil-ai-systems`: `pack_f024177f89a5442db84171c3dd7f58e5`

Canonical truth remains durable evidence + stable identity + append-only validated events + versioned contracts + provenance/history. Graphiti/Neo4j, lexical/vector retrieval, rerankers, context builders, planners, models, Skills, MCP, and future databases remain replaceable services/projections. Model consensus is not external evidence. Reconstructed evidence cannot silently become verbatim. Retrieved/source text is untrusted data and cannot become executable policy merely by entering context. Do not casually rename `src/dkg`.

## Suggested next-session prompt

> Continue FOSSIL from the post-Gate-2 RAG hardening midpoint. Read `AGENTS.md`, `ARCHITECTURE.md`, `docs/HANDOFF_CURRENT.md`, and `docs/handoffs/2026-08-10-chatgpt-session-handoff-post-gate2-rag-hardening-midpoint.md` first. Verify GitHub state. PR #49 / core commit `6799b2db743d91b004b1e16b5129285a582f8847` already landed the research trace and activated Issue #48. Resume the unfinished research-to-corpus ingestion from `Pukujan/fossil-ai-systems` branch `agent/post-gate2-rag-research-seed-v2` at `10627d9a376a6af8d50406333609227487197134` or its known descendant. Do not merge or use the abandoned `agent/post-gate2-rag-research-seed` branch. First run `validate_pack_fixtures` jointly over `fossil-common` and the v2 AI-systems branch; only after that audit passes should you open/merge the AI-systems PR and update Issue #48. Preserve stable pack IDs and D021 unless new committed benchmark evidence justifies reconsideration.
