# Gate 2B Real Retrieval Adapter Proof

Date: 2026-08-10  
Gate: 2B — real retrieval/context adapters  
Control issue: #33  
Child issue: #35  
PR: #43

## Purpose

Gate 2A produced a real, history-rich 21-case corpus and exposed a specific weakness in the Gate 1 controls: both BM25 and signed-token-hash retrieval missed the supported current architecture while ranking stale, rejected, or historical objects above it.

Gate 2B adds materially different retrieval strategies behind the existing replaceable interfaces without changing canonical FOSSIL identity, pack boundaries, benchmark semantics, or the `Retriever` / `Reranker` / `ContextProvider` contracts.

No production winner is selected here. Comparative judgment belongs to #36 and policy selection to #37.

## Candidate A — revision-pinned real semantic retrieval

`SentenceTransformerEmbeddingProvider` is a lazy optional embedding provider. The default real model is:

- model: `BAAI/bge-small-en-v1.5`
- exact model revision: `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`
- local execution: CPU in the proof run
- normalized embeddings: enabled

`SemanticEmbeddingRetriever` uses the existing in-memory cosine retrieval behavior while preserving the full embedding runtime in benchmark service metadata.

The mandatory core package does **not** install the ML runtime. The optional extra is:

```text
python -m pip install -e '.[semantic]'
```

`pyproject.toml` pins:

```text
sentence-transformers==5.2.2
```

The semantic provider imports Sentence Transformers lazily. Standard contract CI injects a deterministic encoder and does not download a model. If the optional runtime is missing, construction fails explicitly with `OptionalRetrievalDependencyUnavailable` and directs the caller to the semantic extra.

## Candidate B — lexical + semantic RRF with lifecycle-aware reranking

`ReciprocalRankFusionRetriever` combines arbitrary retrievers without changing durable document identity. The live candidate fuses:

- BM25 lexical retrieval;
- the real BGE semantic retriever.

`LifecycleIntentReranker` then uses:

- explicit temporal query cues;
- durable claim/relation `current_state` metadata;
- token overlap for query/document fit.

The final policy deliberately avoids benchmark IDs and ambiguous terms such as `accepted` or `after` as standalone current-state cues. Historical queries continue to surface superseded/rejected/stale material, while explicitly current queries can prefer supported/active state.

`RerankedRetriever` exposes the result through the same `Retriever` interface and retrieves a deeper candidate pool before final ranking.

`BudgetedContextProvider` consumes the reranked retriever unchanged; the context integration test proves that no context-provider contract change is required.

## Runtime/provenance metadata

The final real-provider proof records the following service identity in the benchmark artifact:

- Sentence Transformers: **5.2.2**
- PyTorch: **2.13.0**
- Transformers: **5.14.1**
- model: `BAAI/bge-small-en-v1.5@5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`
- device: `cpu`
- normalization: `true`

These transitive runtime versions are resolved once when the provider is constructed and cached. They are not recomputed in the retrieval hot path.

Hybrid metadata serializes the complete component service metadata and reranker metadata, so the benchmark result can be traced through RRF back to the exact dense provider/runtime.

## Exact benchmark corpus

Both candidates use the same Gate 2A gold set and exact pack commits:

- case set: `benchmarks/gate2/real-corpus-history-v2.json`
- case count: **21**
- retrieval limit: **k=5**
- common: `Pukujan/fossil-common@d583005dce06dbb499c3c0de5c22b899655eb8d2`
- AI systems: `Pukujan/fossil-ai-systems@cf7cf4087bde543cb247a978de2a7252b1b8e4de`

The live runner is:

```text
python scripts/run_gate2_real_retrieval_candidates.py \
  --common-root <fossil-common checkout> \
  --ai-root <fossil-ai-systems checkout> \
  --case-set benchmarks/gate2/real-corpus-history-v2.json \
  --output-dir <result directory> \
  --device cpu
```

A temporary PR-only workflow installed the optional runtime, checked out the exact pinned corpus commits, ran the candidates through the unchanged `fossil.benchmark.v1` harness, and printed every imperfect observation. The workflow was removed after the proof and is not part of the landing branch.

## Final real-provider proof

Workflow run: `31361121496`  
Job: `93370056762`

Targeted adapter/context contract tests in the semantic runtime: **10 passed in 0.11s**.

### Dense BGE candidate

Benchmark ID: `bench_774472befc49b8d4af1ea152`

- hit rate: **1.0**
- mean recall@5: **0.9841269841269842**
- MRR: **0.8587301587301588**
- mean latency: **36.624328000011126 ms**
- p95 latency: **39.90808500000509 ms**
- peak Python allocation: **89,679 bytes**
- estimated call cost: **$0.00**
- category failure rate: **0.0 in every Gate 2A category**

Imperfect ranking/multi-target observations:

- current architecture: returned at rank 5;
- SQLite supersession relation: rank 2;
- stale SQLite dependent: rank 3;
- graph disagreement relation: rank 2;
- recovery no-invention claim: rank 2;
- three-target historical/current/supersession bundle: recall **2/3** because the current architecture is absent from the top five.

This is materially better than both Gate 1 controls on full-case failures: the dense candidate has **zero category failures** while BM25 and hash retrieval each had a 50% failure rate in `current-vs-historical`.

### BGE + BM25 RRF + lifecycle reranker candidate

Benchmark ID: `bench_06ebc648d13e597a575737a5`

- hit rate: **0.9523809523809523**
- mean recall@5: **0.9523809523809523**
- MRR: **0.8666666666666666**
- mean latency: **59.10964414284096 ms**
- p95 latency: **63.469130999989076 ms**
- peak Python allocation: **142,668 bytes**
- estimated call cost: **$0.00**
- category failure rate:
  - `current-vs-historical`: **0.5**
  - all other represented categories: **0.0**

Important imperfections:

- `current_architecture_after_reconsideration` is a full miss;
- the SQLite supersession relation is rank 5;
- graph disagreement relation is rank 2;
- recovery no-invention claim is rank 2.

The candidate fixes the first hybrid version's overcorrection on stale/rejected history, but it still does not solve the original current-architecture retrieval problem.

## Context-provider smoke result

The same final hybrid candidate was passed to `BudgetedContextProvider` with a 4,000-character budget for the current-architecture query.

Result:

- characters used: **707**
- no context truncation/overload occurred;
- selected IDs:
  - `clm_76c6bead3d10df4ca7de8af4`
  - `rel_0996c7d4b845cf3a3fc6bdf8`
  - `clm_62b7f9c6184b14371338ca36`
  - `rel_e0102ade0b5fad5cc2668ccd`
  - `rel_c0e74317e7ff1ee59461b036`
- the supported current-architecture claim is absent.

This is a ranking/temporal-selection failure, not a context-window truncation failure.

## Failure-driven refinement performed in this PR

The first live hybrid run overcorrected lifecycle intent: ambiguous words such as `accepted` and `after` pushed some historical queries toward current state and suppressed a rejected graph alternative and stale dependent. The reranker was refined generically by:

- restricting current cues to explicit temporal terms (`current`, `currently`, `latest`, `now`, `present`, `today`);
- keeping explicit historical cues (`former`, `historical`, `rejected`, `stale`, `superseded`, etc.);
- adding token-overlap fit so unrelated claims with the same lifecycle state do not tie solely on state/rank.

No benchmark case IDs or target IDs are encoded in the policy.

After this generic refinement, stale/rejected retrieval recovered, but the current-architecture miss remained. The algorithm is therefore frozen here rather than tuned further to the gold set.

## Setup, skip, and failure modes

### Standard/core CI

- installs `.[test]` only;
- no Sentence Transformers/PyTorch/model download;
- uses injected encoder objects for semantic-provider contract tests;
- verifies optional-runtime failure behavior;
- verifies RRF, lifecycle reranking, pack filtering, provenance, and context integration deterministically.

Pre-proof frozen-code standard CI run `31361121569`, job `93370057061`: **82 passed in 1.19s**.

### Real semantic runtime

Requires the optional `semantic` extra and a local model load. On an uncached machine:

- model files require network access to the pinned model repository;
- Hugging Face may emit an unauthenticated-download warning if `HF_TOKEN` is absent; the public pinned model still loaded successfully in the proof;
- the optional dependency is operationally heavy because Sentence Transformers pulls the PyTorch/Transformers runtime and transitive packages;
- the first uncached setup is therefore much more expensive than ordinary FOSSIL core installation.

This is deliberately separated from standard CI and canonical knowledge durability.

## Interpretation

The real dense path is a serious competitor and, on this 21-case corpus, is the strongest candidate so far on hit rate, recall, and category failures. It does **not** yet justify a production selection: the corpus is still small, the proof uses one CPU runtime, and the historical/current multi-target bundle remains imperfect.

The lifecycle-aware hybrid is also a real, traceable competitor, but its current policy does not improve the most important Gate 2A temporal failure and adds latency/memory. Its value in #35 is evidence-backed comparison and a concrete failure mode for #36, not a claim that hybrid retrieval must win.

Gate 2B therefore exits with two real strategies, reproducible provider/runtime identity, deterministic standard-CI behavior, explicit optional-runtime failure handling, unchanged interface/harness boundaries, and measured limitations. Comparative evidence and failure taxonomy continue in #36.
