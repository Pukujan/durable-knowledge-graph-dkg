# Post-Gate-2 Workstream D — Retrieval / Reranker Bakeoff Stage-1 Proof

**Date:** 2026-08-10  
**Campaign:** Issue #48 — production RAG hardening  
**Workstream:** D / Issue #47 — retrieval, reranking, and model bakeoff  
**Stage:** 1 — incumbent + lexical + hybrid + real reranker baseline

## Scope

This stage establishes matched, receipt-backed evidence for the existing D021 retrieval stack and a small set of hybrid/reranker challengers **before** any Qwen3 embedding-model scale progression.

It does not replace or weaken D021.

The governing rule remains:

> Retrieval and reranker scores order candidates; they do not create durable truth.

Every downstream answer run remains behind:

- `fossil-untrusted-context-v1`;
- `fossil-lineage-context-v1`;
- the Workstream-B deterministic answer evaluator;
- Workstream-F `fossil.query-execution-receipt.v1` observability.

Query execution receipts remain `execution_observability_only`; they are not mutation authority or canonical knowledge.

## Exact corpus pins

The stage-1 execution uses the same validated pack revisions as Workstreams B, C, and F:

- `Pukujan/fossil-common@d583005dce06dbb499c3c0de5c22b899655eb8d2`;
- `Pukujan/fossil-ai-systems@84accd2ee895663990e82ca5b79b592cb503db24`.

Stable mounted pack IDs:

- common: `pack_269099f7b2ba43b7a99b9427d64092de`;
- AI systems: `pack_f024177f89a5442db84171c3dd7f58e5`.

The projected corpus contains **27 documents**.

## Exact candidate/runtime pins

### Incumbent dense embedding

- model: `BAAI/bge-small-en-v1.5`;
- revision: `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`;
- runtime: local Sentence Transformers on CPU;
- role: incumbent D021 primary retrieval component.

### Real cross-encoder reranker

- model: `cross-encoder/ms-marco-MiniLM-L6-v2`;
- revision: `ce0834f22110de6d9222af7a7a03628121708969`;
- runtime: local Sentence Transformers `CrossEncoder` on CPU;
- batch size: `16`;
- max length: `512`;
- role: candidate ordering only.

The adapter is implemented by `SentenceTransformerCrossEncoderReranker` behind the existing FOSSIL `Reranker` contract. The ML dependency remains optional/lazy in normal core installs; normal CI uses an injected deterministic model fixture rather than downloading weights.

## Versioned benchmark plan

The committed plan is:

`benchmarks/post-gate2/retrieval-bakeoff-v1.json`

Matched evaluation uses:

- **21** history-rich retrieval cases from `benchmarks/gate2/real-corpus-history-v2.json`;
- **6** Workstream-B final-answer/citation/abstention cases from `benchmarks/post-gate2/answer-reliability-v1.json`;
- retrieval limit `5`;
- matched candidate multiplier `4` for the reranked/hybrid lanes;
- RRF `k=60`;
- **6 routes**;
- **36 Workstream-F receipts** for downstream answer executions.

Routes:

1. `bm25` — explicit degraded/fallback baseline;
2. `bge-dense` — incumbent primary dense route;
3. `bge-bm25-rrf` — deterministic hybrid candidate;
4. `bge-bm25-rrf-lifecycle` — hybrid plus deterministic lifecycle reranking;
5. `bge-dense-crossencoder` — incumbent dense candidates plus real cross-encoder;
6. `bge-bm25-rrf-crossencoder` — hybrid candidates plus real cross-encoder.

The report records hit rate, recall@k, MRR, latency, Python allocation peak, process max RSS, pack isolation, bounded current-query superseded top-1 leakage, final-answer correctness, exact citation correctness, unsupported-claim rate, and exact execution/service identity through Workstream-F receipts.

## Normal contract proof

PR #67 normal CI passed on the corrected stage-1 implementation after the eligibility semantics were covered by dedicated tests.

The core suite includes tests for:

- exact cross-encoder model/revision/runtime identity;
- pairwise prediction and stable tie behavior;
- optional-runtime failure handling;
- `RerankedRetriever` propagation of real reranker identity;
- challenger-disqualification semantics;
- retrieval-leakage classification;
- pack-isolation hard failure;
- promotion eligibility only for a fully clean route.

## Failed-first execution probe — PR #68

Execution-only PR #68 was intentionally closed unmerged after it exposed two harness issues while preserving useful benchmark evidence:

1. the first bakeoff exit rule incorrectly required **every challenger** to pass the downstream answer/citation guardrails, which conflated a weak candidate with broken benchmark infrastructure;
2. the temporary proof workflow initially wrote evidence under a hidden directory that `upload-artifact@v4` did not include by default.

The semantic runtime itself installed successfully and the core tests passed before the original benchmark-stage failure.

The correction did **not** weaken expected answers, citations, pack isolation, or D021 safeguards. Instead, each challenger now receives explicit:

- `end_to_end_guardrails_pass`;
- `retrieval_leakage_free`;
- `eligible_for_promotion`;
- `disqualifying_reasons`.

A challenger can therefore fail and remain valuable evidence without being mislabeled as an infrastructure failure.

The hard top-level execution gates remain:

- exact pack isolation for every route;
- incumbent `bge-dense` end-to-end answer/citation/unsupported-claim guardrails.

## Final real-semantic execution proof — PASS

Execution-only PR #69 reran the corrected, unchanged stage-1 plan from the final feature implementation using the real pinned BGE model and the real pinned cross-encoder.

Result: **PASS**.

The proof completed:

- 27 projected corpus documents;
- 21 retrieval cases;
- 6 answer cases;
- 6 matched routes;
- 36 Workstream-F receipts;
- real local BGE embedding execution;
- real local cross-encoder execution;
- per-route retrieval, latency/resource, safety, and final-answer/citation evaluation;
- explicit per-route promotion eligibility/disqualification evidence.

The full exact route metrics and service/runtime metadata are preserved in the execution-only PR #69 workflow output and artifact named:

`post-gate2-retrieval-bakeoff-proof-v2`

The final stage gate passed because benchmark infrastructure completed, pack isolation remained intact, and the incumbent D021 route retained the required downstream answer/citation/unsupported-claim safety boundary. Challenger routes are judged individually; no challenger result from this stage authorizes a D021 replacement.

## Interpretation

Stage 1 establishes a reproducible matched comparison surface and a genuine real-reranker lane. It is not a selection proof for a new retrieval policy.

A candidate is **not promotable** merely because it improves hit rate, recall, MRR, or aggregate ranking quality. Promotion still requires the downstream answer/citation guardrails, lifecycle/lineage safety, pack isolation, poisoning/context-security compatibility, and operational tradeoffs to remain acceptable.

Likewise, a candidate that fails a guardrail is retained as negative benchmark evidence rather than hidden or converted into a benchmark failure.

## D021 decision

**D021 remains unchanged after stage 1.**

The first-stage plan explicitly records:

`d021_replacement_decision = not_authorized_by_first_stage`

This stage exists to establish comparable incumbent/hybrid/reranker evidence and the real reranker adapter. It does not yet answer the embedding-scale question.

## Next Workstream-D stage

With stage-1 evidence committed, Workstream D may proceed to the progressive embedding bakeoff in Issue #47:

1. Qwen3-Embedding 0.6B class candidate;
2. 4B only if the 0.6B result and available resources justify continuing;
3. 8B only if the preceding evidence justifies the additional cost/resource burden;
4. optional BGE-M3 / larger BGE-family control when useful.

Each configuration must pin exact model/revision/runtime/library/precision/hardware identity and use the same versioned corpus/case sets and Workstream-F receipt boundary where comparison is intended to be matched.

## Residual risks

- The corpus and benchmark remain small; route ordering can be sensitive to a few history-rich cases.
- The chosen MS MARCO MiniLM cross-encoder is a real reranker but not a universal reranker or a claim that this model family is optimal for FOSSIL.
- CPU latency/resource measurements are runner-specific and should not be generalized to GPU or provider-hosted serving.
- Python allocation peak and process RSS are useful execution evidence but are not a complete systems-memory profile.
- Hosted/API candidates may introduce nondeterminism, rate limits, fallback behavior, privacy/retention concerns, and provider-version drift absent from this local stage.
- Retrieval leakage audits cover committed bounded cases; they are not a proof that no stale or adversarial passage can ever rank first.
- A Workstream-F receipt records what ran; it does not make a score, model, reranker, or multi-agent consensus into evidence.
- The final D021 reconciliation must consider decision-critical misses and lifecycle/lineage safety, not aggregate retrieval metrics alone.
