# Gate 2C comparative bakeoff proof

**Date:** 2026-08-10  
**Issue:** #36  
**PR:** #44

## Scope

This proof records the reproducible Gate 2C retrieval/context comparison over the 21-case history-rich real corpus. It is comparison evidence only. It does **not** select a default retrieval policy; Gate 2D / #37 owns that decision.

The comparison preserves the frozen FOSSIL authority model: durable evidence, stable identities, append-only validated events, provenance/history, and pack boundaries remain canonical; retrieval/model implementations remain replaceable services/projections.

## Exact-head proof

The final semantic-capable proof run before removing the temporary workflow was:

- workflow run: `31364039745`;
- PR head: `1f71b981feb9ff10636901c61bfb16e677a9f258`;
- artifact: `9053475462` (`gate2-comparative-results`);
- artifact digest: `sha256:23c95b46f47cec5a16e0a8c0926a4f13532f283d8f4fbcc0de12ceb63db63c41`;
- exact `comparison.json` SHA-256: `81ccdc958d544fcb4cae2421e72658a24a6142353edec027bba1e2e634b8a38f`;
- exact `context-probes.json` SHA-256: `955bd0d09af2f442ac0a25278bd79f3034e94aad789bd24aad6507f3de775d45`.

The committed `comparison-summary.json` persists the exact-head aggregate metrics, failure counts, context-probe identities, corpus pins, and proof references while intentionally keeping `selection.selected = null`.

An earlier successful same-environment replicate was workflow run `31363490598`, artifact `9053285685`, digest `sha256:0db9650c4343d59ad2055ee391c98519a7cd493443f60d6dc6dc10fc6e27b228`. That run produced the same benchmark IDs and the same qualitative retrieval/failure/context conclusions. Latency and peak Python allocation varied modestly between runs, which is expected operational variance and is not treated as a quality-policy signal by itself.

## Inputs and runtime identity

Corpus pins:

- `Pukujan/fossil-common` — `d583005dce06dbb499c3c0de5c22b899655eb8d2`, stable pack ID `pack_269099f7b2ba43b7a99b9427d64092de`;
- `Pukujan/fossil-ai-systems` — `cf7cf4087bde543cb247a978de2a7252b1b8e4de`, stable pack ID `pack_f024177f89a5442db84171c3dd7f58e5`.

Benchmark:

- case set: `caseset_gate2_real_corpus_history_v2` / `benchmarks/gate2/real-corpus-history-v2.json`;
- 21 cases;
- retrieval limit `k=5`;
- context budget 4,000 characters;
- Python 3.12.13 on Linux Azure x86_64;
- CPU execution.

Real dense runtime:

- model: `BAAI/bge-small-en-v1.5`;
- revision: `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`;
- Sentence Transformers 5.2.2;
- Torch 2.13.0;
- Transformers 5.14.1;
- normalized embeddings enabled.

## Exact-head metrics

| Strategy | Hit rate | Mean recall@5 | MRR | Mean latency | p95 latency | Peak Python alloc | Estimated cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| BM25 control | 0.95238 | 0.95238 | 0.81746 | 3.270 ms | 4.566 ms | 58,844 B | $0 |
| Hash embedding control | 0.95238 | 0.92063 | 0.83730 | 1.283 ms | 1.558 ms | 34,100 B | $0 |
| BGE dense | **1.00000** | **0.98413** | 0.85873 | 36.201 ms | 38.535 ms | 81,779 B | $0 |
| BM25+BGE RRF + lifecycle rerank | 0.95238 | 0.95238 | **0.86667** | 58.658 ms | 66.023 ms | 183,065 B | $0 |

No strategy violated pack isolation in the compared cases. All four context probes stayed under the 4,000-character context budget without truncation/overload.

## Failure taxonomy

Exact-head counts:

| Strategy | Retrieval miss | Incomplete recall | Bad ranking | Stale/superseded leakage | Pack violation |
|---|---:|---:|---:|---:|---:|
| BM25 | 1 | 1 | 5 | 1 | 0 |
| Hash control | 1 | 2 | 4 | 1 | 0 |
| BGE dense | **0** | 1 | 5 | 1 | 0 |
| Hybrid | 1 | 1 | **3** | 0 | 0 |

Observed decision-relevant failures:

- BM25, hash, and hybrid fully miss `current_architecture_after_reconsideration` at `k=5`.
- BGE dense is the only compared strategy with zero full retrieval misses, but on the current-architecture case the correct current claim is only rank 5 and rejected/history material appears ahead of it.
- BGE dense retrieves only 2 of 3 targets for `historical_current_supersession_bundle` at `k=5`.
- The hybrid has the best aggregate MRR but still misses the key current-architecture case, so its ranking advantage is not sufficient evidence for a default.
- Unsupported-confidence leakage is not applicable to this retrieval/context-only comparison because these strategies return ranked corpus objects rather than truth-authoritative model answers.

## Persisted raw evidence and run variance

The four committed `fossil.benchmark.v1` raw JSON files are real same-configuration benchmark outputs. Repeated semantic-capable runs preserve the deterministic benchmark IDs and qualitative failure conclusions while latency, allocation, and some near-tied ranking details can vary between executions. Therefore the exact-head workflow artifact and its digest are the proof anchor for the compact comparison summary; the committed raw files remain inspectable representative run outputs rather than being rewritten post hoc to manufacture byte-for-byte identity with a later timing run.

This distinction is intentional: operational timing/allocation measurements are empirical samples, while the policy decision in #37 should rely primarily on stable quality/failure behavior plus explicit resource tradeoffs.

## Confidence limits

This is sufficient evidence for a FOSSIL-specific Gate 2 policy decision, not a universal retrieval-provider leaderboard.

Limits:

- 21 representative real cases, not an exhaustive corpus;
- one CPU execution environment;
- local strategies with estimated provider cost `$0` in these runs;
- retrieval/context behavior only, not a general answer-generation/model benchmark;
- latency and allocation are environment-sensitive;
- future corpus growth, different hardware, provider/runtime revisions, or materially new failure cases require reconsideration.

## Gate 2C conclusion

BGE dense is the leading **candidate** for #37 because it is the only compared strategy with zero full retrieval misses and has the best mean recall. It is not yet selected because temporal/current-state ranking and multi-target lineage recall remain material weaknesses. The hybrid's higher MRR does not outweigh its full miss on the key current-architecture case.

`selection.selected` remains `null`. The temporary semantic-capable workflow may now be removed; normal branch-independent CI must pass on the landing head before #36 is closed.
