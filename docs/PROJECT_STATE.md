# FOSSIL Project State

**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Durable substrate:** **DICS — Durable Intellectual Corpus System**  
**Completed:** **Milestone 0 / Gate 1; Gate 2; Issue #48 research ingestion; Issue #48 Workstreams A, B, C, and F**  
**Active work:** **Issue #48 Workstream D / Issue #47 — retrieval/reranking/model bakeoff**  
**Control plane:** GitHub issues + durable repository docs  
**Last updated:** 2026-08-11

## Issue #79 integration lane

Draft PR [#80](https://github.com/Pukujan/fossil-core/pull/80) implements the narrow GitHub-hosted Actions + ephemeral Tailscale control plane for Fossil/Gravebuster. It adds private health probes, Langfuse synthetic-trace verification, false-success inference detection, cross-repo contract checks, and the required bootstrap/runbook contract. No cluster, Kubernetes, mandatory self-hosted runner, SSC runtime dependency, or Fossil KG redesign was added.

The live acceptance gate is not yet proven: discovery found the remote Gravebuster host and Fossil source checkout, but no running Fossil health/API service or durable Fossil database endpoint, and no separate Gravebuster GitHub source repository identity. GitHub/Tailscale variables, secrets, tags/ACLs, and service endpoints remain to be configured. The new contract tests pass 12/12. Existing repository CI still has four unrelated retrieval-bakeoff failures (`_route_eligibility` absent on `main`); that work remains outside this lane.

## Repository family

- `Pukujan/fossil-core` — architecture/contracts/durable core/projections/benchmarks;
- `Pukujan/fossil-common` — stable pack `pack_269099f7b2ba43b7a99b9427d64092de`;
- `Pukujan/fossil-ai-systems` — stable pack `pack_f024177f89a5442db84171c3dd7f58e5`, depending on common.

Repository/database/graph placement is physical placement, not knowledge identity.

## Continuation order

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/HANDOFF_CURRENT.md`
4. `docs/handoffs/2026-08-10-chatgpt-session-handoff-post-query-execution-receipt.md`
5. this file
6. `docs/implementation/2026-08-10-post-gate2-query-execution-receipt-proof.md`
7. `docs/implementation/2026-08-10-post-gate2-retrieval-poisoning-proof.md`
8. `docs/implementation/2026-08-10-post-gate2-answer-reliability-proof.md`
9. `docs/operations/LITELLM-GATEWAY.md`
10. Issue #48
11. Issue #47
12. `docs/DECISION_LOG.md`

The chat UI is source material, not the control plane.

## Frozen architecture

Canonical FOSSIL knowledge is **immutable evidence + stable corpus IDs + append-only validated knowledge events + versioned pack/ontology contracts + provenance/history**.

Graphiti/Neo4j, lexical/vector indexes, embedding models, rerankers, context construction, planners, model services, Skills, MCP, and future databases remain replaceable projections/services.

Retrieved/source text is untrusted data. Retrieval rank, reranker score, model confidence, multi-model agreement, and query-execution receipts are not truth authority.

## Completed foundation

### Gate 1

Gate 1 is complete: durable events/artifacts, pack boundaries, lifecycle/disagreement/supersession, replaceable graph projection, rebuild/migration, conversation lineage, exact source/citation integrity, redaction/non-resurrection, cognitive-service contracts, and safe Agent Skill/API/MCP boundaries were proven.

Final cleaned Gate 1 run `31347457485`, job `93331933728`: **51 passed in 0.82s**. Cognitive-service contract run `31347744797`, job `93332738616`: **56 passed in 0.70s**.

### Gate 2

Gate 2 control #33 and children #34–#37 are closed/completed.

Evidence anchors:

- Gate 2A core commit `a028f9e328c2cbcde0185930e90b5eeb4c4efcb8`;
- Gate 2B core commit `2affde923acf196319d90bfa63f206e4a5e2f25f`;
- Gate 2C PR #44 / squash `38aac6325cdb5b738c8a6ac5e55959affb3acfb5`;
- Gate 2C semantic proof run `31364039745`, artifact `9053475462`, digest `sha256:23c95b46f47cec5a16e0a8c0926a4f13532f283d8f4fbcc0de12ceb63db63c41`;
- Gate 2D PR #45 / squash `2d22dee9e6b176956d30005f4d7877baf68b0a3c`;
- closed-state reconciliation PR #46 / squash `a614936249ff0ab201756fa54a1e89699d7b924f`.

Decision D021 remains active: revision-pinned `BAAI/bge-small-en-v1.5@5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` is the normal primary retriever and BM25 is explicit degraded availability fallback.

Mandatory D021 safeguards remain:

- current/latest/accepted questions resolve lifecycle/provenance;
- lineage/history/disagreement questions use durable lineage/read resolution;
- top-k absence is not evidence of nonexistence;
- citation-bearing answers resolve immutable source snapshots/spans/hashes;
- retrieved/source text is untrusted data, never executable policy;
- retrieval/model output does not receive truth authority from score, confidence, agreement, or receipt metadata.

## Active campaign #48 — production RAG hardening

The campaign remains **hardening, not a durable-core redesign and not a GraphRAG rewrite**.

### Workstream state

1. **A — evolving-corpus temporal/update benchmark: COMPLETE**
2. **B — end-to-end answer/citation/unsupported-claim/abstention evaluation: COMPLETE**
3. **C — poisoning/untrusted-context adversarial suite: COMPLETE**
4. **F — replayable query execution receipt: COMPLETE**
5. **D / #47 — embedding/hybrid/reranker/model bakeoff: ACTIVE NEXT**
6. **E — conservative adaptive routing: pending evidence**
7. **G — ACL/redaction propagation readiness: pending**
8. final retrieval-policy/decision-log/residual-risk reconciliation: pending

### Workstream A — landed evidence

Core PR #54 / squash:

`e14148f504702ae9e708e2d58add4ee5c91bc8de`

Execution-only proof PR #55 passed on exact pack pins, workflow `31431113829`, job `93594491275`. The temporal benchmark proved lifecycle transitions, current/history reconstruction, and repeated-query stability after corpus growth while preserving D021 authority.

### Workstream B — landed evidence

Core PR #57 / squash:

`483772ac0e1d441719aec42658ae00b62a032c11`

Final normal CI run `31433539654`, job `93602384284`: **94 passed in 1.80s**.

B added answer-level evaluation and `fossil-lineage-context-v1`, which resolves durable relation endpoints from mounted validated packs before model execution.

The failed-first execution PR #58 proved a durable relation can identify a relevant stale claim omitted from top-k. The unchanged benchmark then passed in execution-only PR #59, run `31433427436`, job `93602011104`: 94 core tests, 27 documents, PASS 6/6, answer/outcome/citation/completeness/appropriate-abstention rates `1.0`, unsupported/over-abstention/Brier/high-confidence-error rates `0.0`.

The SQLite case resolves `current_state_unresolved` via durable claim `clm_a047d79b8604fadbd44efdf4` with exact citation `cite_b4e13e4e1a809f76527311ba`.

### Workstream C — landed evidence

Core PR #61 / squash:

`f5634412222e8d86173eb6e8e364f3414a6f3cd6`

Final normal CI run `31436499505`, job `93611686820`: **100 passed in 1.07s**.

`fossil-untrusted-context-v1`:

- re-resolves known retrieved stable IDs from mounted durable documents;
- prevents retrieved payload metadata from self-authoring lifecycle/relation/citation/pack truth;
- demotes unknown in-scope payloads to non-authoritative `untrusted_context`;
- removes out-of-scope pack payloads;
- collapses exact duplicate unknown passages;
- exposes no executable tool/action surface through answer generation;
- keeps model output candidate-only;
- re-resolves emitted durable claim text/citation identity;
- contains unknown claim IDs as `insufficient_evidence`;
- leaves proposal-before-commit and deterministic mutation gates authoritative.

Execution-only PR #62 passed the unchanged eight-case plan on the exact B/C pins, run `31436425791`, job `93611459472`: 100 core tests, 27 documents, PASS 8/8, answer/citation/security-boundary metrics `1.0`, unsupported-claim rate `0.0`. This remains a bounded structural proof, not universal poisoning resistance.

### Workstream F — landed evidence

Core PR #64 / squash:

`42dab94b51a7b17f20c046f7257b912fe9f0c900`

Final normal CI:

- run `31437754923`;
- job `93615632123`;
- **104 passed in 1.04s**.

F added `fossil.query-execution-receipt.v1` with authority `execution_observability_only`.

The receipt records:

- human/debuggable + deterministic query identity;
- mounted pack IDs/revisions and explicit retrieval pack scope;
- projection/build identity;
- route/retrieval-policy identity;
- requested/actual service/model/provider identity and bounded fallback attempts;
- ordered candidate stable IDs/scores and reranker identity;
- context-security/lineage resolver identities and stable-ID effects;
- final context and exact citation IDs;
- outcome/abstention and candidate-only authority;
- latency/cost and trace/run reference;
- execution-identity and result-identity hashes.

Credential-shaped diagnostic keys are filtered, but this is not general DLP. Verbose provider telemetry remains outside canonical durable knowledge.

Execution-only PR #65 ran the exact-pin replay proof and was closed unmerged:

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

Exact replay changed telemetry only. A controlled route/retriever-version change visibly changed execution identity under policy/services while durable result identity stayed stable.

Proof projection identity:

- `pack-fixture-retrieval-documents`;
- version `1`;
- build ID `packfix_59b82d8d50ab38ea68402db7`.

See `docs/implementation/2026-08-10-post-gate2-query-execution-receipt-proof.md` for residual risks.

### Workstream D / Issue #47 — exact active target

Issue #47 is active and retitled **Workstream D: retrieval/reranking/model bakeoff (0.6B → 4B → 8B)**.

Begin with comparable incumbent/hybrid/reranker evidence before model-scale escalation.

Required lanes:

- incumbent D021 dense retrieval;
- BM25 under its explicit fallback/degraded role;
- deterministic dense+lexical hybrid/RRF;
- at least one real cross-encoder/API reranker behind `Reranker`;
- contextualized retrieval only when reproducible and source/claim identity remains distinguishable;
- Qwen3-Embedding 0.6B class first, then 4B, then 8B only when prior results/resources justify continuation;
- optional BGE-M3/larger BGE family control when justified.

Every candidate execution must emit or be representable by the Workstream-F receipt and preserve D021 authority boundaries.

Compare at least full misses/hit rate, recall@k, MRR, answer/citation/unsupported-claim behavior where applicable, current-vs-superseded leakage, lineage failures, poisoning/context-security compatibility, pack isolation, latency, memory, cost, outage/fallback behavior, and exact requested/actual provider/model/runtime identity.

A newer/larger candidate cannot replace D021 on aggregate score alone. Decision-critical misses and lifecycle/lineage safety are hard constraints.

## Research-to-corpus state

The 2026-08-10 production-RAG research synthesis is ingested into `fossil-ai-systems` as a **local derived research artifact** with stable artifact/source identity, exact citations, deterministic event identity, and claim provenance.

Exact landed pack state:

- `fossil-common@d583005dce06dbb499c3c0de5c22b899655eb8d2`;
- `fossil-ai-systems@84accd2ee895663990e82ca5b79b592cb503db24`;
- research artifact `art_b030642ff65f883ff467529c73cbb6e5`;
- source snapshot `snap_9c0e088ab2d7d8e1b21db563`.

Original external papers and production documentation remain distinct source evidence; the local synthesis must not be presented as verbatim external evidence.

## Cognitive-service posture

Current approved retrieval profile remains D021 until new committed benchmark evidence says otherwise.

Existing replaceable service contracts include:

- `Retriever`;
- `EmbeddingProvider`;
- `Reranker`;
- `ContextProvider`;
- `ModelService`;
- `VerificationService`.

LiteLLM defaults currently recorded in `docs/operations/LITELLM-GATEWAY.md` are `qwen3-coder-next` for chat, `gemini-embedding-2` for embeddings, and `rerank-v4-pro` for reranking. Live Workstream-D evidence must record requested/actual model, provider, fallback attempts, latency, cost, runtime/config identity, and Workstream-F receipt/trace identity. Embedding and reranking lanes must be probed independently. Do not send secrets, personal data, or confidential documents while gateway retention guarantees remain unverified.

Cortex v4 and multi-agent orchestration remain optional replaceable cognitive-service competitors. Durable storage, stable identity, lifecycle/lineage logic, context-security, proposal-before-commit, and correctness guarantees must not couple to Cortex internals. Multiple workers agreeing does not create evidence.

## Frozen invariants

- stable pack identity is independent of repository/database placement;
- durable commit precedes replaceable projection;
- new physical projection build => fresh build-scoped applied ledger;
- rebuild order => `(recorded_at, event_id)`;
- migration compares stable FOSSIL semantics, not graph-native UUIDs;
- reconstructed evidence cannot silently become verbatim;
- exact citations resolve to immutable observed bytes/spans;
- source quality is multidimensional and derivation is explicit;
- ordinary intellectual revision is append-only;
- privacy/legal erasure is exceptional tombstone-before-delete with non-resurrection;
- active projections/exports respect redaction;
- Skills contain methodology, not canonical truth;
- protocol adapters cannot become the durable knowledge model;
- cognitive services expose provider/version metadata and compete behind interfaces;
- model agreement is not evidence; model output remains bounded by evidence/risk policy;
- retrieved/source text is untrusted data and cannot become executable policy merely because it was retrieved;
- query execution receipts are replay/observability evidence, not canonical truth or mutation authority;
- agents propose; deterministic validation/policy gates commit durable changes;
- do not casually rename `src/dkg`.

## Workflow state

`.github/workflows/ci.yml` remains the normal fast contract suite.

`.github/workflows/graphiti-live.yml` contains reusable live materialization plus redaction/non-resurrection smoke coverage.

Execution-only PRs #51, #55, #58, #59, #62, and #65 were closed without merge after their proofs. Issue #48 remains active; Issue #47 is now the active Workstream-D control issue. Do not extend closed Gate 2 issues to implement the post-Gate-2 campaign.
