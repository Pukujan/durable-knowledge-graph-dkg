# Project State

**Current phase:** Research freeze complete → Gate 1 durable executable proof  
**Control plane:** GitHub issues + durable repository docs  
**Last updated:** 2026-08-09

## Continuation entry point

A new agent/session should read:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/HANDOFF_CURRENT.md`
4. this file
5. `docs/research/2026-08-09-final-research-synthesis.md`
6. `docs/research/RESEARCH_TRACE_CONTRACT.md`
7. `docs/DECISION_LOG.md`
8. Issue #1 and the child issue being executed

The chat UI is **not** the project record.

## Tracking rule

GitHub issues track **work state**. Durable docs track **decisions/evidence/contracts**.

An issue may close because work was completed or rejected, but an architectural decision should not exist only inside an issue comment. It must point to a durable document/ADR/schema/benchmark result committed in the repository.

Likewise, durable docs should link to the issue that caused a decision when useful so implementation history remains reconstructable.

## Research-trace rule

The **research process itself is future corpus data**.

The graph must eventually be able to reconstruct how this project was researched: original questions, alternative architectures, searches/source snapshots, claims, critiques, unresolved uncertainty, accepted-for-now decisions, issues, commits, benchmarks, failures, and later supersession.

Durable trace references now include:

- `docs/research/RESEARCH_TRACE_CONTRACT.md`
- `schemas/research-trace/v1.schema.json`
- `docs/research/2026-08-09-dkg-project-research-trace-seed.md`
- `examples/research-trace/dkg-project-research-run-v1.json`

High-volume operational telemetry remains external. The durable corpus stores compact intellectual lineage plus trace IDs when deeper debugging evidence is needed.

## Milestone structure

The GitHub connector currently available to the assistant can create/update issues but cannot create a new GitHub Milestone or a native sub-issue relationship. Until an actual milestone is created through GitHub UI/API support, top-level Issue #1 acts as the milestone control issue and child issues use explicit `Parent: #1` links plus a checklist on the parent.

When a real GitHub milestone exists, the child issues can be assigned to it without changing the durable plan.

## Gate 0 — complete

Research freeze and durable contracts now include:

- 127-source evidence ledger;
- final research synthesis;
- architecture contract;
- event schema v1;
- knowledge-pack schema v1;
- research-trace contract/schema/seed;
- core ontology skeleton;
- source-quality policy;
- projection/model interface skeletons;
- migration/rebuild benchmark direction;
- project/agent boundary rules;
- chat-history recovery checkpoint;
- durable agent continuation contract (`AGENTS.md`);
- current handoff (`docs/HANDOFF_CURRENT.md`);
- durable decision log (`docs/DECISION_LOG.md`);
- research update protocol (`docs/research/README.md`).

## Gate 1 — executable durability proof

The first executable build is accepted only if it can:

1. create and validate immutable events;
2. reject invalid/duplicate writes deterministically;
3. enforce pack read/write boundaries;
4. preserve claim/relation disagreement and supersession;
5. materialize an initial Graphiti/Neo4j projection from already accepted durable events;
6. destroy/rebuild the graph from durable data;
7. build a second candidate projection beside the first;
8. answer lineage/reconstruction benchmark questions;
9. resolve citations/provenance to the intended evidence snapshot;
10. record projection/model/schema versions used;
11. survive projection failure without losing an accepted durable event;
12. reconstruct how a research decision moved from question/evidence/critique to implementation.

## Current issue map

- #1 Milestone-control issue
- #2 Durable event + artifact store with validation/idempotency
- #3 Knowledge-pack boundaries, mounts, and promotion
- #4 Graphiti + Neo4j projection adapter and projection queue
- #5 Destructive rebuild + blue/green migration harness
- #6 Claim/relation lifecycle, disagreement, supersession, staleness
- #7 Pluggable retrieval/model services + local-specialist benchmark contract
- #8 Agent Skills + thin corpus API/MCP contract
- #9 Conversation ingestion + intellectual-lineage reconstruction benchmark
- #10 Source snapshots, citation provenance, quality dimensions, redaction path

## Recommended execution order

Unless a failing benchmark changes it:

`#2 -> #3 -> #6 -> #4 -> #5 -> #9 -> #8 -> #7`

Issue #10 contributes requirements across these stages and should be hardened when source ingestion/redaction becomes executable.

The research-trace contract should be exercised through #9 rather than implemented as a separate large subsystem.

## Immediate next task

Continue **Issue #2**. Inspect current code before rewriting anything. Prove the durable filesystem event/artifact layer, idempotency, validation, stable IDs, atomic writes, and malformed/duplicate fixtures while keeping Neo4j/Graphiti optional.

Then execute **Issue #3** and prove knowledge-pack boundaries before creating separate external pack repositories.

## Knowledge repository split

Do **not** call future Git repositories database shards.

The platform repository is this repo. Future knowledge repositories are **knowledge-pack repositories** that implement the same pack contract.

After Issue #3 passes, the first two external pack repos can reasonably be:

1. a shared/common knowledge pack;
2. a domain/project pack such as AI systems / plugin harness research.

At runtime these packs can map to separate graph namespaces. Later they can map to actual physical shards/databases if scale requires it, without changing their stable `pack_id`.

## Research status

Broad architecture research is frozen enough to implement. New technologies should be tested as adapters/projections against explicit benchmarks rather than causing another broad architecture rewrite.

Reopen architecture research when implementation contradicts an assumption, a dependency materially changes/decays, a new requirement appears, or a competing architecture wins measured benchmarks.

## Continuity checkpoint status

The repository now contains enough durable orientation material that a fresh agent should not need the missing chat to resume. `AGENTS.md` gives the read order and non-negotiable rules; `docs/HANDOFF_CURRENT.md` gives the exact continuation point; `docs/DECISION_LOG.md` preserves major choices and alternatives; the research-trace contract preserves how research itself becomes corpus data.

If a new session cannot continue from these files, treat that as a documentation defect and improve the handoff rather than asking the user to reconstruct the architecture manually.

## End-of-session rule

At the end of substantial work:

- update `docs/HANDOFF_CURRENT.md`;
- update this file if the gate or execution order changed;
- update relevant GitHub issue state/checklist;
- commit material benchmark/test results;
- update `docs/DECISION_LOG.md` for any architectural change;
- append or supersede the relevant research trace when new evidence changes a project decision.
