# Gate 2D default retrieval/routing policy

**Date:** 2026-08-10  
**Issue:** #37  
**Parent:** #33  
**Evidence:** Gate 2C / #36, PR #44, squash commit `38aac6325cdb5b738c8a6ac5e55959affb3acfb5`

## Decision

The Gate 2 default retrieval policy is:

1. **Primary retriever:** revision-pinned BGE dense retrieval using `BAAI/bge-small-en-v1.5@5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` through the existing replaceable semantic retriever interface.
2. **Availability fallback:** BM25, explicitly marked as degraded retrieval. The hash-embedding control is not the fallback.
3. **Temporal/current-state safeguard:** retrieval rank is candidate ordering, not durable truth. Queries asking for current/latest/accepted state must resolve lifecycle/provenance before presenting a current conclusion; rejected, superseded, retracted, stale, or disputed material cannot become current merely because it ranks higher.
4. **Lineage/multi-target safeguard:** questions asking why a decision changed, historical/current bundles, supersession paths, disagreement, or other multi-target lineage must use durable `lineage`/read resolution in addition to retrieval. A top-k miss is not proof that lineage or evidence does not exist.
5. **Citation/source safeguard:** retrieval score never substitutes for exact immutable source/citation resolution. Citation-bearing answers must still resolve the intended source snapshot/span/hash.
6. **Authority safeguard:** retrieval/model output remains candidate/context material. Model agreement is not evidence, and small/local model output remains candidate-only unless the independent evidence/risk policy permits more authority.

This is a routed policy, not a declaration that one retriever is canonical truth.

## Why BGE dense is the primary

The exact-head Gate 2C comparison over the 21-case history-rich real corpus recorded:

| Strategy | Hit rate | Mean recall@5 | MRR | Mean latency | p95 | Peak Python alloc |
|---|---:|---:|---:|---:|---:|---:|
| BM25 | 0.95238 | 0.95238 | 0.81746 | 3.270 ms | 4.566 ms | 58,844 B |
| Hash embedding control | 0.95238 | 0.92063 | 0.83730 | 1.283 ms | 1.558 ms | 34,100 B |
| **BGE dense** | **1.00000** | **0.98413** | 0.85873 | 36.201 ms | 38.535 ms | 81,779 B |
| BM25+BGE RRF + lifecycle rerank | 0.95238 | 0.95238 | **0.86667** | 58.658 ms | 66.023 ms | 183,065 B |

BGE dense is the only compared strategy with zero full retrieval misses and has the best mean recall. Its roughly 36 ms mean CPU latency and ~82 KB peak Python allocation were acceptable in the measured local environment relative to the quality gain. Estimated provider cost was `$0` for all compared local strategies.

The hybrid is **not** selected despite higher MRR because it fully misses the key `current_architecture_after_reconsideration` case. Aggregate ranking score does not outweigh a decision-critical full miss.

The hash control is **not** selected as fallback because it has lower recall than BM25 and shares the key current-architecture full miss. Its lower latency does not justify the quality loss.

## Known BGE weaknesses and mandatory safeguards

### Current-state ranking leakage

BGE retrieves the correct current architecture but places it at rank 5 while rejected/history material appears above it. Therefore:

- current/latest/accepted queries must not equate top rank with current truth;
- durable lifecycle state and supersession provenance must be resolved before a current answer is emitted;
- historical material may be included when useful, but it must be labeled as historical/rejected/superseded rather than silently collapsed into the current answer;
- if current state cannot be resolved from durable lifecycle/provenance, the system must preserve uncertainty rather than infer truth from retrieval order.

### Incomplete multi-target lineage recall

BGE retrieves only 2 of 3 targets for `historical_current_supersession_bundle` at `k=5`. Therefore:

- decision-lineage, supersession, disagreement, and historical/current bundle tasks route to durable lineage/read operations after candidate retrieval;
- callers may expand candidate depth when useful, but candidate-depth tuning is not a replacement for lineage resolution and must be rebenchmarked before becoming a new default;
- absence from top-k cannot be used as evidence of nonexistence.

## Context policy

The existing `BudgetedContextProvider` remains the context-construction mechanism. Gate 2C used a 4,000-character reference budget, and all four compared context probes stayed within that budget without truncation/overload.

The 4,000-character value is a benchmark-backed reference profile for this corpus, **not a frozen universal context limit**. A materially different context budget, chunking strategy, or context builder remains a replaceable service choice and should be re-evaluated against the versioned benchmark set.

## Availability fallback

When the optional semantic runtime/model cannot be constructed or used:

1. fall back to `BM25Retriever` over the same pack-filtered durable retrieval projection;
2. expose the active BM25 service metadata and an explicit degraded-retrieval status to the harness/caller; do not silently claim the BGE policy is active;
3. preserve the same pack boundaries, citation semantics, lifecycle rules, and authority rules;
4. for current/history/lineage-sensitive tasks, require durable lifecycle/lineage resolution before a confident answer because BM25 fully missed the key current-architecture case in Gate 2C;
5. restore the pinned BGE route when the semantic runtime is healthy and its identity matches the approved policy.

BM25 is an **availability fallback**, not an evidence-equivalent substitute for the chosen primary.

## Rollback criteria

Roll back a changed retrieval policy/runtime/configuration to the last known benchmark-passing primary when any of these hard conditions occurs:

- pack isolation is violated;
- provider/model/runtime identity is silently substituted or no longer auditable;
- exact citation/source semantics are weakened;
- current-state safeguards permit rejected/superseded/stale material to be presented as current without durable lifecycle resolution;
- the frozen Gate 2 reference set gains a full retrieval miss under the primary where the approved BGE profile had none;
- durable identity/provenance/authority invariants are changed merely to improve retrieval scores.

An operational outage of the semantic runtime uses the explicit BM25 degraded fallback instead of changing the approved policy.

## Reconsideration triggers

Reopen this decision when evidence materially changes, including:

- the versioned corpus/case set grows or changes enough to alter failure behavior or strategy ordering;
- the BGE model revision, Sentence Transformers runtime, embedding normalization, or material retrieval implementation changes;
- a competing retriever/reranker/graph/context strategy eliminates the current-state and multi-target-lineage weaknesses without introducing decision-critical misses or boundary violations;
- new hardware/deployment constraints make measured latency, memory, or cost unacceptable;
- a new recurring failure class appears;
- provider/runtime availability makes degraded BM25 mode frequent enough that it is no longer an exceptional fallback;
- a future benchmark shows the chosen primary no longer preserves its zero-full-miss advantage or no longer provides the best quality tradeoff.

Reconsideration must use committed `fossil.benchmark.v1` evidence and preserve previous decision history rather than silently rewriting this record.

## Reproducibility anchors

Gate 2C exact-head semantic proof:

- run `31364039745`;
- head `1f71b981feb9ff10636901c61bfb16e677a9f258`;
- artifact `9053475462` (`gate2-comparative-results`);
- artifact digest `sha256:23c95b46f47cec5a16e0a8c0926a4f13532f283d8f4fbcc0de12ceb63db63c41`;
- compact evidence `benchmarks/gate2/results/2026-08-10-comparative/comparison-summary.json`;
- Gate 2C proof `docs/implementation/2026-08-10-gate2-comparative-bakeoff-proof.md`.

Corpus pins:

- `Pukujan/fossil-common` — `d583005dce06dbb499c3c0de5c22b899655eb8d2`;
- `Pukujan/fossil-ai-systems` — `cf7cf4087bde543cb247a978de2a7252b1b8e4de`.

Real semantic runtime identity:

- BGE model `BAAI/bge-small-en-v1.5`;
- revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`;
- Sentence Transformers `5.2.2`;
- Torch `2.13.0`;
- Transformers `5.14.1`;
- normalized embeddings enabled;
- measured proof device: CPU.

## Scope limit

This decision is corpus-specific Gate 2 evidence, not a universal provider leaderboard. It covers retrieval/context routing; it does not grant model truth authority, change canonical storage, or freeze BGE as irreplaceable infrastructure.
