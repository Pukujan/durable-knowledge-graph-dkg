# Project State

**Current phase:** Gate 1 durable executable proof — core durable layer complete; live Graphiti integration next  
**Control plane:** GitHub issues + durable repository docs  
**Last updated:** 2026-08-09

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
10. [ ] pass a live Graphiti + Neo4j integration smoke test;
11. [ ] destroy/rebuild the graph from durable data;
12. [ ] build and compare a second candidate projection;
13. [ ] answer conversation lineage/reconstruction benchmarks;
14. [ ] resolve citations/provenance to intended evidence snapshots;
15. [ ] expose the safe Agent Skill/API boundary.

## Current issue map

- #1 Milestone-control issue — open
- #2 Durable event + artifact store — **complete**
- #3 Knowledge-pack boundaries, mounts, promotion — **complete**
- #4 Graphiti + Neo4j projection adapter/queue — adapter complete; **live integration pending**
- #5 Destructive rebuild + blue/green migration harness — pending
- #6 Claim/relation lifecycle, disagreement, supersession, staleness — **complete**
- #7 Pluggable retrieval/model services + local-specialist benchmark contract — pending
- #8 Agent Skills + thin corpus API/MCP contract — pending
- #9 Conversation ingestion + intellectual-lineage reconstruction benchmark — pending
- #10 Source snapshots, citation provenance, quality dimensions, redaction path — cross-cutting/pending

## Recommended execution order from here

`#4 live integration -> #5 -> #9 -> #8 -> #7`, while applying #10 requirements during source ingestion.

## Immediate next task

Finish **Issue #4** with a real local Graphiti/Neo4j smoke test. The unit adapter is already committed. The remaining proof must:

1. start Neo4j 5.26+;
2. install/use the pinned optional `graphiti-core==0.29.3` projection dependency;
3. initialize Graphiti indices/constraints;
4. commit a durable DKG event first;
5. project that accepted event through `GraphitiProjectionAdapter`;
6. verify it lands under the expected `pack_id` / Graphiti `group_id` namespace;
7. record the real Graphiti/Neo4j/model/ontology/code versions used.

Do not close #4 from mocked tests alone.

Then execute **Issue #5**: destroy the graph, rebuild from durable events, build a candidate projection beside the first, compare semantic invariants, and switch only after it passes.

## Knowledge repository split

Future Git repositories are **knowledge-pack repositories**, not database shards.

Issue #3 has now passed, so the first two external pack repositories can be created when desired:

1. a shared/common knowledge pack;
2. an AI-systems/plugin-harness knowledge pack.

Each should use the existing `dkg.pack.v1` contract and preserve its stable `pack_id`. Repository location, Graphiti namespace, and future physical database placement are operational details rather than identity.

## Current implementation evidence

- `src/dkg/io.py` — atomic immutable publication.
- `src/dkg/event_store.py` — validated, deterministic idempotent durable events.
- `src/dkg/artifact_store.py` — SHA-256 content-addressed evidence and verification.
- `src/dkg/pack.py` — pack validation and read/write boundaries.
- `src/dkg/promotion.py` — explicit cross-pack promotion event.
- `src/dkg/lifecycle.py` — event-replay claim/relation lifecycle and stale propagation.
- `src/dkg/projection/ledger.py` — retry/failure/applied projection ledger.
- `src/dkg/projection/graphiti.py` — isolated Graphiti/Neo4j projection adapter.
- `docs/implementation/2026-08-09-gate1-core-proof.md` — durable implementation checkpoint.

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
