# Current Handoff

**Date:** 2026-08-09  
**Repository:** `Pukujan/durable-knowledge-graph-dkg`  
**Status:** research freeze complete; durable executable skeleton started; continuity docs committed; next work is Gate 1 durability proof.

## Fresh-session continuation order

A future GPT/Codex/Claude session should be able to continue without this chat. Read, in order:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/PROJECT_STATE.md`
4. this file
5. `docs/research/2026-08-09-final-research-synthesis.md`
6. `docs/research/2026-08-09-evidence-ledger.md`
7. `docs/DECISION_LOG.md`
8. Issue #1 and the active child issue

The chat UI is source material, not the control plane.

## What has already been decided

The project is a durable local-first knowledge platform, not merely a RAG database.

The durable core is:

- immutable original evidence/artifacts;
- stable corpus-owned IDs;
- append-only versioned knowledge events;
- portable knowledge-pack manifests/boundaries;
- versioned ontology/schema contracts;
- provenance, disagreement, claim/relation state history, and supersession.

The first operational living graph is **Graphiti + local Neo4j**, but it is a rebuildable projection rather than the irreplaceable source of truth.

Retrieval, embeddings, reranking, long-context models, local specialist models, frontier LLMs, Skills, MCP, and future databases are adapters around the durable contracts.

See `ARCHITECTURE.md` for the complete invariant set.

## Research state

A broad research pass covering 127 primary/official sources and papers has already been committed.

The research covers:

- Graphiti/Zep and temporal knowledge graphs;
- Neo4j and graph operations;
- PostgreSQL/pgvector/Citus as a serious competing architecture;
- Qdrant/Milvus/Weaviate multi-tenancy and logical-vs-physical isolation patterns;
- W3C PROV/SKOS/RDF/OWL/SHACL;
- CloudEvents and JSON Schema;
- RAG, GraphRAG, HippoRAG, LightRAG;
- Kimi Linear/MoBA and changing long-context assumptions;
- Model2Vec/Potion, FastEmbed, BGE-M3, ColBERT and local retrieval options;
- OpenAI/Anthropic harness/context engineering;
- MCP and Agent Skills;
- long-term agent-memory systems and truth-maintenance ideas;
- migration, backup, idempotency, projection/rebuild, and multi-tenant production practices.

Research artifacts:

- `docs/research/2026-08-09-final-research-synthesis.md`
- `docs/research/2026-08-09-evidence-ledger.md`
- `docs/research/README.md`

Research is now considered **frozen enough to implement**. New technologies should be evaluated against adapters and benchmarks rather than restarting the architecture.

## Current GitHub work plan

Issue #1 is the milestone-control issue because the current assistant connector cannot create native GitHub milestones/sub-issue links.

Children:

- #2 Durable event + artifact store with validation/idempotency
- #3 Knowledge-pack boundaries, mounts, and promotion
- #4 Graphiti + Neo4j projection adapter/queue
- #5 Destructive rebuild + blue/green migration harness
- #6 Claim/relation lifecycle, disagreement, supersession, staleness
- #7 Pluggable retrieval/model services and local-specialist benchmark contract
- #8 Agent Skills + thin corpus API/MCP contract
- #9 Conversation ingestion + intellectual-lineage reconstruction benchmark
- #10 Source snapshots, citation provenance, quality dimensions, redaction path

Recommended execution order:

`#2 -> #3 -> #6 -> #4 -> #5 -> #9 -> #8 -> #7`, with #10 requirements applied where needed.

## Existing executable skeleton

The repository already contains:

- event schema v1;
- knowledge-pack schema v1;
- core ontology skeleton;
- source-quality policy;
- example knowledge packs;
- Python service/interface skeletons;
- immutable filesystem event-store skeleton;
- pack validation;
- deterministic duplicate/idempotency behavior;
- a null projection proving the durable layer can exist without Neo4j;
- automated tests;
- GitHub Actions configuration.

The local skeleton was previously reported as **4/4 tests passing**. Do not assume current CI state from that sentence; rerun tests and verify remote CI before relying on it.

## Exact next task

Start with **Issue #2**, but inspect the current repository implementation before changing it.

The goal is not to rewrite the skeleton. Extend it until the durable event/artifact layer proves:

1. JSON Schema validation;
2. stable corpus-owned identity;
3. deterministic idempotent retries;
4. content-addressed artifact metadata;
5. atomic event creation;
6. malformed/duplicate-write tests;
7. no dependency on Graphiti/Neo4j for durable event validity.

Then move to #3 and prove knowledge-pack isolation before creating external pack repositories.

## Planned first external knowledge packs

Do **not** call them database shards.

After #3 passes, create two repositories implementing the exact same pack contract:

1. a common/shared knowledge pack;
2. an AI-systems/plugin-harness domain/project pack.

Each has a stable `pack_id`. Repository location and runtime graph namespace are physical placement details, not identity.

## Harness use case that must remain supported

The corpus is intended to become durable memory for a coding/research harness around Codex, Claude, and other agents.

The harness may use independent/cross-vendor model lanes and enforce:

- provenance;
- citations and source-quality dimensions;
- risk tiering;
- explicit assumptions;
- competing theories;
- claim attack/rebuttal;
- KEDB-style failure memory;
- MAPE-K-style loops;
- claim and relation lifecycle states;
- external tests/sources as truth signals.

Multiple models agreeing is not evidence. They may identify candidate conflicts or confidence, but durable truth-changing state requires policy/evidence.

## Context/retrieval future-proofing

Do not assume permanent vector-RAG architecture.

The frozen ports include:

- `ContextProvider`
- `Retriever`
- `EmbeddingProvider`
- `Reranker`
- `ModelService`
- `VerificationService`

Kimi-style long context, BM25, graph traversal, local/static embedders, rerankers, and future neuro-symbolic systems should be swappable implementations rather than reasons to migrate canonical knowledge.

## Migration invariant

Migration is expected, not exceptional.

Dangerous structural changes should normally create a second projection beside the current one, replay the same durable events, run semantic/reconstruction tests, then switch the active projection only if it passes.

Hard target:

`delete graph -> rebuild from durable evidence/events -> recover stable IDs, provenance, historical states, disagreements, and benchmark answers`.

## Chat-loss/recovery warning

Part of the original ChatGPT conversation appeared to disappear from the UI. A recovery checkpoint was committed under `docs/recovery/`.

Therefore:

- never use chat history as the only project state;
- commit durable decisions and research promptly;
- distinguish verbatim source evidence from reconstructed memory;
- update this handoff at the end of substantial work.

## What not to build yet

Do not add Redis, Elasticsearch/OpenSearch, Citus, Kubernetes, a dedicated vector DB, custom OAuth, a large dashboard, dozens of local model servers, or physical sharding until measured workload/benchmarks justify them.

The goal is a small implementation of permanent contracts, not a throwaway MVP and not infrastructure maximalism.

## Next-session success condition

A fresh agent that has never seen this chat should be able to read the files above, identify Issue #2 as the current execution point, explain the durable-vs-projection distinction, and continue implementation without asking the user to reconstruct the architecture from memory.
