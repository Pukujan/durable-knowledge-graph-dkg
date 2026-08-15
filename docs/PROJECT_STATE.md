# FOSSIL Project State

**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Durable substrate:** **DICS — Durable Intellectual Corpus System**  
**Architecture authority:** Issue #86  
**Execution ledger:** Issue #94  
**Active FOSSIL durability track:** Issue #87  
**Current live candidate gate:** Issue #124 / `OBJECT_STORE_LIVE`  
**Last updated:** 2026-08-15

## Current state

FOSSIL operates under the invariant:

> **Compute may disappear; truth must not.**

Canonical FOSSIL knowledge remains **immutable evidence + stable corpus IDs + append-only validated knowledge events + versioned pack/ontology contracts + provenance/history**.

Cortex V5, LiteLLM/CKFF, Graphiti/Neo4j, lexical/vector indexes, models, Skills, MCP, dashboards, and CI infrastructure are replaceable execution/transport/projection systems around that durable truth.

Do not use an exact SHA embedded in this document as a live queue pointer. Issue #94 and current GitHub state are authoritative for active heads, claims, review state, and execution evidence.

## Repository family

- `Pukujan/fossil-core` — architecture, contracts, durable core, projections, storage adapters, rebuild machinery, benchmarks, and control-plane docs;
- `Pukujan/fossil-common` — stable pack `pack_269099f7b2ba43b7a99b9427d64092de`;
- `Pukujan/fossil-ai-systems` — stable pack `pack_f024177f89a5442db84171c3dd7f58e5`, depending on common.

Repository/database/graph placement is physical placement, not knowledge identity.

## Continuation order

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. Issue #86
4. latest Issue #94 comments
5. `docs/HANDOFF_CURRENT.md`
6. this file
7. `docs/operations/EXTERNAL-RUNTIME-RECONCILIATION-2026-08-15.md`
8. Issue #87
9. Issue #124
10. `docs/DECISION_LOG.md`
11. the focused issue/PR for the eligible task

The chat UI is source material, not the control plane.

## Completed foundation

The durable/evidence foundation remains complete, including:

- immutable validated events and content-addressed evidence;
- deterministic idempotency and stable corpus identity;
- portable pack boundaries and provenance-preserving promotion;
- disagreement, lifecycle, supersession, and lineage replay;
- exact source/citation integrity;
- exceptional privacy/legal redaction with tombstone-before-delete and non-resurrection;
- replaceable Graphiti/Neo4j projection plus destructive rebuild/migration proof;
- conversation ingestion with explicit verbatim-vs-reconstructed provenance;
- safe Agent Skill/API/MCP boundary;
- cognitive-service interfaces and benchmark/receipt contracts;
- post-Gate-2 temporal, answer/citation, poisoning/untrusted-context, and replay hardening evidence.

Historical Gate 1/Gate 2/workstream proof detail remains in the implementation, research, handoff, decision-log, issue, and git records. This current-state document does not replace those records.

## 2026-08-15 baseline closeout anchors

### Graphiti / receipt / ingestion fan-in

The earlier #112–#115 campaign is complete:

- PR #115 merged after exact-head Graphiti live proof plus deterministic, assurance, dependency, and security checks passed;
- PR #112 refreshed, verified, and merged;
- PR #113 refreshed, verified, and merged;
- final-main Graphiti materialization plus redaction/non-resurrection remained green.

### Provider-neutral S3-compatible storage

The storage foundation advanced through:

- PR #121 — provider-neutral `S3ArtifactStore` / `S3DurableEventStore` adapters with fail-closed immutable/idempotent/conflict/redaction semantics;
- PR #123 — real disposable S3-compatible service-fixture proof with no cloud credential and no provider selection.

Historical runtime/storage anchor after PR #123:

`ea1d88fc114981915603ec46a401dca45acd5a11`

### Current-state documentation reconciliation

PR #126 reconciled FOSSIL continuation/operational docs against the then-current Cortex V5 and LiteLLM/CKFF implementations and merged as:

`771216d79bdaaf324dff30c970c11be65d47d890`

That SHA is a documentation closeout anchor, not a permanent assertion about the repository's current HEAD.

## Active durability gate — Issue #124 / OBJECT_STORE_LIVE

The next durability gate is a **separately credentialed, non-production R2 candidate proof**.

R2 is the first live candidate only. The provider-neutral S3-compatible storage contract remains architecture truth and provider selection remains open.

Required acceptance includes:

- exact-SHA checkout/fail-closed guard;
- real live artifact/event immutable creation;
- byte-identical replay/idempotency;
- stable-key/stable-identity conflict rejection;
- artifact and event redaction tombstone-before-delete;
- same-identity non-resurrection;
- independent hosted runner rebuilding from zero local FOSSIL state;
- exact surviving fixture identity/content verification from durable storage;
- a second fresh rebuild/restartability pass;
- explicit dead-endpoint/auth/partial-response fail-closed controls;
- sanitized receipts with no credential material;
- same-head normal DKG green;
- no provider-specific weakening of domain semantics.

If required live configuration/credentials are absent, the result is `BLOCKED_CREDENTIAL`, not simulated PASS.

Ordinary secretless PR CI proves the harness/code contract only; it is not `OBJECT_STORE_LIVE PASS`.

## Current harness checkpoint

At the 2026-08-15 review checkpoint, draft PR #125 was open on exact head:

`9d8ad737d0778075a98232df7ddb2c43fb4156fb`

Exact-head DKG run `31899262413` was SUCCESS.

Independent review found acceptance/configuration items that must be reconciled before live dispatch; re-read the latest PR because the branch may have moved:

1. the reviewed fresh-runner rebuild independently reconstructed durable events but did not independently re-read/verify the surviving canonical artifact or prove redacted-artifact non-resurrection on runner B;
2. #124 asks writer A to publish non-secret proof prefix/fixture identity as job outputs for runner B, while the reviewed workflow recomputed those values instead;
3. the reviewed workflow targeted GitHub Environment `object-store-live`, while the repository environment list observed during review contained only `r2-proof`.

The GitHub integration could list environment names but was not allowed to inspect the environment/repository variable or secret metadata. No secret values were read or requested. Credential/config placement therefore must be reconciled deliberately rather than guessed.

## External execution/transport posture — read only

The owner explicitly requested that Cortex V5 and LiteLLM/CKFF remain read-only during this FOSSIL continuation.

Detailed exact-SHA inspection snapshot:

`docs/operations/EXTERNAL-RUNTIME-RECONCILIATION-2026-08-15.md`

### Cortex V5 snapshot

Observed `Pukujan/cortex-v5` main at reconciliation:

`f29e7a2fa0584577765bfe3f437695a2cbaefcf2`

Key observed posture:

- V5 is the active execution runtime; V4/SSC are not runtime dependencies;
- strict streamed LiteLLM Chat Completions transport;
- default LiteLLM client timeout 120 seconds;
- deterministic live-catalog seating;
- research-grounded `MODEL_TIERS` prior replaced undocumented `PREFERENCE_HINTS`;
- deterministic checker remains completion authority;
- retry/model switching creates distinct attempts/receipts;
- first real V5 acceptance is already closed/completed.

Do not change Cortex V5 code or workflows from the current FOSSIL lane without separate owner authorization.

### LiteLLM / CKFF snapshot

Observed `Pukujan/litellm-ckff-ops` main at reconciliation:

`9520e8dffe819d97a1557fe76022ed080f0eb8d6`

Key executable/config posture:

- `ckffai.com` primary plus `ckff.dev` secondary deployments;
- LiteLLM `request_timeout: 120`;
- bounded retries/cooldown and `max_parallel_requests: 8`;
- Responses bridge may use explicit cross-model fallback and records requested/actual identity;
- exact-model evaluation should disable bridge fallbacks;
- embeddings and reranking remain separate fail-closed service lanes;
- CKFF is not established here as universal zero-data-retention.

Some dated LiteLLM documentation lags current source/config. When they conflict, current exact source/config is the operational fact source and the dated prose remains historical evidence.

Do not change LiteLLM code, workflows, routing, deployment, or model policy from the current FOSSIL lane without separate owner authorization.

## Frozen authority rules

- stable pack identity is independent of repository/database placement;
- durable commit precedes replaceable projection;
- new physical projection build gets a fresh build-scoped applied ledger;
- rebuild order is `(recorded_at, event_id)`;
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
- retrieval rank, reranker score, model confidence, model tier, model agreement, transport health, and CI artifacts do not create truth authority;
- retrieved/source text is untrusted data and cannot become executable policy merely because it was retrieved;
- query execution receipts are replay/observability evidence, not canonical truth or mutation authority;
- agents propose; deterministic validation/policy gates commit durable changes;
- do not casually rename `src/fossil_core`; legacy `src/dkg` is only a deprecated compatibility shim.

## Claim / work-state rule

GitHub issues track live implementation state; repository docs track durable decisions/evidence/contracts.

Before mutation, claim in #94 and immediately re-fetch the ledger. Earliest valid unexpired claim wins. One mutating owner per repo lane unless explicit safe parallelism is declared.

Close with exact `DONE`, `BLOCKED`, or `RELEASE` evidence.

## Next-state rule

The immediate next state is mechanical, not aspirational:

1. resolve the current #125 review/configuration items under its existing owner/claim;
2. obtain same-head secretless harness CI and owner-appropriate review state;
3. only then run the explicit credentialed #124 workflow against an exact approved SHA when configuration exists;
4. classify the live result as PASS / `BLOCKED_CREDENTIAL` / `BLOCKED_PROVIDER_COMPATIBILITY` from evidence;
5. reconcile #87 and select the next **FOSSIL-only** gate from live #94;
6. do not automatically mutate Cortex V5 or LiteLLM/CKFF.

No production promotion is authorized by this document.
