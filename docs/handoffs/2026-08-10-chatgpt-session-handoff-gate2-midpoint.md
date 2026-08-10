# ChatGPT Session Handoff — Gate 2 Midpoint

**Date:** 2026-08-10  
**Repository:** `Pukujan/fossil-core`  
**Campaign:** Gate 2 — Real Corpus + Retrieval/Model Bakeoff (#33)

## Fresh-session order

Read `AGENTS.md`, `ARCHITECTURE.md`, `docs/HANDOFF_CURRENT.md`, this file, `docs/PROJECT_STATE.md`, Gate 2 issues #33–#37, PR #44, and `docs/DECISION_LOG.md`. Verify GitHub before changing anything.

## Current state

- #34 Gate 2A: **closed/completed**.
- #35 Gate 2B: **closed/completed**.
- #36 Gate 2C: **open/current work**.
- #37 Gate 2D: **open/not yet completed**.
- #33 parent: **open**.
- PR #44: **open, draft, mergeable** on `agent/gate2-comparative-bakeoff`.
- PR #44 head at handoff: `1f71b981feb9ff10636901c61bfb16e677a9f258`.
- Exact-head normal CI: run `31364039714`, job `93378520755`, **86 passed in 0.97s**.
- Exact-head comparative proof: run `31364039745`, **success**.

Do not reopen Gate 1 / Issues #1–#10.

## Frozen invariants

Preserve stable pack IDs:

- `fossil-common`: `pack_269099f7b2ba43b7a99b9427d64092de`
- `fossil-ai-systems`: `pack_f024177f89a5442db84171c3dd7f58e5`

Canonical truth is durable evidence + stable identities + append-only validated events + provenance/history. Graphiti/Neo4j, lexical/vector retrieval, models, context construction, Skills, and MCP remain replaceable services/projections. Model consensus is not external evidence. Reconstructed evidence cannot silently become verbatim. Do not casually rename `src/dkg`.

## Gate 2A corpus checkpoint

Pinned real corpus commits used by the history-rich benchmark:

- `Pukujan/fossil-common` — `d583005dce06dbb499c3c0de5c22b899655eb8d2`
- `Pukujan/fossil-ai-systems` — `cf7cf4087bde543cb247a978de2a7252b1b8e4de`

`benchmarks/gate2/real-corpus-history-v2.json` has **21 cases** covering exact lookup, citations, decision lineage, current/history, disagreement, stale/superseded state, cross-pack isolation, deep evidence, conversation lineage, and insufficient-evidence negatives.

Gate 2A landed in core at `a028f9e328c2cbcde0185930e90b5eeb4c4efcb8`.

## Gate 2B adapter checkpoint

Merged core commit: `2affde923acf196319d90bfa63f206e4a5e2f25f`.

Real dense retrieval uses:

- `BAAI/bge-small-en-v1.5`
- model revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`
- Sentence Transformers `5.2.2`
- runtime provenance records Torch `2.13.0`, Transformers `5.14.1`, device, normalization, and revision.

Also implemented: BM25+BGE RRF hybrid, lifecycle-intent reranking, context integration, and optional semantic-runtime behavior.

## Gate 2C / PR #44

PR #44 adds a same-environment four-strategy runner and executable failure taxonomy. The strategies are:

1. BM25 control;
2. signed-token hash embedding control;
3. revision-pinned BGE dense retrieval;
4. BM25+BGE RRF + lifecycle-aware reranking.

The comparison artifact intentionally keeps `selection.selected = null`; #37 owns policy selection.

A temporary workflow `.github/workflows/gate2-comparative-proof.yml` is still on the PR branch and should be removed before landing once durable evidence is committed.

### Persisted proof source

Successful same-environment evidence run: `31363490598`.

Artifact: `9053285685` (`gate2-comparative-results`).  
Digest: `sha256:0db9650c4343d59ad2055ee391c98519a7cd493443f60d6dc6dc10fc6e27b228`.

The earlier run `31363264588` completed the benchmark successfully and failed only because `upload-artifact@v4` ignored the hidden output directory; `include-hidden-files: true` fixed transport. Do not treat that as a benchmark failure.

### Same-environment metrics from the successful comparison artifact

| Strategy | Hit | Recall@5 | MRR | Mean latency | p95 | Peak Python alloc |
|---|---:|---:|---:|---:|---:|---:|
| BM25 | 0.95238 | 0.95238 | 0.81746 | 3.287 ms | 4.560 ms | 51,559 B |
| Hash control | 0.95238 | 0.92063 | 0.83730 | 1.256 ms | 1.463 ms | 34,570 B |
| BGE dense | **1.00000** | **0.98413** | 0.85873 | 36.603 ms | 40.276 ms | 82,048 B |
| Hybrid | 0.95238 | 0.95238 | **0.86667** | 58.636 ms | 66.768 ms | 185,111 B |

All estimated provider cost was $0 in this local run. All four respected pack isolation and stayed below the 4,000-character context budget.

Important failures:

- BM25 and hash both fully miss `current_architecture_after_reconsideration` and surface stale/rejected history ahead of the current answer.
- Hybrid has the best MRR but also fully misses that current-architecture case.
- BGE dense is the only strategy with **zero full retrieval misses**, but the current architecture appears only at rank 5 with rejected history ahead of it, and the three-target `historical_current_supersession_bundle` gets only 2/3 targets at k=5.

This makes BGE dense the leading default candidate, but **that is not yet the Gate 2 policy decision**.

## What the next session should do

Finish #36 first:

1. inspect PR #44 and confirm the committed raw result JSONs match the successful proof;
2. commit the compact comparison/context evidence and a provenance manifest/proof note if not already present;
3. document confidence limits: 21 representative cases, one CPU environment, not a universal provider leaderboard;
4. keep policy selection out of #36;
5. delete the temporary comparative workflow;
6. run final branch-independent CI;
7. mark PR #44 ready, merge it, and close #36 with exact proof references.

Then do #37:

- choose the default retrieval/routing policy from committed evidence;
- define semantic-runtime-unavailable fallback;
- address BGE temporal/current-state leakage and incomplete multi-target lineage recall;
- define rollback/fallback criteria and reconsideration triggers;
- preserve pack boundaries and canonical authority semantics;
- update `docs/DECISION_LOG.md`, `docs/PROJECT_STATE.md`, and `docs/HANDOFF_CURRENT.md`;
- close #37 and then #33 only when Gate 2 exit criteria are satisfied.

## Suggested continuation prompt

Continue FOSSIL from `Pukujan/fossil-core`. Read `AGENTS.md`, `ARCHITECTURE.md`, `docs/HANDOFF_CURRENT.md`, and `docs/handoffs/2026-08-10-chatgpt-session-handoff-gate2-midpoint.md` first. Verify GitHub state. Finish open #36 / PR #44 without reopening Gate 1 or changing stable pack IDs/invariants, then complete #37’s evidence-based retrieval/routing/fallback/rollback policy and close Gate 2 only when its exit criteria are actually satisfied.
