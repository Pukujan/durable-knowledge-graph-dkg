# Agent Continuation Contract

This repository is designed so another GPT/Codex/Claude session can continue the project without relying on chat memory.

## Start here, in this order

1. `ARCHITECTURE.md` — frozen durable invariants.
2. `docs/HANDOFF_CURRENT.md` — exact continuation point.
3. `docs/PROJECT_STATE.md` — completed gate/work state.
4. `docs/handoffs/2026-08-10-chatgpt-session-handoff-gate2-complete.md` — detailed Gate 2 completion transfer.
5. `docs/DECISION_LOG.md` — accepted decisions, alternatives, and reconsideration triggers.
6. Gate/proof documents under `docs/implementation/`.
7. `docs/research/2026-08-09-final-research-synthesis.md` and `docs/research/2026-08-09-evidence-ledger.md` when research rationale is needed.
8. Closed Gate 2 control Issue #33 and child Issues #34–#37 when detailed Gate 2 history is useful.
9. Closed GitHub Issue #1 and child Issues #2–#10 only when detailed Gate 1 history is useful.

## Current state

**Milestone 0 is complete. Gate 1 is 15/15 complete. Gate 2 — Real Corpus + Retrieval/Model Bakeoff is complete. Issues #33–#37 are closed/completed.**

Gate 2 decision D021 selects revision-pinned BGE dense retrieval as the normal primary, with explicit BM25 degraded availability fallback and mandatory lifecycle/lineage/citation safeguards. Do not treat this replaceable policy as canonical truth.

There is no active post-Gate-2 campaign. Do not invent a new Gate 3 from old chat context. Open a new explicit issue/campaign for new work.

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

## Completed campaign — Gate 2

Control issue: **#33 — Gate 2: Real Corpus + Retrieval/Model Bakeoff** — closed/completed.

Children:

1. **#34** representative real corpus fixtures + versioned gold/adversarial benchmark set — closed/completed;
2. **#35** real retrieval/context adapters behind existing interfaces — closed/completed;
3. **#36** reproducible comparative `fossil.benchmark.v1` runs and failure taxonomy — closed/completed;
4. **#37** evidence-based default retrieval/routing policy — closed/completed.

Gate 2 established a 21-case history-rich real corpus and compared four strategies in one semantic-capable environment. Exact-head proof run `31364039745`, artifact `9053475462`, digest `sha256:23c95b46f47cec5a16e0a8c0926a4f13532f283d8f4fbcc0de12ceb63db63c41`.

BGE dense was the only compared strategy with zero full retrieval misses and had the best mean recall@5 (`0.98413`). It still exhibited current-state ranking leakage and incomplete multi-target lineage recall. The hybrid had the best MRR but fully missed the key current-architecture case.

D021 therefore selects pinned BGE dense as the normal primary and BM25 as an explicit degraded availability fallback. Current/history and lineage-sensitive tasks must resolve durable lifecycle/lineage rather than treating retrieval rank or top-k absence as truth. Exact citation/source semantics and model-authority boundaries remain unchanged.

Gate 2D landed in PR #45 / squash commit `2d22dee9e6b176956d30005f4d7877baf68b0a3c`; final branch-independent CI was run `31366800697`, job `93386832166`, **86 passed in 1.02s**.

Evidence:

- `benchmarks/gate2/results/2026-08-10-comparative/comparison-summary.json`;
- `docs/implementation/2026-08-10-gate2-comparative-bakeoff-proof.md`;
- `docs/implementation/2026-08-10-gate2-default-retrieval-policy.md`;
- D021 in `docs/DECISION_LOG.md`.

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
