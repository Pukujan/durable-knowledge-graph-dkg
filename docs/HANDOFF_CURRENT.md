# Current Handoff

**Date:** 2026-08-09  
**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Current GitHub repository:** `Pukujan/fossil-core`  
**Status:** durable core, pack boundaries, lifecycle, Graphiti adapter, and real Graphiti/Neo4j materialization proof complete; destructive rebuild/blue-green is active.

## Naming and repository family

The durable corpus substrate is **DICS — Durable Intellectual Corpus System**.

The repository family is:

1. `fossil-core` — architecture/contracts/core/projection/control-plane repository;
2. `fossil-common` — shared research and engineering methods, preserving stable pack ID `pack_269099f7b2ba43b7a99b9427d64092de`;
3. `fossil-ai-systems` — AI systems/plugin-harness knowledge, preserving stable pack ID `pack_f024177f89a5442db84171c3dd7f58e5` and depending on the common pack.

Repository names and physical placement are not knowledge identity. Stable `pack_id` values remain authoritative across renames, repository moves, graph namespaces, and future physical shards.

## Fresh-session continuation order

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/PROJECT_STATE.md`
4. this file
5. `docs/implementation/2026-08-09-gate1-live-graphiti-proof.md`
6. `docs/research/2026-08-09-final-research-synthesis.md`
7. `docs/research/2026-08-09-evidence-ledger.md`
8. `docs/research/RESEARCH_TRACE_CONTRACT.md`
9. `docs/DECISION_LOG.md`
10. Issue #1 and active Issue #5

The chat UI is source material, not the control plane.

## Durable architecture that must not be casually changed

The canonical system is immutable evidence + stable corpus IDs + append-only validated knowledge events + versioned pack/ontology contracts + provenance/history. Graphiti/Neo4j, vector indexes, models, Skills, MCP, retrieval strategies, and future databases are replaceable projections/services.

A graph deletion must never delete irreplaceable intellectual history.

## Completed implementation gates

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

### Issue #4 — complete, including real integration

Committed implementation:

- `src/dkg/projection/graphiti.py`;
- `src/dkg/projection/ledger.py`;
- `scripts/live_graphiti_smoke.py`;
- fake-client projection tests;
- optional dependency `graphiti-core==0.29.3`.

The real proof passed in GitHub Actions `DKG contract tests` run #70 (`31338875226`), job `93309155019`.

Proven runtime:

- Graphiti `0.29.3`;
- Neo4j `5.26.29`;
- Ollama OpenAI-compatible provider;
- `deepseek-r1:7b`;
- `nomic-embed-text`, dimension 768;
- ontology `1.0.0`;
- `structured_output_mode=json_schema`.

Durable event `evt_27769393996d2827172f6abc0aa086dc` existed before projection. It appeared as exactly one real Graphiti episode under stable group/pack `pack_269099f7b2ba43b7a99b9427d64092de`, with two mentioned entities. Retrying the event returned `skipped: already applied` and left one episode.

The first live run with `json_object` failed because the local model returned `Edges` instead of Graphiti's required `edges`. The failure was recorded without losing the durable event; the same proof passed when schema-constrained `json_schema` output was used. This is now the reusable live-smoke default.

Full durable evidence: `docs/implementation/2026-08-09-gate1-live-graphiti-proof.md`.

## Exact next task — Issue #5

Implement destructive rebuild and blue/green migration as a normal product capability:

1. preserve the immutable event/artifact layer;
2. destroy the current graph projection;
3. rebuild a fresh projection solely from durable events;
4. verify stable corpus IDs, pack namespaces, provenance, claim/relation state semantics, and build manifests;
5. build candidate projection B beside projection A;
6. compare deterministic semantic/invariant snapshots;
7. change an active-projection pointer only if candidate checks pass;
8. retain enough projection/build history to explain a switch or rollback.

Migration fixtures must exercise concept rename/split/merge, claim supersession, disputed claims, temporal change, and cross-pack references.

Do not make a graph-native node/edge ID part of the comparison contract. Compare durable IDs and semantic invariants instead.

## After #5

Execute:

`#9 conversation lineage benchmark -> #8 Skills/API/MCP -> #7 retrieval/model benchmarks`

Apply #10 citation/source-snapshot/redaction requirements throughout source ingestion.

## External knowledge-pack repositories

The first two external logical knowledge packs are physically present:

1. `fossil-common` — shared/common research + engineering methods;
2. `fossil-ai-systems` — AI systems / plugin-harness knowledge.

They use the same `dkg.pack.v1` contract and the stable pack IDs recorded above. Do not call them physical shards; they may later be placed on separate graph/database shards without changing identity.

## Durable trace

Implementation evidence now includes:

- `docs/implementation/2026-08-09-gate1-core-proof.md`;
- `docs/implementation/2026-08-09-gate1-live-graphiti-proof.md`.

The project research trace is intentionally future corpus material so the knowledge graph can later explain how its own architecture moved from question -> research -> decision -> issue -> code -> test -> failure -> revision -> proof.

## Research status

The broad architecture research is frozen enough to implement. Do not restart broad research because a new library appears. Put new approaches behind existing interfaces and make them win a benchmark.

## End-of-session rule

Update this file, `docs/PROJECT_STATE.md`, Issue #1, active child issues, durable benchmark evidence, and decision/research traces after substantial changes.
