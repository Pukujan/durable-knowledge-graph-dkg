# FOSSIL Project State

**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Durable substrate:** **DICS — Durable Intellectual Corpus System**  
**Completed:** **Milestone 0 / Gate 1; Gate 2; Issue #48 research ingestion; Issue #48 Workstreams A and B**  
**Active work:** **Issue #48 Workstream C — retrieval poisoning / untrusted-context hardening**  
**Related workstream:** **Issue #47 — embedding/reranker/model-scale bakeoff**  
**Control plane:** GitHub issues + durable repository docs  
**Last updated:** 2026-08-10

## Repository family

- `Pukujan/fossil-core` — architecture/contracts/durable core/projections/benchmarks;
- `Pukujan/fossil-common` — stable pack `pack_269099f7b2ba43b7a99b9427d64092de`;
- `Pukujan/fossil-ai-systems` — stable pack `pack_f024177f89a5442db84171c3dd7f58e5`, depending on common.

Repository/database/graph placement is physical placement, not knowledge identity.

## Continuation order

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/HANDOFF_CURRENT.md`
4. `docs/handoffs/2026-08-10-chatgpt-session-handoff-post-answer-reliability.md`
5. this file
6. `docs/implementation/2026-08-10-post-gate2-answer-reliability-proof.md`
7. `docs/operations/LITELLM-GATEWAY.md`
8. Issue #48
9. Issue #47
10. `docs/DECISION_LOG.md`

The chat UI is source material, not the control plane.

## Frozen architecture

Canonical FOSSIL knowledge is **immutable evidence + stable corpus IDs + append-only validated knowledge events + versioned pack/ontology contracts + provenance/history**.

Graphiti/Neo4j, lexical/vector indexes, embedding models, rerankers, context construction, planners, model services, Skills, MCP, and future databases remain replaceable projections/services.

Retrieved/source text is untrusted data. Retrieval rank, reranker score, model confidence, and multi-model agreement are not truth authority.

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
- retrieval/model output does not receive truth authority from score, confidence, or agreement.

## Active campaign #48 — production RAG hardening

The campaign remains **hardening, not a durable-core redesign and not a GraphRAG rewrite**.

### Workstream state

1. **A — evolving-corpus temporal/update benchmark: COMPLETE**
2. **B — end-to-end answer/citation/unsupported-claim/abstention evaluation: COMPLETE**
3. **C — poisoning/untrusted-context adversarial suite: ACTIVE NEXT**
4. **F — replayable query execution receipt: pending**
5. **D / #47 — embedding/hybrid/reranker/model bakeoff: pending provider-backed comparison**
6. **E — conservative adaptive routing: pending evidence**
7. **G — ACL/redaction propagation readiness: pending**
8. final retrieval-policy/decision-log/residual-risk reconciliation: pending

### Workstream A — landed evidence

Core PR #54 / squash:

`e14148f504702ae9e708e2d58add4ee5c91bc8de`

Execution-only proof PR #55 ran the exact pack pins and passed, workflow `31431113829`, job `93594491275`.

The temporal benchmark proved lifecycle transitions, current/history reconstruction, and repeated-query stability after corpus growth while preserving D021 authority.

### Workstream B — landed evidence

Core PR #57 / squash:

`483772ac0e1d441719aec42658ae00b62a032c11`

Final normal CI:

- run `31433539654`;
- job `93602384284`;
- **94 passed in 1.80s**.

The implementation added:

- `src/dkg/answer_eval.py` — answer-level evaluator and deterministic durable-evidence baseline;
- `src/dkg/answer_pipeline.py` — deterministic durable relation-endpoint context resolution before model execution;
- `benchmarks/post-gate2/answer-reliability-v1.json` — six-case exact-pin benchmark plan;
- exact-pin runner, tests, and durable proof.

The first execution-only proof PR #58 correctly failed 5/6 because top-k omitted a stale dependent claim while retrieving its durable `DEPENDS_ON` relation. This showed that retrieval-only context could select an unrelated supported claim with confidence `1.0`.

FOSSIL then added `fossil-lineage-context-v1`, resolving stable relation endpoints from mounted validated packs before model execution. The benchmark expectation was not weakened.

Execution-only PR #59 reran the unchanged benchmark against:

- `fossil-common@d583005dce06dbb499c3c0de5c22b899655eb8d2`;
- `fossil-ai-systems@84accd2ee895663990e82ca5b79b592cb503db24`.

Final proof run `31433427436`, job `93602011104`:

- **94 core tests passed**;
- **27 projected documents**;
- benchmark **PASS 6/6**;
- final-answer correctness `1.0`;
- outcome accuracy `1.0`;
- exact citation correctness `1.0`;
- completeness `1.0`;
- appropriate abstention `1.0`;
- unsupported-claim rate `0.0`;
- over-abstention `0.0`;
- Brier score `0.0`;
- high-confidence error rate `0.0`.

The formerly failing SQLite case now resolves `current_state_unresolved` via durable claim `clm_a047d79b8604fadbd44efdf4` with exact citation `cite_b4e13e4e1a809f76527311ba`.

### Workstream C — exact active target

Build a retrieval-poisoning / untrusted-context adversarial suite. Cover at minimum:

- poisoned retrieved documents containing instructions;
- authority spoofing;
- malicious supersession attempts;
- duplicated adversarial passages intended to dominate ranking;
- conflicting-source attacks;
- pack-isolation pressure;
- attempts to bypass proposal-before-commit / deterministic gates;
- residual-risk documentation.

Reuse Workstream B answer metrics where possible. The suite must test downstream behavior, not merely retrieval presence: final-answer correctness, citations, unsupported claims, lifecycle/lineage resolution, abstention, authority boundaries, pack isolation, and proposal-before-commit behavior.

Do not claim universal poisoning resistance. Retrieved/source text is untrusted data and never executable policy merely because it was retrieved.

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

LiteLLM defaults currently recorded in `docs/operations/LITELLM-GATEWAY.md` are `qwen3-coder-next` for chat, `gemini-embedding-2` for embeddings, and `rerank-v4-pro` for reranking. Live benchmark evidence must record requested/actual model, provider, fallback attempts, latency, cost, and runtime identity. Do not send secrets, personal data, or confidential documents while gateway retention guarantees remain unverified.

Cortex v4 and multi-agent orchestration are optional replaceable cognitive-service competitors. Durable storage, stable identity, lifecycle/lineage logic, proposal-before-commit, and correctness guarantees must not couple to Cortex internals. Multiple workers agreeing does not create evidence.

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
- agents propose; deterministic validation/policy gates commit durable changes;
- do not casually rename `src/dkg`.

## Workflow state

`.github/workflows/ci.yml` remains the normal fast contract suite.

`.github/workflows/graphiti-live.yml` contains reusable live materialization plus redaction/non-resurrection smoke coverage.

Execution-only PRs #51, #55, #58, and #59 were closed without merge after their proofs. Issue #48 remains active; do not extend closed Gate 2 issues to implement it.
