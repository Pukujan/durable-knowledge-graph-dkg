# Research Trace Contract

**Status:** frozen extension to the durable architecture  
**Date:** 2026-08-09

## Purpose

The corpus must be able to reconstruct **how a project was researched**, not only store the conclusions that survived.

A later knowledge graph should be able to answer questions such as:

- What question originally triggered this architecture decision?
- Which competing designs were considered?
- Which searches and source families were used?
- Which source/version was actually inspected?
- What claim did each source support, challenge, or leave unresolved?
- Which model/agent proposed a claim or critique?
- Which conclusions changed after criticism?
- Which alternatives were rejected, and why?
- What remained uncertain at the time a decision was made?
- Which implementation issue or commit resulted from the research?
- Which later evidence superseded an earlier research conclusion?

The research process is therefore **first-class evidence and provenance**, not disposable chat/log output.

## Durable objects

The first research-trace ontology should be able to represent at least:

- `ResearchQuestion`
- `ResearchRun`
- `SearchQuery`
- `SourceSnapshot`
- `SourceAssessment`
- `Claim`
- `Assumption`
- `EvidenceAssertion`
- `Critique`
- `AlternativeTheory`
- `Decision`
- `Uncertainty`
- `ExperimentOrBenchmark`
- `ImplementationAction`
- `AgentOrHumanActor`
- `ModelRunReference`

High-volume model traces remain in observability storage; the durable corpus stores only the compact references needed to reproduce or audit the research decision.

## Core relationships

Useful initial relationships include:

- `ASKED_DURING`
- `SEARCHED_FOR`
- `RETURNED_SOURCE`
- `INSPECTED_SOURCE`
- `DERIVED_FROM`
- `SUPPORTS`
- `CHALLENGES`
- `CONTRADICTS`
- `REFINES`
- `ASSUMES`
- `CRITIQUES`
- `COMPETES_WITH`
- `SELECTED_OVER`
- `REJECTED_BECAUSE`
- `LEFT_UNRESOLVED`
- `SUPERSEDES`
- `MOTIVATED`
- `IMPLEMENTED_BY`
- `VERIFIED_BY`
- `FAILED_BY`
- `RECORDED_IN`

Relationship state and provenance follow the normal durable claim/relation lifecycle contract.

## Research run envelope

Each meaningful research pass should have a stable corpus-owned `research_run_id` and record, at minimum:

- research question / scope;
- start and end times;
- initiating artifact/issue/conversation reference;
- actor(s), model(s), harness/skill versions where applicable;
- search strategy or source families examined;
- source snapshots actually inspected;
- candidate claims extracted;
- critiques and competing explanations;
- decision state (`open`, `provisional`, `accepted_for_now`, `rejected`, `superseded`);
- unresolved questions;
- implementation actions/issues/commits produced;
- references to operational trace IDs when useful;
- code commit, schema version, ontology version, and research-policy version.

## Source handling

A URL in a bibliography is not sufficient provenance.

For important sources, preserve the best available version identity:

- canonical identifier/URL;
- title/authors/publisher where available;
- publication/update time where available;
- retrieval time;
- version/release/commit identifier where available;
- content hash or snapshot identity when legally/practically possible;
- exact passage/span reference when the evidence is locally addressable;
- source-quality dimensions;
- what claim(s) the source was actually used for.

A later source update does not silently rewrite what the research run saw.

## Model/agent evidence rule

Model output is **research-process evidence**, not external factual evidence.

Example:

> Model B challenged Claim C because Source S appears inconsistent with it.

This is useful provenance and should survive. It does not make the challenge true. The external source, experiment, test, or other truth signal carries the evidentiary weight.

Cross-vendor/model agreement is stored as review metadata, not multiplied into independent external evidence.

## Decision lineage

A decision should be reconstructable as a path, for example:

```text
ResearchQuestion
   -> Alternative A
   -> Alternative B
   -> Source/benchmark evidence
   -> Critique of A
   -> Critique of B
   -> unresolved uncertainty
   -> accepted-for-now Decision D
   -> GitHub issue / architecture contract / code commit
```

If later evidence changes D, the new decision **supersedes** D and points to the new research run. D remains historically queryable.

## Project-management integration

GitHub issues, PRs, commits, architecture documents, and benchmark artifacts are valid project-state evidence.

They should be linked into the research graph rather than copied wholesale into it. For example:

```text
ResearchRun R17
  MOTIVATED -> Issue #4
  PRODUCED -> Decision D22
  IMPLEMENTED_BY -> Commit abc123
  VERIFIED_BY -> Benchmark B9
```

The durable research trace therefore joins **why**, **evidence**, **decision**, and **implementation**.

## This project's first trace

The research that produced the Durable Knowledge Graph architecture should itself become the first serious research-trace dataset.

At minimum it should preserve:

- the conversation/recovery artifacts that motivated the system;
- the 127-source evidence ledger;
- architecture alternatives considered (SQLite-first, PostgreSQL-first, Graphiti/Neo4j projection, vector-first systems, graph-first systems, plain-file/event-store approaches);
- the reasons individual choices changed over the conversation;
- source-backed research on temporal graphs, provenance, knowledge boundaries, migrations, context/harness engineering, Skills/MCP, long-context attention, retrieval and local specialist models;
- remaining unresolved questions;
- GitHub issues #1 onward and the commits they produce.

This is deliberately recursive: **the first knowledge graph must eventually be able to explain how the knowledge-graph project itself was researched and built.**

## Non-goal

Do not store every token, hidden chain-of-thought, HTTP trace, or intermediate model message in the canonical corpus.

The goal is an auditable intellectual lineage made from durable evidence, explicit claims, decisions, critiques, and compact run references—not an infinite debug log.
