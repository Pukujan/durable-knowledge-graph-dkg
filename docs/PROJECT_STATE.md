# FOSSIL Project State

**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Durable substrate:** **DICS — Durable Intellectual Corpus System**  
**Completed:** **Milestone 0 / Gate 1; Gate 2**  
**Active work:** **Issue #48 — production RAG hardening and evidence-driven retrieval evolution**  
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
4. this file
5. `docs/research/2026-08-10-production-rag-hardening-research-trace.md`
6. Issue #48
7. Issue #47
8. `docs/DECISION_LOG.md`
9. completed Gate 2 proof/policy docs under `docs/implementation/`

The chat UI is source material, not the control plane.

## Frozen architecture

Canonical FOSSIL knowledge is **immutable evidence + stable corpus IDs + append-only validated knowledge events + versioned pack/ontology contracts + provenance/history**.

Graphiti/Neo4j, lexical/vector indexes, embedding models, rerankers, context construction, planners, model services, Skills, MCP, and future databases remain replaceable projections/services.

A graph deletion or embedding replacement must never delete irreplaceable intellectual history.

## Completed foundation

### Gate 1

Gate 1 is complete: durable events/artifacts, pack boundaries, lifecycle/disagreement/supersession, replaceable graph projection, rebuild/migration, conversation lineage, exact source/citation integrity, redaction/non-resurrection, cognitive-service contracts, and safe Agent Skill/API/MCP boundaries were proven.

Final cleaned Gate 1 run `31347457485`, job `93331933728`: **51 passed in 0.82s**. Cognitive-service contract run `31347744797`, job `93332738616`: **56 passed in 0.70s**.

### Gate 2

Gate 2 control #33 and children #34–#37 are closed/completed.

Evidence anchors:

- Gate 2A real history-rich corpus core commit `a028f9e328c2cbcde0185930e90b5eeb4c4efcb8`;
- Gate 2B real retrieval/context adapters core commit `2affde923acf196319d90bfa63f206e4a5e2f25f`;
- Gate 2C PR #44 / squash `38aac6325cdb5b738c8a6ac5e55959affb3acfb5`;
- Gate 2C final CI run `31366259213`, job `93385174741` — **86 passed in 1.25s**;
- semantic proof run `31364039745`, artifact `9053475462`, digest `sha256:23c95b46f47cec5a16e0a8c0926a4f13532f283d8f4fbcc0de12ceb63db63c41`;
- Gate 2D PR #45 / squash `2d22dee9e6b176956d30005f4d7877baf68b0a3c`;
- Gate 2D CI run `31366800697`, job `93386832166` — **86 passed in 1.02s**;
- closed-state reconciliation PR #46 / squash `a614936249ff0ab201756fa54a1e89699d7b924f`.

The 21-case history-rich corpus compared BM25, a hash embedding control, revision-pinned BGE dense, and BM25+BGE hybrid/lifecycle reranking. BGE dense was the only compared strategy with zero full retrieval misses and had mean recall@5 `0.98413`. It still showed current-state ranking leakage and incomplete multi-target lineage recall.

Decision D021 therefore selects revision-pinned `BAAI/bge-small-en-v1.5@5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` as the normal primary retriever and BM25 as an explicit degraded availability fallback.

Mandatory D021 safeguards remain:

- current/latest/accepted questions resolve lifecycle/provenance;
- lineage/history/disagreement questions use durable lineage/read resolution;
- top-k absence is not evidence of nonexistence;
- citation-bearing answers resolve immutable source snapshot/span/hash identity;
- retrieval/model output does not receive truth authority from score, confidence, or agreement.

Policy proof: `docs/implementation/2026-08-10-gate2-default-retrieval-policy.md`.

## Active campaign #48 — production RAG hardening

Research basis:

`docs/research/2026-08-10-production-rag-hardening-research-trace.md`

The current external review covers version-aware/temporal RAG, answer/citation/refusal evaluation, uncertainty under retrieval noise, adaptive routing, hybrid+rereanking, poisoning attacks, simple long-context baselines, contextual retrieval, and observable agentic retrieval.

The conclusion is **harden, do not redesign the durable core**.

### Workstream order

1. evolving-corpus temporal/update benchmark;
2. end-to-end answer/citation/unsupported-claim/abstention evaluation;
3. poisoning/untrusted-context adversarial suite;
4. replayable query execution receipt;
5. #47 embedding/hybrid/reranker bakeoff;
6. conservative adaptive routing if it earns a matched-baseline win;
7. ACL/redaction propagation readiness before multi-user/shared/cloud use.

### New hardening principles under test

- retrieved/source text is untrusted data, not executable policy;
- uncertainty/abstention should be explicit answer behavior when evidence is insufficient/conflicting/unresolved;
- simple direct-source/read and fixed retrieval baselines remain mandatory competitors;
- a reranker can improve candidate ordering but cannot decide lifecycle truth;
- adaptive planners must expose route/execution metadata and earn their cost/complexity;
- important benchmark queries should be replayable after provider/model/projection changes.

These are campaign hypotheses/requirements, not silent changes to `ARCHITECTURE.md`.

## Research-to-corpus state

The 2026-08-10 production-RAG research trace is designed to be ingested into `fossil-ai-systems` as a **local derived research artifact** with stable artifact/source identity and claim provenance.

Original external papers and production documentation must later be captured as distinct source snapshots. The synthesis or chat transcript must not be presented as verbatim external evidence.

## Cognitive-service posture

Current approved retrieval profile remains D021 until new committed benchmark evidence says otherwise.

Existing replaceable service contracts already include:

- `Retriever`;
- `EmbeddingProvider`;
- `Reranker`;
- `ContextProvider`;
- `ModelService`;
- `VerificationService`.

This allows #48/#47 to test new embeddings, rerankers, routing/context strategies, and model services without coupling canonical knowledge to them.

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
- model agreement is not evidence; model output remains bounded by evidence/risk policy.

## Workflow state

`.github/workflows/ci.yml` remains the normal fast contract suite.

`.github/workflows/graphiti-live.yml` contains reusable live materialization plus redaction/non-resurrection smoke coverage.

Gate 2 temporary proof workflows were removed before landing. Issue #48 is now the active campaign; do not extend closed Gate 2 issues to implement it.
