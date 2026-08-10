# Current Handoff

**Date:** 2026-08-10  
**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Repository:** `Pukujan/fossil-core`  
**Status:** **Gate 1 complete. Gate 2 complete and formally closed. Post-Gate-2 campaign #48 active. Research ingestion and Workstreams A, B, and C are complete. Workstream F is next.**

## Fresh-session transfer

Read, in order:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. this file
4. `docs/handoffs/2026-08-10-chatgpt-session-handoff-post-retrieval-poisoning.md`
5. `docs/PROJECT_STATE.md`
6. `docs/implementation/2026-08-10-post-gate2-retrieval-poisoning-proof.md`
7. `docs/implementation/2026-08-10-post-gate2-answer-reliability-proof.md`
8. `docs/operations/LITELLM-GATEWAY.md`
9. Issue #48 — active production RAG hardening campaign
10. Issue #47 — embedding/reranker/model-scale bakeoff workstream
11. `docs/DECISION_LOG.md`

Verify GitHub state before changing anything.

## Exact active continuation point

**Do not redo research ingestion or Workstreams A, B, or C.**

The next unfinished Issue #48 workstream is:

**F. Reproducible query execution receipt.**

Define a compact versioned receipt containing at minimum:

1. query ID and deterministic query hash;
2. mounted stable pack IDs and exact pack revisions;
3. route/retrieval-policy identity;
4. requested and actual service/model/provider/version/runtime identity;
5. retrieved candidate stable IDs and scores;
6. reranker identity and reranked order when present;
7. deterministic lifecycle/lineage/context-security resolution and resolved IDs;
8. final model-bound context stable IDs and exact citation IDs;
9. final outcome / abstention;
10. latency, cost, and trace/run reference.

Keep verbose telemetry outside canonical durable knowledge. The receipt is execution observability/evidence, not a new truth source and not a durable knowledge event merely because it exists.

The replay proof should show that important benchmark queries can be rerun after retriever/model/projection changes and the receipt makes the changed execution identity visible.

## Workstream C proof — complete

Implementation landed in core PR #61 / squash:

`f5634412222e8d86173eb6e8e364f3414a6f3cd6`

Landed artifacts:

- `src/dkg/context_security.py`;
- `src/dkg/poisoning_eval.py`;
- `benchmarks/post-gate2/retrieval-poisoning-v1.json`;
- `scripts/run_post_gate2_retrieval_poisoning.py`;
- `tests/test_context_security.py`;
- `docs/implementation/2026-08-10-post-gate2-retrieval-poisoning-proof.md`.

The provider-independent structural boundary is `fossil-untrusted-context-v1`:

- known stable IDs are re-resolved from mounted durable documents;
- retrieved payload metadata cannot self-author lifecycle/relation/citation/pack truth;
- unknown in-scope payloads are demoted to non-authoritative `untrusted_context`;
- out-of-scope pack payloads are removed;
- exact duplicate unknown passages are collapsed;
- answer/model output is candidate-only with no executable tool/action surface;
- emitted claim text/citation identity is re-resolved from mounted durable claims;
- invalid claim IDs are contained as `insufficient_evidence`;
- proposal-before-commit and deterministic domain gates remain authoritative.

Final normal CI:

- run `31436499505`;
- job `93611686820`;
- **100 passed in 1.07s**.

Execution-only PR #62 ran the unchanged eight-case adversarial plan against exact pack pins and was closed unmerged.

Proof:

- run `31436425791`;
- job `93611459472`;
- **100 core tests passed in 0.96s**;
- **27 projected documents**;
- benchmark **PASS 8/8**;
- final-answer correctness `1.0`;
- outcome accuracy `1.0`;
- citation correctness `1.0`;
- completeness `1.0`;
- appropriate abstention `1.0`;
- unsupported-claim rate `0.0`;
- over-abstention `0.0`;
- Brier score `0.0`;
- high-confidence error rate `0.0`;
- pack-isolation preservation `1.0`;
- candidate-only authority `1.0`;
- executable-output containment `1.0`;
- durable-claim output boundary `1.0`;
- aggregate security-boundary pass rate `1.0`.

The poisoned SQLite lifecycle case still returned `current_state_unresolved` using `clm_a047d79b8604fadbd44efdf4` with exact citation `cite_b4e13e4e1a809f76527311ba`.

Do not claim a universal poisoning defense. See the C proof for residual risks.

## Workstream B anchor

Workstream B landed in PR #57 / squash:

`483772ac0e1d441719aec42658ae00b62a032c11`

Its failed-first real-corpus proof established that top-k can omit a stale claim even when a durable relation points to it. `fossil-lineage-context-v1` resolves stable relation endpoints before model execution. Final unchanged B benchmark proof: PR #59, run `31433427436`, job `93602011104`, PASS 6/6 with exact citations.

D021 therefore continues to include: **top-k absence is not evidence of nonexistence**.

## D021 remains frozen

Do not replace or weaken D021 without new committed benchmark evidence.

Current rules:

- revision-pinned BGE dense is the normal primary retriever;
- BM25 is explicit degraded availability fallback;
- current/latest/accepted queries resolve durable lifecycle/provenance;
- history/lineage/disagreement queries resolve durable lineage/read state;
- top-k absence is not evidence of nonexistence;
- citations resolve immutable source snapshot/span/hash identity;
- retrieved/source text is untrusted data, never executable policy;
- retrieval score is not truth;
- reranker score is not truth;
- model confidence is not truth;
- multi-model consensus is not external evidence.

Stable pack IDs:

- common: `pack_269099f7b2ba43b7a99b9427d64092de`;
- AI systems: `pack_f024177f89a5442db84171c3dd7f58e5`.

Exact pack revisions used by the B/C proofs:

- `fossil-common@d583005dce06dbb499c3c0de5c22b899655eb8d2`;
- `fossil-ai-systems@84accd2ee895663990e82ca5b79b592cb503db24`.

Do not casually rename `src/dkg`.

## LiteLLM / Cortex boundary

Read `docs/operations/LITELLM-GATEWAY.md` before live model work.

Recorded LiteLLM defaults at this handoff:

- chat: `qwen3-coder-next`;
- embeddings: `gemini-embedding-2`;
- reranking: `rerank-v4-pro`.

For every live benchmark and future Workstream-F receipt, record requested model, actual model, provider, fallback/attempt diagnostics, latency, cost, and runtime identity. A fallback response is not proof that the requested model succeeded. Probe embedding and reranking lanes independently. Do not send secrets, personal information, or confidential documents while gateway retention guarantees remain unverified.

Cortex v4 may be used as a replaceable cognitive-service/orchestration competitor, but FOSSIL durable storage, stable identity, lifecycle/lineage, context-security, proposal-before-commit, and correctness guarantees must not couple to Cortex internals. Multiple agents agreeing does not manufacture truth. Future worker/model invocations should fit the Workstream-F receipt without changing that authority model.

## Remaining campaign order

1. **F** — reproducible query execution receipt;
2. **D / Issue #47** — embeddings, hybrid retrieval, rerankers, model bakeoff;
3. **E** — conservative adaptive routing, only if benchmark justified;
4. **G** — ACL/redaction propagation readiness;
5. final D021/retrieval-policy decision reconciliation;
6. decision log + residual risks + final handoff.

## Suggested next-session prompt

> Continue FOSSIL Issue #48 from this handoff. Verify GitHub first. Workstreams A, B, and C are complete; do not redo them. C landed in PR #61 / squash `f5634412222e8d86173eb6e8e364f3414a6f3cd6`; exact-pin execution proof PR #62 was closed unmerged after run `31436425791`, job `93611459472`, with 100 core tests, 27 documents, adversarial PASS 8/8, exact answer/citation/security-boundary metrics at 1.0, and unsupported-claim rate 0.0. Begin Workstream F: a compact reproducible query execution receipt and replay proof. Preserve D021, stable pack IDs, `fossil-lineage-context-v1`, `fossil-untrusted-context-v1`, proposal-before-commit, and deterministic lifecycle/lineage authority. The receipt is observability/evidence, not truth authority.
