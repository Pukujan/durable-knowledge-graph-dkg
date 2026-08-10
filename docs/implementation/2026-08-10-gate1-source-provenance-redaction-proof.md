# Gate 1 Source Provenance + Redaction Proof

**Date:** 2026-08-10  
**Issue:** #10  
**Result:** passed

## Contract implemented

FOSSIL now preserves source observations independently of mutable URLs and projections:

- immutable source snapshots carry a stable `source_id`, source locator/identifier, retrieval time, optional publication time, content hash, version metadata, and source role;
- multiple snapshots of the same mutable source can coexist historically;
- source quality is represented as independent dimensions (`authority`, `directness`, `independence`, `reproducibility`, `timeliness`) rather than one universal tier;
- citations resolve to an immutable snapshot/artifact and optionally an exact byte span with its own SHA-256 passage hash;
- derived/reconstructed snapshots require explicit parent snapshot provenance;
- citation role checks prevent a derived summary from masquerading as a primary source;
- source lifecycle is explicit durable data through `source.stale`, `source.retracted`, and `source.restored` events.

Implementation:

- `schemas/source-snapshot/v1.schema.json`
- `schemas/citation/v1.schema.json`
- `src/dkg/source.py`
- `tests/test_source_provenance.py`

## Exceptional redaction path

Normal intellectual history remains append-only. Privacy/legal erasure is deliberately separate from ordinary revision.

### Evidence/artifact redaction

`ArtifactStore.redact(...)` publishes a minimal immutable tombstone before deleting the content-addressed blob. The manifest/hash identity survives for audit, while the erased bytes cannot be read or silently rehydrated under the same content identity.

### Durable event redaction

If sensitive text has been copied into a canonical durable event, deleting only its evidence blob is insufficient. `DurableEventStore.redact(...)` therefore:

1. publishes a minimal immutable event tombstone;
2. records stable event ID, pack ID, event type, recorded time, canonical SHA-256, authority/reason/request reference;
3. intentionally does **not** copy payload, subjects, evidence refs, or provenance into the tombstone;
4. physically deletes the canonical event bytes only after the tombstone exists;
5. rejects publication of the same redacted deterministic event identity later.

`DurableEventStore.iter_redactions()` makes these minimal tombstones available to projection cleanup after restart without recovering the deleted payload.

Implementation/tests:

- `src/dkg/artifact_store.py`
- `src/dkg/event_store.py`
- `tests/test_event_redaction.py`

## Projection/export behavior

`RedactionPolicy` suppresses events whose evidence/source snapshots are redacted. Exports return redaction state rather than the deleted bytes.

Graphiti projection applied receipts now retain the actual Graphiti episode UUID when available. Projection redaction is a separate append-only operational receipt; the earlier applied record is preserved for audit.

`GraphitiProjectionAdapter` supports:

- source/evidence visibility filtering during apply/rebuild;
- active `remove_episode` purge for an already-materialized hidden event;
- `purge_event_redactions_async(event_store=...)`, which can recover after a crash between canonical event erasure and projection cleanup by joining the stable event tombstone to the build-scoped applied ledger;
- fresh rebuilds that cannot resurrect physically erased canonical events because those events are absent from the durable replay source.

No graph-native UUID is promoted to canonical FOSSIL identity; the episode UUID is only an operational deletion handle for a particular projection build.

## Deterministic contract proof

Trusted GitHub Actions run `31345462801`, job `93326450028` passed the finalized source/citation/redaction suite:

**51 passed in 1.40s**

The suite proves mutable snapshot coexistence, exact passage hashing, anti-laundering source roles, quality dimensions, source lifecycle replay, artifact tombstone-before-delete behavior, durable-event tombstone-before-delete behavior, non-resurrection, export filtering, active projection purge behavior, and tombstone-based crash/restart cleanup.

## Real Graphiti + Neo4j redaction proof

Trusted GitHub Actions run `31346791333`, live job `93330095684` executed the real stack:

- Graphiti `0.29.3`
- Neo4j `5.26.29`
- local Ollama OpenAI-compatible provider
- `qwen2.5:3b`
- `nomic-embed-text`
- structured output `json_schema`
- stable AI-systems namespace `pack_f024177f89a5442db84171c3dd7f58e5`

Proof event:

`evt_416e5c516581c8dea8c5c54025361960`

Graphiti episode UUID for this projection build:

`4355c63d-4e88-481a-9f13-a5668bf30e76`

Before redaction the pack contained exactly:

- 1 matching Graphiti episode;
- 1 pack-local entity;
- 0 fact edges for this deliberately tiny fixture.

The canonical event was then redacted behind a minimal tombstone. Its canonical hash is:

`9e31b2d452efbd790bc7152538285fc369c2d22183015f5dc4c41fcb415b7fc1`

Observed proof after active purge:

- episode count: **0**;
- entity count: **0**;
- fact-edge count: **0**;
- projection receipt: `redacted` / `Graphiti episode removed`;
- canonical event bytes deleted: **true**;
- same event identity republication blocked: **true**.

A fresh projection build then replayed the canonical event source. It produced **zero rebuild receipts** and the pack remained at zero episode/entity/fact records. The redacted event did not resurrect.

Proof artifact:

- GitHub Actions artifact ID `9047631921`;
- uploaded artifact ZIP SHA-256 `cf9d58ac4b22be4da59b3ac02bb8fb07308c7c84fd2495ab06ba732d421169d9`.

## Workflow reliability fix discovered during the gate

The standalone Graphiti workflow previously failed to register runs because `${{ runner.temp }}` had been referenced in job-level `env`, where the runner context is not available. The permanent `.github/workflows/graphiti-live.yml` now puts runner-dependent proof paths at step scope and includes both the ordinary live Graphiti proof and the redaction/non-resurrection smoke.

## Gate result

Issue #10 acceptance is satisfied. Gate 1 can now treat source snapshot/citation provenance and the minimal redaction/tombstone path as executable, tested contracts.

Frozen redaction invariants:

1. ordinary knowledge revision remains append-only;
2. privacy/legal erasure is an explicit exceptional operation;
3. a non-sensitive immutable tombstone must exist before physical bytes are removed;
4. erased content/event identities cannot silently resurrect;
5. active projections and exports must respect redaction state;
6. historical projection-applied receipts remain audit history while redaction is recorded separately;
7. crash/restart must not strand erased canonical knowledge in an active projection;
8. fresh rebuilds cannot recover data whose canonical bytes were intentionally erased.
