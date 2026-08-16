# FOSSIL modularization Phase 0 baseline

Status: implementation baseline for #82 under architecture authority #81 and #86.

This document freezes the dependency direction and migration rules before any structural package move. It does not change runtime behavior, storage semantics, identifiers, schemas, hashes, provider selection, or acceptance criteria.

## Current package baseline

`src/fossil_core/` is still predominantly a flat package. The first storage seam already exists, but its components are top-level modules:

- `storage_ports.py` — provider-neutral storage Protocols.
- `artifact_store.py` — filesystem/local artifact implementation and current concrete public export.
- `event_store.py` — filesystem/local durable event implementation and current concrete public export.
- `s3_storage.py` — S3-compatible artifact/event adapter.
- `projection/` — the main existing bounded subpackage.

The package root currently declares an explicit `__all__` surface. Phase 0 records that list as the **declared compatibility baseline**, not as a decision that every current concrete export must remain permanent. Direct submodule imports that exist today are migration inputs and must not be broken accidentally during the bounded refactor.

Run the mechanical inventory with:

```bash
python scripts/architecture_inventory.py --pretty
```

The command parses source with the Python AST and does not import or execute `fossil_core`. It reports:

- every Python module under `src/fossil_core`;
- first-party `fossil_core` import edges; and
- the package-root `__all__` declaration.

The output is deterministic so two revisions can be compared mechanically during migration.

## Target dependency direction

The modular monolith target is:

```text
domain        -> no adapters/providers/runtime infrastructure
ports         -> stable interfaces and types around domain/application capabilities
application   -> orchestrates domain through ports, not concrete providers
adapters      -> implements ports (filesystem, S3, Graphiti, Neo4j, vector, etc.)
api/config    -> composition and wiring; never durable semantic authority
```

Allowed direction is inward toward domain/contracts. Provider dependencies stay at the adapter/composition edge.

The following are architectural violations once the corresponding bounded packages exist:

1. `domain -> adapters` imports.
2. `domain -> provider SDK` imports.
3. application code importing a concrete provider when an established port exists.
4. provider-specific configuration changing durable identities, event schemas, canonical hashes, lifecycle semantics, redaction semantics, or rebuild truth.
5. circular dependencies introduced to preserve an old flat import path.

## Migration invariants

Every package-move PR must satisfy all of the following:

1. **Behavior freeze.** A move is not a feature change.
2. **One bounded responsibility per PR.** No repository-wide mega-restructure.
3. **Compatibility first.** Old supported paths remain thin forwarding imports until consumers migrate.
4. **Stable durable truth.** IDs, canonical bytes/hashes, schemas, event ordering, provenance, lifecycle, redaction, conflict, and rebuild semantics remain unchanged.
5. **Provider neutrality.** R2 remains a live S3-compatible candidate, not domain truth.
6. **Exact-head verification.** Focused tests, the full deterministic suite, and required hosted gates remain at least as strict as before the move.
7. **No architecture theater.** Do not create empty target directories in advance of moving a real responsibility.

## First implementation slice after Phase 0

Storage is the first bounded move because the provider-neutral seam and live proof already exist. The approximate target is:

```text
fossil_core/
  ports/
    artifact_store.py
    event_store.py
  adapters/
    filesystem/
    s3/
```

The move order is deliberately narrow:

1. place the existing storage port definitions behind bounded `ports` paths without semantic changes;
2. retain compatibility imports from `fossil_core.storage_ports`;
3. move filesystem implementations behind `adapters/filesystem` while keeping supported compatibility paths;
4. move the S3-compatible implementation behind `adapters/s3`;
5. run the same storage contract suite against filesystem and S3 implementations;
6. only after the imports are stable, add CI enforcement for dependency direction.

No storage provider, production topology, microservice split, ContextProvider policy, or retrieval policy decision is part of that slice.

## Public API policy during migration

Until a later Phase 3 API reduction is explicitly approved:

- the current package-root `__all__` is treated as a compatibility baseline;
- removing or renaming an existing root export requires an explicit migration/deprecation decision;
- new internal bounded paths do not automatically become permanent public API;
- first-party consumers should migrate toward capability/contract imports rather than provider implementation details;
- compatibility shims are temporary and tested, with removal handled in an explicit cleanup phase.

## Phase 0 exit criteria

Phase 0 is complete when:

- the deterministic inventory tool is green in the normal test suite;
- the current declared root API is mechanically recorded;
- dependency direction and migration invariants are documented;
- no runtime behavior or package path has moved; and
- the next PR can perform the first storage port/adapter move with a small, reviewable diff.
