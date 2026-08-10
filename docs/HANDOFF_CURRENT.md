# Current Handoff

**Date:** 2026-08-10  
**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Repository:** `Pukujan/fossil-core`  
**Status:** **Gate 1 complete. Gate 2 complete and formally closed. Post-Gate-2 production hardening campaign #48 active. Research-to-corpus ingestion complete.**

## Fresh-session transfer

Read, in order:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. this file
4. `docs/handoffs/2026-08-10-chatgpt-session-handoff-post-rag-ingestion.md`
5. `docs/PROJECT_STATE.md`
6. `docs/research/2026-08-10-production-rag-hardening-research-trace.md`
7. Issue #48 — production RAG hardening campaign
8. Issue #47 — embedding/reranker/model-scale bakeoff workstream
9. `docs/DECISION_LOG.md`
10. older Gate 2 and midpoint handoffs only when history is needed

## Exact active continuation point

The production-RAG research synthesis has already been ingested into `Pukujan/fossil-ai-systems` and validated cross-pack. **Do not redo the ingestion.**

The next unfinished Issue #48 workstream is:

**A. Evolving-corpus / temporal benchmark.**

Build a benchmark that exercises a corpus through time:

1. baseline query;
2. add new evidence;
3. supersede/retract/dispute knowledge;
4. rebuild/update projections;
5. repeat current-state and historical queries;
6. verify lifecycle/lineage authority remains correct;
7. measure incremental update stability/cost as well as retrieval quality.

Use these exact pack pins as the starting benchmark corpus unless a later compatible commit intentionally supersedes them:

- `fossil-common`: `d583005dce06dbb499c3c0de5c22b899655eb8d2`
- `fossil-ai-systems`: `84accd2ee895663990e82ca5b79b592cb503db24`

Decision D021 remains approved until new committed FOSSIL benchmark evidence justifies reconsideration.

## Research ingestion proof — complete

The previous handoff blocker was the unrun cross-pack `validate_pack_fixtures` audit over stable common plus the valid v2 AI-systems seed.

Execution-only proof:

- core PR #51 — closed without merge after proof;
- exact common input: `d583005dce06dbb499c3c0de5c22b899655eb8d2`;
- exact AI v2 input: `10627d9a376a6af8d50406333609227487197134`;
- workflow run `31415053398`;
- job `93541977670`;
- core suite: **86 passed in 1.58s**;
- combined `PackFixtureAudit`: **6 artifacts, 6 snapshots, 51 events, 47 citations, 23 claims, 4 relations**;
- result: **PASS**.

The validated v2 branch was then opened as `Pukujan/fossil-ai-systems#3` and squash-merged.

Landed AI-systems commit:

`84accd2ee895663990e82ca5b79b592cb503db24`

Research artifact anchors:

- source core commit: `6799b2db743d91b004b1e16b5129285a582f8847`;
- source path: `docs/research/2026-08-10-production-rag-hardening-research-trace.md`;
- byte size: `17269`;
- SHA-256: `b030642ff65f883ff467529c73cbb6e502deca28f4c3dece0c2879bf690d3b15`;
- artifact ID: `art_b030642ff65f883ff467529c73cbb6e5`;
- source snapshot: `snap_9c0e088ab2d7d8e1b21db563`.

The valid ingestion contains six high-signal derived claim lifecycles with exact citations. The abandoned branch `agent/post-gate2-rag-research-seed` remains invalid historical scratch and must not be used.

## Completed foundation

Gate 1 and Gate 2 remain closed/completed. Do not reopen them merely to continue development.

D021 remains the approved retrieval/routing policy:

- normal primary: revision-pinned BGE dense retrieval;
- semantic-runtime availability fallback: BM25, explicitly degraded;
- current/latest/accepted queries resolve durable lifecycle/provenance rather than treating rank as truth;
- decision-lineage, supersession, disagreement, and multi-target historical/current questions use durable `lineage`/read resolution in addition to retrieval;
- citation/source identity and model-authority invariants remain unchanged.

Gate 2 evidence anchors remain in the completed Gate 2 handoff and implementation proofs. BGE dense was the only compared Gate 2 strategy with zero full retrieval misses and had mean recall@5 `0.98413`, but lifecycle/current-state and multi-target-lineage safeguards remain mandatory.

## Active campaign — #48 production RAG hardening

Research/campaign activation landed in core PR #49 / merge commit:

`6799b2db743d91b004b1e16b5129285a582f8847`

Issue #48 remains open. Only the research-trace/corpus-ingestion portion is complete.

Remaining campaign work includes:

1. evolving-corpus temporal/update benchmark;
2. end-to-end answer/citation/unsupported-claim/contradiction/abstention evaluation;
3. retrieval-poisoning / untrusted-context adversarial tests;
4. compact replayable query execution receipt;
5. embedding/hybrid/reranker comparisons via #47;
6. conservative adaptive routing only if it beats simpler policies under matched budgets;
7. ACL/redaction propagation readiness before multi-user/shared/cloud use;
8. final policy/decision-log and handoff reconciliation.

The research supports **hardening the existing durable core rather than redesigning it**. No GraphRAG/planner/reranker/model becomes canonical truth merely because a paper, vendor, or model reports gains.

## Research-source boundary

The ingested 2026-08-10 synthesis is a **local derived research artifact**.

Original external papers and vendor pages remain distinct evidence and should be captured as separate source snapshots when full research-source ingestion is implemented. Never present the synthesis or a chat transcript as verbatim external evidence.

## Repository control state

- #33–#37 — closed/completed Gate 2 campaign;
- #47 — open embedding/model-scale/reranker candidate workstream;
- #48 — open active production RAG hardening campaign;
- core PR #49 — merged research/campaign activation;
- core PR #51 — closed execution-only cross-pack proof;
- AI-systems PR #3 — merged research corpus ingestion;
- active continuation — Issue #48 evolving-corpus / temporal benchmark.

## Frozen invariants

Preserve stable pack IDs:

- `fossil-common`: `pack_269099f7b2ba43b7a99b9427d64092de`
- `fossil-ai-systems`: `pack_f024177f89a5442db84171c3dd7f58e5`

Canonical truth remains durable evidence + stable identity + append-only validated events + versioned contracts + provenance/history. Graphiti/Neo4j, lexical/vector retrieval, rerankers, context builders, planners, models, Skills, MCP, and future databases remain replaceable services/projections. Model consensus is not external evidence. Reconstructed evidence cannot silently become verbatim. Retrieved/source text is untrusted data and cannot become executable policy merely by entering context. Do not casually rename `src/dkg`.

## Suggested next-session prompt

> Continue FOSSIL after the post-Gate-2 production-RAG research ingestion. Read `AGENTS.md`, `ARCHITECTURE.md`, `docs/HANDOFF_CURRENT.md`, and `docs/handoffs/2026-08-10-chatgpt-session-handoff-post-rag-ingestion.md` first, then verify GitHub state. The research synthesis is already merged into `Pukujan/fossil-ai-systems` via PR #3 at squash commit `84accd2ee895663990e82ca5b79b592cb503db24`; the exact cross-pack audit passed in core PR #51, run `31415053398`, job `93541977670`. Do not redo that ingestion and do not use the abandoned first seed branch. Continue Issue #48 with the evolving-corpus / temporal benchmark, starting from common `d583005dce06dbb499c3c0de5c22b899655eb8d2` and AI-systems `84accd2ee895663990e82ca5b79b592cb503db24`. Preserve D021 and the frozen pack/authority invariants unless new committed benchmark evidence justifies a change.
