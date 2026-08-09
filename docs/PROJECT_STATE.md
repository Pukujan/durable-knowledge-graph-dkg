# Project State

**Current phase:** Research freeze → durable executable skeleton  
**Control plane:** GitHub issues + durable repository docs  
**Last updated:** 2026-08-09

## Tracking rule

GitHub issues track **work state**. Durable docs track **decisions/evidence/contracts**.

An issue may close because work was completed or rejected, but an architectural decision should not exist only inside an issue comment. It must point to a durable document/ADR/schema/benchmark result committed in the repository.

Likewise, durable docs should link to the issue that caused a decision when useful so implementation history remains reconstructable.

## Milestone structure

The GitHub connector currently available to the assistant can create/update issues but cannot create a new GitHub Milestone or a native sub-issue relationship. Until an actual milestone is created through GitHub UI/API support, a top-level tracking issue acts as the milestone control issue and child issues use explicit `Parent: #N` links plus a checklist on the parent.

When a real GitHub milestone exists, the child issues can be assigned to it without changing the durable plan.

## Current gate

**Gate 0 — Research freeze and durable contracts**

Required outputs:

- final evidence ledger (100+ sources);
- final research synthesis;
- architecture contract;
- event schema;
- knowledge-pack schema;
- core ontology skeleton;
- projection adapter contract;
- migration/rebuild benchmark definitions;
- project/agent boundary rules;
- recovery checkpoint for the chat-history loss incident.

## Next gate

**Gate 1 — Executable durability proof**

The first executable build is accepted only if it can:

1. create and validate immutable events;
2. reject invalid/duplicate writes deterministically;
3. enforce pack read/write boundaries;
4. materialize an initial Graphiti/Neo4j projection;
5. preserve claim disagreement and supersession;
6. destroy/rebuild the graph from durable data;
7. build a second candidate projection beside the first;
8. answer lineage/reconstruction benchmark questions;
9. resolve citations/provenance to the original evidence;
10. record projection/model/schema versions used.

## Knowledge repository split

Do **not** call future Git repositories database shards.

The platform repository is this repo. Future knowledge repositories are **knowledge-pack repositories** that implement the same pack contract.

After the local pack examples pass validation, the first two external pack repos can reasonably be:

1. a shared/common knowledge pack;
2. a domain/project pack such as AI systems / plugin harness research.

At runtime these packs can map to separate graph namespaces. Later they can map to actual physical shards/databases if scale requires it, without changing their stable `pack_id`.
