# Architecture Contract

**Frozen:** 2026-08-09  
**Meaning of frozen:** these are durable invariants. Runtime libraries may change when evidence or benchmarks justify it.

## 1. What must survive

The durable system is **not** a Neo4j database, a vector index, a Graphiti installation, an embedding model, or an LLM conversation.

The durable system is:

1. immutable original evidence;
2. stable corpus-owned identities;
3. append-only knowledge-changing events;
4. versioned ontology and validation contracts;
5. provenance explaining where derived knowledge came from;
6. explicit history of disagreement, revision, supersession, and unresolved claims.

Everything else must be reconstructable.

## 2. Architecture

```text
                         AGENTS / HUMANS
                              |
                    Harness + Agent Skills
                              |
              task/risk routing + commit gates
                              |
                  Cognitive service ports
       retriever / embedder / reranker / critic / reasoner
                              |
                   Stable corpus service API
                              |
        +---------------------+---------------------+
        |                                           |
 DURABLE KNOWLEDGE                              PROJECTIONS
        |                                           |
 immutable evidence                         Graphiti + Neo4j
 append-only events                         lexical/vector index
 pack manifests                             RDF/PROV/SKOS export
 ontology versions                          analytics projection
 provenance                                 future databases
        |
 content-addressed artifacts
```

Operational telemetry is outside the canonical corpus. Durable state-changing audit/provenance events remain inside it.

## 3. Durable evidence

Original evidence is immutable. Large binaries live in a content-addressed artifact store; Git tracks manifests and small durable text artifacts where practical.

Every artifact receives a corpus-owned stable ID and content hash. Derived claims must resolve to a source artifact/episode/span when the source permits exact addressing.

A summary never replaces its source. A newer source snapshot never silently overwrites the earlier snapshot.

## 4. Append-only knowledge events

Knowledge changes are represented as immutable events rather than destructive mutations.

Examples:

- claim proposed;
- evidence attached;
- claim challenged;
- claim state changed;
- relation proposed/invalidated;
- claim superseded;
- ontology concept created/renamed/split/merged;
- project knowledge promoted into a domain/common pack;
- source marked stale/retracted;
- redaction/suppression requested;
- projection build completed/failed.

The first storage representation is **one immutable JSON event per file**, validated by JSON Schema. Bulk JSONL is an export format, not the concurrent authoring format. This prevents one giant append file from becoming a Git/agent merge-conflict hotspot.

The event envelope borrows useful ideas from CloudEvents (`id`, `source`, `type`, `time`, schema/version fields) without making CloudEvents itself the domain model.

## 5. Stable identity

Never use Neo4j node IDs, file paths, array positions, vector IDs, or database sequence numbers as durable knowledge identity.

Stable IDs belong to this corpus and survive:

- database rebuilds;
- ontology renames;
- repository movement;
- physical sharding;
- graph database replacement;
- embedding replacement.

Cross-pack references use stable IDs/URIs, never relative filesystem coupling.

## 6. Knowledge packs and boundaries

A **knowledge pack** is a logical portable boundary.

Examples:

```text
common/research-methods
domain/swe
domain/database
domain/ai-systems
project/plugin-harness
project/adaptive-learning
```

Each pack has one stable `pack_id`, a type (`common`, `domain`, `project`, or later another declared type), versioned contract metadata, dependencies, read mounts, and default write target.

Pack identity is separate from physical placement. A pack may later move from shared storage to a dedicated database/shard/repository without changing its identity.

`pack_id` maps to Graphiti `group_id` in the first graph projection, but Graphiti's namespace is **not** the canonical identity model.

### Read/write rule

Agents receive an explicit manifest of readable packs and writable pack(s). Shared knowledge can be read without granting the right to modify it.

Cross-boundary writes and promotion are explicit events. Search is restricted to mounted packs before results become context.

## 7. Claim and relationship lifecycle

A claim is not a boolean truth value.

Core claim states initially include:

- `proposed`
- `open`
- `supported`
- `disputed`
- `rejected`
- `superseded`
- `retracted`
- `stale_pending_review`

A state change creates an event with reasons/evidence. Earlier states remain reconstructable.

Relationships also have lifecycle/provenance. A relationship such as `SUPPORTS`, `CHALLENGES`, `CONTRADICTS`, `REFINES`, `DEPENDS_ON`, `ASSUMES`, `DERIVED_FROM`, or `SUPERSEDES` can itself become inactive/superseded without destroying history.

`DISPUTED` is a valid long-lived state. The system must not force consensus when evidence is insufficient.

## 8. Source quality

Do not collapse source quality to one universal tier.

Store independent properties such as source type, primary/secondary status, domain authority, directness to the claim, methodology, publication/retrieval dates, conflicts of interest when known, replication/reproducibility, and current validity.

A computed source tier may be useful for a particular question, but it must remain derived from these dimensions.

Model agreement is not external evidence.

## 9. Proposal before commit

Agents do not receive arbitrary graph/database mutation as their normal interface.

```text
agent/model
   -> structured proposal
   -> schema validation
   -> stable-reference validation
   -> namespace/write-scope check
   -> provenance/evidence requirements
   -> policy/risk gate
   -> atomic durable event commit
   -> asynchronous projection update
```

High-risk knowledge changes can require stronger external verification or cross-model review. The deterministic gate owns the final state-changing transaction.

## 10. Graph projection

The initial living graph is Graphiti + local Neo4j because Graphiti already provides temporal episodes/facts, provenance, custom entity/edge types, namespaces, and hybrid graph/text/vector retrieval.

However:

- Graphiti/Neo4j are projection technology;
- custom ontology definitions remain versioned outside Graphiti;
- accepted knowledge events exist before graph projection succeeds;
- projection workers are idempotent and retryable;
- failed projection work enters a retry/dead-letter state instead of losing the durable event.

A hard invariant is:

```text
delete graph storage
-> rebuild projection from durable evidence/events
-> pass semantic invariants and reconstruction benchmarks
```

## 11. Migration model

Migration is expected.

### Small additive change

`expand -> backfill -> verify -> switch readers -> remove old projection later`

### Dangerous structural change

Use blue/green projections:

```text
same durable evidence/events
        |             |
    projection A  projection B
       current       candidate
```

Build B independently, run invariant/retrieval/reconstruction tests, then change the active projection pointer. Keep A until confidence is sufficient.

Do not demand reversible destructive down-migrations. Prefer preserved history + forward migration + rollback by projection switch.

Independently version:

- event schema;
- pack schema;
- ontology;
- graph projection;
- corpus API;
- Graphiti;
- Neo4j;
- embedding model;
- retrieval policy;
- Agent Skills.

Every projection build records a reproducibility manifest containing code commit, schema/ontology versions, model/provider identifiers, prompts/configuration, graph/runtime versions, and source event range.

## 12. Retrieval and future model services

Storage, retrieval, context construction, and reasoning are separate.

Interfaces are planned for:

- `ContextProvider`
- `Retriever`
- `EmbeddingProvider`
- `Reranker`
- `ModelService`
- `VerificationService`

This prevents permanent coupling to one assumption such as "vector RAG with 20 chunks". Future long-context/linear-attention models, graph retrieval, BM25, static local embeddings, late-interaction models, or other systems can compete behind adapters.

Cheap/local models may be excellent for candidate generation, tagging, deduplication, routing, citation matching, and anomaly screening. Higher-risk truth-state changes require stronger evidence and can escalate to more capable/cross-vendor models. Specialization must be earned by corpus-specific evaluation.

## 13. Skills, MCP, and API

**Agent Skills = methodology.** They teach procedures such as source verification, contradiction review, knowledge promotion, and citation audit and can load progressively only when needed.

**Corpus API/MCP = capability.** The external surface stays small, for example:

- `search`
- `read`
- `lineage`
- `propose`
- `validate`
- `commit`
- `manage`

MCP is an adapter, not the internal service contract. Local scripts/CLI can use the same domain service directly.

## 14. Harness integration

The corpus is intended to support a coding/research harness around Codex, Claude, or other agents.

The harness may route difficult work into independent model lanes and require:

- provenance;
- citations;
- source-quality assessment;
- risk tiering;
- competing theories;
- explicit assumptions;
- KEDB-style failure knowledge;
- MAPE-K-style observe/analyze/plan/execute/knowledge loops;
- cross-vendor criticism;
- external tests/sources as truth signals;
- claim/relation lifecycle changes stored durably.

Multiple models agreeing is metadata, not proof.

## 15. Observability

High-volume operational data stays outside the durable graph:

- traces;
- token/tool events;
- timing;
- stack traces;
- CPU/GPU metrics;
- verbose debug logs.

The corpus stores durable references such as run ID, trace ID, model/harness/skill versions, affected proposal/event IDs, outcome, and important failure classification.

## 16. Redaction and deletion

Append-only history cannot mean "sensitive data can never be removed." The contract therefore distinguishes historical knowledge revision from content suppression/redaction.

A future redaction operation must be explicit, auditable, and able to remove/suppress sensitive payloads from active projections and exports while retaining only the minimum non-sensitive tombstone needed to explain that an object was intentionally removed. Exact policy depends on the eventual data sensitivity and legal requirements.

## 17. Non-goals for the first executable build

Do not build prematurely:

- distributed physical sharding;
- Kubernetes;
- Redis;
- Elasticsearch/OpenSearch;
- Citus;
- dedicated vector database;
- custom authentication/OAuth;
- autonomous ontology rewriting;
- a large dashboard;
- dozens of local model servers.

Start localhost-only with the smallest useful projection and prove the durable contracts first.

## 18. Acceptance invariants

Before calling the system durable enough for real ingestion:

1. Every derived claim resolves to provenance/evidence or is explicitly marked unsourced/proposed.
2. Earlier claim states and disagreements survive later revisions.
3. Pack isolation tests pass.
4. Cross-pack references use stable IDs.
5. Superseded temporal knowledge remains historically reconstructable.
6. A graph can be destroyed and rebuilt.
7. A second projection can be built beside the first and compared.
8. Stable IDs survive rebuilds and ontology renames.
9. Duplicate ingestion is idempotent.
10. Failed graph projection cannot lose an accepted durable event.
11. Known reconstruction questions recover the intellectual path, not only the final summary.
12. Source/citation references resolve to the intended evidence snapshot.
