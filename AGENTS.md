# Agent Continuation Contract

This repository is designed so another GPT/Codex/Claude session can continue without relying on chat memory.

## Start here, in this order

1. `ARCHITECTURE.md` — durable FOSSIL invariants and non-goals.
2. GitHub Issue #86 — current cross-project architecture authority.
3. Latest GitHub Issue #94 comments — current execution queue, claims, and closeouts.
4. `docs/HANDOFF_CURRENT.md` — current continuation summary.
5. `docs/PROJECT_STATE.md` — current FOSSIL state plus durable proof anchors.
6. `docs/operations/EXTERNAL-RUNTIME-RECONCILIATION-2026-08-15.md` — read-only Cortex V5 / LiteLLM inspection snapshot.
7. GitHub Issue #87 — provider-neutral S3-compatible durability track.
8. GitHub Issue #124 — current `OBJECT_STORE_LIVE` candidate gate.
9. `docs/DECISION_LOG.md` — accepted decisions and reconsideration triggers.
10. The focused issue/PR for the task you actually claim.

Live #86/#94 state supersedes stale operational ordering in repository prose. Re-fetch exact heads, CI, review state, environment/config state, and claims immediately before any write, rebase, merge, deployment, credentialed proof, or task claim.

## Current boundary

The project invariant is:

> **Compute may disappear; truth must not.**

The subsystem boundary is:

> **Cortex V5 owns execution policy. FOSSIL owns durable knowledge/evidence. GitHub owns source/coordination/review. LiteLLM/CKFF owns provider/model/route transport facts. Infrastructure and projections are replaceable.**

The owner has explicitly requested that `Pukujan/cortex-v5` and `Pukujan/litellm-ckff-ops` remain **read-only** during the current FOSSIL continuation. Inspect them when needed to understand behavior; do not change their code, workflow, routing, deployment, or model policy unless the owner separately authorizes that work.

## Current FOSSIL lane

The secretless S3-compatible storage foundation is complete. Historical runtime/storage anchor `ea1d88fc114981915603ec46a401dca45acd5a11` includes merged PR #123, which proved the provider-neutral storage contract against a real disposable S3-compatible service with no cloud credential/provider selection.

The active durability gate is Issue #124 / `OBJECT_STORE_LIVE`: a separately credentialed, non-production R2 **candidate** durability + empty-runner rebuild proof. R2 is the first live candidate only; `S3ArtifactStore` / `S3DurableEventStore` remain the provider-neutral architecture boundary.

Do not infer `OBJECT_STORE_LIVE PASS` from ordinary PR CI. Live PASS requires the exact issue acceptance, including fresh-runner reconstruction, redaction/non-resurrection, fail-closed controls, sanitized receipts, and same-head normal DKG.

As of the 2026-08-15 checkpoint, draft PR #125 carried the credential-free harness and had exact-head DKG green, but independent review found acceptance/config reconciliation items. Re-read the current PR and #94 before acting; do not treat this sentence as live branch state.

## Non-negotiable authority rules

- Durable FOSSIL evidence/events, stable IDs, provenance, lifecycle, lineage, redaction, and accepted contracts remain semantic authority.
- Neo4j/Graphiti, vector/lexical indexes, retrievers, rerankers, models, Cortex, LiteLLM, Skills, MCP, dashboards, and CI artifacts are replaceable services/projections, not durable truth.
- Retrieval rank, reranker score, model confidence, model tier, and multi-model agreement do not create evidence authority.
- A gateway fallback response is not evidence that the requested model itself succeeded.
- `2xx` with empty, malformed, truncated, or zero-usable semantic output is failure, not success.
- Reconstructed evidence cannot silently become verbatim evidence.
- Privacy/legal erasure is exceptional tombstone-before-delete; erased identities must not silently resurrect.
- Stable knowledge-pack identity is logical and independent of repository/database/graph placement.
- Ordinary PR CI remains secretless.
- Production promotion requires separate explicit human authorization.
- Never weaken, skip, xfail, suppress, or narrow an acceptance path merely to obtain green.

## Legacy SSC

Legacy `stupidly-simple-cortex` is retired/superseded as runtime, memory, RAG, ontology/current-state, orchestration, and project authority. Cortex V5 does not depend on it.

Potentially useful historical eval/checker assets may survive only after independent extraction/revalidation with exact bytes, hashes, provenance, license, checker dependencies, and leakage controls. Do not revive SSC runtime to preserve an old asset.

Durable retirement decision: D023 in `docs/DECISION_LOG.md`.

## Repository family invariants

- `Pukujan/fossil-common` keeps stable pack ID `pack_269099f7b2ba43b7a99b9427d64092de`.
- `Pukujan/fossil-ai-systems` keeps stable pack ID `pack_f024177f89a5442db84171c3dd7f58e5` and its required dependency on common.
- Do not call pack repositories database shards; physical placement/sharding is a separate concern.

## Claim protocol

Before mutating FOSSIL work, use Issue #94:

```text
CLAIM task=<TASK_ID>
agent=<unique-agent-id>
mode=<LOCAL_CODEX|CLOUD_CODEX|CHATGPT|ACTIONS>
lease_until=<ISO-8601 UTC>
repo=<repo>
starting_ref=<branch/SHA/PR>
```

Immediately re-fetch #94. Earliest valid unexpired claim wins. One active mutating owner per repo lane unless the task explicitly declares safe parallelism.

Close with `DONE`, `BLOCKED`, or `RELEASE` using exact refs, tests, hosted run IDs, and evidence required by that task.

## Engineering policy

- SDD always.
- TDD for deterministic behavior where practical.
- Infra/config: contract first -> failing verification/probe -> smallest change -> passing verification.
- Integration/wiring tests where there is actual wiring.
- E2E for important real flows.
- Fault injection for recovery/retry infrastructure.
- Explicit security checks at credential/deployment boundaries.
- Hidden holdouts for autonomous model evaluation where appropriate.
- Selective mutation testing on small critical validators/gates/security/recovery logic.
- Regression coverage for every discovered bug.

For deterministic changes, prefer:

1. **RED** — reproduce the defect/invariant first.
2. **GREEN** — smallest correct change.
3. **REGRESSION** — neighboring tests + full suite.
4. **CLEAN VERIFY** — independent clean environment/worktree.
5. **HOSTED EVIDENCE** — exact-head CI where the PR has hosted acceptance.

## Immediate fresh-agent behavior

1. Read #86, #94, #87, and #124 live.
2. Confirm current `main`, open PR heads, review state, environment/config state, and active claims.
3. Treat Cortex V5 and LiteLLM/CKFF as read-only unless the owner explicitly opens separate mutation work.
4. Take only an eligible task matching access and collision rules.
5. Work on an isolated branch/target.
6. Test mechanically without weakening acceptance.
7. Post exact `DONE`, `BLOCKED`, or `RELEASE` evidence.
8. Re-read #94 before taking another task.

If no eligible task exists, stop with explicit idle/BLOCKED evidence rather than inventing work.

## Session continuity protocol

At the end of substantial work:

- update #94 with exact claim/closeout evidence;
- update `docs/HANDOFF_CURRENT.md` when the continuation point materially changes;
- update `docs/PROJECT_STATE.md` when the campaign/gate state changes;
- update the relevant focused issue/PR;
- commit benchmark/test results that materially justify a decision;
- record architectural changes in `docs/DECISION_LOG.md` and #86 when appropriate;
- never rely on the chat UI as the only record of a decision.

If history is missing or ambiguous, label reconstructed material as reconstructed rather than presenting it as verbatim evidence.
