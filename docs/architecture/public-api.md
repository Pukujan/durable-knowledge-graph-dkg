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

## Canonical promotion domain

Cross-pack promotion event construction is canonical under:

```python
from fossil_core.domain.promotion import build_promotion_event
```

This is a pure domain event factory. It enforces that promotion has at least one stable subject reference and crosses a real pack boundary, then returns the existing `dkg.event.v1` `knowledge.promoted` event. It does not persist the event or select a storage provider; committing and schema validation remain outside the pure domain module.

Promotion is append-only: the source pack is not mutated. The target records a new durable event whose payload points to the source pack and whose evidence/provenance fields preserve why the promotion was accepted. The existing event type, schema version, payload keys, provenance method, and validation messages are compatibility-sensitive and are not changed by package movement.

## Canonical provider-neutral ports

New code that depends on storage capabilities rather than a concrete implementation should use:

```python
from fossil_core.ports import ArtifactStorePort, EventStorePort
```

These are the canonical provider-neutral storage interfaces. Application/domain code should depend on bounded capabilities rather than on S3/R2/filesystem implementation details when a port is sufficient; pure domain modules must not depend on storage ports at all.

Replaceable projection code should use:

```python
from fossil_core.ports import ProjectionAdapter, ProjectionReceipt
# equivalent canonical module:
from fossil_core.ports.projection import ProjectionAdapter, ProjectionReceipt
```

`ProjectionAdapter` describes a replaceable materialized view of already-durable knowledge. `ProjectionReceipt` records the outcome of applying or rebuilding that view. Neither type makes Graphiti, Neo4j, a local ledger, or any other projection authoritative durable truth.

Every replaceable cognitive capability shares the canonical metadata contract:

```python
from fossil_core.ports import VersionedCognitiveService
# equivalent canonical module:
from fossil_core.ports.cognitive_service import VersionedCognitiveService
```

`VersionedCognitiveService` requires the existing `metadata()` surface used to record implementation/provider/model/runtime provenance.

Retrieval capability code should depend on the canonical Retriever port:

```python
from fossil_core.ports import Retriever
# equivalent canonical module:
from fossil_core.ports.retriever import Retriever
```

`Retriever.search` retains the existing contract: `query`, keyword-only `pack_ids`, and keyword-only `limit=20`, returning ranked candidate dictionaries. Moving the Protocol does not alter lexical, embedding, hybrid, reranking, filtering, or query semantics implemented by concrete services.

Context-construction capability code should depend on the canonical ContextProvider port:

```python
from fossil_core.ports import ContextProvider
# equivalent canonical module:
from fossil_core.ports.context_provider import ContextProvider
```

`ContextProvider.build_context` retains the existing `build_context(request) -> dict[str, Any]` contract. Moving the Protocol does not change context budgets, compression policy, source selection, redaction/security policy, ranking, or any concrete context-construction implementation.

Embedding capability code should depend on the canonical EmbeddingProvider port:

```python
from fossil_core.ports import EmbeddingProvider
# equivalent canonical module:
from fossil_core.ports.embedding_provider import EmbeddingProvider
```

`EmbeddingProvider` retains the existing `model_id` property and `embed(texts) -> list[list[float]]` contract. Moving the Protocol does not select a provider/model, change vector dimensions or normalization, alter batching/caching behavior, or change any retrieval/reranking policy.

Reranking capability code should depend on the canonical Reranker port:

```python
from fossil_core.ports import Reranker
# equivalent canonical module:
from fossil_core.ports.reranker import Reranker
```

`Reranker.rerank` retains the existing `query`, `candidates`, and keyword-only `limit` contract. Moving the Protocol does not select a reranking provider/model or change candidate scoring, ordering, truncation, filtering, retrieval, or context-construction behavior.

Model-execution capability code should depend on the canonical ModelService port:

```python
from fossil_core.ports import ModelService
# equivalent canonical module:
from fossil_core.ports.model_service import ModelService
```

`ModelService.run` retains the existing `run(task) -> dict[str, Any]` contract. Moving the Protocol does not select a model/provider, change routing or prompting policy, alter task/output semantics, or change verification behavior.

Verification capability code should depend on the canonical VerificationService port:

```python
from fossil_core.ports import VerificationService
# equivalent canonical module:
from fossil_core.ports.verification_service import VerificationService
```

`VerificationService.verify` retains the existing `verify(proposal) -> dict[str, Any]` contract. Moving the Protocol does not change verification rules, scoring, evidence requirements, proposal semantics, model/provider selection, or any acceptance policy.

All projection/cognitive types historically exposed by `fossil_core.contracts` now forward to canonical port modules with object identity preserved. `fossil_core.contracts` remains available as the historical aggregate and keeps its exact implicit namespace and absence of `__all__`; this structural move does not authorize deleting, warning on, or reclassifying that module. Any compatibility cleanup is a separate Phase 6 decision after first-party and cross-repository consumers are migrated and verified.

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
| `fossil_core.promotion` | `fossil_core.domain.promotion` |
| `fossil_core.storage_ports` | `fossil_core.ports` |
| `fossil_core.artifact_store` | `fossil_core.adapters.filesystem` |
| `fossil_core.event_store` | `fossil_core.adapters.filesystem` |
| `fossil_core.s3_storage` | `fossil_core.adapters.s3` |

They intentionally preserve object identity with canonical classes/protocols/functions. The lifecycle shim preserves its historical implicit star-import names rather than adding a new `__all__`. The `ids` shim likewise preserves its historical implicit `annotations`, `hashlib`, and `uuid` names as well as the two identity functions. The promotion shim preserves its historical `Any`, `Iterable`, `annotations`, and `build_promotion_event` names. None of these compatibility-only modules gains a new `__all__`. No runtime deprecation warning is added to these `fossil_core` compatibility paths because that would mix behavior changes into structural migration.

`fossil_core.pack` is not listed as compatibility-only: it remains the active home of `KnowledgePackValidator` while `PackAccess` and `PackBoundaryError` are identity aliases to the pure domain boundary. `fossil_core.contracts` is also intentionally not reclassified here: it is now a forwarding aggregate for canonical projection/cognitive ports, and its cleanup status remains a separate migration decision.

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
