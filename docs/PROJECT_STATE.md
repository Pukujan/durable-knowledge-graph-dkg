# Project State

**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Durable substrate:** **DICS — Durable Intellectual Corpus System**
**Current phase:** Gate 1 executable durability proof — live projection + destructive rebuild/blue-green complete; conversation lineage active  
**Control plane:** GitHub issues + durable repository docs  
**Last updated:** 2026-08-09

## Repository family

GitHub repository family:

- `fossil-core` — architecture, contracts, durable core, projections, and control plane;
- `fossil-common` — stable pack `pack_269099f7b2ba43b7a99b9427d64092de`;
- `fossil-ai-systems` — stable pack `pack_f024177f89a5442db84171c3dd7f58e5`, with a required dependency on the common pack.

The repository family physically exists as `Pukujan/fossil-core`, `Pukujan/fossil-common`, and `Pukujan/fossil-ai-systems`. This physical split does not change pack identity: stable `pack_id` values remain authoritative across repository moves, projections, and future storage changes.

## Continuation entry point

A new agent/session should read:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/HANDOFF_CURRENT.md`
4. this file
5. `docs/implementation/2026-08-09-gate1-live-graphiti-proof.md`
6. `docs/implementation/2026-08-09-gate1-rebuild-blue-green-proof.md`
7. `docs/research/2026-08-09-final-research-synthesis.md`
8. `docs/research/RESEARCH_TRACE_CONTRACT.md`
9. `docs/DECISION_LOG.md`
10. Issue #1 and active Issue #9

The chat UI is **not** the project record.

## Tracking rule

GitHub issues track **work state**. Durable docs track **decisions/evidence/contracts**.

An issue may close because work was completed or rejected, but an architectural decision should not exist only inside an issue comment. It must point to a durable document/ADR/schema/benchmark result committed in the repository.

Likewise, durable docs should link to the issue that caused a decision when useful so implementation history remains reconstructable.

## Research-trace rule

The **research process itself is future corpus data**.

The graph must eventually be able to reconstruct how this project was researched: original questions, alternative architectures, searches/source snapshots, claims, critiques, unresolved uncertainty, accepted-for-now decisions, issues, commits, benchmarks, failures, and later supersession.

Durable trace references include:

- `docs/research/RESEARCH_TRACE_CONTRACT.md`
- `schemas/research-trace/v1.schema.json`
- `docs/research/2026-08-09-dkg-project-research-trace-seed.md`
- `examples/research-trace/dkg-project-research-run-v1.json`
- `docs/implementation/2026-08-09-gate1-core-proof.md`
- `docs/implementation/2026-08-09-gate1-live-graphiti-proof.md`
- `docs/implementation/2026-08-09-gate1-rebuild-blue-green-proof.md`

High-volume operational telemetry remains external. The durable corpus stores compact intellectual lineage plus trace IDs when deeper debugging evidence is needed.

## Gate 0 — complete

Research freeze and durable contracts include the 127-source evidence ledger, final synthesis, architecture contract, event/pack/research-trace schemas, core ontology, source-quality policy, migration/rebuild direction, agent continuation docs, decision log, and research trace seed.

## Gate 1 — executable durability proof

Completed so far:

1. [x] create and validate immutable events;
2. [x] reject invalid/duplicate writes deterministically;
3. [x] store immutable content-addressed artifacts with verification;
4. [x] enforce pack read/write boundaries and required dependencies;
5. [x] represent cross-pack promotion as a new provenance-preserving event;
6. [x] preserve claim/relation disagreement, lifecycle history, supersession, and stale-dependency state through event replay;
7. [x] isolate Graphiti calls behind a replaceable adapter;
8. [x] make projection retries idempotent and preserve failure records;
9. [x] record projection build metadata in the projection ledger;
10. [x] pass a live Graphiti + Neo4j integration smoke test;
11. [x] destroy/rebuild the graph from durable data;
12. [x] build and compare a second candidate projection;
13. [ ] answer conversation lineage/reconstruction benchmarks;
14. [ ] resolve citations/provenance to intended evidence snapshots;
15. [ ] expose the safe Agent Skill/API boundary.

## Live projection proof

Issue #4 crossed the real integration gate in GitHub Actions run #70 (`31338875226`). The proof used Graphiti `0.29.3`, Neo4j `5.26.29`, local Ollama `deepseek-r1:7b`, `nomic-embed-text`, and `structured_output_mode=json_schema`.

Durable event `evt_27769393996d2827172f6abc0aa086dc` existed before projection. A real Graphiti `Episodic` node was observed exactly once under `group_id == pack_269099f7b2ba43b7a99b9427d64092de`, with two mentioned entities. Replaying the same event returned `skipped: already applied` and the episode count remained exactly one.

The first real attempt with `json_object` failed because the local model emitted `Edges` instead of the required `edges`; the projection ledger recorded the failure and the durable event remained intact. The successful retry used schema-constrained output. See `docs/implementation/2026-08-09-gate1-live-graphiti-proof.md`.

## Destructive rebuild + blue/green proof

Issue #5 passed a real two-Neo4j proof in trusted CI run #81 (`31339930551`), job `93311926075`.

Durable event `evt_aadf683e9aa41443f95be71c211cd2c4` survived a real candidate-graph destructive reset from one sentinel node to **0 nodes**. Green/candidate then replayed the same durable source using fresh build-scoped ledger `green-rebuild-1`, produced an `applied` receipt, and returned to **3 graph nodes** while blue/current remained live with **3 graph nodes**.

Expected durable, blue, and green projection-independent semantic digests all matched:

`c8d790b3a1d6741a86e280db44595b463347e6c47a4d933274e1c829696e4696`

The append-only active switch `blue -> green` was written only after named migration checks passed. Final unit guardrails, including stale source-slot rejection, passed trusted CI run #84: **26 passed in 0.44s**.

See `docs/implementation/2026-08-09-gate1-rebuild-blue-green-proof.md`.

## Current issue map

- #1 Milestone-control issue — open
- #2 Durable event + artifact store — **complete**
- #3 Knowledge-pack boundaries, mounts, promotion — **complete**
- #4 Graphiti + Neo4j projection adapter/queue — **complete**
- #5 Destructive rebuild + blue/green migration harness — **complete**
- #6 Claim/relation lifecycle, disagreement, supersession, staleness — **complete**
- #7 Pluggable retrieval/model services + local-specialist benchmark contract — pending
- #8 Agent Skills + thin corpus API/MCP contract — pending
- #9 Conversation ingestion + intellectual-lineage reconstruction benchmark — **active**
- #10 Source snapshots, citation provenance, quality dimensions, redaction path — cross-cutting/pending

## Recommended execution order from here

`#9 conversation lineage benchmark -> #8 Skills/API/MCP -> #7 retrieval/model benchmarks`, while applying #10 requirements during source ingestion.

## Immediate next task

Execute **Issue #9** without flattening the source conversation into a polished summary:

1. define a durable conversation/source envelope with stable conversation/message identities and explicit source status (`verbatim` vs `reconstructed`);
2. preserve raw/verbatim text as an immutable artifact when available;
3. represent reconstructed recovery material explicitly as reconstruction rather than verbatim evidence;
4. preserve message order, reply/parent relationships, actor/model/tool/run metadata where available, and source spans;
5. derive claims, challenges, rebuttals, assumptions, conclusions, and position changes with provenance back to source messages/spans;
6. keep opposing positions separately retrievable;
7. benchmark reconstruction of the required intellectual path and the current conclusion;
8. prove current state and historical path can both be queried without relying on chat UI history.

The recovered chat-loss checkpoint is provenance and must never be silently promoted to a verbatim transcript.

## Migration invariants now frozen

- destructive graph replacement uses a fresh projection build identity/applied ledger;
- event replay order is `(recorded_at, event_id)`, not filesystem path and not `occurred_at`;
- migration comparison excludes graph-native UUIDs;
- semantic snapshots compare durable IDs, pack namespaces, provenance, claim/relation state, and event inventory;
- active projection changes are append-only switch records written only after checks pass;
- once an active slot exists, stale switch proposals from an old source slot are rejected.

## Knowledge repository split

The external repositories are **knowledge-pack repositories**, not database shards.

The first two external knowledge-pack repositories are:

1. `fossil-common` — shared/common research + engineering methods;
2. `fossil-ai-systems` — AI-systems/plugin-harness knowledge.

They preserve the existing `dkg.pack.v1` contract and stable pack IDs listed at the top of this file. Repository location, Graphiti namespace, and future physical database placement are operational details rather than identity.

## Current implementation evidence

- `src/dkg/io.py` — atomic immutable publication.
- `src/dkg/event_store.py` — validated, deterministic idempotent durable events.
- `src/dkg/artifact_store.py` — SHA-256 content-addressed evidence and verification.
- `src/dkg/pack.py` — pack validation and read/write boundaries.
- `src/dkg/promotion.py` — explicit cross-pack promotion event.
- `src/dkg/lifecycle.py` — event-replay claim/relation lifecycle and stale propagation.
- `src/dkg/projection/ledger.py` — retry/failure/applied projection ledger with build scoping.
- `src/dkg/projection/graphiti.py` — isolated Graphiti/Neo4j adapter with durable replay ordering.
- `src/dkg/projection/migration.py` — semantic comparison, destructive rebuild orchestration, and guarded blue/green switch ledger.
- `tests/test_projection_migration.py` — deterministic migration fixtures and guardrails.
- `scripts/live_graphiti_smoke.py` — reusable real Graphiti/Neo4j proof runner.
- `docs/implementation/2026-08-09-gate1-core-proof.md` — durable-core checkpoint.
- `docs/implementation/2026-08-09-gate1-live-graphiti-proof.md` — real projection checkpoint.
- `docs/implementation/2026-08-09-gate1-rebuild-blue-green-proof.md` — real destructive rebuild/blue-green checkpoint.

## Research status

Broad architecture research remains frozen enough to implement. New technologies should compete behind adapters and benchmarks rather than restarting the architecture.

Reopen architecture research when implementation contradicts an assumption, a dependency materially changes/decays, a new requirement appears, or a competing architecture wins measured benchmarks.

## End-of-session rule

At the end of substantial work:

- update `docs/HANDOFF_CURRENT.md`;
- update this file if gate state changed;
- update relevant GitHub issues;
- commit material benchmark/test results;
- update `docs/DECISION_LOG.md` for architectural changes;
- append/supersede the relevant research trace when evidence changes a project decision.
