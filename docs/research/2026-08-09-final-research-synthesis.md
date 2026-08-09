# Final Research Synthesis — Durable Knowledge Graph

**Date:** 2026-08-09  
**Scope:** production database management, temporal knowledge graphs, multi-tenant/boundary design, provenance/semantic-web standards, vector/RAG systems, context engineering, long-term agent memory, harness engineering, MCP/Skills, local embedding/retrieval models, and migration/backup practices.

This document records the architectural conclusions after a broad review of more than 100 primary/official technical sources. The companion [evidence ledger](2026-08-09-evidence-ledger.md) records the source set.

## Executive conclusion

The strongest design is **not one magical database**.

The durable system should separate:

1. **evidence and history that must survive technology changes**;
2. **logical knowledge boundaries that must survive physical movement**;
3. **operational graph/search projections optimized for today's workload**;
4. **agent/model services that are expected to change rapidly**.

This leads to the contract in [`ARCHITECTURE.md`](../../ARCHITECTURE.md): immutable evidence + append-only events + portable knowledge packs are canonical; Graphiti/Neo4j is the first living graph projection; retrieval/model systems are adapters; agent writes go through proposal/validation gates.

## What the research changed

### 1. Graphiti is useful, but its ontology and namespace must not become our permanent schema

Graphiti already solves important hard problems: incremental temporal graph construction, episodes/provenance, custom entity/edge types, hybrid semantic/keyword/graph retrieval, and namespace separation with `group_id`.

Sources:
- [Graphiti repository](https://github.com/getzep/graphiti)
- [Graph namespacing](https://help.getzep.com/graphiti/core-concepts/graph-namespacing)
- [Custom entity and edge types](https://help.getzep.com/graphiti/core-concepts/custom-entity-and-edge-types)

However, custom type changes do not automatically transform previously ingested knowledge, and Graphiti's provided MCP server is explicitly described as experimental. Therefore:

- our ontology remains independently versioned;
- our `pack_id` remains canonical and maps to `group_id`;
- Graphiti is behind an adapter;
- projection rebuild tests are mandatory;
- Graphiti MCP is not our internal contract.

### 2. Logical boundary and physical shard are different concepts

This conclusion was strongly reinforced by mature vector/distributed systems.

Qdrant recommends shared collections with tenant-aware partitioning for many tenants and now supports promoting selected tenants to dedicated shards. Milvus documents several tenancy levels with different isolation/scalability tradeoffs. Weaviate represents tenants as separate shards and supports tenant storage states. Citus recommends a tenant/distribution key to colocate related data.

Sources:
- [Qdrant multitenancy](https://qdrant.tech/documentation/guides/multiple-partitions/)
- [Milvus multi-tenancy](https://milvus.io/docs/multi_tenancy.md)
- [Weaviate multi-tenancy](https://docs.weaviate.io/weaviate/manage-collections/multi-tenancy)
- [Citus data modeling](https://docs.citusdata.com/en/stable/sharding/data_modeling.html)

The portable semantic identity should therefore be a **knowledge pack/library**, not a physical shard. Physical placement can later become shared, partitioned, dedicated, replicated, or federated without changing stable knowledge IDs.

### 3. Git repositories should be control/contract planes, not live graph databases

Git is excellent for:

- architecture and ADRs;
- schemas;
- ontology definitions;
- pack manifests;
- small immutable text evidence/events;
- migration code;
- benchmark fixtures;
- Agent Skills;
- project state and review history.

It is poor as the only runtime graph/search store or large binary artifact store.

OpenAI's published harness-engineering approach strongly supports treating repository knowledge, structured docs, plans, checks, and mechanical boundaries as first-class infrastructure rather than stuffing all behavior into one giant prompt.

Sources:
- [OpenAI — Harness engineering](https://openai.com/index/harness-engineering/)
- [Anthropic — Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Anthropic — Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

### 4. One event per immutable file is safer than one giant JSONL authoring log

The original idea used JSONL for append-only history. For multiple agents/Git repositories, one hot append file becomes a conflict point.

The revised pattern is:

```text
events/<id-prefix>/<event-id>.json
```

Each event is immutable and independently validated. Bulk JSONL remains an import/export format. Rebuildable indexes/manifests can be generated from the event directory.

The envelope borrows stable event concepts from CloudEvents and is validated by JSON Schema, while our own schema defines claim/ontology/provenance semantics.

Sources:
- [CloudEvents specification](https://github.com/cloudevents/spec)
- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)

### 5. Provenance needs standards-aligned semantics, not just a `citation` string

W3C PROV distinguishes entities, activities, and agents and explicitly models derivation/revision/source relationships. SKOS gives portable concept-scheme semantics. RDF/OWL provide interchange/formal semantics, and SHACL provides graph validation.

Sources:
- [PROV-O](https://www.w3.org/TR/prov-o/)
- [SKOS](https://www.w3.org/TR/skos-reference/)
- [RDF 1.2 Concepts](https://www.w3.org/TR/rdf12-concepts/)
- [OWL 2 Overview](https://www.w3.org/TR/owl2-overview/)
- [SHACL 1.2 Core](https://www.w3.org/TR/shacl12-core/)

We should align our internal concepts with these standards and support exports, but not force the operational application into an RDF triple store on day one.

### 6. Accepted knowledge and successful graph projection must be separate states

Graph extraction can fail because an LLM/API/backend is down. A failure to update Neo4j must **not** mean a knowledge event was lost.

Therefore:

```text
validated durable event
        |
        +--> projection job --> success
                         |
                         +--> retry / dead-letter / review
```

Projection is asynchronous/idempotent. The durable event is committed first.

This is a major durability improvement over letting agents write directly into the graph.

### 7. Idempotency is a first-class requirement

Agent systems retry. Importers retry. Network operations retry.

Every ingest/proposal path needs a deterministic idempotency strategy based on stable event IDs, artifact/source hashes, and explicit operation IDs where appropriate. Duplicate ingestion must not create duplicate intellectual history.

### 8. Append-only history needs a redaction escape hatch

Append-only knowledge history is useful, but future legal/finance/private corpora may require actual content suppression or deletion.

Therefore the system needs a separate **redaction/tombstone** mechanism. It must not pretend sensitive payloads remain forever merely because history is append-only. A redaction can remove active/exported payloads while retaining only the minimum safe audit marker needed to explain intentional removal.

We do not need to implement full privacy machinery now, but the event model must not make future redaction impossible.

### 9. Retrieval cannot be permanently equal to vector RAG

Kimi Linear/MoBA and modern long-context systems show that the economics of context are changing. Anthropic's contextual retrieval work combines semantic, lexical, contextual, and reranking signals rather than treating one embedding search as sufficient. GraphRAG/HippoRAG/LightRAG explore graph-centered retrieval for multi-hop knowledge.

Sources:
- [Kimi Linear](https://arxiv.org/abs/2510.26692)
- [MoBA](https://arxiv.org/abs/2502.13189)
- [Anthropic — Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval)
- [Microsoft GraphRAG](https://github.com/microsoft/graphrag)
- [HippoRAG](https://github.com/OSU-NLP-Group/HippoRAG)
- [LightRAG](https://github.com/HKUDS/LightRAG)

So storage, retrieval, context construction, and reasoning remain separate interfaces.

### 10. Cheap/local specialists are promising, but they should earn authority through benchmarks

Small/static embedding systems such as Model2Vec/Potion and lightweight ONNX systems such as FastEmbed can make local candidate generation, deduplication, routing, and background auditing very cheap. Dense/sparse/multi-vector systems such as BGE-M3 and ColBERT illustrate other retrieval tradeoffs.

Sources:
- [Model2Vec](https://github.com/MinishLab/model2vec)
- [FastEmbed](https://github.com/qdrant/fastembed)
- [BGE-M3](https://arxiv.org/abs/2402.03216)
- [ColBERTv2](https://arxiv.org/abs/2112.01488)

But specialization must be measured on our corpus. A small model can propose duplicate/contradiction candidates without being allowed to finalize a high-risk claim state merely because it is cheap.

### 11. The harness should route by risk and uncertainty, not only by task size

A practical future policy:

```text
LOW      deterministic rules / local embeddings / small classifier
MEDIUM   specialist local/cheap model; escalate on uncertainty
HIGH     strong reasoning model + evidence verification
CRITICAL independent/cross-vendor review + external truth signals + explicit gate
```

Model consensus is not a source. Independent models can expose disagreements; external sources/tests/experiments determine whether a claim has adequate support.

### 12. MCP and Skills solve different problems

The current MCP specification continues evolving. Skills use progressive disclosure to load methodology only when relevant. Therefore:

- internal corpus contract is normal domain code/API;
- Agent Skills contain workflows/methodology;
- MCP is a thin interoperability adapter;
- tool surface stays small;
- no knowledge format depends on MCP.

Sources:
- [Model Context Protocol specification](https://modelcontextprotocol.io/specification/2026-07-28)
- [Agent Skills](https://agentskills.io/)

## Production patterns we intentionally copy

The research found several recurring patterns across unrelated mature systems:

1. **Separate logical tenancy from physical placement.**
2. **Use stable application identities rather than storage-native IDs.**
3. **Make indexes/caches rebuildable from canonical records.**
4. **Use explicit migration/version contracts.**
5. **Back up for disaster recovery, but maintain vendor-neutral export/rebuild paths for portability.**
6. **Prefer additive migrations and blue/green replacement for dangerous structural changes.**
7. **Make retries/idempotency normal.**
8. **Do not rely on one retrieval algorithm.**
9. **Keep permissions/context boundaries explicit at query/write time.**
10. **Record provenance of derived state.**

## Competing architecture considered: PostgreSQL-first

A serious alternative is PostgreSQL + pgvector as canonical operational storage with Neo4j only as a graph projection.

Benefits:

- mature transactions/concurrency/migrations;
- excellent SQL/analytics ecosystem;
- FTS + vector in one system;
- easier conventional production operations.

Cost:

- we would implement more temporal knowledge-graph behavior ourselves;
- the first useful system would take longer.

Decision: **do not reject this alternative permanently.** Keep our durable event/pack contracts independent enough that a PostgreSQL projection can be added or promoted later without changing canonical knowledge.

## Competing architecture considered: plain files + Git + embeddings

Benefits:

- extremely simple and portable;
- almost no operational dependency.

Cost:

- difficult multi-hop dependency, temporal, disagreement, and supersession queries;
- pushes too much semantic reconstruction into retrieval-time LLM work.

Decision: files/Git are appropriate for the durable contract/control plane but not sufficient as the only operational representation for the intended relationship-heavy workload.

## Decision on the proposed two GitHub "shards"

The idea is useful, but they should be called **knowledge-pack repositories**, not database shards.

Recommended sequence:

1. keep this repository as the **platform/contracts/control-plane repo**;
2. first prove `knowledge-pack/v1` using the example packs in this repository;
3. then create two pack repositories using the exact same contract;
4. import/mount those packs into the local runtime graph as separate namespaces;
5. never let cross-repository file paths become knowledge identity.

Reasonable first pair:

- **common/shared pack** — research methodology, source policies, cross-project engineering knowledge;
- **project/domain pack** — e.g. plugin-harness/AI-systems research or another first real domain.

If scale later demands physical database sharding, pack placement can change independently.

## Research freeze

The architecture has enough evidence to begin implementation without another platform rewrite.

New technologies should now be evaluated as adapters/projections against explicit benchmarks rather than causing architecture churn.

The next work should prove five things before large corpus ingestion:

1. immutable evidence + event validation;
2. knowledge-pack boundary contract;
3. Graphiti/Neo4j projection from accepted events;
4. destructive rebuild and blue/green migration;
5. reconstruction of a difficult conversation lineage with citations, disagreements, and supersession.
