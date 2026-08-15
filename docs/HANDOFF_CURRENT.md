# Current Handoff

**Date:** 2026-08-15  
**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Repository:** `Pukujan/fossil-core`  
**Architecture authority:** Issue #86  
**Execution queue / claim ledger:** Issue #94

## Current status

FOSSIL is operating under the disposable-compute invariant:

> **Compute may disappear; truth must not.**

The current subsystem boundary is:

> **Cortex V5 owns execution policy. FOSSIL owns durable knowledge/evidence. GitHub owns source/coordination/review. LiteLLM/CKFF owns provider/model/route transport facts. Infrastructure and projections are replaceable.**

Current `fossil-core` main at this checkpoint:

`ea1d88fc114981915603ec46a401dca45acd5a11`

That main includes the merged real secretless S3-compatible service-fixture proof from PR #123.

## Recent FOSSIL closeout

The earlier #112–#115 repair/fan-in campaign is no longer pending:

- PR #115 Graphiti compatibility/receipt lane merged after exact-head live Graphiti evidence, deterministic suite, assurance, dependency and security checks passed.
- PR #112 was refreshed, verified and merged.
- PR #113 was refreshed, verified and merged.
- final-main Graphiti fan-in remained green.
- PR #121 landed the provider-neutral S3-compatible canonical storage adapter.
- PR #123 landed the **secretless real S3-compatible service fixture** proof using a disposable local/service-container implementation; no cloud provider was selected and no cloud credential was used.

The next storage phase is Issue #124 / `OBJECT_STORE_LIVE`: a separately credential-gated live R2 candidate durability + empty-runner rebuild proof. R2 remains only the first candidate, not architecture truth or a permanent provider choice.

## External runtime posture — read only

The owner has explicitly requested that **Cortex V5 and LiteLLM/CKFF not be modified as part of this FOSSIL continuation**. Inspect them to understand current behavior; do not change their repositories or workflows unless the owner separately authorizes that work.

Detailed exact-SHA reconciliation:

`docs/operations/EXTERNAL-RUNTIME-RECONCILIATION-2026-08-15.md`

### Cortex V5

Observed current `Pukujan/cortex-v5` main:

`f29e7a2fa0584577765bfe3f437695a2cbaefcf2`

Key current facts:

- V5 has no runtime dependency on Cortex V4 or legacy SSC.
- Tasks enter through the V5 HTTP API.
- V5 refreshes the live LiteLLM `/v1/models` catalog and selects a deterministic seat.
- V5 uses strict streamed `/v1/chat/completions`; invalid/premature SSE is failure.
- V5's LiteLLM client default timeout is 120 seconds.
- the old undocumented `PREFERENCE_HINTS` ordering was removed;
- current `MODEL_TIERS` is a documented research-grounded prior, with availability and task/methodology relevance ranked ahead of the tier;
- model output never replaces the deterministic checker/verification gate;
- retry/model switch remains a new attempt/receipt, not hidden success.

The first real V5 HumanEval acceptance is already closed/completed. Do not reopen V5 acceptance or automatically make CORTEX-02/workflow changes merely because older FOSSIL queue text mentions them.

### LiteLLM / CKFF

Observed current `Pukujan/litellm-ckff-ops` main:

`9520e8dffe819d97a1557fe76022ed080f0eb8d6`

Current executable/config facts include:

- configured logical models have CKFF deployments on `https://ckffai.com/v1` plus `https://ckff.dev/v1`;
- LiteLLM `request_timeout` is 120 seconds, aligned with V5's default client deadline;
- router retries/cooldown remain bounded and `max_parallel_requests` is 8;
- the Responses bridge has an explicit cross-model fallback table and records requested/actual model identity; exact-model work should disable bridge fallbacks;
- embeddings and reranking remain separate `/v1/embeddings` and `/v1/rerank` service lanes;
- gateway privacy warnings are advisory; CKFF is not verified zero-data-retention.

LiteLLM's repository documentation is **not fully reconciled with current config**: the timeout contract is current, but the compatibility report still contains a 90-second LiteLLM value and the implementation-gap document still claims `ckffai.com` is absent from generated config. Treat those dated reports as historical evidence where they conflict with current exact source/config.

Do **not** edit the LiteLLM repository or its workflows from this FOSSIL task.

## Read first

For a fresh session:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. this file
4. `docs/PROJECT_STATE.md`
5. `docs/operations/EXTERNAL-RUNTIME-RECONCILIATION-2026-08-15.md`
6. Issue #86 — current architecture reconciliation
7. Issue #94 — execution queue and append-only claim ledger
8. Issue #87 — S3-compatible canonical storage + rebuild proof
9. Issue #124 — current live object-store candidate proof
10. `docs/DECISION_LOG.md`
11. `docs/operations/LITELLM-GATEWAY.md`

Verify live GitHub state immediately before any write, merge, rebase, deployment, credentialed proof or task claim.

## Frozen authority rules

- Retrieval rank is candidate ordering, not truth.
- Reranker score is not truth.
- Model confidence, model tier and multi-model agreement are not truth.
- A gateway fallback response is not evidence that the requested model itself succeeded.
- GitHub Actions artifacts/caches are not canonical FOSSIL truth.
- FOSSIL durable evidence/events, stable IDs, provenance, lifecycle, lineage, redaction and accepted contracts remain semantic authority.
- Cortex V5 owns execution/methodology/model seating; that policy does not become FOSSIL semantic authority.
- LiteLLM/CKFF owns factual transport/routing/capability/timeout state; callers own task-specific acceptance.
- Ordinary PR CI remains secretless.
- Production promotion always requires separate explicit authorization.

## Legacy SSC

Legacy `stupidly-simple-cortex` is retired/superseded as runtime, memory, RAG, ontology/current-state, orchestration and project authority. Cortex V5 does not depend on it.

Potentially useful historical eval/checker assets may survive only after independent extraction/revalidation with exact bytes, hashes, provenance, license and leakage controls. Do not revive SSC runtime to preserve an old asset.

Durable retirement decision: D023 in `docs/DECISION_LOG.md`.

## Current execution order

### Active FOSSIL lane — Issue #124 / OBJECT_STORE_LIVE

The secretless storage foundation has passed. The current live phase is narrowly scoped to a dedicated non-production R2 bucket/prefix and must remain fail-closed.

PASS requires, among other issue-specific checks:

- exact-SHA checkout;
- live immutable/idempotent/conflict semantics;
- independent fresh hosted-runner rebuild from zero local state;
- repeated rebuild/restartability;
- redaction tombstone-before-delete and non-resurrection;
- negative controls for dead endpoint/auth/partial response;
- sanitized receipts with no credential material;
- normal DKG green on the same code head;
- no provider-specific weakening of the core storage contract.

If the required live config/credential is absent, report `BLOCKED_CREDENTIAL`; do not improvise secrets.

### Parallel docs lane

`DOCS-RECONCILE-20260815` is explicitly docs-only and parallel-safe. It must not modify #124 harness/workflow/runtime files or alter the active live-proof state.

### After #124

Reconcile the exact live evidence first, then choose the next **FOSSIL-only** gate. Do not automatically mutate Cortex V5 or LiteLLM/CKFF. Any external-runtime change is a separate owner decision.

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

Immediately re-fetch #94 comments. Earliest valid unexpired claim wins. One active mutating owner per repo lane unless the task explicitly declares safe parallelism.

Close with `DONE`, `BLOCKED` or `RELEASE` using exact refs/tests/evidence.

## Engineering policy

- SDD always.
- TDD for deterministic behavior where practical.
- Integration/wiring tests for real boundaries.
- E2E for important actual flows.
- Hidden holdouts for autonomous model evaluation.
- Fault injection for recovery/retry infrastructure.
- Explicit security checks at credential/deployment boundaries.
- Regression coverage for discovered bugs.
- Never weaken acceptance merely to obtain green.

## Immediate fresh-agent behavior

1. Read #86, #94, #87 and #124 live.
2. Confirm current `main` and active claim state.
3. Treat Cortex V5 and LiteLLM as read-only unless the owner explicitly opens a separate mutation task.
4. Take only an eligible task matching access and collision rules.
5. Work on an isolated branch/target.
6. Test mechanically and record exact evidence.
7. Post `DONE`, `BLOCKED` or `RELEASE`.
8. Re-read the queue before taking another task.

If no eligible task exists, stop with explicit idle/BLOCKED evidence rather than inventing work.
