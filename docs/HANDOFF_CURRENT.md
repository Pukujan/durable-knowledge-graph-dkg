# Current Handoff

**Date:** 2026-08-15  
**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Repository:** `Pukujan/fossil-core`  
**Architecture authority:** Issue #86  
**Execution queue / claim ledger:** Issue #94

## Current status

FOSSIL operates under the invariant:

> **Compute may disappear; truth must not.**

The current subsystem boundary is:

> **Cortex V5 owns execution policy. FOSSIL owns durable knowledge/evidence. GitHub owns source/coordination/review. LiteLLM/CKFF owns provider/model/route transport facts. Infrastructure and projections are replaceable.**

Do not treat an exact SHA embedded in this file as the live queue. Re-fetch #94 and current GitHub state before any write, merge, deployment, credentialed proof, or task claim.

## Recent closeout anchors

The earlier #112–#115 repair/fan-in campaign is complete:

- PR #115 merged after exact-head live Graphiti evidence plus deterministic, assurance, dependency, and security checks passed.
- PR #112 refreshed, verified, and merged.
- PR #113 refreshed, verified, and merged.
- final-main Graphiti materialization plus redaction/non-resurrection remained green.

The provider-neutral storage lane then advanced:

- PR #121 landed S3-compatible artifact/event adapters with fail-closed immutable/idempotent/conflict semantics.
- PR #123 proved those adapters against a real disposable S3-compatible service with no cloud credentials and no provider selection.
- Runtime/storage anchor after PR #123: `ea1d88fc114981915603ec46a401dca45acd5a11`.

Docs reconciliation PR #126 later merged as `771216d79bdaaf324dff30c970c11be65d47d890`. Treat these SHAs as evidence anchors, not as a substitute for checking live `main`.

## Active FOSSIL lane — Issue #124 / OBJECT_STORE_LIVE

The next durability gate is a separately credentialed, **non-production R2 candidate** proof. R2 is the first live candidate only; the provider-neutral `S3ArtifactStore` / `S3DurableEventStore` contract remains architecture truth.

PASS requires the exact #124 acceptance, including:

- exact-SHA checkout/fail-closed guard;
- live immutable create, byte-identical replay, and stable-identity conflict behavior;
- artifact and event durability from a genuinely fresh hosted runner;
- repeated rebuild/restartability from zero local state;
- redaction tombstone-before-delete and non-resurrection;
- dead-endpoint/auth/partial-response fail-closed controls;
- sanitized receipts with no credential material;
- same-head normal DKG green;
- no provider-specific weakening of FOSSIL semantics.

Ordinary PR CI is **not** `OBJECT_STORE_LIVE PASS`.

### Current harness checkpoint

As of this handoff checkpoint, draft PR #125 carried the credential-free live harness on head `9d8ad737d0778075a98232df7ddb2c43fb4156fb`, and exact-head DKG was green (`31899262413`). Re-read the PR before acting because the branch may move.

Independent review on that head identified two acceptance/configuration items before live dispatch:

1. fresh-runner rebuild covered durable events but did not independently re-read/verify the surviving canonical artifact or prove redacted-artifact non-resurrection from runner B;
2. the workflow targeted GitHub Environment `object-store-live`, while the repository environment list observed during review contained only `r2-proof`. Environment variable/secret names were not readable through the GitHub integration, so credential placement must be reconciled deliberately rather than guessed.

The review also noted that #124 asks the writer to publish non-secret proof prefix/fixture identity as job outputs for runner B; the reviewed workflow instead recomputed them. Re-read the latest PR review state to see whether these points were addressed.

If required configuration/credentials are absent, the result is `BLOCKED_CREDENTIAL`, not simulated PASS.

## External runtime posture — read only

The owner explicitly requested that **Cortex V5 and LiteLLM/CKFF not be modified as part of this FOSSIL continuation**. Inspect them to understand current behavior; do not change their repositories or workflows unless the owner separately authorizes that work.

Detailed inspection snapshot:

`docs/operations/EXTERNAL-RUNTIME-RECONCILIATION-2026-08-15.md`

### Cortex V5

Observed main at the reconciliation snapshot:

`f29e7a2fa0584577765bfe3f437695a2cbaefcf2`

Key facts at that snapshot:

- no runtime dependency on Cortex V4 or legacy SSC;
- tasks enter through the V5 HTTP API;
- live LiteLLM `/v1/models` catalog refresh plus deterministic seat selection;
- strict streamed `/v1/chat/completions`; invalid/premature SSE is failure;
- 120-second LiteLLM client default timeout;
- documented research-grounded `MODEL_TIERS` replaced undocumented `PREFERENCE_HINTS`;
- deterministic checker remains completion authority;
- retry/model switch creates a new attempt/receipt rather than hidden success.

V5 acceptance is already closed/completed. Do not reopen it or automatically mutate V5 because older queue text mentions CORTEX-02.

### LiteLLM / CKFF

Observed main at the reconciliation snapshot:

`9520e8dffe819d97a1557fe76022ed080f0eb8d6`

Key executable/config facts at that snapshot:

- configured logical models have `ckffai.com` primary plus `ckff.dev` secondary deployments;
- LiteLLM `request_timeout` is 120 seconds;
- retries/cooldown are bounded and `max_parallel_requests` is 8;
- Responses bridge can use explicit cross-model fallback and records requested/actual identity;
- exact-model work should disable bridge fallbacks;
- embeddings and reranking remain separate fail-closed service lanes;
- CKFF is not established here as universal zero-data-retention.

Some dated LiteLLM docs lag current source/config. When they conflict, use current exact source/config as operational fact and treat the dated prose as historical evidence.

## Read first

For a fresh session:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. Issue #86
4. latest Issue #94 comments
5. this file
6. `docs/PROJECT_STATE.md`
7. `docs/operations/EXTERNAL-RUNTIME-RECONCILIATION-2026-08-15.md`
8. Issue #87
9. Issue #124
10. `docs/DECISION_LOG.md`
11. the focused issue/PR for the eligible task

## Frozen authority rules

- FOSSIL durable evidence/events, stable IDs, provenance, lifecycle, lineage, redaction, and accepted contracts remain semantic authority.
- Retrieval rank, reranker score, model confidence, model tier, and multi-model agreement are not truth.
- Graphiti/Neo4j, search/vector indexes, models, Cortex, LiteLLM, Skills, MCP, dashboards, and CI artifacts remain replaceable services/projections.
- A fallback response is not evidence that the requested model itself succeeded.
- `2xx` with empty/malformed/truncated/zero-usable output is failure.
- Reconstructed evidence cannot silently become verbatim evidence.
- Ordinary PR CI remains secretless.
- Production promotion always requires separate explicit human authorization.
- Never weaken acceptance merely to obtain green.

## Legacy SSC

Legacy `stupidly-simple-cortex` is retired/superseded as runtime, memory, RAG, ontology/current-state, orchestration, and project authority. Cortex V5 does not depend on it.

Potentially useful historical eval/checker assets may survive only after independent extraction/revalidation with exact bytes, hashes, provenance, license, checker dependencies, and leakage controls. Do not revive SSC runtime to preserve an old asset.

Durable retirement decision: D023 in `docs/DECISION_LOG.md`.

## Claim protocol

Before mutating work, use Issue #94:

```text
CLAIM task=<TASK_ID>
agent=<unique-agent-id>
mode=<LOCAL_CODEX|CLOUD_CODEX|CHATGPT|ACTIONS>
lease_until=<ISO-8601 UTC>
repo=<repo>
starting_ref=<branch/SHA/PR>
```

Immediately re-fetch #94. Earliest valid unexpired claim wins. One active mutating owner per repo lane unless the task explicitly declares safe parallelism.

Close with exact `DONE`, `BLOCKED`, or `RELEASE` evidence.

## Engineering policy

- SDD always.
- TDD for deterministic behavior where practical.
- Integration/wiring tests for actual boundaries.
- E2E for important real flows.
- Fault injection for recovery/retry infrastructure.
- Explicit security checks at credential/deployment boundaries.
- Regression coverage for discovered bugs.
- Hidden holdouts for autonomous model evaluation where appropriate.
- Never weaken, skip, or suppress acceptance merely to obtain green.

## Immediate fresh-agent behavior

1. Read #86, #94, #87, and #124 live.
2. Confirm current `main`, active PR heads, review state, environment/config state, and claim ownership.
3. Treat Cortex V5 and LiteLLM/CKFF as read-only unless the owner explicitly opens separate mutation work.
4. Take only an eligible task matching access and collision rules.
5. Work on an isolated branch/target.
6. Test mechanically and record exact evidence.
7. Post `DONE`, `BLOCKED`, or `RELEASE`.
8. Re-read #94 before taking another task.

If no eligible task exists, stop with explicit idle/BLOCKED evidence rather than inventing work.
