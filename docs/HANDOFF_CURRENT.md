# Current Handoff

**Date:** 2026-08-19  
**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Repository:** `Pukujan/fossil-core`  
**Architecture authority:** Issue #86  
**Execution queue / claim ledger:** Issue #94  
**Semantic hardening authority:** Issue #111  
**PDD / formal assurance campaign:** Issue #176

## Current checkpoint

Verified pre-handoff `main`:

`e14ef747547e86add2d3e819a537c1a8d2b35294` — `[ARCH] Accept issue #111 semantic freeze (#221)`

Do **not** treat that SHA as a live lock. Re-fetch `main`, Issue #94, Issue #111, and Issue #176 before any mutation.

The detailed current-session transfer record is:

`docs/handoffs/2026-08-19-pdd-semantic-freeze-session-handoff.md`

Read that file before resuming work.

## Immediate state

The public PDD campaign has landed its property catalog/oracles, currently unblocked mutation lanes, public hidden-holdout receipt/manifest boundary, TLA+/Lean foundations, CI hygiene, and fail-closed formal-reference traceability.

PR #221 has now merged the accepted #111 semantic freeze. This **freezes the semantic target but does not complete #111 implementation**.

The required post-freeze implementation sequence is:

1. event-type contract/evidence-policy registry + deterministic fail-closed accepted-commit gates;
2. `dkg.packset-lock.v1` + exact revision locking + cycle/layer validation + replay/portability tests;
3. versioned promotion payload with source revision/event pin + source-resolvability tests;
4. longitudinal epistemic benchmark;
5. reviewed evidence ingestion + compact receipt.

Promotion mutation/Lean work under #176 must wait until the Promotion law and its prerequisites are implemented. Do not skip directly to formal/mutation evidence merely because the semantic freeze is accepted.

## Exact stop point

The previous session briefly claimed Step 1, characterized the current event envelope / event store / agent boundary, then the user requested a session stop and durable handoff.

That Step 1 claim was explicitly released. There were:

- no Step 1 repository-file changes;
- no Step 1 implementation branch to preserve;
- no Step 1 PR to resume.

Restart from live `main` after re-reading #94.

## Hidden holdout boundary

The abstract least-privilege mechanism is approved, but concrete private placement/verifier provisioning remains out-of-band.

Public repository rules remain strict:

- no sealed cases;
- no private exact oracles;
- no credentials;
- no private paths/URLs;
- no verifier identity;
- public receipts contain safe aggregate evidence only.

No sealed-execution PASS is currently claimed.

## Mandatory coordination

Before any GitHub mutation:

```text
CLAIM task=<TASK_ID>
agent=<unique-agent-id>
mode=<LOCAL_CODEX|CLOUD_CODEX|CHATGPT|ACTIONS>
lease_until=<ISO-8601 UTC>
repo=<repo>
starting_ref=<branch/SHA/PR>
scope=<bounded scope>
parallel_safe=<yes|no>
```

Immediately re-fetch #94 and confirm the claim wins. One active mutating owner per repo lane unless explicitly parallel-safe.

Close work with `DONE`, `BLOCKED`, or `RELEASE` and exact evidence.

Before merge, re-check exact head, exact-head CI, current main, changed-file scope, mergeability, reviews, review threads, conversation blockers, and #94 ownership. Use SHA-fenced merge for bounded assurance/architecture PRs.

## Frozen boundaries

- Compute/projections/models are replaceable; durable evidence/events/contracts/provenance remain authority.
- Retrieval rank, reranker score, model confidence, and multi-model agreement are not truth.
- Historical events must remain replayable and must not be silently upgraded.
- Ordinary PR CI remains secretless.
- Never weaken acceptance merely to obtain green.
- Never expose private hidden-holdout material.
- Never conflate mutation / holdout / TLA+ / Lean in one slice.
- No production promotion or deployment is authorized by this handoff.
- Do not touch unrelated open PRs just to keep the queue busy.

## Fresh-session first action

1. Read `AGENTS.md`, `ARCHITECTURE.md`, #86, latest #94, #111, #176, this file, and the dated handoff.
2. Re-fetch current `main`.
3. Confirm no newer owner/PR exists for #111 Step 1.
4. If unowned, claim a bounded Step 1 lane and characterize all event types/direct durable-store callers before implementation.
5. If another owner exists, do not duplicate it.

If live GitHub state differs from this document, live GitHub wins.
