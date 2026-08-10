# Agent Continuation Contract

This repository is designed so another GPT/Codex/Claude session can continue the project without relying on chat memory.

## Start here, in this order

1. `ARCHITECTURE.md` — frozen durable invariants.
2. `docs/HANDOFF_CURRENT.md` — exact continuation point.
3. `docs/PROJECT_STATE.md` — completed gate/work state.
4. `docs/handoffs/2026-08-10-chatgpt-session-handoff.md` — detailed transfer record for the completed Milestone 0 / Gate 1 checkpoint and the rationale for Gate 2.
5. `docs/DECISION_LOG.md` — accepted decisions, alternatives, and reconsideration triggers.
6. Gate/proof documents under `docs/implementation/`.
7. `docs/research/2026-08-09-final-research-synthesis.md` and `docs/research/2026-08-09-evidence-ledger.md` when research rationale is needed.
8. GitHub Gate 2 control Issue #33 and active child issues #34–#37 for current implementation state.
9. Closed GitHub Issue #1 and child Issues #2–#10 only when detailed Gate 1 history is useful.

## Current state

**Milestone 0 is complete. Gate 1 is 15/15 complete. Issues #1–#10 are closed completed. Gate 2 — Real Corpus + Retrieval/Model Bakeoff is now active under control Issue #33 with child Issues #34–#37.**

Current first implementation slice: Issue #34, with draft PR #38 adding a persistent/versioned benchmark case-set contract before representative pack data is seeded.

Do not reopen the completed milestone merely to continue development.

## Non-negotiable rules

- Do not treat Neo4j, Graphiti, an embedding index, MCP, a specific model, or a chat transcript as the durable source of truth.
- Original evidence is preserved; summaries never replace source evidence.
- Normal knowledge-changing history is append-only and versioned.
- Privacy/legal erasure is an exceptional explicit tombstone-before-delete path; erased identities must not silently resurrect.
- Stable IDs belong to the corpus, not to a storage engine.
- Stable knowledge-pack identity is logical and independent of repository path, graph namespace, or physical database placement.
- Graph/search/vector structures are rebuildable projections.
- A new/rebuilt physical projection gets a fresh build-scoped applied ledger.
- Rebuild replay order is `(recorded_at, event_id)`.
- Migration compares stable FOSSIL semantics, not graph-native UUID equality.
- `DISPUTED` and unresolved disagreement are valid durable states.
- Model agreement is metadata, not external evidence.
- Small/local model output remains candidate-only unless independent evidence/risk policy permits downstream authority.
- Agents normally propose; deterministic validation/policy gates commit durable changes.
- Skills contain methodology, not canonical truth.
- Protocol adapters remain thin and must not become the durable knowledge model.
- Operational telemetry stays outside canonical knowledge; durable knowledge-changing provenance stays inside.
- Reconstructed evidence can never silently become verbatim evidence.
- Do not add infrastructure because it is fashionable. New technology must beat the existing adapter/benchmark contract.
- Do not casually rename the internal `src/dkg` module/API namespace.

## Repository family invariants

- `Pukujan/fossil-common` keeps stable pack ID `pack_269099f7b2ba43b7a99b9427d64092de`.
- `Pukujan/fossil-ai-systems` keeps stable pack ID `pack_f024177f89a5442db84171c3dd7f58e5` and its required dependency on common.
- Do not call pack repositories "database shards"; physical sharding/placement is a separate concern.

## Frozen does not mean unchangeable

`ARCHITECTURE.md` is frozen as a contract, not as dogma. A durable invariant may be changed only when implementation evidence or stronger research justifies it.

When changing one:

1. open/update the relevant active issue;
2. record the competing theory or failure;
3. cite evidence/benchmark results;
4. update `docs/DECISION_LOG.md`;
5. update the architecture contract explicitly;
6. preserve the previous decision and why it was superseded.

Do not silently rewrite history.

## Work-state rule

GitHub issues track implementation state. Repository docs track durable decisions/evidence/contracts.

An issue can close, but an architectural decision must not exist only in an issue comment. Conversely, durable docs should point back to the issue/benchmark that caused the change when useful.

## Active campaign — Gate 2

Control issue: **#33 — Gate 2: Real Corpus + Retrieval/Model Bakeoff**.

Children:

1. **#34** representative real corpus fixtures + versioned gold/adversarial benchmark set;
2. **#35** a small number of materially different real retrieval/context adapters behind existing interfaces;
3. **#36** reproducible comparative `fossil.benchmark.v1` runs and failure taxonomy;
4. **#37** evidence-based default retrieval/routing policy.

Initial Gate 2 inspection established that `fossil-common` and `fossil-ai-systems` are currently pack scaffolds with empty event/artifact payloads. Issue #34 therefore includes seeding representative canonical evidence/events into those existing stable packs before calling the benchmark corpus "real".

Draft PR #38 adds the missing persistent case-set layer. Its first trusted CI run `31356440481`, job `93356916077`, passed **60 tests in 0.69s**. Exact citation gold is being stored as full immutable citation span/hash metadata rather than citation IDs alone.

Current BM25/hash-embedding/token-overlap implementations remain **controls, not production winners**. Gate 2 provider/routing choices must be earned by measured corpus performance.

## Session continuity protocol

At the end of any substantial work session:

- update `docs/HANDOFF_CURRENT.md`;
- update `docs/PROJECT_STATE.md` if the gate changed;
- update the relevant active GitHub issue checklist/status;
- commit benchmark/test results that materially justify a decision;
- record architectural changes in `docs/DECISION_LOG.md`;
- add/update a dated handoff when a long session is being retired;
- never rely on the chat UI as the only record of a decision.

If a chat history is missing or ambiguous, label reconstructed material as reconstructed rather than presenting it as verbatim evidence.
