# Current Handoff

**Date:** 2026-08-09  
**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Current GitHub repository:** `Pukujan/fossil-core`  
**Status:** durable core, pack boundaries, lifecycle, real Graphiti/Neo4j materialization, and destructive rebuild/blue-green migration are complete; conversation ingestion/intellectual-lineage reconstruction is active.

## Naming and repository family

The durable corpus substrate is **DICS — Durable Intellectual Corpus System**.

The repository family is:

1. `fossil-core` — architecture/contracts/core/projection/control-plane repository;
2. `fossil-common` — shared research and engineering methods, stable pack ID `pack_269099f7b2ba43b7a99b9427d64092de`;
3. `fossil-ai-systems` — AI systems/plugin-harness knowledge, stable pack ID `pack_f024177f89a5442db84171c3dd7f58e5`, depending on the common pack.

Repository names and physical placement are not knowledge identity. Stable `pack_id` values remain authoritative across renames, repository moves, graph namespaces, and future physical shards.

## Fresh-session continuation order

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/PROJECT_STATE.md`
4. this file
5. `docs/implementation/2026-08-09-gate1-live-graphiti-proof.md`
6. `docs/implementation/2026-08-09-gate1-rebuild-blue-green-proof.md`
7. `docs/recovery/2026-08-09-chat-recovery-checkpoint.md`
8. `docs/research/RESEARCH_TRACE_CONTRACT.md`
9. `docs/DECISION_LOG.md`
10. Issue #1 and active Issue #9

The chat UI is source material, not the project control plane.

## Durable architecture that must not be casually changed

The canonical system is immutable evidence + stable corpus IDs + append-only validated knowledge events + versioned pack/ontology contracts + provenance/history. Graphiti/Neo4j, vector indexes, models, Skills, MCP, retrieval strategies, and future databases are replaceable projections/services.

A graph deletion must never delete irreplaceable intellectual history.

## Completed implementation gates

### Issue #2 — complete

- atomic immutable publication;
- deterministic event idempotency;
- content-addressed artifact store;
- integrity/tamper checks.

### Issue #3 — complete

- pack read/write boundaries;
- required dependencies;
- explicit provenance-preserving promotion;
- logical pack identity independent of physical placement.

### Issue #6 — complete

- claim/relation replay;
- disputed state;
- support/challenge/contradiction/refinement/dependency relations;
- supersession and stale dependent propagation.

### Issue #4 — complete, including real Graphiti/Neo4j integration

Trusted CI run #70 (`31338875226`, job `93309155019`) proved:

- Graphiti `0.29.3` + Neo4j `5.26.29`;
- local Ollama `deepseek-r1:7b` + `nomic-embed-text`;
- `structured_output_mode=json_schema`;
- durable event existed before projection;
- exactly one real Graphiti episode under the stable `pack_id`/`group_id`;
- two entities extracted in the smoke input;
- retry returned `skipped: already applied` and did not duplicate the episode;
- a prior malformed-model run was recorded as projection failure without losing canonical durable knowledge.

Evidence: `docs/implementation/2026-08-09-gate1-live-graphiti-proof.md`.

### Issue #5 — complete, including real destructive rebuild + blue/green

Permanent implementation:

- `src/dkg/projection/migration.py`;
- build-scoped projection ledgers in `src/dkg/projection/ledger.py`;
- durable `(recorded_at, event_id)` rebuild ordering in `src/dkg/projection/graphiti.py`;
- `tests/test_projection_migration.py`.

Critical invariant: **a physically new/rebuilt projection must use a fresh projection build identity/applied ledger.** Reusing an old applied ledger after deleting Neo4j can cause every event to be incorrectly skipped and yield an empty graph.

Semantic migration comparison deliberately excludes Graphiti/Neo4j-native UUIDs. It compares stable FOSSIL event IDs, pack namespaces, provenance, claim/relation state, and event inventory.

Trusted real proof run #81 (`31339930551`, job `93311926075`) used two independent Neo4j `5.26.29` instances plus Graphiti `0.29.3`, local Ollama `qwen2.5:3b`, `nomic-embed-text`, and `json_schema` structured output.

Durable event `evt_aadf683e9aa41443f95be71c211cd2c4` existed first. Blue/current held 3 nodes while green/candidate was deliberately seeded, destroyed to **0 nodes**, then rebuilt from the same immutable event source with fresh build ledger `green-rebuild-1` and returned to **3 nodes** with an `applied` receipt.

Expected durable, blue, and green semantic digests matched exactly:

`c8d790b3a1d6741a86e280db44595b463347e6c47a4d933274e1c829696e4696`

The append-only switch `blue -> green` was written only after every check passed. Final trusted unit run #84 (`31340381436`, job `93313061964`) passed **26 tests in 0.44s**, including rejection of stale source-slot switch proposals.

Evidence: `docs/implementation/2026-08-09-gate1-rebuild-blue-green-proof.md`.

## Exact next task — Issue #9

Use the recovered long conversation/history-loss incident as the first difficult lineage benchmark **without pretending reconstructed material is verbatim**.

Required implementation direction:

1. introduce a durable conversation envelope with stable conversation and message identities;
2. each source segment/message must carry explicit evidence status such as `verbatim` or `reconstructed`;
3. raw/verbatim text, when actually available, belongs in immutable evidence/artifacts rather than only in a derived summary;
4. preserve message order and parent/reply relationships;
5. retain actor, model/provider, tool/run, timestamp, and source-span metadata when available without inventing missing values;
6. derived claims/challenges/rebuttals/assumptions/conclusions/position changes must point back to source message/span IDs;
7. opposing positions remain separately addressable rather than collapsed into a consensus sentence;
8. current conclusion and historical path must both be queryable;
9. benchmark the required path:
   `parabola/learning UX -> representation mismatch -> AI translation layer -> failure learning -> MAPE-K/KEDB -> truth maintenance -> temporal knowledge graph`;
10. the recovery checkpoint must remain labeled reconstruction and must never silently become a verbatim transcript.

Issue #9 acceptance also requires citations to resolve to source artifacts/spans where available. Apply #10 provenance/source-snapshot requirements while building this rather than postponing them entirely.

## Migration invariants now frozen

- new physical projection build => fresh build-scoped applied ledger;
- replay order => `(recorded_at, event_id)`;
- semantic comparison => durable identities/state, never graph UUID equality;
- candidate activation => append-only switch only after semantic/benchmark checks;
- recorded active slot => later stale `from_slot` proposals rejected.

## After #9

Execute:

`#8 Skills/API/MCP -> #7 retrieval/model benchmarks`

Continue #10 citation/source-snapshot/redaction requirements throughout ingestion.

## External knowledge-pack repositories

The first two external logical knowledge packs are physically present:

1. `fossil-common` — shared/common research + engineering methods;
2. `fossil-ai-systems` — AI systems/plugin-harness knowledge.

They use the same `dkg.pack.v1` contract and stable pack IDs recorded above. Do not call them physical shards.

## Durable trace

Implementation evidence now includes:

- `docs/implementation/2026-08-09-gate1-core-proof.md`;
- `docs/implementation/2026-08-09-gate1-live-graphiti-proof.md`;
- `docs/implementation/2026-08-09-gate1-rebuild-blue-green-proof.md`.

The project research/conversation trace is intentionally future corpus material so FOSSIL can explain how architecture moved from question -> research -> opposing claims -> decision -> issue -> code -> runtime failure -> revision -> proof.

## Research status

The broad architecture research is frozen enough to implement. Do not restart broad research because a new library appears. Put new approaches behind existing interfaces and make them win a benchmark.

## End-of-session rule

Update this file, `docs/PROJECT_STATE.md`, Issue #1, active child issues, durable benchmark evidence, and decision/research traces after substantial changes.
