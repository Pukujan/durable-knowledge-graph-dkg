# DKG Project Research Trace Seed

**Date:** 2026-08-09  
**Status:** partial reconstruction + durable project evidence. This is **not** a verbatim replacement for missing chat turns.

## Research question

How should a local-first durable knowledge system preserve evidence, claims, disagreement, temporal change, provenance, domain/project boundaries, migrations, retrieval, and agent access while remaining replaceable at the database/model layer?

## Origin

The project emerged from a long discussion about learning, representation, failure-driven reasoning, agent harnesses, KEDB/MAPE-K loops, and the need to preserve not only conclusions but the path by which assumptions changed.

A later chat-history/UI loss reinforced a central requirement: the chat interface cannot be the canonical research record. Major research passes and decisions need durable checkpoints outside the conversation UI.

## Major alternatives considered

1. SQLite as the canonical corpus database.
2. PostgreSQL + pgvector as the canonical corpus database.
3. Graph database as canonical storage.
4. Graphiti + Neo4j as an operational temporal graph.
5. Vector-first systems such as Qdrant/Weaviate/Milvus as the main corpus.
6. Plain files/JSONL/Git as the entire corpus.
7. Immutable evidence + append-only knowledge events as durable truth, with Graphiti/Neo4j and retrieval systems as rebuildable projections.

## Current accepted-for-now architecture

The current architecture selects option 7.

Durable:
- immutable original evidence;
- content hashes and corpus-owned stable IDs;
- append-only versioned knowledge events;
- versioned ontology/contracts;
- claim/relation lifecycle and disagreement history;
- provenance and research-decision lineage;
- logical knowledge-pack identities independent of physical placement.

Replaceable projections/services:
- Graphiti + Neo4j as the first living graph;
- lexical/vector/graph retrieval;
- embedders/rerankers;
- local specialist models/frontier models;
- MCP adapters;
- analytics/search projections.

## Important research corrections made during the process

- A first SQLite prototype was built too early and later demoted from canonical architecture after broader production-database research.
- PostgreSQL-first was considered strongly because of concurrency, migration maturity, pgvector, partitioning, and future scaling.
- Graphiti/Neo4j became attractive because temporal facts, episodes/provenance, namespaces, and graph retrieval match the required living-knowledge behavior.
- Graphiti/Neo4j were then explicitly demoted from deepest source of truth so future migrations do not strand the corpus.
- Migration became a first-class product feature: rebuildable projections, stable IDs, blue/green graph builds, and semantic invariants.
- Knowledge boundaries were reframed as logical packs/namespaces rather than immediate physical shards.
- Security was reduced for the initial localhost system; correctness/isolation boundaries are required now, heavy auth is deferred.
- Agent Skills were separated from MCP: Skills carry lazily loaded methodology; MCP/API carries capability.
- High-volume telemetry was separated from knowledge-changing audit/provenance.
- Source quality was changed from a single tier to multiple dimensions.
- Cross-model consensus was explicitly rejected as evidence; it is review metadata unless supported by external sources/tests.
- Local/small specialist models were planned as replaceable cognitive services for routing, deduplication, retrieval, citation matching, and anomaly detection, with higher-risk state changes escalated.

## Research evidence already preserved in this repository

- `ARCHITECTURE.md`
- `docs/research/2026-08-09-final-research-synthesis.md`
- `docs/research/2026-08-09-evidence-ledger.md`
- `docs/research/RESEARCH_TRACE_CONTRACT.md`
- `docs/recovery/2026-08-09-chat-recovery-checkpoint.md`
- `schemas/events/v1.schema.json`
- `schemas/knowledge-pack/v1.schema.json`
- `schemas/research-trace/v1.schema.json`
- `ontology/core/v1.yaml`
- GitHub issues beginning with #1
- implementation commits linked by Git history

## Intended future graph reconstruction

The later graph should be able to represent paths like:

```text
User problem / conversation observation
  -> ResearchQuestion
  -> AlternativeArchitecture
  -> SearchQuery / SourceSnapshot
  -> SourceClaim
  -> Critique / Counterclaim
  -> Decision accepted-for-now
  -> ArchitectureContract
  -> GitHub Issue
  -> Implementation Commit
  -> Benchmark / Failure
  -> Revised Decision
```

The graph should also preserve rejected alternatives and the reasons they were rejected, rather than retaining only the winning design.

## Current uncertainty

The contracts are frozen enough to implement, but the operational stack remains intentionally benchmarkable. Graphiti/Neo4j, retrieval methods, embedding models, long-context models, and local specialist models can be replaced if measured evidence supports another projection/service.

## Research state

`accepted_for_now`

This state is intentionally not `final_truth`. New implementation failures, benchmarks, database advances, or research can supersede the architecture through another explicit research trace.
