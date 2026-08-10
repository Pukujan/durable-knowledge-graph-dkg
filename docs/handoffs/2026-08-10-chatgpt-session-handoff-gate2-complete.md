# ChatGPT Session Handoff — Gate 2 Complete

**Date:** 2026-08-10  
**Repository:** `Pukujan/fossil-core`  
**Campaign:** Gate 2 — Real Corpus + Retrieval/Model Bakeoff (#33)

## Status

Gate 1 remains complete. Gate 2 is complete once #37's documentation PR is merged and Issues #37 and #33 are closed.

Do not reopen Gate 1 / Issues #1–#10 or Gate 2 children #34–#37 merely to continue development. Open a new issue/campaign for new work.

## Frozen invariants

Preserve stable pack IDs:

- `fossil-common`: `pack_269099f7b2ba43b7a99b9427d64092de`
- `fossil-ai-systems`: `pack_f024177f89a5442db84171c3dd7f58e5`

Canonical truth remains durable evidence + stable identity + append-only validated events + provenance/history. Graphiti/Neo4j, lexical/vector retrieval, context builders, models, Skills, MCP, and future databases remain replaceable services/projections. Model consensus is not external evidence. Reconstructed evidence cannot silently become verbatim. Do not casually rename `src/dkg`.

## Gate 2A — real corpus

Pinned history-rich source corpus:

- `Pukujan/fossil-common` — `d583005dce06dbb499c3c0de5c22b899655eb8d2`
- `Pukujan/fossil-ai-systems` — `cf7cf4087bde543cb247a978de2a7252b1b8e4de`

`benchmarks/gate2/real-corpus-history-v2.json` contains 21 real cases spanning exact lookup, citation recovery, current/history, decision lineage, disagreement, stale/superseded state, cross-pack isolation, deep evidence, conversation lineage, and insufficient-evidence negatives.

Gate 2A core commit: `a028f9e328c2cbcde0185930e90b5eeb4c4efcb8`.

## Gate 2B — real retrieval adapters

Core commit: `2affde923acf196319d90bfa63f206e4a5e2f25f`.

Real semantic identity used by Gate 2:

- BGE model `BAAI/bge-small-en-v1.5`
- revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`
- Sentence Transformers `5.2.2`
- Torch `2.13.0`
- Transformers `5.14.1`
- normalized embeddings enabled

Also available behind replaceable interfaces: BM25+BGE RRF, lifecycle-aware reranking, and optional semantic-runtime behavior.

## Gate 2C — comparative bakeoff

Issue #36 is closed completed. PR #44 merged as squash commit:

`38aac6325cdb5b738c8a6ac5e55959affb3acfb5`

Final branch-independent CI on the landing head:

- run `31366259213`
- job `93385174741`
- **86 passed in 1.25s**

Exact-head semantic comparative proof:

- run `31364039745`
- head `1f71b981feb9ff10636901c61bfb16e677a9f258`
- artifact `9053475462` (`gate2-comparative-results`)
- digest `sha256:23c95b46f47cec5a16e0a8c0926a4f13532f283d8f4fbcc0de12ceb63db63c41`

Durable comparison evidence:

- `benchmarks/gate2/results/2026-08-10-comparative/comparison-summary.json`
- `docs/implementation/2026-08-10-gate2-comparative-bakeoff-proof.md`

Exact-head metrics:

| Strategy | Hit | Recall@5 | MRR | Mean latency | p95 | Peak alloc |
|---|---:|---:|---:|---:|---:|---:|
| BM25 | 0.95238 | 0.95238 | 0.81746 | 3.270 ms | 4.566 ms | 58,844 B |
| Hash control | 0.95238 | 0.92063 | 0.83730 | 1.283 ms | 1.558 ms | 34,100 B |
| BGE dense | **1.00000** | **0.98413** | 0.85873 | 36.201 ms | 38.535 ms | 81,779 B |
| Hybrid | 0.95238 | 0.95238 | **0.86667** | 58.658 ms | 66.023 ms | 183,065 B |

Stable qualitative conclusions:

- BGE dense is the only strategy with zero full retrieval misses and has the best mean recall.
- BM25, hash, and hybrid fully miss `current_architecture_after_reconsideration`.
- BGE gets the current architecture only at rank 5 behind rejected/history material.
- BGE retrieves only 2/3 targets in `historical_current_supersession_bundle` at k=5.
- Hybrid's better MRR does not outweigh its decision-critical full miss.
- No strategy violated pack isolation.
- All measured context probes stayed below the 4,000-character reference budget.
- All estimated provider cost was `$0` in the local proof environment.

## Gate 2D — default policy

Durable decision: D021 in `docs/DECISION_LOG.md`.

Policy proof: `docs/implementation/2026-08-10-gate2-default-retrieval-policy.md`.

Selected policy:

1. **Primary:** pinned BGE dense retrieval.
2. **Availability fallback:** BM25, explicitly degraded. Hash control is not the fallback.
3. **Current-state safeguard:** retrieval rank is not durable truth; current/latest/accepted queries resolve lifecycle/provenance before answering.
4. **Lineage safeguard:** decision-lineage, supersession, disagreement, and multi-target historical/current questions use durable `lineage`/read resolution in addition to retrieval; top-k absence is not proof of nonexistence.
5. **Citation safeguard:** exact source snapshot/span/hash resolution remains mandatory.
6. **Authority safeguard:** retrieval/model output remains candidate/context material; model agreement is not evidence.

BM25 is only an availability fallback. A quality/configuration rollback returns to the last known benchmark-passing BGE profile.

Hard rollback conditions include pack isolation violation, unaudited runtime/model substitution, weakened citation semantics, bypassed current-state safeguards, or a new full miss on the frozen reference set where the approved BGE profile had none.

Reconsider D021 when the corpus changes materially, BGE/runtime identity changes, a competitor removes the observed weaknesses without new critical misses, deployment resource constraints change materially, new recurring failure classes appear, or degraded mode becomes common.

## Current repository control state

After the Gate 2D documentation PR lands and #37/#33 close, there should be **zero open Gate 2 issues**. At the start of a future session, verify GitHub rather than assuming this handoff is still current.

Do not invent a Gate 3 from chat context alone. New work should begin with an explicit issue/campaign and should cite D021/Gate 2 evidence when changing retrieval policy.

## Start order for the next session

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/HANDOFF_CURRENT.md`
4. this handoff
5. `docs/PROJECT_STATE.md`
6. `docs/DECISION_LOG.md`
7. current open GitHub issues/PRs

The chat UI is not required to recover the project state.
