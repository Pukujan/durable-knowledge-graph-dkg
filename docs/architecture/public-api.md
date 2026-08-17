# FOSSIL Python public API

Status: versioned public-API contract for #82 under architecture authority #81 and #86.

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

This is the compatibility-stable root surface. Bounded migration does not remove, rename, or warn on any of these imports.

## Canonical lifecycle domain

New code that works directly with claim/relation lifecycle semantics should use the pure domain boundary:

```python
from fossil_core.domain.lifecycle import (
    CLAIM_STATES,
    RELATION_STATES,
    RELATION_TYPES,
    KnowledgeState,
    LifecycleError,
    RelationRecord,
)
```

This module contains deterministic domain state and invariants only. Architecture CI forbids it from importing ports, concrete adapters, or legacy storage shims.

## Canonical pack-boundary domain

Pure pack access and boundary checks are canonical under:

```python
from fossil_core.domain.pack import PackAccess, PackBoundaryError
```

`PackAccess` is a domain capability describing readable mounts and writable targets. It has no JSON Schema, filesystem, storage-provider, or runtime dependency.

`KnowledgePackValidator` intentionally remains available from `fossil_core` / `fossil_core.pack`. It performs JSON Schema-backed manifest validation and file loading, so this bounded move does not relabel that validation/integration concern as pure domain logic.

## Canonical identity domain

Corpus-owned identity helpers are canonical under:

```python
from fossil_core.domain.identity import deterministic_event_id, new_id
```

These helpers define FOSSIL-owned durable identity rather than provider- or storage-native identity. Storage object keys, database IDs, projection IDs, or provider-specific identifiers must not become durable semantic identity.

The exact deterministic event-ID derivation is compatibility-sensitive. Moving this code between packages does not authorize changing its input framing, SHA-256 derivation, prefix, truncation, or output shape. Likewise, `new_id` retains the existing `<prefix>_<uuid4 hex>` shape.

## Canonical provider-neutral storage ports

New code that depends on storage capabilities rather than a concrete implementation should use:

```python
from fossil_core.ports import ArtifactStorePort, EventStorePort
```

These are the canonical provider-neutral storage interfaces. Application/domain code should depend on bounded capabilities rather than on S3/R2/filesystem implementation details when a port is sufficient; pure domain modules must not depend on storage ports at all.

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
| `fossil_core.ids` | `fossil_core.domain.identity` |
| `fossil_core.lifecycle` | `fossil_core.domain.lifecycle` |
| `fossil_core.storage_ports` | `fossil_core.ports` |
| `fossil_core.artifact_store` | `fossil_core.adapters.filesystem` |
| `fossil_core.event_store` | `fossil_core.adapters.filesystem` |
| `fossil_core.s3_storage` | `fossil_core.adapters.s3` |

They intentionally preserve object identity with canonical classes/protocols/functions. The lifecycle shim preserves its historical implicit star-import names rather than adding a new `__all__`. The `ids` shim likewise preserves its historical implicit `annotations`, `hashlib`, and `uuid` names as well as the two identity functions; it does not add a new `__all__`. No runtime deprecation warning is added to these `fossil_core` compatibility paths because that would mix behavior changes into structural migration.

`fossil_core.pack` is not listed as compatibility-only: it remains the active home of `KnowledgePackValidator` while `PackAccess` and `PackBoundaryError` are identity aliases to the pure domain boundary.

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
