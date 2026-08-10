# FOSSIL Session Handoff — Post-Retrieval-Poisoning

**Date:** 2026-08-10  
**Repository:** `Pukujan/fossil-core`  
**Campaign:** Issue #48 — production RAG hardening  
**State:** Gate 1 complete; Gate 2 complete/formally closed; Workstreams A, B, and C complete; **Workstream F is next**.

## Read first

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/HANDOFF_CURRENT.md`
4. this file
5. `docs/PROJECT_STATE.md`
6. `docs/implementation/2026-08-10-post-gate2-retrieval-poisoning-proof.md`
7. `docs/implementation/2026-08-10-post-gate2-answer-reliability-proof.md`
8. `docs/operations/LITELLM-GATEWAY.md`
9. Issue #48
10. Issue #47
11. `docs/DECISION_LOG.md`

Verify GitHub state before changing anything.

## Completed work — do not redo

- production-RAG research trace + AI-systems ingestion;
- Workstream A — evolving-corpus / temporal benchmark;
- Workstream B — end-to-end answer/citation/abstention reliability;
- Workstream C — retrieval poisoning / untrusted-context hardening.

## Workstream C — landed

Core PR #61 landed with squash:

`f5634412222e8d86173eb6e8e364f3414a6f3cd6`

Landed artifacts:

- `src/dkg/context_security.py`;
- `src/dkg/poisoning_eval.py`;
- `benchmarks/post-gate2/retrieval-poisoning-v1.json`;
- `scripts/run_post_gate2_retrieval_poisoning.py`;
- `tests/test_context_security.py`;
- `docs/implementation/2026-08-10-post-gate2-retrieval-poisoning-proof.md`.

The structural boundary is named:

`fossil-untrusted-context-v1`

Its rule is not natural-language poison classification. Retrieved/source text stays data, while authority is resolved structurally:

- known retrieved stable IDs are re-resolved from mounted durable documents;
- retrieved text/lifecycle/relation/citation/pack metadata cannot override durable identity;
- unknown in-scope payloads are demoted to `untrusted_context` and lose claim/relation/lifecycle/citation authority;
- out-of-scope pack payloads are dropped before model execution;
- exact duplicate unknown payloads are collapsed to reduce trivial context flooding;
- the answer boundary exposes no executable tool/action surface;
- model output is `candidate_only`;
- emitted claim IDs must resolve to mounted durable claims, with canonical text/citation copied from durable documents;
- invalid claim IDs become `insufficient_evidence` rather than new truth;
- mutation remains behind the existing capability/provenance/validation/proposal-before-commit gates.

This wrapper is provider/model independent and composes outside `fossil-lineage-context-v1` so B's durable relation-endpoint correction remains active.

## Workstream C proof

Final normal PR #61 CI:

- run `31436499505`;
- job `93611686820`;
- **100 passed in 1.07s**.

Execution-only PR #62 ran the unchanged adversarial plan against exact pack pins and was closed unmerged by design.

Proof:

- run `31436425791`;
- job `93611459472`;
- **100 core tests passed in 0.96s**;
- **27 projected documents**;
- adversarial benchmark **PASS 8/8**;
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

The attack set covers:

1. poisoned retrieved instructions;
2. authority spoofing with a real durable ID;
3. malicious supersession metadata;
4. duplicate adversarial ranking/context pressure;
5. fake conflicting claims/relations;
6. pack-isolation pressure;
7. lifecycle/lineage spoofing of the stale SQLite case;
8. proposal-before-commit bypass instructions.

The SQLite regression remained correct under direct spoofing:

- outcome `current_state_unresolved`;
- claim `clm_a047d79b8604fadbd44efdf4`;
- exact citation `cite_b4e13e4e1a809f76527311ba`.

Do not turn this into a claim of universal prompt-injection or poisoning resistance. Residual risks are documented in the proof file, including semantic near-duplicate flooding, context-budget/ranking pressure before the model boundary, upstream evidence compromise, and future generative-model confusion/refusal/error.

## Workstream B anchor

B remains landed in PR #57 / squash:

`483772ac0e1d441719aec42658ae00b62a032c11`

The failed-first execution PR #58 established the critical D021 lesson: a retrieved durable relation can point to a relevant claim that fell outside top-k; top-k absence is not evidence of nonexistence.

The final unchanged B benchmark passed in execution-only PR #59, run `31433427436`, job `93602011104`, after `fossil-lineage-context-v1` resolved durable relation endpoints before model execution.

## Exact next workstream — F

Build the **reproducible query execution receipt** before the retrieval/model bakeoff.

Issue #48 requires a compact receipt containing at minimum:

- query ID and/or deterministic query hash;
- mounted stable pack IDs and exact pack revisions;
- route / retrieval policy identity;
- service/model/provider/version/runtime identity;
- retrieved candidate stable IDs and scores;
- reranker identity and reranked ordering when present;
- deterministic lifecycle/lineage resolution performed;
- final model-bound context stable IDs;
- exact citation IDs;
- final outcome / abstention state;
- latency and provider/model cost;
- trace/run reference suitable for replay and debugging.

Keep verbose provider telemetry outside canonical durable knowledge. The receipt is execution evidence/observability, not a new truth source and not a durable knowledge event merely because it exists.

The completion proof should show that important benchmark queries can be replayed after retriever/model/projection changes and that the receipt is sufficient to identify what changed.

### Suggested F design constraints

- prefer a versioned compact JSON contract under a stable FOSSIL namespace;
- keep deterministic fields separate from provider-specific diagnostics;
- hash/identify the normalized query without making the hash the only human-debuggable field;
- record requested **and actual** model/provider identity for fallbacks;
- record retrieval/reranking candidate ordering without granting score authority;
- record lifecycle/lineage/context-security resolver identities (`fossil-lineage-context-v1`, `fossil-untrusted-context-v1`) and their resolved stable IDs;
- record mounted pack IDs and exact source revisions so replay does not silently change corpus state;
- do not embed secrets, raw credentials, or unnecessary private telemetry;
- make receipts reproducible enough for Workstream D/#47 comparisons and future Cortex multi-worker execution receipts.

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
- multi-model consensus is not external evidence;
- retrieved/source text is untrusted data, never executable policy.

Stable pack IDs:

- common: `pack_269099f7b2ba43b7a99b9427d64092de`;
- AI systems: `pack_f024177f89a5442db84171c3dd7f58e5`.

Exact current pack revisions used by B/C proofs:

- `fossil-common@d583005dce06dbb499c3c0de5c22b899655eb8d2`;
- `fossil-ai-systems@84accd2ee895663990e82ca5b79b592cb503db24`.

Do not casually rename `src/dkg`.

## LiteLLM / Cortex boundary

Read `docs/operations/LITELLM-GATEWAY.md` before live provider work.

Recorded LiteLLM defaults remain:

- chat: `qwen3-coder-next`;
- embeddings: `gemini-embedding-2`;
- reranking: `rerank-v4-pro`.

For every live benchmark/receipt record requested model, actual model, provider, fallback/attempt diagnostics, latency, cost, and runtime identity. A fallback response is not proof that the requested model succeeded. Embedding and reranking are separate lanes and should be probed independently. Do not send secrets, personal information, or confidential documents while retention guarantees remain unverified.

Cortex v4 remains a replaceable cognitive-service/orchestration competitor. FOSSIL stable identity, durable storage, lifecycle/lineage, context-security, proposal-before-commit, and correctness guarantees must not couple to Cortex internals. Multiple workers agreeing does not manufacture truth. Future worker/model invocations should fit into the Workstream F execution receipt without changing that authority model.

## Remaining campaign order

1. **F** — reproducible query execution receipt;
2. **D / Issue #47** — embeddings, hybrid retrieval, rerankers, model bakeoff;
3. **E** — conservative adaptive routing, only if benchmark justified;
4. **G** — ACL/redaction propagation readiness;
5. final D021/retrieval-policy decision reconciliation;
6. decision log + residual risks + final handoff.

## Suggested next-session prompt

> Continue FOSSIL Issue #48 from the post-retrieval-poisoning handoff. Verify GitHub first. Workstreams A, B, and C are complete; do not redo them. C landed in PR #61 / squash `f5634412222e8d86173eb6e8e364f3414a6f3cd6`. Its exact-pin execution proof ran in closed-unmerged PR #62, run `31436425791`, job `93611459472`, with 100 core tests, 27 documents, adversarial PASS 8/8, exact answer/citation/security-boundary metrics at 1.0, and unsupported-claim rate 0.0. The poisoned SQLite case still returned `current_state_unresolved` via `clm_a047d79b8604fadbd44efdf4` / `cite_b4e13e4e1a809f76527311ba`. Begin Workstream F: a compact reproducible query execution receipt and replay proof. Preserve D021, stable pack IDs, proposal-before-commit, deterministic lifecycle/lineage authority, and `fossil-untrusted-context-v1`. The receipt is observability/evidence, not truth authority.
