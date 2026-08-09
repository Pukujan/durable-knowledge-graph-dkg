# Gate 1 Destructive Rebuild + Blue/Green Proof

Date: 2026-08-09  
Issue: #5 — Destructive rebuild + blue/green migration harness

This checkpoint records the first real proof that FOSSIL can destroy a replaceable Graphiti/Neo4j projection, rebuild it from durable events, compare a candidate beside the current projection, and switch active projection only after deterministic checks pass.

## Result

**PASS.** The durable event layer survived graph destruction, a fresh candidate projection rebuilt from the same immutable event source, current and candidate projections coexisted during comparison, their projection-independent semantic digests matched the durable source exactly, and the active projection switch was recorded only after all checks passed.

## Durable implementation

Issue #5 introduced:

- `src/dkg/projection/migration.py`
  - deterministic durable replay ordering by `(recorded_at, event_id)`;
  - `SemanticSnapshot` excluding graph-native IDs;
  - semantic comparison of event inventory, pack namespaces, provenance, claim state, relation state, and event-type counts;
  - named migration benchmark results;
  - destructive rebuild orchestration;
  - append-only active-projection switch history;
  - rejection of stale switch proposals once an active slot is recorded.
- `src/dkg/projection/ledger.py`
  - optional build-scoped projection ledgers so a destroyed graph never inherits stale `already applied` markers from an earlier physical build.
- `src/dkg/projection/graphiti.py`
  - rebuild replay in durable commit order rather than filesystem/hash-path order.
- `tests/test_projection_migration.py`
  - deterministic migration fixtures and guardrail coverage.

## Critical rebuild invariant discovered

A projection ledger cannot be reused blindly across destructive graph replacement.

If Neo4j is deleted while the old applied ledger is retained as the ledger for the new physical build, every durable event can incorrectly appear to be `already applied`. The rebuild may then skip all events and silently produce an empty graph.

FOSSIL therefore scopes applied/failure markers to a **projection build identity** for destructive rebuilds and candidate projections. Historical build ledgers remain available for explanation, but a fresh physical projection build receives a fresh build-scoped applied ledger.

## Deterministic migration fixture coverage

The unit migration fixture exercises the semantic cases required by Issue #5:

- concept rename;
- concept split;
- concept merge;
- claim supersession;
- long-lived disputed claim state;
- dependent-claim staleness after premise supersession;
- temporal difference between `occurred_at` and later corpus `recorded_at`;
- cross-pack references from the AI-systems pack to the common pack;
- claim and relation state reconstruction;
- namespace boundaries and provenance comparison;
- switch rejection on semantic mismatch;
- switch rejection on benchmark failure;
- stale source-slot switch rejection.

Replay order is based on durable corpus `recorded_at`, with `event_id` as deterministic tie breaker. `occurred_at` remains the represented real-world/intellectual time and must not reorder later corpus commits during state reconstruction.

## Unit proof

Trusted GitHub Actions `DKG contract tests` run #80:

- run ID: `31339804323`
- job ID: `93311606836`
- result: **25 passed in 0.65s**

After adding stale active-slot protection, final trusted CI run #84:

- run ID: `31340381436`
- job ID: `93313061964`
- result: **26 passed in 0.44s**

The final guard prevents a stale migration proposal such as `blue -> red` from writing a new active switch after the ledger has already recorded `blue -> green`.

## Real two-projection proof

The physical proof ran through disposable execution-only PR #19 using the ordinary trusted CI workflow. The branch-only live test is intentionally not product code and must not be merged.

Workflow evidence:

- workflow: `DKG contract tests`
- run number: **81**
- run ID: `31339930551`
- job ID: `93311926075`
- proof CI merge SHA: `8ebab724010eb7b215fdf4d0f24d13e43c22a59e`
- final result: **26 passed, 1 warning in 420.21s**

The warning was an upstream Graphiti/Pydantic deprecation warning and did not affect the proof.

## Real runtime/build manifest

```json
{
  "graphiti_version": "0.29.3",
  "neo4j_version": "5.26.29",
  "llm_provider": "ollama-openai-compatible",
  "model_id": "qwen2.5:3b",
  "embedding_model_id": "nomic-embed-text",
  "embedding_dim": 768,
  "structured_output_mode": "json_schema",
  "ontology_version": "1.0.0",
  "software_commit": "8ebab724010eb7b215fdf4d0f24d13e43c22a59e"
}
```

`qwen2.5:3b` successfully completed this **small migration smoke input** under schema-constrained output. That is not a blanket model-quality endorsement and does not replace later retrieval/extraction benchmarks.

## Durable event used by the live rebuild

Event:

`evt_aadf683e9aa41443f95be71c211cd2c4`

Stable pack/group:

`pack_269099f7b2ba43b7a99b9427d64092de`

The event was committed to `DurableEventStore` before either graph projection was trusted. The same immutable event source was then used for both blue and green.

## Blue/current projection A

Blue was materialized first and remained live while green was destroyed and rebuilt.

- projection build ID: `blue-build-1`
- Neo4j: `5.26.29`
- graph node count: **3**
- semantic digest: `c8d790b3a1d6741a86e280db44595b463347e6c47a4d933274e1c829696e4696`

The node count remained **3** after the green rebuild, proving the current projection was still present beside the candidate during the migration proof.

## Green/candidate projection B destructive reset

Before destructive reset, green received an explicit sentinel node:

- sentinel/node count before destructive reset: **1**

The candidate graph was then destroyed with a real Neo4j `MATCH (n) DETACH DELETE n` operation:

- green node count immediately after destroy: **0**
- durable event still readable: **true**
- durable event file still existed: **true**

The replacement build used a fresh build-scoped projection ledger:

`green-rebuild-1`

This is the condition that prevents stale applied markers from suppressing rebuild work.

## Green rebuild result

Rebuild from the same durable event source produced:

- rebuild receipts: `["applied"]`
- green node count after rebuild: **3**
- stable pack namespace preserved: **true**
- semantic digest: `c8d790b3a1d6741a86e280db44595b463347e6c47a4d933274e1c829696e4696`

The event was **applied**, not skipped, which directly proves the fresh build ledger worked as intended after physical graph loss.

## Projection-independent comparison

Expected durable digest:

`c8d790b3a1d6741a86e280db44595b463347e6c47a4d933274e1c829696e4696`

Blue digest:

`c8d790b3a1d6741a86e280db44595b463347e6c47a4d933274e1c829696e4696`

Green digest:

`c8d790b3a1d6741a86e280db44595b463347e6c47a4d933274e1c829696e4696`

Mismatches: **none**.

Named live checks all passed:

```json
{
  "blue_matches_durable": true,
  "durable_event_survived_graph_destruction": true,
  "green_destroyed_before_rebuild": true,
  "green_matches_durable": true,
  "namespace_preserved": true
}
```

The comparison deliberately excludes Neo4j/Graphiti-generated node and edge UUIDs. Stable FOSSIL event/pack/claim/relation identities and semantic state are the migration contract.

## Active switch evidence

Only after the comparison and named checks passed did the harness write an append-only switch record:

- switch ID: `switch_1e200eb87701403d83f43e9fd0a6bc17`
- from: `blue`
- to: `green`
- expected semantic digest: matched
- candidate semantic digest: matched
- mismatches: none
- candidate build manifest retained: yes

The permanent switch ledger additionally rejects later stale switch proposals whose `from_slot` no longer equals the recorded active slot.

## Scope boundary

The **live** proof validates physical graph destruction/rebuild, simultaneous blue/green operation, stable namespace/event reconstruction, build identity, semantic digest comparison, and guarded activation using a small real Graphiti input.

The more complex ontology/lifecycle/cross-pack migration fixtures are exercised deterministically in the unit migration suite rather than all being delegated to LLM extraction during this live smoke. That distinction is intentional: stable FOSSIL semantics are tested deterministically, while Graphiti remains a replaceable materialized projection.

## Gate conclusion

Issue #5 conditions are satisfied:

1. Neo4j data can be destroyed while durable FOSSIL history survives.
2. A fresh physical projection can replay the durable event source rather than inherit stale applied markers.
3. Stable corpus semantics and namespaces survive rebuild.
4. Candidate B can coexist beside current projection A.
5. Projection comparisons use durable semantic invariants, not graph-native IDs.
6. Claim/relation/ontology/cross-pack migration fixtures are present.
7. Build manifests and projection build IDs are retained.
8. Active selection changes only after checks pass.
9. Append-only switch history supports explanation/rollback and rejects stale source-slot transitions.

The next Gate 1 task is Issue #9: conversation ingestion and intellectual-lineage reconstruction benchmark.
