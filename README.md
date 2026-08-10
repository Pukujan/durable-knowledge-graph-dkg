# FOSSIL

**Fault-tolerant Open Semantic Store for Intellectual Lineage**

A local-first, migration-safe knowledge system for durable research and agent memory.

> **Evidence is durable. History is explainable. Interpretations can evolve. Databases are replaceable. Disagreement is data. Every conclusion must be able to explain where it came from.**

The durable substrate is **DICS — Durable Intellectual Corpus System**.

## Repository family

- `fossil-core` — architecture, contracts, durable event/artifact core, projection adapters, migration/rebuild machinery, benchmarks, and project control plane;
- `fossil-common` — shared research and engineering methods, stable pack ID `pack_269099f7b2ba43b7a99b9427d64092de`;
- `fossil-ai-systems` — AI systems / plugin-harness knowledge, stable pack ID `pack_f024177f89a5442db84171c3dd7f58e5`, reading from `fossil-common`.

Repository names, graph namespaces, and physical database placement are operational details. Knowledge-pack identity remains the stable `pack_id`.

## Status

**Gate 1 executable durability proof is complete: 15/15.**

FOSSIL has executable proof for:

- immutable validated durable events and content-addressed evidence;
- deterministic idempotency;
- portable knowledge-pack boundaries and provenance-preserving promotion;
- disagreement, lifecycle, supersession, and stale dependency replay;
- real Graphiti + Neo4j materialization with retry/failure history;
- destructive rebuild and guarded blue/green migration;
- conversation ingestion with explicit verbatim-vs-reconstructed provenance and intellectual-lineage reconstruction;
- a protocol-independent safe Agent Skill/API/MCP boundary;
- immutable source snapshots, exact byte-span citations, anti-laundering source roles, source quality dimensions, source lifecycle, and exceptional privacy/legal redaction;
- real active Graphiti redaction plus fresh-rebuild non-resurrection.

The current operational graph implementation is **Graphiti + Neo4j**, but neither is the deepest source of truth. Graphs, embeddings, retrieval indexes, dashboards, models, Skills, and protocol adapters remain rebuildable/replaceable around the durable corpus.

**Next:** Issue #7 — pluggable retrieval/model services and a specialist benchmark contract. The goal is measured replaceability, not a model zoo.

## Core layers

1. **Evidence** — immutable source snapshots/artifacts, exact source references, quality dimensions, lifecycle, and an explicit exceptional erasure path.
2. **Knowledge events** — append-only normal intellectual history describing proposals, challenges, support, supersession, lifecycle changes, and provenance.
3. **Knowledge packs** — portable logical boundaries for common, domain, and project knowledge.
4. **Ontology + provenance** — versioned semantics independent of graph/model vendors.
5. **Projection adapters** — Graphiti/Neo4j first; other storage/search systems remain replaceable.
6. **Cognitive services** — pluggable retrievers, embedders, rerankers, context providers, local/frontier models, and verification services.
7. **Agent boundary** — lazily loaded Skills plus a thin protocol-independent corpus capability surface; no arbitrary graph mutation.
8. **Observability** — external traces/metrics/logs; only durable knowledge-changing provenance belongs in the corpus.

## Start here

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — architectural contract and non-goals.
- [`docs/HANDOFF_CURRENT.md`](docs/HANDOFF_CURRENT.md) — exact continuation point.
- [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) — Gate state and issue map.
- [`docs/DECISION_LOG.md`](docs/DECISION_LOG.md) — durable architectural decisions.
- [`docs/implementation/2026-08-10-gate1-source-provenance-redaction-proof.md`](docs/implementation/2026-08-10-gate1-source-provenance-redaction-proof.md) — final Gate 1 source/redaction proof.
- [`docs/research/2026-08-09-final-research-synthesis.md`](docs/research/2026-08-09-final-research-synthesis.md) — frozen research synthesis.
- [`docs/research/2026-08-09-evidence-ledger.md`](docs/research/2026-08-09-evidence-ledger.md) — primary/official source ledger.
- [`schemas/knowledge-pack/v1.schema.json`](schemas/knowledge-pack/v1.schema.json) — portable pack contract.
- [`schemas/events/v1.schema.json`](schemas/events/v1.schema.json) — durable event envelope.

## Important terminology

A **knowledge pack** is a logical portable unit. It is **not** a physical database shard. A pack may move repository/database/partition without changing stable identity.

A **projection** is a rebuildable representation optimized for a workload. Neo4j/Graphiti, RDF, vector indexes, lexical indexes, analytics tables, or future databases can all be projections.

**Redaction** is not ordinary revision. Normal intellectual history is append-only. Privacy/legal erasure is an explicit exceptional tombstone-before-delete operation whose active projections and future rebuilds must respect the erasure.

## Current implementation direction

Gate 1 deliberately proved the durable contracts before optimizing retrieval. The next work compares retrieval/context/model choices behind interfaces and benchmarks them on corpus-specific quality, latency, resource cost, and failure behavior. Small/local models may propose bounded candidates; they do not gain truth-changing authority merely by agreeing with each other.
