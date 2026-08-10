# Current Handoff

**Date:** 2026-08-10  
**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Repository:** `Pukujan/fossil-core`  
**Status:** **Gate 1 complete. Gate 2 complete and formally closed. Post-Gate-2 campaign #48 active. Research ingestion and Workstreams A, B, C, and F are complete. Workstream D / Issue #47 is active next.**

## Fresh-session transfer

Read, in order:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. this file
4. `docs/handoffs/2026-08-10-chatgpt-session-handoff-post-query-execution-receipt.md`
5. `docs/PROJECT_STATE.md`
6. `docs/implementation/2026-08-10-post-gate2-query-execution-receipt-proof.md`
7. `docs/implementation/2026-08-10-post-gate2-retrieval-poisoning-proof.md`
8. `docs/implementation/2026-08-10-post-gate2-answer-reliability-proof.md`
9. `docs/operations/LITELLM-GATEWAY.md`
10. Issue #48 — active production RAG hardening campaign
11. Issue #47 — active Workstream D retrieval/reranking/model bakeoff
12. `docs/DECISION_LOG.md`

Verify GitHub state before changing anything.

## Exact active continuation point

**Do not redo research ingestion or Workstreams A, B, C, or F.**

The next unfinished Issue #48 workstream is:

**D / Issue #47 — retrieval/reranking/model bakeoff.**

Start with comparable incumbent/hybrid/reranker evidence before escalating embedding model size:

1. rerun comparable incumbent D021 dense and BM25 baselines using exact corpus pins and Workstream-F receipts;
2. compare deterministic dense+lexical hybrid/RRF;
3. add at least one real cross-encoder/API reranker behind `Reranker` and prove requested/actual/fallback identity;
4. only then progress Qwen3-Embedding 0.6B → 4B → 8B if evidence and resources justify continuing;
5. keep contextualized retrieval optional and reproducible, with original source/claim identity distinguishable.

Every candidate/configuration must emit or be representable by `fossil.query-execution-receipt.v1` and preserve deterministic lifecycle/lineage/context-security authority.

Do not replace D021 because a candidate is newer/larger or wins an aggregate score. Decision-critical misses and lifecycle/lineage safety remain hard constraints.

## Workstream F proof — complete

Implementation landed in core PR #64 / squash:

`42dab94b51a7b17f20c046f7257b912fe9f0c900`

Landed artifacts:

- `src/dkg/execution_receipt.py`;
- `schemas/query-execution-receipt/v1.schema.json`;
- `tests/test_execution_receipt.py`;
- `scripts/run_post_gate2_query_receipt.py`;
- `docs/implementation/2026-08-10-post-gate2-query-execution-receipt-proof.md`;
- observability-only resolver diagnostics in `src/dkg/answer_pipeline.py` and `src/dkg/context_security.py`.

The receipt schema is `fossil.query-execution-receipt.v1` and its authority is explicitly `execution_observability_only`.

It records query identity, exact pack mounts and scope, projection/build identity, route/policy, requested and actual services/models/providers, bounded fallback attempts, candidate stable IDs/scores, reranker identity, resolver effects, final context/citation IDs, outcome/abstention, latency/cost, and trace/run references. Credential-shaped diagnostic keys are filtered, but this is not general DLP.

Final normal CI:

- run `31437754923`;
- job `93615632123`;
- **104 passed in 1.04s**.

Execution-only PR #65 ran the exact-pin replay proof and was closed unmerged.

Proof:

- run `31437447245`;
- job `93614630416`;
- **104 core tests passed in 2.41s**;
- **27 projected documents**;
- **6 queries / 18 receipts**;
- answer correctness `1.0`;
- exact replay identity `1.0`;
- resolver recording `1.0`;
- semantic-result stability `1.0`;
- service-change visibility `1.0`.

Exact replay changed telemetry only while execution/result identity remained stable. A controlled route/retriever-version change was visible under policy/services while preserving result identity and durable answers/citations.

Projection identity used for the proof:

- `pack-fixture-retrieval-documents`;
- version `1`;
- build ID `packfix_59b82d8d50ab38ea68402db7`.

The receipt is observability/replay evidence, not truth authority or a mutation capability.

## Workstream C / B authority anchors

C landed in PR #61 / squash:

`f5634412222e8d86173eb6e8e364f3414a6f3cd6`

`fossil-untrusted-context-v1` re-resolves known retrieved IDs from mounted durable documents, demotes unknown context, enforces pack scope, contains executable/output escape, and keeps model output candidate-only. C's exact-pin proof passed 8/8.

B landed in PR #57 / squash:

`483772ac0e1d441719aec42658ae00b62a032c11`

`fossil-lineage-context-v1` resolves durable relation endpoints before model execution. The failed-first B proof established: **top-k absence is not evidence of nonexistence**.

The SQLite regression remains:

- outcome `current_state_unresolved`;
- claim `clm_a047d79b8604fadbd44efdf4`;
- exact citation `cite_b4e13e4e1a809f76527311ba`.

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
- multi-model consensus is not external evidence;
- query execution receipts are observability/replay evidence, not truth authority.

Stable pack IDs:

- common: `pack_269099f7b2ba43b7a99b9427d64092de`;
- AI systems: `pack_f024177f89a5442db84171c3dd7f58e5`.

Exact pack revisions used by B/C/F proofs:

- `fossil-common@d583005dce06dbb499c3c0de5c22b899655eb8d2`;
- `fossil-ai-systems@84accd2ee895663990e82ca5b79b592cb503db24`.

Do not casually rename `src/dkg`.

## Workstream D measurement rules

Compare at minimum:

- full retrieval misses / hit rate;
- recall@k;
- MRR / ranking quality;
- final-answer correctness where applicable;
- exact citation correctness / unsupported-claim rate;
- current-vs-superseded leakage;
- lineage / multi-target historical-current failures;
- poisoning/context-security compatibility;
- pack isolation violations;
- latency;
- memory/resource use;
- provider/runner cost;
- outage/fallback behavior;
- exact requested and actual provider/model/service/runtime identity.

Use the same exact corpus pins and matched candidate budgets where comparisons are meant to be fair. Hardware/runtime/precision/quantization differences must stay visible.

## LiteLLM / Cortex boundary

Read `docs/operations/LITELLM-GATEWAY.md` before live provider work.

Recorded LiteLLM defaults at this handoff:

- chat: `qwen3-coder-next`;
- embeddings: `gemini-embedding-2`;
- reranking: `rerank-v4-pro`.

For every live D candidate, record requested model, actual model, provider, fallback/attempt diagnostics, latency, cost, runtime identity, and exact model/configuration identity where available. A fallback response is not proof that the requested model succeeded. Probe embedding and reranking lanes independently. Do not send secrets, personal information, or confidential documents while gateway retention guarantees remain unverified.

Cortex v4 remains a replaceable cognitive-service/orchestration competitor. FOSSIL durable storage, stable identity, lifecycle/lineage, context-security, proposal-before-commit, and correctness guarantees must not couple to Cortex internals. Multiple agents agreeing does not manufacture truth.

## Remaining campaign order

1. **D / Issue #47** — embeddings, hybrid retrieval, rerankers, model bakeoff;
2. **E** — conservative adaptive routing, only if benchmark justified;
3. **G** — ACL/redaction propagation readiness;
4. final D021/retrieval-policy decision reconciliation;
5. decision log + residual risks + final handoff.

## Suggested next-session prompt

> Continue FOSSIL Issue #48 / Workstream D from this handoff. Verify GitHub first. Workstreams A, B, C, and F are complete; do not redo them. F landed in PR #64 / squash `42dab94b51a7b17f20c046f7257b912fe9f0c900`; final CI run `31437754923`, job `93615632123`, was 104/104 green. Execution-only PR #65 was closed unmerged after exact-pin run `31437447245`, job `93614630416`: 27 documents, 6 queries, 18 receipts, with answer correctness / exact replay identity / resolver recording / semantic-result stability / service-change visibility all 1.0. Issue #47 is active Workstream D. Start with comparable incumbent BM25/dense/hybrid/reranker evidence using `fossil.query-execution-receipt.v1`, then progress Qwen3-Embedding 0.6B → 4B → 8B only if justified. Preserve D021, stable pack IDs, `fossil-lineage-context-v1`, `fossil-untrusted-context-v1`, proposal-before-commit, and deterministic lifecycle/lineage authority. Receipts and model/reranker scores are not truth authority.
