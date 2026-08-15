# FOSSIL Project State

**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Durable substrate:** **DICS — Durable Intellectual Corpus System**  
**Architecture authority:** Issue #86  
**Execution ledger:** Issue #94  
**Active FOSSIL durability track:** Issue #87  
**Current live candidate gate:** Issue #124 / `OBJECT_STORE_LIVE`  
**Last updated:** 2026-08-15

## Current checkpoint

Current `fossil-core` main at this checkpoint:

`ea1d88fc114981915603ec46a401dca45acd5a11`

This includes the merged PR #123 real secretless S3-compatible service-fixture proof.

The project invariant remains:

> **Compute may disappear; truth must not.**

FOSSIL owns durable semantic/evidence authority. Cortex V5 and LiteLLM/CKFF are external replaceable execution/transport systems. Their current behavior may be documented and consumed, but their repositories/workflows are not part of the active FOSSIL mutation scope unless the owner explicitly opens that work.

## Repository family

- `Pukujan/fossil-core` — architecture, contracts, durable core, projections, storage adapters, rebuild machinery, benchmarks and control-plane docs;
- `Pukujan/fossil-common` — stable pack `pack_269099f7b2ba43b7a99b9427d64092de`;
- `Pukujan/fossil-ai-systems` — stable pack `pack_f024177f89a5442db84171c3dd7f58e5`, depending on common.

Repository/database/graph placement is physical placement, not knowledge identity.

## Continuation order

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/HANDOFF_CURRENT.md`
4. this file
5. `docs/operations/EXTERNAL-RUNTIME-RECONCILIATION-2026-08-15.md`
6. Issue #86
7. Issue #94
8. Issue #87
9. Issue #124
10. `docs/DECISION_LOG.md`
11. `docs/operations/LITELLM-GATEWAY.md`

The chat UI is source material, not the control plane.

## Frozen architecture

Canonical FOSSIL knowledge is **immutable evidence + stable corpus IDs + append-only validated knowledge events + versioned pack/ontology contracts + provenance/history**.

Graphiti/Neo4j, lexical/vector indexes, embedding models, rerankers, context construction, planners, model services, Skills, MCP, Cortex, LiteLLM and future databases remain replaceable projections/services.

Retrieved/source text is untrusted data. Retrieval rank, reranker score, model confidence, model tier, multi-model agreement, route success and query-execution receipts are not truth authority.

## Completed foundation

The earlier durable/evidence foundation remains complete, including:

- immutable validated events and content-addressed evidence;
- stable pack identity and portable pack boundaries;
- provenance, lifecycle, disagreement, supersession and lineage replay;
- exact source/citation integrity;
- exceptional redaction with tombstone-before-delete and non-resurrection;
- replaceable Graphiti/Neo4j projection and rebuild/migration proof;
- safe Agent Skill/API/MCP boundary;
- cognitive-service interfaces and benchmark/receipt contracts;
- post-Gate-2 answer, poisoning/untrusted-context and query-replay hardening evidence.

Historical Gate 1/Gate 2/workstream proof detail remains in the existing implementation, research, handoff and decision-log documents and in git history. This current-state file does not replace those records.

## Recent 2026-08-15 reconciliation

### #112–#115 baseline/fan-in

The previously open repair/fan-in work is now reconciled:

- PR #115 merged after exact-head Graphiti live proof, deterministic tests and engineering/dependency/security gates passed;
- PR #112 refreshed, verified and merged;
- PR #113 refreshed, verified and merged;
- final-main Graphiti materialization plus redaction/non-resurrection remained green.

### #87 secretless storage foundation

The provider-neutral S3-compatible storage lane advanced:

- PR #121 landed explicit provider-neutral S3-compatible artifact/event storage adapters and fail-closed durability semantics;
- exact-head DKG/engineering/dependency/Graphiti evidence passed;
- no live cloud credentials were used and no provider was selected.

### Real secretless S3-compatible service fixture

PR #123 then proved the adapter against a real local/service-container S3-compatible implementation. The final-main proof covered the storage contract without cloud credentials/provider lock-in, including the required secretless service-fixture path and normal DKG.

Current main after that merge is `ea1d88fc114981915603ec46a401dca45acd5a11`.

## Active FOSSIL work — Issue #124 / OBJECT_STORE_LIVE

The next durability gate is a **separately credentialed, non-production R2 candidate proof**.

R2 is the first live candidate only. The provider-neutral `S3ArtifactStore` / `S3DurableEventStore` contract remains architecture truth.

Required acceptance includes:

- exact-SHA checkout/fail-closed guard;
- live artifact/event immutable create, byte-identical replay and stable-identity conflict behavior;
- live redaction tombstone-before-delete and non-resurrection;
- independent hosted runner rebuilding from zero local FOSSIL state;
- a second rebuild/restartability pass from durable truth;
- explicit dead-endpoint/partial/auth failure controls;
- sanitized receipts with no credential material;
- normal DKG green on the same code head;
- no provider-specific weakening of FOSSIL domain semantics.

If required configuration/credentials are absent, the result is `BLOCKED_CREDENTIAL`, not simulated PASS.

## External execution/transport state — read only

Detailed exact-SHA inspection is recorded in:

`docs/operations/EXTERNAL-RUNTIME-RECONCILIATION-2026-08-15.md`

### Cortex V5

Observed main:

`f29e7a2fa0584577765bfe3f437695a2cbaefcf2`

Current posture:

- active execution runtime is Cortex V5, not V4;
- V5 has no runtime dependency on SSC;
- strict streamed LiteLLM Chat Completions transport;
- 120-second default client timeout;
- deterministic live-catalog seating;
- research-grounded `MODEL_TIERS` prior replaces undocumented `PREFERENCE_HINTS`;
- deterministic checker remains completion authority;
- the V5 acceptance issue is already closed/completed.

**Policy for this FOSSIL checkpoint:** do not change Cortex V5 code or workflows. Older queue text suggesting automatic CORTEX-02 work is not authorization to mutate V5 after the owner's explicit read-only boundary.

### LiteLLM / CKFF

Observed main:

`9520e8dffe819d97a1557fe76022ed080f0eb8d6`

Current executable/config posture:

- configured models have `ckffai.com` primary plus `ckff.dev` secondary deployments;
- LiteLLM `request_timeout: 120`;
- bounded retries/cooldown and `max_parallel_requests: 8`;
- Responses bridge may use explicit cross-model fallback and exposes requested/actual/attempt metadata;
- exact-model evaluation should disable bridge fallbacks;
- embeddings and reranking are separate fail-closed service lanes;
- upstream privacy remains model/provider-dependent and CKFF is not verified zero-data-retention.

The LiteLLM repo's documentation is only partially reconciled with source/config. In particular, a dated compatibility report still mentions a 90-second LiteLLM timeout and the implementation-gap document still says `ckffai.com` is absent from generated config. FOSSIL therefore treats current exact source/config as the operational fact source when those dated docs conflict.

**Policy for this FOSSIL checkpoint:** do not change LiteLLM code, workflows, routing or deployment.

## Cognitive-service posture

FOSSIL service contracts remain replaceable:

- `Retriever`;
- `EmbeddingProvider`;
- `Reranker`;
- `ContextProvider`;
- `ModelService`;
- `VerificationService`.

Current external service availability must not silently rewrite FOSSIL architecture. Benchmark/model work must continue to record exact requested/actual model/provider/runtime identity, fallback attempts, latency/cost and receipt/trace identity.

## Frozen invariants

- stable pack identity is independent of repository/database placement;
- durable commit precedes replaceable projection;
- new physical projection build => fresh build-scoped applied ledger;
- rebuild order => `(recorded_at, event_id)`;
- migration compares stable FOSSIL semantics, not graph-native UUIDs;
- reconstructed evidence cannot silently become verbatim;
- exact citations resolve to immutable observed bytes/spans;
- ordinary intellectual revision is append-only;
- privacy/legal erasure is exceptional tombstone-before-delete with non-resurrection;
- retrieved/source text is untrusted data;
- model confidence/tier/agreement is not evidence;
- gateway fallback does not prove the requested model succeeded;
- query execution receipts are observability/replay evidence, not mutation authority;
- agents propose; deterministic validation/policy gates commit durable changes;
- no provider-specific storage semantics may leak into the FOSSIL domain contract;
- do not casually rename `src/fossil_core`; legacy `src/dkg` remains only a deprecated compatibility shim where still present.

## Workflow state

Normal FOSSIL CI/assurance workflows remain repository-owned acceptance surfaces. The Graphiti live workflow remains a replaceable-projection proof, and the real S3-compatible fixture workflow is now part of the secretless storage evidence.

The active Issue #124 live proof is a separate credential boundary. Ordinary PR code must not gain live cloud credentials merely because the fixture proof passed.

## Next decision boundary

1. Complete or explicitly block Issue #124 with exact live evidence.
2. Reconcile its result into #87/#86 and durable docs.
3. Choose the next **FOSSIL-only** gate from evidence.
4. Do not automatically schedule Cortex V5 or LiteLLM mutations; those require separate owner authorization.
