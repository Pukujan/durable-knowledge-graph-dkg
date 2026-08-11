# Current Handoff

**Date:** 2026-08-10  
**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Repository:** `Pukujan/fossil-core`  
**Status:** **Gate 1 complete. Gate 2 complete/formally closed. Post-Gate-2 campaign #48 active. Workstreams A/B/C/F complete. Workstream D stage 1 complete. D stage 2 is active next. Cortex↔FOSSIL ownership boundary is now explicitly documented; legacy `stupidly-simple-cortex` is being retired as a live memory/runtime authority while its evaluation estate is preserved separately.**

## Fresh-session transfer

Read, in order:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. this file
4. `docs/architecture/2026-08-10-cortex-fossil-ownership-boundary.md`
5. `docs/research/2026-08-10-legacy-ssc-evaluation-estate-inventory.md`
6. `docs/handoffs/2026-08-10-chatgpt-session-handoff-post-retrieval-bakeoff-stage1.md`
7. `docs/PROJECT_STATE.md`
8. `docs/implementation/2026-08-10-post-gate2-retrieval-bakeoff-stage1-proof.md`
9. `docs/implementation/2026-08-10-post-gate2-query-execution-receipt-proof.md`
10. `docs/implementation/2026-08-10-post-gate2-retrieval-poisoning-proof.md`
11. `docs/implementation/2026-08-10-post-gate2-answer-reliability-proof.md`
12. `docs/operations/LITELLM-GATEWAY.md`
13. Issue #48 — active production RAG hardening campaign
14. Issue #47 — active Workstream D retrieval/reranking/model bakeoff
15. `docs/DECISION_LOG.md`

Verify GitHub state before changing anything.

## Do not redo

Do not redo:

- Gate 1 or Gate 2;
- production-RAG research ingestion;
- Workstream A — evolving-corpus temporal/update benchmark;
- Workstream B — answer/citation/abstention reliability;
- Workstream C — retrieval poisoning/untrusted context;
- Workstream F — query execution receipts;
- Workstream D stage 1 — incumbent/hybrid/real-reranker matched bakeoff.

## Workstream D stage 1 — complete

Core PR #67 landed the first matched retrieval/reranker comparison surface.

Execution-only PR #68 was a failed-first instrumentation/exit-semantics probe and was closed unmerged.

Execution-only PR #69 was the corrected final real-semantic proof and was closed unmerged after PASS.

Stage-1 proof inputs:

- common pack revision `d583005dce06dbb499c3c0de5c22b899655eb8d2`;
- AI-systems pack revision `84accd2ee895663990e82ca5b79b592cb503db24`;
- 27 projected documents;
- 21 history-rich retrieval cases;
- 6 Workstream-B answer cases;
- 6 routes;
- 36 Workstream-F receipts;
- real D021 `BAAI/bge-small-en-v1.5@5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` on CPU;
- real `cross-encoder/ms-marco-MiniLM-L6-v2@ce0834f22110de6d9222af7a7a03628121708969` on CPU, batch 16, max length 512.

The final stage gate passed with pack isolation intact and the incumbent D021 downstream answer/citation/unsupported-claim guardrails intact. Challenger routes have explicit promotion eligibility/disqualification evidence. Stage 1 does **not** authorize replacing D021.

## Live LiteLLM retrieval-lane checkpoint

Execution-only PR #71 was used only to probe the shared LiteLLM gateway and was closed unmerged.

Final probe:

- run `31441469357`;
- job `93626893009`;
- `POST /v1/embeddings` with `gemini-embedding-2` -> HTTP 200, non-empty 3072-dimensional embedding, response model `google/gemini-embedding-2`;
- `POST /v1/rerank` with `rerank-v4-pro` -> HTTP 200 and ranked results;
- privacy-warning header present on the live retrieval lanes;
- `/v1/models` and `/v1/model/info` -> HTTP 500;
- chat/responses probes for Qwen and Gemini aliases -> HTTP 500.

Conclusion: embedding and reranking lanes are live and usable for Workstream D. Chat/model-discovery failure is a separate gateway issue and must not be represented as proof that Gemini chat itself is unavailable.

Do not infer that hosted reranking is free from zero token counters; hosted rerank billing may use a different unit. If the gateway does not expose actual upstream reranker identity, record provenance as unresolved rather than inventing it.

## Exact next Workstream-D task

Run a matched D stage-2 benchmark with the existing exact corpus pins and Workstream-F receipts.

Minimum candidate set:

1. incumbent pinned BGE D021 baseline;
2. Qwen3-Embedding 0.6B, after resolving an immutable official model revision and pinning runtime/prompt/dimension/precision/device settings;
3. live LiteLLM `gemini-embedding-2` embedding lane with requested/actual identity recorded;
4. comparable local cross-encoder rerank route;
5. live LiteLLM `rerank-v4-pro` route, with actual upstream identity explicitly recorded when available or marked unresolved.

Reuse the stage-1 21 retrieval cases and six Workstream-B answer cases unless a versioned benchmark change is explicitly justified.

Compare at minimum:

- full retrieval misses/hit rate;
- recall@k;
- MRR/ranking quality;
- decision-critical misses;
- current-vs-superseded leakage;
- lineage/multi-target failures;
- final-answer correctness;
- exact citation correctness;
- unsupported-claim/abstention behavior;
- poisoning/context-security compatibility;
- pack isolation;
- latency;
- memory/resource use;
- provider cost;
- outage/fallback behavior;
- exact requested and actual provider/model/service/runtime identity;
- Workstream-F receipt identity.

Do not automatically progress to Qwen 4B or 8B. The preceding result and resource evidence must justify escalation.

## Cortex ↔ FOSSIL ownership boundary

The durable boundary is now:

> **Cortex owns execution. FOSSIL owns knowledge. FOSSIL projections retrieve knowledge. Infrastructure runs the components. Models propose; deterministic gates commit.**

And:

> **Cortex may decide when and why to ask memory; it cannot decide what durable memory means. FOSSIL may use replaceable cognitive services internally; it cannot decide what an agent is allowed to do next.**

See `docs/architecture/2026-08-10-cortex-fossil-ownership-boundary.md` for the full contract.

### Cortex owns

- agent/session/mission state;
- task classification and executable methodology selection;
- preflight/tool/risk gates;
- model/worker dispatch;
- retry/decomposition/fan-out/merge strategy;
- context-window/resource budgets;
- compression/decomposition decisions;
- operational checkpoints/closeouts.

### FOSSIL owns

- immutable evidence;
- persistent semantic memory;
- stable claim/source/relation/citation IDs;
- provenance;
- lifecycle/current-state semantics;
- disagreement/supersession/history;
- lineage reconstruction;
- pack boundaries;
- exact citations;
- redaction/suppression;
- proposal validation and durable commit;
- corpus retrieval semantics and rebuildable graph/vector/lexical projections.

Prevent double routing: Cortex provides task intent, pack scope, risk/resource/context constraints; FOSSIL executes the approved retrieval/lifecycle/lineage/citation semantics. Cortex must not bypass FOSSIL by querying a graph/vector index and treating that result as knowledge authority.

## Gravebuster + local-PC deployment

Treat the cluster as **one logical FOSSIL**, even when services run on multiple machines.

Initial rule: use **one logical durable FOSSIL commit authority**, not independent multi-master semantic writers.

Gravebuster and the local PC may host replaceable:

- Graphiti/Neo4j projections;
- BM25/vector indexes;
- embedding/reranking services;
- model servers/LiteLLM;
- caches;
- replicas/backups;
- benchmark workers.

Hosting does not confer semantic authority. Stable IDs and pack identity remain independent of machine/database placement.

A future multi-writer topology requires a separate concurrency/consensus decision and proof.

## Compression boundary

Cortex owns model-context budgeting and the decision to compress/direct-read/decompose.

FOSSIL owns the exact evidence/stable identities that compression is forbidden to corrupt.

Required rules:

- summaries never replace source evidence;
- protected citation/source/claim identities survive verbatim where required;
- numbers/code identifiers/provenance IDs may be protected spans;
- compressed packets remain temporary untrusted context;
- required-span loss fails closed;
- if safe compression cannot meet budget, raise budget/direct-read/decompose instead of silent destructive compression;
- a durable summary is a new derived proposal with provenance, never replacement evidence.

The legacy SSC protected-span compressor is prior art only, not a live dependency.

## Legacy `stupidly-simple-cortex` retirement

The old SSC runtime should be retired rather than maintained as a second live memory system.

Do **not** import the following as FOSSIL truth:

- old SSC living-ontology/current-state values;
- SSC BM25/vector ranking results;
- generated conclusions/summaries;
- old research prose merely because it was labeled research/reviewed/accepted/current;
- old task/project state;
- model consensus/judge conclusions.

Old SSC research prose can remain historical/unverified source material for manual discovery, but no automatic ingestion into normal FOSSIL knowledge is required.

## Legacy SSC evaluation estate — preserve separately

A substantial valuable evaluation estate is actually committed in SSC and should be extracted separately from the retired runtime.

Verified source revision inspected:

`Pukujan/stupidly-simple-cortex@3b6668eff7a1859c37f1aa50c565f0387fdc4ffe`

Verified asset classes include:

- checker-decided `hard_gold` datasets;
- generated 73-lane objective manifest with deterministic verdict paths and `judge_in_verdict_path=false`;
- third-party-derived objective benchmark slices;
- semi-ground/semi-truth judgment data;
- rubrics/calibration anchors;
- oracle/checker code;
- frozen tests;
- checker cores/resolvers;
- promotion/quarantine/results-ledger machinery;
- live/trainable hard-gold references and holdouts;
- durable evaluation artifact indexes.

Directly inspected examples include:

- `evals/objective_tool_calling/hard_gold.jsonl` — real rows with objective verdict, BFCL AST checker authority, error/perturbation metadata, source/case ID, hard-gold provenance and reproducibility hash metadata;
- `evals/hf_datasets/gsm_plus/hard_gold.jsonl` — committed prompt/reference-solution/reference-answer rows;
- `evals/fable_capture/prompt_evals_semitruth.jsonl` — explicitly provisional candidate-only rows with `human_reviewed=false` and `ground_truth_for_now=false`.

### Important stale-index finding

Do not trust SSC's narrative artifact counts as the archive manifest.

Observed example:

- `evals/FABLE_DURABLE_ARTIFACT_INDEX.md` reports 500 HaluEval semi-ground rows;
- direct read of `evals/hf_datasets/halu_eval/semi_ground.jsonl` on current `main` returned empty content.

`evals/README.md` also contains older build-status prose predating later hard-gold work.

Therefore extract by:

`exact source commit + path + content hash + actual bytes/row count + license/source + checker/test dependency`.

See `docs/research/2026-08-10-legacy-ssc-evaluation-estate-inventory.md`.

### Target extraction posture

Do not make FOSSIL or Cortex depend on SSC at runtime.

Create a standalone versioned/content-addressed evaluation archive containing selected:

- hard gold;
- semi-ground;
- rubrics;
- checkers;
- frozen tests;
- resolvers;
- manifests;
- quarantine data;
- reports/source-license metadata.

Revalidate each historical `hard_gold` label during extraction. If checker/reference/license provenance cannot be established, downgrade the archive classification rather than trusting the old filename/label.

Resolve holdout secrecy before copying any `*_holdout` assets into a developer-visible archive.

## D021 remains frozen

Do not replace or weaken D021 without new committed comparative evidence.

Current rules:

- revision-pinned BGE dense is the normal primary retriever;
- BM25 is explicit degraded availability fallback;
- current/latest/accepted queries resolve durable lifecycle/provenance;
- history/lineage/disagreement queries use durable lineage/read-state;
- top-k absence is not evidence of nonexistence;
- citations resolve immutable source snapshot/span/hash identity;
- retrieved/source text is untrusted data;
- retrieval score is not truth;
- reranker score is not truth;
- model confidence is not truth;
- multi-model consensus is not external evidence;
- query execution receipts are observability/replay evidence, not truth authority.

Stable pack IDs:

- common: `pack_269099f7b2ba43b7a99b9427d64092de`;
- AI systems: `pack_f024177f89a5442db84171c3dd7f58e5`.

Exact pack revisions used by B/C/F/D-stage-1 proofs:

- `fossil-common@d583005dce06dbb499c3c0de5c22b899655eb8d2`;
- `fossil-ai-systems@84accd2ee895663990e82ca5b79b592cb503db24`.

Do not casually rename `src/dkg`.

## Remaining campaign / integration order

1. **D stage 2** — BGE vs Qwen3-Embedding 0.6B vs Gemini Embedding 2, with matched reranker routes and Workstream-F receipts.
2. **Legacy SSC evaluation-estate extraction** — separate archive/inventory track; not a live runtime dependency and not a blocker for basic D retrieval benchmarking unless an extracted eval is intentionally used.
3. **Context-budget/compression benchmark** — preservation-safe Cortex context handling against direct/uncompressed baselines.
4. **D 4B/8B only if justified** by prior evidence/resources.
5. **E** — conservative adaptive routing, including direct-read vs retrieve vs retrieve+compress vs decompose where evidence supports it.
6. **G** — ACL/redaction propagation readiness, including proof that retrieval/reranking/compression/replicas cannot resurrect suppressed data.
7. **Cortex↔FOSSIL live integration proof** — Cortex persistent memory uses FOSSIL without SSC runtime dependency; exact IDs/citations/lifecycle/lineage survive the boundary; FOSSIL outage yields pending/uncommitted state rather than false success.
8. final D021/retrieval-policy decision reconciliation;
9. decision log + residual risks + final handoff.
