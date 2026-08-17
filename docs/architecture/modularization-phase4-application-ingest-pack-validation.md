# Phase 4: pack validation application boundary

Status: bounded behavior-preserving modularization slice under #82.

`KnowledgePackValidator` is canonical under `fossil_core.application.ingest`. It is not pure domain logic: construction reads a JSON Schema from the filesystem and validation delegates structural checks to `jsonschema` before applying the existing pure pack-boundary invariants.

The pure capability model remains in `fossil_core.domain.pack`:

```python
from fossil_core.domain.pack import PackAccess, PackBoundaryError
```

The ingestion validation service is:

```python
from fossil_core.application.ingest import KnowledgePackValidator
```

The supported package-root import remains unchanged and aliases the canonical application object:

```python
from fossil_core import KnowledgePackValidator
```

`fossil_core.pack` remains an import-compatible mixed legacy path during the migration. Its historical implicit namespace is preserved, while `KnowledgePackValidator` forwards to the application boundary and `PackAccess` / `PackBoundaryError` forward to the pure domain boundary.

This move does not change the knowledge-pack schema, manifest fields, dependency/read/write validation rules, validation messages, storage/provider behavior, stable identities, hashes, projection behavior, LiteLLM/Cortex V5 runtime, or any acceptance threshold. Cleanup or removal of the legacy path requires a separate compatibility decision.
