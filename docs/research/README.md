# Research Index

This directory is the durable research record behind the architecture. It exists so future sessions do not have to rediscover why decisions were made.

## Open research — not architecture authority

### Agent engineering methodology and executor options — 2026-08-11

`2026-08-11-agent-engineering-methodology-and-executor-options.md`

**Status: OPEN / UNDECIDED.** This trace preserves the current research on AI engineering preflight, GitHub Spec Kit, OpenAI harness engineering, Google production-readiness patterns, OpenCode, Aider, V4/SSC summon history, task granularity, and the unresolved executor boundary. It intentionally does **not** update `ARCHITECTURE.md` or `docs/DECISION_LOG.md`.

Research envelope:

- `examples/research-trace/2026-08-11-agent-methodology-executor-options.json`

Use this trace when another session needs to reconstruct why execution is currently treated as an executor bakeoff rather than an OpenCode/Aider/V4 conclusion.

## Frozen research set

### Final synthesis

`2026-08-09-final-research-synthesis.md`

Use this first. It explains what the research changed and which architecture was selected.

### Evidence ledger

`2026-08-09-evidence-ledger.md`

Companion source ledger containing the broad review of 127 primary/official sources and original papers used for the research freeze.

### Research trace contract

`RESEARCH_TRACE_CONTRACT.md`

Defines how the **research process itself** becomes durable corpus data: questions, searches, source snapshots, claims, critiques, alternative theories, decisions, uncertainty, implementation actions, benchmarks, and later supersession.

Supporting seed artifacts:

- `../schemas/research-trace/v1.schema.json` when resolved from repository root as `schemas/research-trace/v1.schema.json`;
- `2026-08-09-dkg-project-research-trace-seed.md`;
- repository example `examples/research-trace/dkg-project-research-run-v1.json`.

## Covered research areas

The frozen review includes:

- temporal knowledge graphs and Graphiti/Zep;
- Neo4j and graph operations;
- PostgreSQL, pgvector, Citus, Supabase/PostgREST;
- Qdrant, Milvus, Weaviate and multi-tenant/vector-database patterns;
- provenance and semantic standards: PROV, SKOS, RDF, OWL, SHACL;
- JSON Schema and CloudEvents-style event-envelope patterns;
- truth-maintenance and dependency/supersession ideas;
- RAG, GraphRAG, HippoRAG, LightRAG and contextual retrieval;
- context engineering and harness engineering;
- MCP and Agent Skills/progressive disclosure;
- long-context/attention work including Kimi Linear/MoBA;
- lightweight/local retrieval systems including Model2Vec/Potion, FastEmbed, BGE-M3 and ColBERT;
- agent memory systems;
- production tenancy/boundary patterns;
- migrations, rebuilds, backups, idempotency and disaster recovery.

## Evidence rule

Do not add a research claim merely because a model states it confidently.

Prefer, in order appropriate to the question:

- official specifications/documentation for what a protocol/product guarantees;
- original papers for research claims;
- primary repositories/release notes for implementation status;
- mature production documentation for operational patterns;
- independent empirical work for comparative performance claims.

Secondary articles can help discovery but should not silently become the primary evidence when a better source exists.

## Source quality

Do not reduce every source to one universal tier. Follow `policies/source-quality-v1.md` and record dimensions such as authority for the particular question, directness, primary/secondary status, methodology, date/version, conflicts, replication/reproducibility, and current validity.

## When to reopen research

The architecture research freeze should be reopened only when at least one is true:

1. an implementation test contradicts a frozen assumption;
2. a dependency becomes abandoned, unsafe, or materially changes its contract;
3. a new technology plausibly removes a major layer or failure mode;
4. measured corpus workload makes the current design inappropriate;
5. a security/legal requirement appears that the current contract cannot satisfy;
6. a benchmark shows a competing architecture materially better.

Interesting new papers alone are not enough to restart the architecture. They should first be evaluated as potential adapters/projections behind the existing contracts.

### Agent closeouts / skip authority (2026-08-15)

`2026-08-15-agent-closeout-memory-poison.md` and `2026-08-15-agent-closeout-memory-poison-trace.json`.

Provisional: closeout prose is not FOSSIL ingest and not a skip signal. “Don’t redo this” is a fail-closed receipt + live issue + hash match. Journal TTL scratch stays blank on purpose.

## How to add new research

For a meaningful new research pass:

1. create a dated research note in this directory;
2. create/update a research-trace record for the run;
3. state the question before searching;
4. include competing theories, not only confirming evidence;
5. cite primary/official sources where possible;
6. distinguish fact, inference, recommendation, and unresolved uncertainty;
7. state exactly which architecture decision is challenged or refined;
8. update `docs/DECISION_LOG.md` if the conclusion changes;
9. update `ARCHITECTURE.md` only if a durable invariant changes;
10. link resulting issues/commits/benchmarks so the graph can later connect research to implementation.

## Current research conclusion

Implementation should proceed. The next useful evidence is expected to come from durability, isolation, rebuild, lineage, retrieval, and migration benchmarks on the real corpus rather than from another broad technology survey.
