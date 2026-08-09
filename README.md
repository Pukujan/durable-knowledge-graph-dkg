# Durable Knowledge Graph (DKG)

A local-first, migration-safe knowledge system for durable research and agent memory.

> **Evidence is permanent. History is append-only. Interpretations can evolve. Databases are replaceable. Disagreement is data. Every conclusion must be able to explain where it came from.**

## Status

**Research freeze / durable skeleton.** The repository is intentionally separating durable contracts from runtime technology before committing large amounts of knowledge.

The current operational graph candidate is **Graphiti + Neo4j**, but neither is the deepest source of truth. The durable source is immutable evidence plus append-only versioned knowledge events. The graph, embeddings, retrieval indexes, dashboards, and model services must be rebuildable projections.

## Core layers

1. **Evidence** — immutable source artifacts and exact source references.
2. **Knowledge events** — append-only statements of what was proposed, challenged, supported, superseded, or changed and why.
3. **Knowledge packs** — portable logical boundaries for common, domain, and project knowledge.
4. **Ontology + provenance** — versioned semantics independent of the graph vendor.
5. **Projection adapters** — Graphiti/Neo4j first; future storage/search systems remain replaceable.
6. **Cognitive services** — pluggable retrievers, embedders, rerankers, local models, frontier models, and verification services.
7. **Harness** — risk routing, parallel theories, cross-model criticism, citation/source checks, KEDB/MAPE-K loops, and deterministic commit gates.
8. **Observability** — external traces/metrics/logs; only durable knowledge-changing provenance belongs in the corpus.

## Start here

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — frozen architectural contract and non-goals.
- [`docs/research/2026-08-09-final-research-synthesis.md`](docs/research/2026-08-09-final-research-synthesis.md) — final research conclusions and changes made after the broad source review.
- [`docs/research/2026-08-09-evidence-ledger.md`](docs/research/2026-08-09-evidence-ledger.md) — primary/official source ledger.
- [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) — project tracking contract and GitHub issue map.
- [`schemas/knowledge-pack/v1.schema.json`](schemas/knowledge-pack/v1.schema.json) — first portable pack contract.
- [`schemas/events/v1.schema.json`](schemas/events/v1.schema.json) — first append-only event envelope.

## Important terminology

A **knowledge pack** is a logical portable unit such as `common/research`, `domain/swe`, or `project/plugin-harness`. It is **not** a physical database shard. A pack can later be placed in shared storage, a dedicated partition, another graph database, or another repository without changing its stable identity.

A **projection** is a rebuildable representation optimized for a workload. Neo4j/Graphiti, RDF, vector indexes, lexical indexes, analytics tables, or a future database can all be projections.

## Initial runtime target

For the first executable implementation:

- local immutable artifact store;
- immutable one-event-per-file event store with JSON Schema validation;
- stable corpus-owned IDs;
- versioned ontology files;
- Graphiti adapter over local Neo4j;
- namespace mapping from `pack_id` to Graphiti `group_id`;
- reconstruction, namespace, provenance, supersession, and destructive-rebuild tests;
- Agent Skills for methodology;
- a very small local API/MCP adapter only after the core contracts pass.

No Redis, Elasticsearch, Citus, Supabase, Kubernetes, or custom authentication is required for the first local build.
