# Project State

**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Durable substrate:** **DICS — Durable Intellectual Corpus System**
**Current phase:** Gate 1 executable durability proof — live Graphiti/Neo4j materialization complete; destructive rebuild/blue-green next  
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
5. `docs/research/2026-08-09-final-research-synthesis.md`
6. `docs/research/RESEARCH_TRACE_CONTRACT.md`
7. `docs/DECISION_LOG.md`
8. Issue #1 and the active child issue

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
11. [ ] destroy/rebuild the graph from durable data;
12. [ ] build and compare a second candidate projection;
13. [ ] answer conversation lineage/reconstruction benchmarks;
14. [ ] resolve citations/provenance to intended evidence snapshots;
15. [ ] expose the safe Agent Skill/API boundary.

## Live projection proof

Issue #4 crossed the real integration gate in GitHub Actions run #70 (`31338875226`). The proof used Graphiti `0.29.3`, Neo4j `5.26.29`, local Ollama `deepseek-r1:7b`, `nomic-embed-text`, and `structured_output_mode=json_schema`.

The durable event `evt_27769393996d2827172f6abc0aa086dc` existed before projection. A real Graphiti `Episodic` node was observed exactly once under `group_id == pack_269099f7b2ba43b7a99b9427d64092de`, with two mentioned entities. Replaying the same event returned `skipped: already applied` and the episode count remained exactly one.

The first real attempt with `json_object` failed because the local model emitted `Edges` instead of the required `edges`; the projection ledger recorded the failure and the durable event remained intact. The successful retry used schema-constrained output. See `docs/implementation/2026-08-09-gate1-live-graphiti-proof.md`.

## Current issue map

- #1 Milestone-control issue — open
- #2 Durable event + artifact store — **complete**
- #3 Knowledge-pack boundaries, mounts, promotion — **complete**
- #4 Graphiti + Neo4j projection adapter/queue — **complete**
- #5 Destructive rebuild + blue/green migration harness — **active**
- #6 Claim/relation lifecycle, disagreement, supersession, staleness — **complete**
- #7 Pluggable retrieval/model services + local-specialist benchmark contract — pending
- #8 Agent Skills + thin corpus API/MCP contract — pending
- #9 Conversation ingestion + intellectual-lineage reconstruction benchmark — pending
- #10 Source snapshots, citation provenance, quality dimensions, redaction path — cross-cutting/pending

## Recommended execution order from here

`#5 destructive rebuild/blue-green -> #9 conversation lineage benchmark -> #8 Skills/API/MCP -> #7 retrieval/model benchmarks`, while applying #10 requirements during source ingestion.

## Immediate next task

Execute **Issue #5** without weakening the durability invariant:

1. destroy a Graphiti/Neo4j projection while retaining the immutable FOSSIL event/artifact layer;
2. rebuild the projection entirely from durable events;
3. verify stable corpus IDs, pack namespaces, provenance, claim/relation state invariants, and build manifests after rebuild;
4. build candidate projection B beside current projection A;
5. compare A/B with deterministic semantic checks and reconstruction benchmarks;
6. switch the active projection pointer only after candidate checks pass;
7. keep enough build metadata to explain and reproduce the switch.

Migration fixtures must include concept rename/split/merge, claim supersession, disputed claims, temporal change, and cross-pack references.

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
- `src/dkg/projection/ledger.py` — retry/failure/applied projection ledger.
- `src/dkg/projection/graphiti.py` — isolated Graphiti/Neo4j projection adapter.
- `scripts/live_graphiti_smoke.py` — reusable real Graphiti/Neo4j proof runner.
- `docs/implementation/2026-08-09-gate1-core-proof.md` — durable-core checkpoint.
- `docs/implementation/2026-08-09-gate1-live-graphiti-proof.md` — real projection checkpoint.

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
