# FOSSIL Python public API

Status: Phase 3 public-API contract for #82 under architecture authority #81 and #86.

The machine-readable source of truth is [`contracts/python-public-api-v1.json`](../../contracts/python-public-api-v1.json). Tests must fail if the declared imports, `__all__` surfaces, or compatibility aliases drift from that contract.

## Supported package-root API

The small package-root surface remains supported during modularization:

```python
from fossil_core import (
    ArtifactIntegrityError,
    ArtifactStore,
    DurableEventStore,
    IdempotencyConflict,
    KnowledgeState,
    LifecycleError,
    RelationRecord,
    KnowledgePackValidator,
    PackAccess,
    PackBoundaryError,
    build_promotion_event,
)
```

This is the compatibility-stable root surface. Phase 3 does not remove, rename, or warn on any of these imports.

## Canonical provider-neutral storage ports

New code that depends on storage capabilities rather than a concrete implementation should use:

```python
from fossil_core.ports import ArtifactStorePort, EventStorePort
```

These are the canonical provider-neutral storage interfaces. Application/domain code should depend on these boundaries rather than on S3/R2/filesystem implementation details when a port is sufficient.

## Canonical concrete adapters

Code that intentionally performs composition/wiring or directly selects a concrete provider may use the bounded adapter packages.

Filesystem:

```python
from fossil_core.adapters.filesystem import ArtifactStore, DurableEventStore
```

S3-compatible:

```python
from fossil_core.adapters.s3 import S3ArtifactStore, S3DurableEventStore
```

Adapter imports are supported bounded surfaces, but they are not domain truth. Selecting R2, AWS S3, MinIO, local filesystem, or another compatible implementation must not alter durable IDs, hashes, event schemas, provenance, lifecycle, conflict, redaction, or rebuild semantics.

## Compatibility-only modules

The following flat paths remain valid only to prevent migration breakage:

| Compatibility path | Canonical replacement |
| --- | --- |
| `fossil_core.storage_ports` | `fossil_core.ports` |
| `fossil_core.artifact_store` | `fossil_core.adapters.filesystem` |
| `fossil_core.event_store` | `fossil_core.adapters.filesystem` |
| `fossil_core.s3_storage` | `fossil_core.adapters.s3` |

They intentionally preserve object identity with the canonical classes/protocols. No runtime deprecation warnings are emitted in this phase because adding warnings would be a behavior change mixed into structural migration.

Removal is not authorized by this document. Compatibility modules may be removed only in an explicit cleanup phase after first-party consumers, clean-install tests, cross-repository contracts, and required hosted gates demonstrate that the old paths are no longer needed.

## Internal-by-default rule

A module or symbol is **internal until explicitly promoted** into the versioned API contract. Being importable from Python does not by itself make a module a supported API.

This rule lets bounded domain/application packages move incrementally without accidentally turning every implementation path into a permanent external contract.

## Change policy

Any change to a supported surface must be deliberate:

1. update the versioned public-API contract;
2. update compatibility policy or migration guidance as needed;
3. update contract tests;
4. keep behavior-preserving aliases when required for existing consumers;
5. pass the deterministic suite and architecture-boundary gate on the exact head;
6. use a separate explicit cleanup decision for removals.

Package movement alone is not permission to change semantics, stable identities, schemas, canonical hashes, provider policy, or acceptance thresholds.
