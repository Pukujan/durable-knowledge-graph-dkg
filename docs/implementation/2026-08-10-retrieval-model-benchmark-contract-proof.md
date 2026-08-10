# Retrieval / Model Service Benchmark Contract Proof

**Date:** 2026-08-10  
**Issue:** #7  
**Result:** acceptance contract passed

## Purpose

This gate does **not** select a permanent retriever, embedder, reranker, context strategy, or model. It creates the replaceable service boundary and a measurable baseline so later approaches have to win on corpus behavior rather than novelty.

The deterministic/local implementations in this proof are controls. In particular, the signed hash embedding is deliberately a dependency-free baseline and must not be interpreted as a semantic embedding recommendation.

## Versioned service interfaces

`src/dkg/contracts.py` now treats every cognitive service as versioned/provenanced and preserves the existing interfaces:

- `Retriever`
- `EmbeddingProvider`
- `Reranker`
- `ContextProvider`
- `ModelService`
- `VerificationService`

Every implementation exposes service metadata including provider, provider version, implementation/version, optional model ID, local/remote status, estimated call cost, and runtime metadata.

## Initial implementations

`src/dkg/services.py` provides one small executable baseline for every capability:

- `BM25Retriever` — dependency-free lexical baseline with pack filtering;
- `HashEmbeddingProvider` — deterministic signed-token hashing control;
- `EmbeddingRetriever` — in-memory cosine retrieval over any embedding provider;
- `TokenOverlapReranker` — deterministic lexical reranking control;
- `BudgetedContextProvider` — retrieval/reranking under an explicit context character budget;
- `CallableCandidateModelService` — provider adapter whose model output is always labeled `candidate_only`;
- `RiskEscalationPolicy` + `PolicyVerificationService` — explicit evidence/risk/uncertainty authority gate.

These implementations are intentionally simple enough to inspect and replace. They do not create a new durable store or couple canonical knowledge to their scoring behavior.

## Provider/model provenance

The durable event provenance envelope now accepts optional:

- `model_provider`
- `model_provider_version`
- `model_runtime`
- `model_service_version`
- `benchmark_ref`

This complements the actor's existing `model_id` / harness / Skill metadata and projection build manifests. Review events can therefore record the exact cognitive provider/runtime that produced or evaluated a candidate.

## Authority boundary

A local/specialist model response from `CallableCandidateModelService` has `authority == candidate_only`.

`RiskEscalationPolicy` represents:

- requested action (`propose` vs `commit`);
- whether a proposal changes truth state;
- risk level;
- uncertainty;
- independent evidence references;
- required evidence threshold.

Candidate models may always emit proposals. A candidate-only truth-changing commit with insufficient independent evidence escalates. High-risk or over-threshold uncertainty also escalates. A low-risk candidate truth change may become commit-eligible only **after** the separate verification policy observes sufficient independent evidence. Authority therefore comes from the evidence/policy gate, not model consensus.

## Benchmark contract

`schemas/benchmark/v1.schema.json` and `src/dkg/benchmark.py` define executable retrieval/model result contracts.

### Retrieval benchmark metrics

- hit rate;
- mean recall@k;
- mean reciprocal rank (MRR);
- mean latency;
- p95 latency;
- peak Python allocation bytes;
- estimated provider cost;
- failure rate grouped by corpus/domain category.

### Bounded model benchmark metrics

- exact-match rate for a defined specialist task;
- mean/p95 latency;
- peak Python allocation bytes;
- estimated provider cost;
- failure rate grouped by domain category;
- observed output authority.

The result includes service/provider/model versions and execution environment metadata. The benchmark ID depends on benchmark kind, service metadata, and case identities rather than measured timing, so repeated executions of the same contract remain logically comparable while runtime measurements may vary.

## Test proof

`tests/test_cognitive_services_benchmark.py` verifies:

- BM25 pack-scoped retrieval;
- deterministic embedding identity and cosine replacement path;
- reranker replacement path;
- context budgeting;
- retrieval benchmark schema + quality/latency/memory/cost/failure dimensions;
- candidate-only model behavior and provider/model versions;
- bounded model benchmark schema;
- independent-evidence escalation for truth-changing candidate proposals;
- high-risk escalation;
- durable event commit of model/provider/runtime/benchmark provenance.

Trusted GitHub Actions run:

- run ID: `31347744797`
- job ID: `93332738616`
- result: **56 passed in 0.70s**

## Gate result

Issue #7 acceptance is satisfied at the **contract/baseline** level:

1. all six cognitive interfaces exist and are versioned;
2. each has an executable initial implementation;
3. provider/model/runtime versions can be persisted in review/projection provenance;
4. risk/uncertainty escalation is explicit and testable;
5. benchmark results measure quality, latency, Python memory, estimated cost, and domain-specific failures;
6. local/small model output remains candidate-only until independent evidence/policy grants downstream commit eligibility.

## What this does not prove

This gate does not claim that BM25, hash embeddings, token overlap, or the fixture specialist are production winners. It does not benchmark every researched technology or justify a model zoo.

Future benchmark campaigns should plug real candidates behind these interfaces and use the same corpus-specific cases/metrics. A new provider is an implementation competitor, not a reason to change FOSSIL's canonical durable knowledge contracts.
