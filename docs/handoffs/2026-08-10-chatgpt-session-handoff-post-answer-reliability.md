# ChatGPT Session Handoff — Post-Answer-Reliability

**Date:** 2026-08-10  
**Project:** FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage  
**Campaign:** Issue #48 — production RAG hardening  
**State:** Gate 1 closed; Gate 2 closed; research ingestion complete; Workstream A complete; **Workstream B complete**; Workstream C next.

## Read first

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/HANDOFF_CURRENT.md`
4. this file
5. `docs/PROJECT_STATE.md`
6. `docs/implementation/2026-08-10-post-gate2-answer-reliability-proof.md`
7. `docs/operations/LITELLM-GATEWAY.md`
8. Issue #48
9. Issue #47
10. `docs/DECISION_LOG.md`

## Exact continuation

Do **not** redo research ingestion, Workstream A, or Workstream B.

The exact next Issue #48 workstream is:

**C. Retrieval poisoning / untrusted-context hardening.**

Build an adversarial suite that proves retrieved/source text remains data rather than executable policy. Cover at least:

- poisoned-document instructions;
- authority spoofing;
- malicious supersession attempts;
- duplicated adversarial passages intended to dominate ranking;
- conflicting-source cases;
- pack-isolation pressure;
- proposal-before-commit / deterministic-gate preservation;
- explicit residual-risk documentation rather than a claim of universal poisoning defense.

Reuse Workstream B's answer reliability metrics where useful. A poisoning test should not only ask whether a malicious passage was retrieved; it should check whether the final answer, citations, lifecycle resolution, abstention, and authority boundary remained correct.

## Workstream B — landed

Core PR #57 squash:

`483772ac0e1d441719aec42658ae00b62a032c11`

Landed components:

- `src/dkg/answer_eval.py` — structured answer-level evaluator + deterministic durable-evidence baseline;
- `src/dkg/answer_pipeline.py` — deterministic durable relation-endpoint context resolution before model execution;
- `benchmarks/post-gate2/answer-reliability-v1.json` — six-case exact-pin real-corpus plan;
- `scripts/run_post_gate2_answer_reliability.py` — exact-pin runner;
- `tests/test_answer_eval.py` and `tests/test_answer_pipeline.py` — evaluator, abstention, contradiction, unsupported-claim, citation, and lineage regression tests;
- `docs/implementation/2026-08-10-post-gate2-answer-reliability-proof.md` — durable proof including the failed first execution.

Final PR #57 CI:

- run `31433539654`;
- job `93602384284`;
- **94 passed in 1.80s**.

## Workstream B — important failed-first proof

Execution-only PR #58 was deliberately closed without merge after exposing a real failure.

- run `31433165782`;
- job `93601155740`;
- core suite: **92 passed in 8.68s**;
- six-case answer benchmark: **FAIL**, 5/6 correct.

The failed query asked whether the first SQLite prototype was the current canonical architecture implementation. Retrieval returned its durable `DEPENDS_ON` relation but the stale dependent claim itself fell outside top-k. A retrieval-only answer context therefore chose an unrelated supported claim with confidence 1.0.

This directly reinforced D021: **top-k absence is not evidence of nonexistence**. The fix was not to weaken the expected answer. FOSSIL added `fossil-lineage-context-v1`, resolving stable source/target refs from retrieved durable relations before model execution.

Regression CI after the fix:

- run `31433377445`;
- job `93601846449`;
- **94 passed in 1.24s**.

## Workstream B — final real-corpus proof

Execution-only PR #59 reran the unchanged six-case plan against exact pack pins and was closed without merge after PASS.

Exact inputs:

- `fossil-common@d583005dce06dbb499c3c0de5c22b899655eb8d2`;
- `fossil-ai-systems@84accd2ee895663990e82ca5b79b592cb503db24`.

Proof:

- run `31433427436`;
- job `93602011104`;
- **94 core tests passed in 1.04s**;
- corpus projection: **27 documents**;
- benchmark: **PASS, 6/6 cases**;
- final-answer correctness: `1.0`;
- outcome accuracy: `1.0`;
- exact citation correctness: `1.0`;
- completeness: `1.0`;
- appropriate abstention: `1.0`;
- mean unsupported-claim rate: `0.0`;
- over-abstention: `0.0`;
- Brier score: `0.0`;
- high-confidence error rate: `0.0`;
- baseline estimated model cost: `$0.0`;
- mean deterministic answer-service latency: about `0.863 ms` on that runner.

The formerly failing SQLite dependent case resolved to `current_state_unresolved`, using durable claim `clm_a047d79b8604fadbd44efdf4` and exact citation `cite_b4e13e4e1a809f76527311ba`.

## LiteLLM / model integration boundary

A shared LiteLLM gateway configuration is already present in core. Read `docs/operations/LITELLM-GATEWAY.md` before live model work.

Current recorded defaults at this handoff:

- chat: `qwen3-coder-next`;
- embeddings: `gemini-embedding-2`;
- reranking: `rerank-v4-pro`;
- gateway key is a GitHub Actions secret, not repository data.

Important operational rules:

- gateway/chat fallbacks are possible, so benchmark evidence must record **requested model and actual model** plus attempt/fallback diagnostics;
- a fallback response is not evidence that the requested model succeeded;
- embedding and reranking lanes should be probed independently;
- the gateway privacy warning means secrets, personal data, or confidential documents should not be sent until the data-retention boundary is verified.

LiteLLM, Cortex, frontier models, and future OSS models belong behind FOSSIL's replaceable cognitive-service interfaces. They can compete on the Workstream B contract; they do not become durable truth or a prerequisite for correctness.

## Cortex / multi-agent posture

Cortex v4 is evolving. Do not couple FOSSIL's durable substrate or benchmark correctness to its current internal orchestration shape.

If Cortex workers are used later, treat each worker/model invocation as a replaceable cognitive service and preserve:

- requested/actual provider and model identity;
- route/fallback identity;
- FOSSIL stable retrieved IDs and citations;
- deterministic lifecycle/lineage resolution before truth-changing conclusions;
- proposal-before-commit gates;
- replayable receipts in future Workstream F.

A multi-agent consensus is not evidence merely because multiple models agree.

## Workstream A / ingestion anchors

Workstream A landed in PR #54 / squash:

`e14148f504702ae9e708e2d58add4ee5c91bc8de`

Its exact-pack temporal proof passed in execution-only PR #55, run `31431113829`, job `93594491275`.

Research ingestion remains landed in AI-systems at:

`84accd2ee895663990e82ca5b79b592cb503db24`

Cross-pack ingestion audit passed in core execution-only PR #51, run `31415053398`, job `93541977670`.

## D021 / frozen authority

D021 remains approved and unchanged.

- revision-pinned BGE dense remains the normal primary retriever;
- BM25 remains explicit degraded availability fallback;
- current/latest/accepted questions resolve lifecycle/provenance;
- lineage/history/disagreement questions resolve durable lineage/read state;
- top-k absence is not evidence of nonexistence;
- exact citation-bearing answers resolve immutable source snapshot/span/hash identity;
- retrieval scores, reranker scores, model confidence, multi-model agreement, and planner output are not truth authority.

Stable pack IDs remain:

- common: `pack_269099f7b2ba43b7a99b9427d64092de`;
- AI-systems: `pack_f024177f89a5442db84171c3dd7f58e5`.

## Suggested continuation prompt

> Continue FOSSIL Issue #48 after Workstream B. Read `AGENTS.md`, `ARCHITECTURE.md`, `docs/HANDOFF_CURRENT.md`, and `docs/handoffs/2026-08-10-chatgpt-session-handoff-post-answer-reliability.md`, then verify GitHub state. Workstream B landed in core PR #57 / squash `483772ac0e1d441719aec42658ae00b62a032c11`. The first execution-only proof #58 correctly failed because top-k omitted a stale dependent claim; the unchanged benchmark passed after deterministic durable relation-endpoint resolution in proof #59, run `31433427436`, job `93602011104`, with 6/6 final-answer correctness and exact citation correctness. Do not redo A or B. Continue Workstream C: retrieval poisoning / untrusted-context hardening. Preserve D021 and stable pack identities. LiteLLM/Cortex models may be evaluated as replaceable competitors behind the existing service boundary, never as truth authority.
