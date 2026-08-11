# Legacy SSC Engineering Retrospective — Lessons Without Integration

**Date:** 2026-08-10  
**Source system:** `Pukujan/stupidly-simple-cortex`  
**Primary source revision inspected:** `3b6668eff7a1859c37f1aa50c565f0387fdc4ffe`  
**Status:** historical engineering retrospective only  
**Authority:** non-normative; not a source of current FOSSIL/Cortex architecture or semantic truth

## Purpose

This document preserves engineering lessons from earlier `stupidly-simple-cortex` (SSC) development without importing SSC as a runtime dependency, architecture authority, or source of current semantic truth.

The old project contains substantial research, reviews, experiments, security work, state-machine design, retrieval work, evaluation machinery, orchestration ideas, provenance work, and audit history. Much of that work is useful for understanding *why* the current Cortex/FOSSIL ownership boundary exists. It should therefore be retained as project history even when its mechanisms are obsolete, failed, incomplete, or superseded.

The governing rule is:

> **Preserve the lesson and the evidence of the experiment. Do not inherit the old subsystem merely because the old research was thoughtful.**

This retrospective is deliberately separate from the legacy SSC evaluation-estate extraction. The evaluation estate contains potentially reusable benchmark/checker assets. This document instead records architectural and methodological learning.

## Non-integration rule

Nothing in this retrospective authorizes:

- copying SSC runtime components into FOSSIL or Cortex;
- mounting old SSC research prose as normal FOSSIL semantic memory;
- treating old SSC current-state/ontology values as truth;
- treating historical research claims as current evidence without independent revalidation;
- reintroducing the old SSC database, FTS/vector indexes, ontology, state engine, or MCP server as a live dependency;
- changing current Cortex/FOSSIL ownership merely because a prior design chose a different boundary.

Historical source material may be cited when documenting what happened in the project. Current architectural decisions still require current evidence, contracts, and tests.

## What the early research did well

### Evidence-tier discipline

The early Fable research handoff (`docs/research/fable-research-handoff-2026-07-03.md`) explicitly distinguished production-deployed evidence from design-only/WIP references and asked later reviewers to label those evidence tiers rather than blur them.

It also preserved correction history when imported research was wrong. The handoff describes prior uploaded research where quantitative or descriptive claims about PASTE, NabaOS, MARCH, and Letta were checked rather than trusted, and where errors were corrected before the material was allowed to influence the roadmap.

**Lesson that survives:** derived research is not self-authenticating. Decision-driving claims should be traceable to stronger sources and corrected openly when verification fails.

This principle is consistent with current FOSSIL provenance rules, but this retrospective does not claim the old research itself is current evidence.

### Adversarial, executable review

The July 2026 SSRF/fetch episode is a strong methodology example.

The sequence was approximately:

1. an independent deep review dogfooded the installed system;
2. a real `file://` local-file exfiltration path was demonstrated;
3. a separate TDD/fix contract was written;
4. implementation was performed against that contract;
5. another review exercised real local servers, redirects, large bodies, and the original exploit;
6. the follow-up review discovered a residual DNS-rebinding check/use gap even though the nominal contract suite passed.

Relevant historical artifacts include:

- `reviewed/opus-deep-review-2026-07-03.md`;
- `reviewed/ssrf-fix-contract-2026-07-03.md`;
- `reviewed/ssrf-fix-review-2026-07-03.md`;
- `reviewed/ssrf-r1-pinning-fix-contract-2026-07-03.md`;
- `reviewed/ssrf-r1-r2-pinning-fix-review-2026-07-04.md`;
- `evals/objective_ssrf_path_traversal_behavioral/`.

The follow-up review is particularly instructive: the initial critical primitive was closed, but live verification showed that validation-time DNS resolution and connection-time DNS resolution were still independent, leaving a DNS-rebinding TOCTOU path.

**Lesson that survives:** passing tests are not automatically proof of the security property. For important boundaries, independently attack the property itself, and record residual risk rather than declaring universal closure.

Current FOSSIL poisoning/security work follows a similar philosophy, but no old fetch implementation is adopted from SSC.

### Recognition of provenance and evidence preservation

Later SSC work explored owner directives, engineering logs, transcript audit, hashes/Merkle roots, and external timestamping in `docs/design/ownership-provenance/`.

One healthy property of that design is that it explicitly stated its own limit: until built and externally anchored, it provided zero cryptographic protection. It also distinguished what cryptography could prove (for example byte integrity/existence upper bounds) from what it could only corroborate or not prove at all.

**Lesson that survives:** a proposed control is not an implemented control, and an implemented mechanism should state precisely which proposition it establishes.

The current project should preserve that epistemic precision without inheriting the old design wholesale.

## What failed at the system level

The central retrospective conclusion is that SSC accumulated many individually reasonable subsystems without a sufficiently hard ownership model.

The resulting problem was not simply “too much code.” It was **multiple overlapping definitions of authority, state, retrieval, and contract ownership inside one project**.

### The corpus could not reliably know itself

The July 3 deep review found that the search/index discovery logic did not include several of the repository's own most important planning documents, including `docs/ROADMAP.md`, `docs/BUILD-PLAN.md`, `docs/PHASE-GATES.md`, and `docs/ARCHITECTURE.md`.

That produced an especially important failure mode:

> A system intended to be the project's memory could be unable to retrieve the documents that defined how the system itself should work.

No amount of reindexing could solve a discovery contract that excluded the relevant paths.

**Ownership lesson:** corpus discovery, project-control documentation, and runtime behavior need explicit contracts and tests. A memory system must not silently infer that its index coverage equals the set of authoritative project state.

### Retrieval false negatives looked like absence

The same deep review found a natural-language retrieval failure caused by the FTS5 query normalizer joining all terms with strict AND semantics. Queries for concepts that existed in the corpus returned zero results while an OR formulation returned many relevant hits.

This is a direct historical example of why current FOSSIL freezes the rule:

> top-k absence is not evidence of nonexistence.

**Lesson that survives:** retrieval is an access mechanism, not an ontology of what exists or what is true.

The current D021 policy and lifecycle/lineage resolution are current FOSSIL decisions; the historical SSC retrieval implementation is not reused.

### Documentation and runtime contracts diverged

The deep review also found that documented commands and installed commands diverged. For example, documentation referred to `cortex-write-log` as if it were a CLI command while the installed entrypoint was `cortex-audit` and `cortex-write-log` was a skill/protocol concept.

Separately, the Fable research handoff called out multiple non-reconciled MCP tool-name lists across different design documents, including naming that conflicted with the intended client/tool constraints.

**Ownership lesson:** one contract must own a public interface. Multiple documents may explain it, but they cannot each independently define it.

This is one reason the current Cortex/FOSSIL boundary assigns semantic APIs to FOSSIL and mission/tool orchestration to Cortex rather than allowing both to define overlapping surfaces.

### Concurrency and state responsibilities were mixed into the corpus

The early system used SQLite for search/index state and encountered concurrent writer crashes during normal multi-agent interleavings. At the same time, the project was evolving toward task state, agent orchestration, audit history, and corpus writes in the same overall system boundary.

SQLite itself was not the architectural failure. The problem was that operational concurrency, retrieval indexing, persistent memory, and orchestration were all becoming responsibilities of the same product without clearly distinct authority planes.

**Ownership lesson:** operational execution state and semantic knowledge state have different consistency/recovery requirements and should not be conflated merely because one database can physically store both.

## The state-machine research: a useful near-miss

The Fable state-machine design (`docs/research/STATE-MACHINE-DESIGN-fable-research-2026-07-06.md`) contains several strong bounded ideas:

- server-interpreted operational state;
- event sourcing;
- single-writer discipline;
- optimistic sequence fencing;
- idempotency keys;
- explicit task intent;
- legal-tool gating;
- deterministic gate checks before model/rubric checks;
- mechanism-vs-policy separation;
- versioned policy tables;
- referential-integrity validation before loading a routing/execution bundle;
- worker leases/heartbeats;
- explicit merge/single-writer behavior.

Those are useful historical ideas about **agent execution control**.

However, the same design also states that the server DB is “the only truth.” Inside a task-state engine, that statement can be read as “the only authority for operational task state.” Inside legacy SSC as a whole, it was dangerously ambiguous because SSC simultaneously contained or planned:

- corpus knowledge;
- ontology/current-state knowledge;
- audit history;
- project/task state;
- model/routing policy;
- retrieval indexes;
- evaluation results;
- provenance records;
- MCP orchestration.

The missing abstraction was not better state-machine theory. It was **truth-domain ownership**.

The current correction is explicit:

- **Cortex owns operational/execution truth** for a session/mission/task;
- **FOSSIL owns durable semantic knowledge truth** and its provenance/lifecycle/lineage;
- **versioned evaluation assets/checkers own benchmark-label authority within their stated scope**;
- **infrastructure/projections own no semantic truth merely because they host state**.

This is a retrospective interpretation, not a claim that the old state-machine design should be ported.

## Deep-audit, summarization, and context research

Early SSC research around “Deep Audit Mode” explored:

- recursive/hierarchical summarization;
- checkpointed intermediate summaries;
- source IDs carried through digests;
- “provenance, never replacement”;
- context-budget-aware batching;
- RAPTOR-style recursive structures;
- RAGAS-style faithfulness gates;
- Letta/MemGPT-style growing-memory analogies;
- direct-source drillback.

The important retrospective lesson is not that any one of those mechanisms is correct for current FOSSIL.

It is that the project correctly encountered a fundamental problem that remains relevant:

> persistent history grows faster than model context, so a control plane needs bounded context construction without allowing lossy summaries to become replacement evidence.

Current policy now places this at a cleaner boundary:

- Cortex owns task-level context budget and the decision to direct-read/decompose/escalate;
- FOSSIL `ContextProvider` owns evidence-safe context construction/compression of FOSSIL-sourced material;
- immutable FOSSIL evidence, IDs, citations, ACLs, redaction, lifecycle, and lineage remain authoritative;
- context compression must earn itself under matched benchmarks.

Therefore old deep-audit research is historical prior art only. It should not be cited as proof that the current compression strategy is correct.

## Research-mode and multi-agent lessons

Early research repeatedly explored lead/worker fan-out, model-tiering, boundary contracts, single-writer synthesis, worker isolation, checkpointing, and external research collection.

A recurring concern in those documents was duplicated agent work and coordination drift. Several designs attempted to solve this with stronger orchestration, worker claims, blackboards, reducers, or state machines.

The retrospective lesson is broader:

> stronger orchestration does not fix an ambiguous ownership boundary between subsystems.

A perfectly coordinated set of workers can still produce inconsistent system state when the corpus, task engine, ontology, audit system, and project-state documents each believe they own the same concept.

Current Cortex should coordinate agents; FOSSIL should resolve durable knowledge. Cross-plane integration should happen through narrow contracts instead of shared internal state.

## Why “one big smart system” failed despite good ideas

The old architecture can be summarized as a composition failure:

```text
reasonable local subsystem A
+ reasonable local subsystem B
+ reasonable local subsystem C
+ more policies, indexes, logs, agents, gates, and docs
--------------------------------------------------------
without explicit authority ownership
=
multiple competing sources of truth and hidden coupling
```

Symptoms included:

- search could not see critical control documents;
- retrieval false negatives looked like missing knowledge;
- multiple MCP interface definitions drifted;
- docs and executable entrypoints diverged;
- operational state, audit, memory, and retrieval lived too close together;
- security-sensitive fetch content could become searchable persistent corpus material;
- future designs kept adding new logs, state engines, provenance systems, evaluators, and orchestration layers to the same ownership domain;
- individually strong research recommendations accumulated without a single composition contract saying which subsystem had final authority for each concern.

The architectural correction is not “never build rich systems.” It is:

> **Every durable or executable concern gets one explicit owner, and all other components cross that boundary through versioned interfaces.**

## Principles that survived independently into the current design

The following principles appear in old SSC work and also make sense in the current architecture, but they are retained because they are independently justified by current FOSSIL/Cortex contracts—not because SSC established them as authority:

1. **Single writer per authoritative state domain.**
2. **Proposal/evidence before durable commit.**
3. **Provenance never replacement.**
4. **Deterministic checks before subjective model judgment where possible.**
5. **Adversarial/live verification for important security and correctness properties.**
6. **Explicit residual risk rather than universal-success claims.**
7. **Versioned policy and interface identities.**
8. **Reproducible evaluation assets and checker authority separated from model consensus.**
9. **Context budgets are real architectural constraints, but compression cannot redefine evidence.**
10. **Replaceable indexes/models/projections must not become truth merely because they are convenient.**
11. **Interface drift should fail visibly rather than silently producing divergent behavior.**
12. **Dogfood the system against its own real workflows; a memory/control system that cannot retrieve or obey its own current contracts is not coherent.**

## Classification scheme for future historical inventory

When more old SSC research or owner-supplied historical material is reviewed, classify it as one or more of:

- `validated_methodology_example` — an old process/experiment that demonstrated a useful evaluation/review method;
- `historical_lesson` — useful evidence about why a current principle exists;
- `failed_experiment` — a mechanism/design that materially failed or produced unacceptable behavior;
- `superseded_design` — coherent at the time but replaced by a newer ownership/contract model;
- `obsolete_unverified` — historical content whose decision-driving claims were not sufficiently verified;
- `historical_source_only` — worth preserving for project archaeology but not otherwise actionable.

These labels describe historical use, not semantic truth authority.

## Future source bundles

The GitHub revision above is not assumed complete. Additional historical research, transcripts, reports, datasets, or artifacts may exist outside the repository.

When the owner provides them later:

1. preserve each upload as a separate immutable source bundle;
2. record its source/date/context when known;
3. hash the raw bytes before normalization;
4. do not silently merge it into the GitHub-derived corpus;
5. classify historical lessons separately from reusable eval assets;
6. preserve contradictions and failed ideas rather than rewriting history into one clean narrative;
7. keep the no-integration rule unless a new, current decision explicitly authorizes a specific independently validated idea.

## Relationship to the evaluation estate

The evaluation estate has a different preservation path.

Potentially reusable hard-gold/semi-ground datasets, checkers, oracle gates, rubrics, frozen tests, resolvers, and related assets are being inventoried for standalone extraction under a separate content-addressed archive and deduplication policy.

This retrospective should not be used to decide that an eval asset is valid. Eval authority must be established from actual bytes, provenance, checker/test reproducibility, source/license status, and holdout/leakage controls.

## Relationship to normal FOSSIL memory

This retrospective may live in the FOSSIL repository as project documentation, but that does not mean historical SSC research should be mounted as normal semantic-memory evidence.

If FOSSIL later stores facts about this history, they should be explicit historical/provenance statements such as:

- a particular review occurred;
- a particular exploit was demonstrated;
- a particular design document existed at a particular revision;
- a particular mechanism was superseded or retired.

Do not convert old research conclusions directly into current claims such as “this architecture is correct” or “this model/library should be used.”

## Current architectural conclusion

The most important preserved lesson from SSC is:

> **Good local designs do not compose safely when ownership is ambiguous.**

The current architecture therefore keeps these ownership statements explicit:

> **Cortex owns execution. FOSSIL owns knowledge. FOSSIL projections retrieve knowledge. Infrastructure runs the components. Models propose; deterministic gates commit.**

and:

> **Operational truth, semantic knowledge truth, evaluation-label authority, and infrastructure state are different domains. No subsystem becomes owner of another domain merely because it stores, retrieves, summarizes, or executes data from it.**

That boundary is the principal architectural learning being carried forward. The old monolith itself is not.
