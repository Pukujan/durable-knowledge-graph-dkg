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

## Current coordination state — 2026-08-15

FOSSIL's durable architecture is stable; current work is a **FOSSIL-only verification and continuation campaign**.

Use these sources in this order for live project state:

1. **Issue #86** — current cross-project architecture authority.
2. **Issue #94** — append-only execution queue, claims, and closeout ledger.
3. **Issue #116** — visible SDD/TDD for the current FOSSIL verification campaign.
4. `docs/HANDOFF_CURRENT.md` — fresh-agent handoff; it must defer to live #86/#94 when state has moved.

Completed dependencies must not be reopened without actual regression evidence:

- **Cortex V5** is the active execution runtime. `V5-ACCEPTANCE` received human PASS on 2026-08-14. Cortex V4 is preserved/frozen historical implementation evidence, not runtime authority.
- **LiteLLM/CKFF** gateway repair and Railway production-health reconciliation are closed completed. Transport/model/route health remains LiteLLM/CKFF-owned factual state; caller policy remains outside the gateway.
- The **trusted-local broker/verifier** foundation is closed completed under #96.

Current FOSSIL baseline at this documentation branch point:

- `main` is `27764c4ab20c196ee0bc76a0d020fc961a385c4e`, containing the merged PR #114 Graphiti/dependency repair and #82/#84/#88 fan-in.
- PR #115 remains at `c4432f577e6182efd4126c3bbd1171a1fb58cbbd`. Clean local verification passes.
- `FOSSIL-07A` completed a bounded repeatability experiment and closed **BLOCKED / NONDETERMINISTIC_GATE**: identical Graphiti runs on the same exact SHA produced materially different extraction outcomes (`0 entities/0 facts`, `5 entities/0 facts` with incomplete timeout, then `5 entities/2 facts` with final PASS).
- The variability is localized to the Graphiti LLM extraction/interpretation boundary, not the #115 receipt/schema contract or repaired dependency/import path. A later green rerun is not stable acceptance.
- PR #115 must not merge until the required semantic gate is stabilized without lowering what it proves.
- #87 secretless/local-fixture storage work remains gated until the current baseline is trustworthy.

Always re-fetch #94 before acting; the exact heads above are historical anchors, not a substitute for live claim/CI state.

## Proven foundation

Milestone 0 / Gate 1 and Gate 2 are complete. FOSSIL has executable proof for:

- immutable validated durable events and content-addressed evidence;
- deterministic idempotency;
- portable knowledge-pack boundaries and provenance-preserving promotion;
- disagreement, lifecycle, supersession, and stale dependency replay;
- Graphiti + Neo4j materialization behind a replaceable projection boundary;
- destructive rebuild and guarded blue/green migration;
- conversation ingestion with explicit verbatim-vs-reconstructed provenance and intellectual-lineage reconstruction;
- a protocol-independent safe Agent Skill/API/MCP boundary;
- immutable source snapshots, exact byte-span citations, anti-laundering source roles, source quality dimensions, lifecycle, and exceptional privacy/legal redaction;
- active Graphiti redaction plus fresh-rebuild non-resurrection;
- versioned pluggable retrieval/context/model/verification interfaces and benchmark contracts.

The current operational graph implementation is **Graphiti + Neo4j**, but neither is the deepest source of truth. Graphs, embeddings, retrieval indexes, dashboards, models, Skills, and protocol adapters remain rebuildable/replaceable around the durable corpus.

## Core layers

1. **Evidence** — immutable source snapshots/artifacts, exact source references, quality dimensions, lifecycle, and an explicit exceptional erasure path.
2. **Knowledge events** — append-only normal intellectual history describing proposals, challenges, support, supersession, lifecycle changes, and provenance.
3. **Knowledge packs** — portable logical boundaries for common, domain, and project knowledge.
4. **Ontology + provenance** — versioned semantics independent of graph/model vendors.
5. **Projection adapters** — Graphiti/Neo4j first; other storage/search systems remain replaceable.
6. **Cognitive services** — versioned pluggable retrievers, embedders, rerankers, context providers, local/frontier models, and verification services.
7. **Agent boundary** — lazily loaded Skills plus a thin protocol-independent corpus capability surface; no arbitrary graph mutation.
8. **Observability** — external traces/metrics/logs; only durable knowledge-changing provenance belongs in the corpus.

## Start here

- [`AGENTS.md`](AGENTS.md) — fresh-agent continuation contract and non-negotiable engineering rules.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — durable architectural contract and non-goals.
- [`docs/HANDOFF_CURRENT.md`](docs/HANDOFF_CURRENT.md) — current continuation point.
- [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) — current project state plus historical proof anchors.
- [`docs/DECISION_LOG.md`](docs/DECISION_LOG.md) — durable architectural decisions.
- [`docs/operations/LITELLM-GATEWAY.md`](docs/operations/LITELLM-GATEWAY.md) — gateway boundary and current completed-repair posture.
- [`schemas/knowledge-pack/v1.schema.json`](schemas/knowledge-pack/v1.schema.json) — portable pack contract.
- [`schemas/events/v1.schema.json`](schemas/events/v1.schema.json) — durable event envelope.

## Important terminology

A **knowledge pack** is a logical portable unit. It is **not** a physical database shard. A pack may move repository/database/partition without changing stable identity.

A **projection** is a rebuildable representation optimized for a workload. Neo4j/Graphiti, RDF, vector indexes, lexical indexes, analytics tables, or future databases can all be projections.

**Redaction** is not ordinary revision. Normal intellectual history is append-only. Privacy/legal erasure is an explicit exceptional tombstone-before-delete operation whose active projections and future rebuilds must respect the erasure.

**Model output is not evidence merely because models agree.** Small/local models may propose bounded candidates; downstream truth-changing authority requires the separate evidence/risk policy.

## Current continuation

Resolve the current FOSSIL baseline mechanically before expanding the roadmap: stabilize the required Graphiti semantic acceptance path without rerun-until-green or weakened semantics; verify the actual exact head; use owner-approved merges only; reconcile the remaining open FOSSIL work on the resulting baseline; then proceed to the eligible secretless/local-fixture portion of #87. Workstream #47 remains later retrieval/model-bakeoff roadmap work and is not the current execution authority.
