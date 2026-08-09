# Agent Continuation Contract

This repository is designed so another GPT/Codex/Claude session can continue the project without relying on chat memory.

## Start here, in this order

1. `ARCHITECTURE.md` — frozen durable invariants.
2. `docs/PROJECT_STATE.md` — current gate and work state.
3. `docs/HANDOFF_CURRENT.md` — exact continuation point and next actions.
4. `docs/research/2026-08-09-final-research-synthesis.md` — why the architecture was chosen.
5. `docs/research/2026-08-09-evidence-ledger.md` — source ledger for the research freeze.
6. `docs/DECISION_LOG.md` — accepted decisions, alternatives, and reconsideration triggers.
7. GitHub Issue #1 and child issues #2–#10 — executable work tracking.

## Non-negotiable rules

- Do not treat Neo4j, Graphiti, an embedding index, MCP, a specific model, or a chat transcript as the durable source of truth.
- Original evidence is preserved; summaries never replace source evidence.
- Knowledge-changing history is append-only and versioned.
- Stable IDs belong to the corpus, not to a storage engine.
- Graph/search/vector structures are rebuildable projections.
- `DISPUTED` and unresolved disagreement are valid durable states.
- Model agreement is metadata, not external evidence.
- Agents normally propose; deterministic validation/policy gates commit durable changes.
- Knowledge-pack identity is logical and must not depend on repository path or physical database placement.
- Operational telemetry stays outside canonical knowledge; durable knowledge-changing provenance stays inside.
- Do not add infrastructure because it is fashionable. New technology must beat the existing adapter/benchmark contract.

## Frozen does not mean unchangeable

`ARCHITECTURE.md` is frozen as a contract, not as dogma. A durable invariant may be changed only when implementation evidence or stronger research justifies it.

When changing one:

1. open/update the relevant issue;
2. record the competing theory or failure;
3. cite evidence/benchmark results;
4. update `docs/DECISION_LOG.md`;
5. update the architecture contract explicitly;
6. preserve the previous decision and why it was superseded.

Do not silently rewrite history.

## Work-state rule

GitHub issues track implementation state. Repository docs track durable decisions/evidence/contracts.

An issue can close, but an architectural decision must not exist only in an issue comment. Conversely, durable docs should point back to the issue/benchmark that caused the change when useful.

## Current implementation order

Unless a failing test changes the order:

1. #2 durable event/artifact store
2. #3 knowledge-pack boundaries/mounts/promotion
3. #6 claim/relation lifecycle + staleness
4. #4 Graphiti + Neo4j projection adapter
5. #5 destructive rebuild + blue/green migration harness
6. #9 conversation lineage benchmark
7. #8 Agent Skills + thin API/MCP adapter
8. #7 pluggable retrieval/model-service benchmarking
9. #10 source snapshot/redaction hardening as required across the above work

Do not create external knowledge-pack repositories until #3 proves the pack contract and namespace isolation.

## Session continuity protocol

At the end of any substantial work session:

- update `docs/HANDOFF_CURRENT.md`;
- update `docs/PROJECT_STATE.md` if the gate changed;
- update the relevant GitHub issue checklist/status;
- commit benchmark/test results that materially justify a decision;
- record architectural changes in `docs/DECISION_LOG.md`;
- never rely on the chat UI as the only record of a decision.

If a chat history is missing or ambiguous, label reconstructed material as reconstructed rather than presenting it as verbatim evidence.
