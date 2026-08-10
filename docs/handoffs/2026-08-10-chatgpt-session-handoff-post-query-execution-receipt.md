# FOSSIL Session Handoff — Post-Query-Execution-Receipt

**Date:** 2026-08-10  
**Repository:** `Pukujan/fossil-core`  
**Campaign:** Issue #48 — production RAG hardening  
**State:** Gate 1 complete; Gate 2 complete/formally closed; Workstreams A, B, C, and F complete; **Workstream D / Issue #47 is next and active**.

## Read first

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/HANDOFF_CURRENT.md`
4. this file
5. `docs/PROJECT_STATE.md`
6. `docs/implementation/2026-08-10-post-gate2-query-execution-receipt-proof.md`
7. `docs/implementation/2026-08-10-post-gate2-retrieval-poisoning-proof.md`
8. `docs/implementation/2026-08-10-post-gate2-answer-reliability-proof.md`
9. `docs/operations/LITELLM-GATEWAY.md`
10. Issue #48
11. Issue #47
12. `docs/DECISION_LOG.md`

Verify GitHub state before changing anything.

## Completed work — do not redo

- production-RAG research trace + AI-systems ingestion;
- Workstream A — evolving-corpus / temporal benchmark;
- Workstream B — end-to-end answer/citation/abstention reliability;
- Workstream C — retrieval poisoning / untrusted-context hardening;
- Workstream F — reproducible query execution receipt + replay proof.

## Workstream F — landed

Core PR #64 landed with squash:

`42dab94b51a7b17f20c046f7257b912fe9f0c900`

Landed artifacts:

- `src/dkg/execution_receipt.py`;
- `schemas/query-execution-receipt/v1.schema.json`;
- `tests/test_execution_receipt.py`;
- `scripts/run_post_gate2_query_receipt.py`;
- `docs/implementation/2026-08-10-post-gate2-query-execution-receipt-proof.md`;
- observability-only resolver diagnostics in `src/dkg/answer_pipeline.py` and `src/dkg/context_security.py`.

The receipt contract is:

`fossil.query-execution-receipt.v1`

Its authority is explicitly:

`execution_observability_only`

The receipt is not canonical durable knowledge, does not become truth authority, and cannot authorize mutation.

### Receipt fields

The compact receipt records:

- query ID, text, normalized query, and deterministic SHA-256;
- mounted stable pack IDs and exact revisions;
- explicit retrieval pack scope separate from mounts;
- projection name/version/build ID;
- route/retrieval-policy identity;
- requested and actual provider/model/service identity;
- bounded fallback/attempt diagnostics;
- candidate stable IDs, pack IDs, rank/score, plus base/rerank scores when available;
- reranker service identity when present;
- `fossil-untrusted-context-v1` and `fossil-lineage-context-v1` resolver identities and stable-ID effects;
- final model-bound context IDs and exact citation IDs;
- outcome/abstention, emitted durable claim IDs, confidence, and candidate-only authority;
- latency/cost and trace/run reference;
- execution-identity and result-identity hashes.

Credential-shaped runtime/attempt fields are recursively removed by key-name filtering. This is a compact safeguard, not general DLP.

### Replay semantics

`execution_identity_sha256` excludes ordinary timing/run-reference telemetry. `result_sha256` covers retrieved candidates, resolver effects, final context, and durable result.

The replay comparator separates query/corpus/scope/projection/policy/service/retrieval/resolver/context/result changes from telemetry-only changes.

This is the observability substrate for Workstream D/#47; it does not make candidate scores authoritative.

## Workstream F proof

Final normal PR #64 CI:

- run `31437754923`;
- job `93615632123`;
- **104 passed in 1.04s**.

Execution-only PR #65 ran the exact-pin replay proof and was closed unmerged by design.

Proof:

- run `31437447245`;
- job `93614630416`;
- **104 core tests passed in 2.41s**;
- **27 projected documents**;
- **6 Workstream-B queries**;
- **18 receipts** — baseline, exact replay, controlled route/service-version variant for every query;
- answer correctness `1.0`;
- exact replay identity `1.0`;
- resolver recording `1.0`;
- semantic result stability `1.0`;
- service-change visibility `1.0`.

Exact replay behavior:

- same logical query/corpus/scope/projection/policy/services;
- `changed_dimensions: []`;
- execution identity matches;
- result identity matches;
- telemetry changes as expected.

Controlled variant behavior:

- route changed from `d021-answer-baseline-v1` to `workstream-f-service-version-probe`;
- retriever implementation version changed from `answer-reliability-baseline-v1` to `query-receipt-replay-probe-v2`;
- execution identity changed visibly under `policy` / `services`;
- result identity and semantic durable answer remained stable.

Projection used for the proof:

- name `pack-fixture-retrieval-documents`;
- version `1`;
- build ID `packfix_59b82d8d50ab38ea68402db7`.

Residual risks are explicit in the proof document. In particular, deterministic local replay does not establish hosted-provider determinism; compact key-name sanitization is not general DLP; trace retention is external; hashes are not trusted signing; and future Cortex/multi-worker runs may need causal child-invocation IDs.

## Workstream C / B authority anchors

C landed in PR #61 / squash:

`f5634412222e8d86173eb6e8e364f3414a6f3cd6`

`fossil-untrusted-context-v1` structurally prevents retrieved payloads from self-authoring lifecycle/relation/citation/pack authority and keeps model output candidate-only.

B landed in PR #57 / squash:

`483772ac0e1d441719aec42658ae00b62a032c11`

`fossil-lineage-context-v1` resolves durable relation endpoints before model execution. The failed-first B proof established the frozen lesson: **top-k absence is not evidence of nonexistence**.

The SQLite regression remains:

- outcome `current_state_unresolved`;
- claim `clm_a047d79b8604fadbd44efdf4`;
- exact citation `cite_b4e13e4e1a809f76527311ba`.

## Exact next workstream — D / Issue #47

Issue #47 is now active and retitled:

**Workstream D: retrieval/reranking/model bakeoff (0.6B → 4B → 8B)**

Begin with comparable incumbent/hybrid/reranker evidence before escalating model size.

Required lanes:

1. incumbent D021 dense retrieval;
2. BM25 in its explicit degraded/fallback role;
3. deterministic dense+lexical hybrid/RRF;
4. at least one real cross-encoder/API reranker behind `Reranker`;
5. contextualized retrieval only if construction is reproducible and source/claim identity remains distinguishable;
6. Qwen3-Embedding 0.6B class first, then 4B, then 8B only if evidence/resources justify continuing;
7. optional BGE-M3/larger BGE family control if justified.

Every candidate/configuration must pin exact model/revision/runtime/library/precision/hardware details and emit or be representable by `fossil.query-execution-receipt.v1`.

Compare at minimum:

- full misses / hit rate;
- recall@k;
- MRR;
- final-answer correctness where applicable;
- exact citation correctness / unsupported claims;
- current-vs-superseded leakage;
- lineage/historical-current failures;
- poisoning/context-security compatibility;
- pack isolation;
- latency/memory/cost;
- outage/fallback behavior;
- requested versus actual provider/model/runtime identity.

Do not replace D021 because a newer/larger model wins an aggregate score. Decision-critical misses and lifecycle/lineage safety remain hard constraints.

### Suggested immediate D sequence

1. inspect existing Gate-2/post-Gate-2 retrieval benchmark runners and `real_retrieval.py` adapters;
2. define a versioned Workstream-D comparison plan that reuses exact corpus pins and Workstream-F receipts;
3. rerun comparable incumbent BM25/dense baseline;
4. add/measure deterministic hybrid/RRF using existing service interfaces;
5. add one real reranker candidate behind `Reranker` and independently prove requested/actual/fallback identity;
6. only then begin the 0.6B → 4B → 8B embedding progression.

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

## LiteLLM / Cortex boundary

Read `docs/operations/LITELLM-GATEWAY.md` before live provider work.

Recorded LiteLLM defaults remain:

- chat: `qwen3-coder-next`;
- embeddings: `gemini-embedding-2`;
- reranking: `rerank-v4-pro`.

For every live D candidate record requested model, actual model, provider, fallback/attempt diagnostics, latency, cost, runtime identity, exact model revision/configuration where available, and the Workstream-F receipt/trace reference. A fallback response is not proof that the requested model succeeded. Probe embedding and reranking lanes independently. Do not send secrets, personal information, or confidential documents while retention guarantees remain unverified.

Cortex v4 remains replaceable. FOSSIL stable identity, durable storage, lifecycle/lineage, context-security, proposal-before-commit, and correctness guarantees must not couple to Cortex internals. Multiple workers agreeing does not manufacture truth. Future worker/model invocations can extend the receipt with causal child-invocation structure without changing FOSSIL authority.

## Remaining campaign order

1. **D / Issue #47** — embeddings, hybrid retrieval, rerankers, model bakeoff;
2. **E** — conservative adaptive routing, only if benchmark justified;
3. **G** — ACL/redaction propagation readiness;
4. final D021/retrieval-policy decision reconciliation;
5. decision log + residual risks + final handoff.

## Suggested next-session prompt

> Continue FOSSIL Issue #48 / Workstream D from the post-query-execution-receipt handoff. Verify GitHub first. Workstreams A, B, C, and F are complete; do not redo them. F landed in PR #64 / squash `42dab94b51a7b17f20c046f7257b912fe9f0c900`; final CI run `31437754923`, job `93615632123`, was 104/104 green. Execution-only PR #65 was closed unmerged after exact-pin run `31437447245`, job `93614630416`: 27 documents, 6 queries, 18 receipts, with answer correctness / exact replay identity / resolver recording / semantic-result stability / service-change visibility all 1.0. Issue #47 is active Workstream D. Start with comparable incumbent BM25/dense/hybrid/reranker evidence using `fossil.query-execution-receipt.v1`, then progress Qwen3-Embedding 0.6B → 4B → 8B only if justified. Preserve D021, stable pack IDs, `fossil-lineage-context-v1`, `fossil-untrusted-context-v1`, proposal-before-commit, and deterministic lifecycle/lineage authority. Receipts and model/reranker scores are not truth authority.
