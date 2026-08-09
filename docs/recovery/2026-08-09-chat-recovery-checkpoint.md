# Recovery Checkpoint — 2026-08-09

**Status:** reconstructed checkpoint, **not a verbatim transcript** of the missing UI messages.

This file exists because part of the visible chat history appears to have disappeared or desynchronized. It records only material that can still be supported by the surviving conversation context, accessible generated files, and the user's current reconstruction. Missing wording is deliberately not invented.

## Surviving durable artifacts

The conversation still exposed at recovery time:
- `learning_ai_systems_self_reflection.docx`
- `living_research_corpus.zip`
- `knowledge.db`

The later "evidence package / frozen contract" described by the user was not exposed as a retained conversation file at recovery time.

## Recovered architecture direction

The later design had moved beyond the original SQLite prototype toward a migration-safe durable knowledge system:

- immutable original evidence/artifacts
- append-only, versioned knowledge events
- stable IDs owned by the corpus rather than a database vendor
- Graphiti + Neo4j as a rebuildable temporal/knowledge-graph projection
- custom claim/argument/assumption/evidence ontology
- namespaces / project and domain boundaries
- provenance and temporal validity
- disagreement preserved as first-class data
- blue/green projection rebuilds for dangerous migrations
- Agent Skills for lazily loaded methodology
- a thin local API/MCP surface for agent interoperability
- external telemetry rather than stuffing operational logs into the knowledge graph
- rebuildability as a hard invariant: deleting the graph must not destroy intellectual history

## Newly recovered harness requirement

The knowledge corpus is also intended to support a **coding/research harness** that can wrap Codex, Claude, or other mature coding agents.

The harness should be capable of:

- enforcing a repeatable user-defined workflow rather than accepting the coding agent's default behavior
- routing hard tasks into multiple pre-written model lanes
- using many frontier model/model endpoints for parallel/adversarial review when justified
- cross-vendor challenge rather than same-model self-validation
- requiring provenance for important claims and decisions
- requiring citations and source tiering/quality analysis
- risk-tiering claims/actions so higher-risk work receives stronger verification
- preserving parallel theories instead of collapsing early to one answer
- integrating KEDB-style failure knowledge and MAPE-K-style monitor/analyze/plan/execute/knowledge loops
- having models attack one another's claims with independent sources
- preserving claim lifecycle states such as open, disputed, supported, rejected, superseded, retracted, and stale/pending review
- representing claim relationships and supersession in the operational graph
- making the corpus usable by agents as durable research/engineering memory, not merely passive RAG

## Important distinction

The system should not treat "three models agree" as evidence.

Model agreement is metadata. Evidence must still resolve to sources, experiments, tests, or other external truth signals.

The desired pattern is closer to:

1. produce candidate claim
2. preserve its origin
3. retrieve supporting evidence
4. route independent critics
5. retrieve counterevidence
6. classify risk
7. preserve unresolved disagreement
8. verify against external signals where possible
9. update claim state
10. record why the state changed
11. propagate staleness to dependent claims without silently rewriting history

## Missing material

What was **not** recoverable verbatim from the visible conversation at checkpoint time:

- the exact lost conversation with the other person
- their precise claims and wording
- the exact source list used in the lost research pass
- the exact later "evidence package / frozen contract" files, if generated but not retained by the conversation file surface
- any exact claim-state schema added only in the missing turn

If screenshots, copied text, exported chat data, or a local copy of the later package becomes available, it should be ingested as primary evidence rather than reconstructed from memory.

## Recovery rule going forward

Every major architecture decision should be checkpointed outside the chat as an append-only artifact before continuing.

At minimum each checkpoint should record:

- date/time
- claim/decision
- alternatives considered
- evidence and citations
- objections
- unresolved disagreement
- decision state
- supersedes / superseded-by links
- implementation version
- migration implications
- exact source artifact references
