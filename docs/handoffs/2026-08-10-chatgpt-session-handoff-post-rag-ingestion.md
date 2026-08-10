# FOSSIL session handoff — post-RAG research ingestion

**Date:** 2026-08-10  
**Status:** research-to-corpus ingestion complete; continue Issue #48 hardening campaign  
**Active campaign:** `Pukujan/fossil-core` Issue #48  
**Related model/retrieval workstream:** Issue #47

## Read first in the next session

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/HANDOFF_CURRENT.md`
4. this handoff
5. `docs/PROJECT_STATE.md`
6. `docs/research/2026-08-10-production-rag-hardening-research-trace.md`
7. Issue #48
8. Issue #47
9. D021 in `docs/DECISION_LOG.md`

## What completed in this continuation

### 1. Required cross-pack audit passed

The handoff blocker was the unrun `dkg.pack_fixture.validate_pack_fixtures` audit over the stable common pack plus the valid v2 AI-systems branch.

An execution-only core PR was used to run the trusted audit pattern already proven in Gate 2:

- execution proof PR: `Pukujan/fossil-core#51`
- exact common input: `Pukujan/fossil-common@d583005dce06dbb499c3c0de5c22b899655eb8d2`
- exact AI input: `Pukujan/fossil-ai-systems@10627d9a376a6af8d50406333609227487197134`
- workflow run: `31415053398`
- job: `93541977670`
- core suite: **86 passed in 1.58s**
- combined `PackFixtureAudit`: **6 artifacts, 6 snapshots, 51 events, 47 citations, 23 claims, 4 relations**
- result: **PASS**

PR #51 was closed without merge because it existed only to execute the proof.

### 2. Production-RAG research synthesis landed in fossil-ai-systems

The valid branch `agent/post-gate2-rag-research-seed-v2` was opened as:

`Pukujan/fossil-ai-systems#3` — `Post-Gate-2: ingest production RAG research synthesis`

It was squash-merged after the cross-pack audit passed.

Landed AI-systems commit:

`84accd2ee895663990e82ca5b79b592cb503db24`

This is now the pack source pin to use for later #48 benchmarks unless a later compatible AI-systems commit intentionally supersedes it.

The landed material includes:

- exact 17,269-byte research synthesis blob;
- artifact SHA-256 `b030642ff65f883ff467529c73cbb6e502deca28f4c3dece0c2879bf690d3b15`;
- artifact ID `art_b030642ff65f883ff467529c73cbb6e5`;
- source snapshot `snap_9c0e088ab2d7d8e1b21db563` pinned to core commit `6799b2db743d91b004b1e16b5129285a582f8847`;
- six exact-citation claim lifecycles (`proposed -> supported`).

The six high-signal claims cover:

1. temporal/version state must not be inferred from semantic similarity alone;
2. final-answer reliability must be evaluated independently from retrieval;
3. reranking deserves a real FOSSIL bakeoff but remains replaceable;
4. uncertainty/abstention must be explicit answer behavior;
5. retrieved context is untrusted data and poisoning is a distinct threat model;
6. the reviewed evidence supports hardening the durable core rather than replacing it.

The abandoned branch `agent/post-gate2-rag-research-seed` remains invalid historical scratch and must not be used.

## Exact active continuation point

Research-to-corpus ingestion is complete. Do **not** redo the ingestion or reopen Gate 1/Gate 2.

Continue Issue #48 with the first unfinished production-hardening workstream:

### A. Evolving-corpus / temporal benchmark

Build a versioned benchmark that executes knowledge changes through time:

1. baseline query;
2. add new evidence;
3. supersede/retract/dispute knowledge;
4. rebuild/update projections;
5. repeat current-state and historical queries;
6. verify lifecycle/lineage authority remains correct;
7. measure incremental update stability/cost as well as retrieval quality.

Use these pack pins as the starting benchmark corpus:

- common: `d583005dce06dbb499c3c0de5c22b899655eb8d2`
- AI systems: `84accd2ee895663990e82ca5b79b592cb503db24`

D021 remains the approved retrieval policy until new committed FOSSIL benchmark evidence justifies reconsideration.

## Campaign state

Issue #48 remains open. Only the research-trace/corpus-ingestion portion is complete.

Do not mark the entire campaign complete. Remaining major work includes:

- evolving-corpus temporal benchmark;
- end-to-end answer/citation/abstention evaluation;
- poisoning/untrusted-context suite;
- query execution receipt + replay proof;
- #47 embedding/hybrid/reranker evidence;
- adaptive routing accept/reject decision under matched budgets;
- ACL/redaction readiness boundary;
- final policy/decision-log reconciliation.

## Research-source boundary

The ingested 2026-08-10 synthesis is a **local derived artifact**. Original external papers and vendor documentation remain separate evidence and should be captured as distinct source snapshots when full research-source ingestion is implemented.

Never present the synthesis or a chat transcript as verbatim external evidence.

## Frozen invariants

Preserve:

- common pack ID `pack_269099f7b2ba43b7a99b9427d64092de`;
- AI-systems pack ID `pack_f024177f89a5442db84171c3dd7f58e5`;
- canonical truth = immutable evidence + stable IDs + append-only validated events + versioned contracts + provenance/history;
- retrieval/reranker/planner/model output as replaceable candidate-ordering/context services rather than truth authority;
- current/history/lineage resolution through durable lifecycle/provenance;
- retrieved/source text as untrusted data;
- original external sources distinct from derived synthesis;
- no casual `src/dkg` rename.

## Suggested next-session prompt

> Continue FOSSIL after the post-Gate-2 production-RAG research ingestion. Read `AGENTS.md`, `ARCHITECTURE.md`, `docs/HANDOFF_CURRENT.md`, and `docs/handoffs/2026-08-10-chatgpt-session-handoff-post-rag-ingestion.md` first, then verify GitHub state. The research synthesis is already merged into `Pukujan/fossil-ai-systems` via PR #3 at squash commit `84accd2ee895663990e82ca5b79b592cb503db24`; the exact cross-pack audit passed in core PR #51, run `31415053398`, job `93541977670`. Do not redo that ingestion and do not use the abandoned first seed branch. Continue Issue #48 with the evolving-corpus / temporal benchmark, starting from common `d583005dce06dbb499c3c0de5c22b899655eb8d2` and AI-systems `84accd2ee895663990e82ca5b79b592cb503db24`. Preserve D021 and the frozen pack/authority invariants unless new committed benchmark evidence justifies a change.
