# Current Handoff

**Date:** 2026-08-09  
**Repository:** `Pukujan/durable-knowledge-graph-dkg`  
**Status:** research frozen; durable event/artifact, pack-boundary, promotion, and lifecycle layers implemented; Graphiti adapter implemented; live Neo4j/Graphiti proof is next.

## Fresh-session continuation order

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/PROJECT_STATE.md`
4. this file
5. `docs/research/2026-08-09-final-research-synthesis.md`
6. `docs/research/2026-08-09-evidence-ledger.md`
7. `docs/research/RESEARCH_TRACE_CONTRACT.md`
8. `docs/DECISION_LOG.md`
9. Issue #1 and active Issue #4

The chat UI is source material, not the control plane.

## Durable architecture that must not be casually changed

The canonical system is immutable evidence + stable corpus IDs + append-only validated knowledge events + versioned pack/ontology contracts + provenance/history. Graphiti/Neo4j, vector indexes, models, Skills, MCP, retrieval strategies, and future databases are replaceable projections/services.

A graph deletion must never delete irreplaceable intellectual history.

## Work completed in the latest implementation pass

### Issue #2 — complete

- atomic immutable publication primitive;
- hardened event-store idempotency identity;
- content-addressed SHA-256 artifact store;
- artifact verification/tamper detection tests;
- invalid/duplicate event tests.

### Issue #3 — complete

- explicit pack read mounts and write targets;
- required dependency validation;
- cross-pack boundary tests;
- explicit `knowledge.promoted` event with source-pack provenance;
- logical pack identity remains separate from repository/database placement.

### Issue #6 — complete

- event-replay claim state;
- event-replay relation state;
- long-lived `disputed` state;
- relation state history;
- support/challenge/contradiction/refinement/dependency relations;
- superseded premises mark active dependents `stale_pending_review` instead of silently rewriting them.

### Issue #4 — partially complete

Committed:

- `src/dkg/projection/graphiti.py`;
- `src/dkg/projection/ledger.py`;
- fake-client projection tests;
- Graphiti pinned as optional `graphiti-core==0.29.3` dependency.

Behavior already proved in unit tests:

- `pack_id` maps directly to Graphiti `group_id`;
- already-applied events are skipped on retry;
- failed projection attempts are recorded without losing the durable event;
- successful projection records build-manifest versions.

Do **not** close #4 yet. A real Neo4j + Graphiti run is still required.

## Exact next task

Finish Issue #4 with a live local integration:

1. start Neo4j 5.26+;
2. install the project with the `graphiti` optional dependency;
3. supply the configured Graphiti LLM/embedding provider credentials or a proven local provider;
4. initialize Graphiti indices/constraints;
5. commit a durable event before projection;
6. run it through `GraphitiProjectionAdapter`;
7. verify the expected Graphiti namespace/group contains the projected episode/facts;
8. record real runtime/model/ontology/code versions in a durable implementation checkpoint;
9. rerun the event and prove no duplicate projection occurs.

The current execution environment used by ChatGPT does not contain Docker, so mocked adapter tests were run here but the live Neo4j gate was deliberately left open rather than falsely marked complete.

## After #4

Execute:

`#5 destructive rebuild/blue-green -> #9 conversation lineage benchmark -> #8 Skills/API/MCP -> #7 retrieval/model benchmarks`

Apply #10 citation/source-snapshot/redaction requirements throughout source ingestion.

## External knowledge-pack repositories

Issue #3 has passed. It is now safe to create the first two external logical knowledge packs:

1. shared/common research + engineering methods;
2. AI systems / plugin-harness knowledge.

They should use the same `dkg.pack.v1` contract and stable pack IDs. Do not call them physical shards; they may later be placed on separate graph/database shards without changing identity.

## Durable trace of this implementation pass

Read `docs/implementation/2026-08-09-gate1-core-proof.md` for the implementation-evidence checkpoint. The project research trace is intentionally future corpus material so the knowledge graph can later explain how its own architecture moved from question -> research -> decision -> issue -> code -> test -> revision.

## Research status

The 127-source research pass is frozen enough to implement. Current Graphiti primary documentation confirms namespaced ingestion through `group_id`, JSON episodes, and Neo4j 5.26+ support. Graphiti 0.29.3 was the latest release observed during the adapter implementation pass.

Do not restart broad research because a new library appears. Put new approaches behind existing interfaces and make them win a benchmark.

## End-of-session rule

Update this file, `docs/PROJECT_STATE.md`, Issue #1, active child issues, durable benchmark evidence, and decision/research traces after substantial changes.
