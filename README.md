# FOSSIL

**Fault-tolerant Open Semantic Store for Intellectual Lineage**

A local-first, migration-safe knowledge system for durable research and agent memory.

> **Evidence is durable. History is explainable. Interpretations can evolve. Databases are replaceable. Disagreement is data. Every conclusion must be able to explain where it came from.**

The durable substrate is **DICS — Durable Intellectual Corpus System**.

## License and rights

**FOSSIL is proprietary software and is not open source.**

Copyright © 2026 Pukujan. **All rights reserved.** No license is granted to use, copy, modify, distribute, sublicense, sell, host, deploy, or create derivative works from this repository or its original contents, in whole or in part, without prior express written permission from the copyright holder.

Public visibility of this repository does not grant additional permission to use the code. Viewing or forking through GitHub remains subject only to the rights provided by GitHub's Terms of Service. Third-party software, dependencies, data, and other materials remain subject to their respective licenses and rights holders.

See [`LICENSE`](LICENSE) for the repository's proprietary rights notice.

## Repository family

- `fossil-core` — architecture, contracts, durable event/artifact core, projection adapters, storage/rebuild machinery, benchmarks, and project control plane;
- `fossil-common` — shared research and engineering methods, stable pack ID `pack_269099f7b2ba43b7a99b9427d64092de`;
- `fossil-ai-systems` — AI systems / plugin-harness knowledge, stable pack ID `pack_f024177f89a5442db84171c3dd7f58e5`, reading from `fossil-common`.

Repository names, graph namespaces, and physical database placement are operational details. Knowledge-pack identity remains the stable `pack_id`.

## Status

The durable/evidence foundation, Gate 1/Gate 2 work, post-Gate-2 hardening foundation, Graphiti redaction/rebuild proof, and current engineering-assurance baseline are complete.

The S3-compatible durability track has advanced through two important secretless milestones:

- a provider-neutral S3-compatible artifact/event adapter with fail-closed semantics;
- a real local/service-container S3-compatible fixture proof, merged in PR #123.

Current `main` at the 2026-08-15 checkpoint is:

`ea1d88fc114981915603ec46a401dca45acd5a11`

The active live durability gate is Issue #124 / `OBJECT_STORE_LIVE`: a narrowly scoped, non-production R2 candidate proof for live durability plus fresh hosted-runner rebuild from zero local state. R2 is a candidate, not architecture truth or a permanent provider decision.

FOSSIL has executable proof for:

- immutable validated durable events and content-addressed evidence;
- deterministic idempotency;
- portable knowledge-pack boundaries and provenance-preserving promotion;
- disagreement, lifecycle, supersession, and stale dependency replay;
- real Graphiti + Neo4j materialization with retry/failure history;
- destructive rebuild and guarded migration;
- conversation ingestion with explicit verbatim-vs-reconstructed provenance and intellectual-lineage reconstruction;
- a protocol-independent safe Agent Skill/API/MCP boundary;
- immutable source snapshots, exact byte-span citations, anti-laundering source roles, source quality dimensions, lifecycle, and exceptional privacy/legal redaction;
- real active Graphiti redaction plus fresh-rebuild non-resurrection;
- versioned pluggable retrieval/context/model/verification interfaces and benchmark/receipt contracts;
- provider-neutral S3-compatible artifact/event durability semantics;
- secretless real S3-compatible service-fixture compatibility and rebuild behavior.

The current operational graph implementation is **Graphiti + Neo4j**, but neither is the deepest source of truth. Graphs, embeddings, retrieval indexes, dashboards, models, Skills, protocol adapters, Cortex and LiteLLM remain rebuildable/replaceable around the durable corpus.

## External runtime boundary

Cortex V5 and LiteLLM/CKFF are currently treated as **read-only external execution/transport systems** from FOSSIL's perspective unless the owner separately authorizes changes to those repositories.

Current exact-SHA reconciliation is recorded in:

[`docs/operations/EXTERNAL-RUNTIME-RECONCILIATION-2026-08-15.md`](docs/operations/EXTERNAL-RUNTIME-RECONCILIATION-2026-08-15.md)

That reconciliation records the current Cortex V5 seating/transport contract and the current LiteLLM routing/timeout state, including known places where LiteLLM's dated documentation lags its exact source/config.

## Core layers

1. **Evidence** — immutable source snapshots/artifacts, exact source references, quality dimensions, lifecycle, and an explicit exceptional erasure path.
2. **Knowledge events** — append-only normal intellectual history describing proposals, challenges, support, supersession, lifecycle changes, and provenance.
3. **Knowledge packs** — portable logical boundaries for common, domain, and project knowledge.
4. **Ontology + provenance** — versioned semantics independent of graph/model vendors.
5. **Projection adapters** — Graphiti/Neo4j first; other storage/search systems remain replaceable.
6. **Durable storage adapters** — filesystem reference plus provider-neutral S3-compatible artifact/event storage behind the same domain semantics.
7. **Cognitive services** — versioned pluggable retrievers, embedders, rerankers, context providers, models, and verification services.
8. **Agent boundary** — lazily loaded Skills plus a thin protocol-independent corpus capability surface; no arbitrary graph mutation.
9. **Observability** — external traces/metrics/logs; only durable knowledge-changing provenance belongs in the corpus.

## Start here

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — architectural contract and non-goals.
- [`docs/HANDOFF_CURRENT.md`](docs/HANDOFF_CURRENT.md) — exact continuation point.
- [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) — current project/gate state.
- [`docs/operations/EXTERNAL-RUNTIME-RECONCILIATION-2026-08-15.md`](docs/operations/EXTERNAL-RUNTIME-RECONCILIATION-2026-08-15.md) — read-only Cortex V5/LiteLLM reconciliation.
- [`docs/operations/LITELLM-GATEWAY.md`](docs/operations/LITELLM-GATEWAY.md) — FOSSIL-side gateway consumption contract.
- [`docs/DECISION_LOG.md`](docs/DECISION_LOG.md) — durable architectural decisions.
- [`docs/implementation/2026-08-10-gate1-source-provenance-redaction-proof.md`](docs/implementation/2026-08-10-gate1-source-provenance-redaction-proof.md) — source/citation/redaction proof.
- [`docs/implementation/2026-08-10-retrieval-model-benchmark-contract-proof.md`](docs/implementation/2026-08-10-retrieval-model-benchmark-contract-proof.md) — cognitive-service/benchmark proof.
- [`schemas/knowledge-pack/v1.schema.json`](schemas/knowledge-pack/v1.schema.json) — portable pack contract.
- [`schemas/events/v1.schema.json`](schemas/events/v1.schema.json) — durable event envelope.
- [`schemas/benchmark/v1.schema.json`](schemas/benchmark/v1.schema.json) — retrieval/model benchmark result contract.

## Important terminology

A **knowledge pack** is a logical portable unit. It is **not** a physical database shard. A pack may move repository/database/partition without changing stable identity.

A **projection** is a rebuildable representation optimized for a workload. Neo4j/Graphiti, RDF, vector indexes, lexical indexes, analytics tables, or future databases can all be projections.

**Redaction** is not ordinary revision. Normal intellectual history is append-only. Privacy/legal erasure is an explicit exceptional tombstone-before-delete operation whose active projections and future rebuilds must respect the erasure.

**Model output is not evidence merely because models agree.** Model tier, route success, fallback, confidence and agreement are execution metadata; downstream truth-changing authority requires the separate evidence/risk policy.

## Current next campaign

The active next campaign is **not** a new model/framework rewrite. It is the live durability proof under Issue #124:

1. exact-SHA live write/durability semantics against a dedicated non-production R2 candidate prefix;
2. independent fresh hosted-runner rebuild from zero local FOSSIL state;
3. repeated rebuild/restartability;
4. redaction/non-resurrection;
5. fail-closed negative controls;
6. sanitized evidence with normal DKG green on the same head.

After that proof is completed or explicitly blocked, reconcile the evidence and choose the next **FOSSIL-only** gate. Do not automatically modify Cortex V5 or LiteLLM/CKFF as a side effect of FOSSIL continuation.
