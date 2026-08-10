# Current Handoff

**Date:** 2026-08-10  
**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Repository:** `Pukujan/fossil-core`  
**Status:** **Gate 1 complete. Gate 2 complete and formally closed. Post-Gate-2 campaign #48 active. Research ingestion, Workstream A, and Workstream B are complete. Workstream C is next.**

## Fresh-session transfer

Read, in order:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. this file
4. `docs/handoffs/2026-08-10-chatgpt-session-handoff-post-answer-reliability.md`
5. `docs/PROJECT_STATE.md`
6. `docs/implementation/2026-08-10-post-gate2-answer-reliability-proof.md`
7. `docs/operations/LITELLM-GATEWAY.md`
8. Issue #48 — active production RAG hardening campaign
9. Issue #47 — embedding/reranker/model-scale bakeoff workstream
10. `docs/DECISION_LOG.md`

## Exact active continuation point

**Do not redo the research ingestion, Workstream A, or Workstream B.**

The next unfinished Issue #48 workstream is:

**C. Retrieval poisoning / untrusted-context hardening.**

Build an adversarial suite proving that retrieved/source text remains untrusted data rather than executable policy. Cover at minimum:

1. poisoned retrieved documents containing instructions;
2. authority spoofing;
3. malicious supersession attempts;
4. duplicated adversarial passages intended to dominate ranking;
5. conflicting-source attacks;
6. pack-isolation pressure;
7. attempts to bypass proposal-before-commit / deterministic gates;
8. explicit residual-risk documentation.

Reuse Workstream B metrics wherever useful. Do not only test whether poisoned text is retrieved; test whether poisoning changes final-answer correctness, citation correctness, unsupported claims, lifecycle/lineage resolution, abstention behavior, authority boundaries, pack isolation, or proposal-before-commit behavior.

Do not claim a universal poisoning defense.

## Workstream B proof — complete

Implementation landed in core PR #57 / squash:

`483772ac0e1d441719aec42658ae00b62a032c11`

Landed artifacts:

- `src/dkg/answer_eval.py`;
- `src/dkg/answer_pipeline.py`;
- `benchmarks/post-gate2/answer-reliability-v1.json`;
- `scripts/run_post_gate2_answer_reliability.py`;
- `tests/test_answer_eval.py`;
- `tests/test_answer_pipeline.py`;
- `docs/implementation/2026-08-10-post-gate2-answer-reliability-proof.md`.

Final normal CI:

- run `31433539654`;
- job `93602384284`;
- **94 passed in 1.80s**.

### Failed-first execution proof

Execution-only PR #58 intentionally exposed a real failure and was closed without merge.

- run `31433165782`;
- job `93601155740`;
- core tests passed;
- answer benchmark scored **5/6**.

The query asking whether the first SQLite prototype was still the current canonical architecture implementation retrieved its durable `DEPENDS_ON` relation, but the stale dependent claim fell outside top-k. The answerer then selected an unrelated supported claim with confidence `1.0`.

This reinforced D021: **top-k absence is not evidence of nonexistence**.

The fix was `fossil-lineage-context-v1`: when a durable relation is retrieved, FOSSIL resolves stable `source_ref` / `target_ref` endpoints from the mounted validated packs before model execution. This sits around the `ModelService` boundary so future LiteLLM/Cortex/frontier/OSS models receive the same deterministic lineage correction.

### Final execution proof

Execution-only PR #59 reran the unchanged benchmark against:

- `fossil-common@d583005dce06dbb499c3c0de5c22b899655eb8d2`;
- `fossil-ai-systems@84accd2ee895663990e82ca5b79b592cb503db24`.

Proof:

- run `31433427436`;
- job `93602011104`;
- **94 core tests passed**;
- corpus projection: **27 documents**;
- benchmark: **PASS 6/6**;
- final-answer correctness `1.0`;
- outcome accuracy `1.0`;
- citation correctness `1.0`;
- completeness `1.0`;
- appropriate abstention `1.0`;
- unsupported-claim rate `0.0`;
- over-abstention `0.0`;
- Brier score `0.0`;
- high-confidence error rate `0.0`.

The previously failing SQLite case now correctly returns `current_state_unresolved` using claim `clm_a047d79b8604fadbd44efdf4` with exact citation `cite_b4e13e4e1a809f76527311ba`.

PR #59 was closed unmerged because it was execution-only.

## Workstream A / ingestion anchors

Workstream A landed in PR #54 / squash:

`e14148f504702ae9e708e2d58add4ee5c91bc8de`

Its exact-pack temporal proof passed in execution-only PR #55, run `31431113829`, job `93594491275`.

The production-RAG synthesis remains ingested in `fossil-ai-systems` at:

`84accd2ee895663990e82ca5b79b592cb503db24`

Cross-pack ingestion proof passed in core execution-only PR #51, run `31415053398`, job `93541977670`.

## D021 remains frozen

Do not replace or weaken D021 without new committed benchmark evidence.

Current rules:

- revision-pinned BGE dense is the normal primary retriever;
- BM25 is explicit degraded availability fallback;
- current/latest/accepted queries resolve durable lifecycle/provenance;
- history/lineage/disagreement queries resolve durable lineage/read state;
- top-k absence is not evidence of nonexistence;
- citations resolve immutable source snapshot/span/hash identity;
- retrieval score is not truth;
- reranker score is not truth;
- model confidence is not truth;
- multi-model consensus is not external evidence.

Stable pack IDs:

- common: `pack_269099f7b2ba43b7a99b9427d64092de`;
- AI systems: `pack_f024177f89a5442db84171c3dd7f58e5`.

Do not casually rename `src/dkg`.

## LiteLLM / Cortex boundary

Read `docs/operations/LITELLM-GATEWAY.md` before live model work.

Recorded LiteLLM defaults at this handoff:

- chat: `qwen3-coder-next`;
- embeddings: `gemini-embedding-2`;
- reranking: `rerank-v4-pro`.

For every live benchmark record requested model, actual model, provider, fallback/attempt diagnostics, latency, cost, and runtime identity. A fallback response is not proof that the requested model succeeded. Probe embedding and reranking lanes independently. Do not send secrets, personal information, or confidential documents while gateway retention guarantees remain unverified.

Cortex v4 may be used as a replaceable cognitive-service competitor, but FOSSIL durable storage, stable identity, lifecycle logic, proposal-before-commit, and correctness guarantees must not couple to Cortex internals. Multiple agents agreeing does not manufacture truth.

## Remaining campaign order

1. **C** — poisoning / untrusted context;
2. **F** — reproducible query execution receipt;
3. **D / Issue #47** — embeddings, hybrid retrieval, rerankers, model bakeoff;
4. **E** — conservative adaptive routing, only if benchmark justified;
5. **G** — ACL/redaction propagation readiness;
6. final D021/retrieval-policy decision reconciliation;
7. decision log + residual risks + final handoff.

## Suggested next-session prompt

> Continue FOSSIL Issue #48 from this handoff. Verify GitHub first. Workstreams A and B are complete; do not redo them. Workstream B landed in PR #57 / squash `483772ac0e1d441719aec42658ae00b62a032c11`. Its first real-corpus proof intentionally failed because top-k omitted a stale lineage endpoint; the unchanged benchmark passed after deterministic relation-endpoint resolution in execution-only PR #59, run `31433427436`, job `93602011104`, with 6/6 correctness and exact citations. Continue Workstream C: retrieval poisoning / untrusted-context hardening. Preserve D021, stable pack IDs, proposal-before-commit, and deterministic lifecycle/lineage authority. LiteLLM and Cortex v4 are optional replaceable cognitive-service competitors, never truth authority.
