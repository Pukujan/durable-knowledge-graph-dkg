# Post-Gate-2 Workstream B — Answer Reliability Proof

**Date:** 2026-08-10  
**Campaign:** Issue #48 — production RAG hardening  
**Workstream:** B — end-to-end answer/citation/abstention evaluation

## Scope

This proof establishes a provider-independent answer-level baseline above retrieval. It does **not** grant model output truth authority and it does not replace D021.

The committed evaluator measures:

- final-answer correctness;
- exact citation identity including source snapshot, artifact, byte span, and passage hash;
- unsupported-claim rate;
- answer completeness;
- contradiction handling;
- explicit `insufficient_evidence`, `conflicting_evidence`, and `current_state_unresolved` outcomes;
- appropriate abstention / over-abstention;
- confidence calibration through Brier error and high-confidence error rate;
- latency and provider cost metadata.

The deterministic baseline can only emit durable claim/citation objects supplied through FOSSIL context. It cannot manufacture a new knowledge claim.

## Exact corpus pins

- `Pukujan/fossil-common@d583005dce06dbb499c3c0de5c22b899655eb8d2`
- `Pukujan/fossil-ai-systems@84accd2ee895663990e82ca5b79b592cb503db24`

The combined validated projection contained **27 retrieval documents**.

## Initial proof — intentionally failed

Execution-only PR #58 ran the unchanged six-case real-corpus plan before durable lineage-context expansion.

- workflow run: `31433165782`
- job: `93601155740`
- core suite: **92 passed in 8.68s**
- answer benchmark result: **FAIL**
- final-answer correctness: `0.8333333333333334`
- citation correctness: `0.8333333333333334`
- unsupported-claim mean: `0.16666666666666666`
- appropriate abstention: `0.5`
- Brier score: `0.16666666666666666`
- high-confidence error rate: `0.16666666666666666`

The failed case was `current-stale-sqlite-prototype`. BM25 + lifecycle reranking retrieved the durable `DEPENDS_ON` relation but the stale dependent claim itself fell outside top-k. The answerer then selected an unrelated supported research-hardening claim and answered with confidence `1.0`.

That failure is evidence for D021 rather than a reason to weaken the benchmark: **top-k absence is not evidence of nonexistence**, and current/history questions must resolve durable lifecycle/lineage state.

PR #58 was closed without merge.

## Fix

The base implementation added `fossil-lineage-context-v1`, a deterministic relation-endpoint resolver that runs between retrieval and model execution.

When a retrieved durable relation carries stable `source_ref` / `target_ref` IDs, the resolver loads those referenced documents from the already mounted, validated packs before answer generation. Retrieval remains candidate ordering; durable IDs and lifecycle/lineage remain the authority path.

The resolver is wrapped around the `ModelService` boundary, so future LiteLLM/Cortex/frontier/OSS model competitors can receive the same corrected context while retaining their underlying provider/model metadata.

Regression tests were added for the exact observed failure: relation retrieved, stale endpoint absent from top-k, endpoint recovered by stable ID, final outcome correctly becomes `current_state_unresolved`.

Normal PR #57 CI after the fix:

- workflow run: `31433377445`
- job: `93601846449`
- result: **94 passed in 1.24s**

## Final real-corpus proof — PASS

Execution-only PR #59 reran the **same unchanged six-case plan** against the same exact corpus pins after the lineage fix.

- workflow run: `31433427436`
- job: `93602011104`
- core suite inside proof: **94 passed in 1.04s**
- answer benchmark: **PASS**
- cases: `6`
- final-answer correctness: `1.0`
- outcome accuracy: `1.0`
- citation correctness: `1.0`
- mean unsupported-claim rate: `0.0`
- completeness: `1.0`
- appropriate abstention: `1.0`
- over-abstention: `0.0`
- Brier score: `0.0`
- high-confidence error rate: `0.0`
- estimated model cost: `$0.0`
- mean answer-service latency in this local baseline: approximately `0.863 ms`

The stale SQLite dependent case now resolves to:

- outcome: `current_state_unresolved`;
- claim: `clm_a047d79b8604fadbd44efdf4`;
- exact citation: `cite_b4e13e4e1a809f76527311ba`;
- unsupported claims: none.

PR #59 was closed without merge after proof.

## Interpretation

Workstream B now has a deterministic, provider-independent answer reliability floor. A hosted/frontier/OSS model is allowed to beat this baseline on synthesis quality, language quality, breadth, or matched complex-answer cases, but it must not silently regress exact citation identity, unsupported-claim behavior, abstention, lifecycle resolution, or provider/model provenance.

LiteLLM/Cortex integration belongs behind this same `ModelService` boundary. Requested model, actual model, fallback attempts, privacy warnings, provider/model/runtime identity, latency, and cost must be recorded for live model evidence. A fallback response is not proof that the originally requested model succeeded.

## Authority conclusion

D021 remains unchanged. Durable evidence + lifecycle/lineage + exact citation identity outrank retrieval score and model confidence. The failed first proof strengthened this requirement with direct FOSSIL evidence.
