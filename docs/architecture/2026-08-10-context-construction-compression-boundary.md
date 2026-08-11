# Context Construction and Compression Boundary

**Date:** 2026-08-10  
**Status:** accepted design boundary; benchmark and implementation pending  
**Refines:** `docs/architecture/2026-08-10-cortex-fossil-ownership-boundary.md`

## Decision

Compression is split into **control policy** and **evidence-safe context construction**.

- **Cortex owns the task-level budget decision:** how much context a worker may receive, latency/cost preference, whether compression is allowed, and whether the task should instead direct-read, expand the budget, or decompose.
- **FOSSIL owns evidence-safe context construction over FOSSIL knowledge:** selection, retrieval-resolved source/claim/citation identity, protected-span handling, and any lossy compression applied to FOSSIL-sourced context.
- A FOSSIL implementation should live behind the replaceable `ContextProvider`/context-construction service boundary rather than becoming durable-storage logic.
- Cortex may independently compress its own operational/session notes because those are Cortex working memory, not FOSSIL evidence.

This split prevents Cortex from becoming a second RAG implementation while keeping orchestration decisions in the harness.

## Invariant

**A compressed packet is a temporary execution view. It never replaces, rewrites, or upgrades the authority of its source evidence.**

The source snapshot/span/hash remains the citation target. A summary is derived context, not the cited original.

## Prior art being retained

The legacy `stupidly-simple-cortex` GAP-CORTEX-0011 work is useful prior art, especially:

1. select/retrieve before compressing;
2. retain protected/high-relevance material verbatim;
3. content-type-specific reduction rather than one universal compressor;
4. fail closed when protected material disappears;
5. explicitly decompose/escalate when safe compression cannot fit the target budget.

That implementation is **not** imported as authority and the old SSC runtime is not a dependency. The ideas must be re-expressed behind the FOSSIL context contract and re-evaluated.

## Required pipeline

Conceptually:

```text
Cortex request
  task/query class
  readable pack/sensitivity scope
  target context budget
  direct-read/compression/decompose permissions
        |
        v
FOSSIL retrieval + lifecycle/lineage resolution
        |
        v
ACL/redaction/suppression filter
        |
        v
selection/ranking of eligible evidence
        |
        v
FOSSIL ContextProvider
  protected-span registry
  content-aware skeletonization/extraction
  optional lossy prose compression
  preservation verification
        |
        +--> context packet fits -> return packet + mapping/receipt
        |
        +--> cannot fit safely -> explicit NEEDS_DECOMPOSITION / LARGER_CONTEXT

Cortex then decides whether to decompose, direct-read, change worker/model, or request a larger budget.
```

Compression never runs before pack/sensitivity filtering.

## Protected material

At minimum the preservation contract must be able to protect:

- stable FOSSIL source IDs;
- claim/relation IDs when supplied to the model;
- citation IDs;
- exact citation spans required by the task;
- source snapshot hashes/revision identifiers where present;
- numbers and units when material to a claim;
- dates when material to temporal reasoning;
- code identifiers, symbols, API names, file paths, and exact configuration keys when material;
- explicit lifecycle terms needed to distinguish current/superseded/disputed/retracted state;
- provenance identifiers required to reconstruct source → derived context lineage.

Not every number/token in a large document must always be protected. Protection is task/context-contract driven, and the preservation report must record what was designated protected.

## Content-type handling

The initial benchmark should distinguish at least:

- prose;
- code/configuration;
- tables/structured records;
- numeric/financial material;
- citation-heavy research;
- lifecycle/lineage histories.

A single lossy prose compressor must not be assumed safe for all of them.

Preferred order:

1. **selection first** — remove irrelevant evidence before transforming relevant evidence;
2. **verbatim protected/high-value slices**;
3. **structure-preserving extraction/skeletonization** where possible;
4. **optional lossy prose compression** only on eligible surviving prose;
5. **verification** of protected spans and source mapping;
6. **decomposition/escalation** if the budget remains impossible.

## Failure semantics

Compression must fail closed when:

- a required protected span cannot be restored exactly;
- source→compressed mapping is missing or ambiguous for cited material;
- compression crosses a pack/ACL/sensitivity boundary;
- redacted/suppressed material appears in the packet;
- a claimed citation can no longer resolve to the original immutable source span;
- required lifecycle/lineage distinction is lost;
- the target budget can be reached only by violating the preservation contract.

The terminal outcome is not `best_effort_success`. It is an explicit result such as:

- `larger_context_required`;
- `direct_source_read_required`;
- `decompose_required`;
- `unsafe_to_compress`.

## Untrusted-context rule

Compressed text remains untrusted model context and must remain compatible with `fossil-untrusted-context-v1`.

Compression cannot:

- turn source instructions into harness policy;
- generate a new trusted claim merely by summarizing several sources;
- bypass the deterministic lifecycle/lineage resolver;
- convert model confidence/consensus into evidence;
- silently invent or regenerate stable IDs/citations.

## Context-budget benchmark

A dedicated benchmark is required before enabling lossy compression in normal operation.

Suggested budgets:

- 8k;
- 16k;
- 32k;
- 64k;
- optionally a larger direct-read control when the selected model supports it.

Compare, under matched selected evidence where possible:

1. uncompressed retrieve-then-read;
2. selection-only context construction;
3. structure-preserving/extractive reduction;
4. safe compressed context;
5. decompose/direct-read route when compression cannot safely fit.

Measure at least:

- final-answer correctness;
- exact citation/source-snapshot correctness;
- unsupported-claim rate;
- current-vs-superseded leakage;
- lineage/history reconstruction correctness;
- numeric/date/code-identifier preservation;
- protected-span preservation rate;
- source→compressed mapping completeness;
- compression ratio;
- context tokens/bytes before and after;
- latency;
- memory/resource use;
- model/provider cost when applicable;
- decomposition frequency;
- fail-closed frequency and reason;
- poisoning/untrusted-context compatibility;
- ACL/redaction non-leakage.

The simple uncompressed/selection-only baseline is mandatory. Compression earns deployment only if it improves the quality/resource frontier without weakening evidence guarantees.

## Query execution receipt extension

Workstream-F receipts should be extended or versioned to record context construction when compression is used:

- requested context budget;
- actual context size;
- ContextProvider/compressor name + version/revision;
- exact runtime/provider/model if a model-based compressor is used;
- selected input stable IDs;
- protected-span policy/version;
- protected-span count/hash or bounded preservation summary;
- compression stages/strategy;
- source→compressed mapping identity;
- final context IDs;
- preservation verification result;
- compression/decomposition/fallback outcome;
- latency/cost/resource observations;
- run/trace reference.

The receipt remains observability/replay evidence, not truth authority.

## Security dependency

Workstream G must prove that every context-construction route obeys the same pack/ACL/redaction boundary.

Hard rule:

**filter first, compress second.**

A compressor must never receive inaccessible source material and then be expected to redact it afterward. This limits accidental leakage through summaries, embeddings, caches, or restoration buffers.

## Relationship to retrieval/model bakeoff

Do not mix compression changes into the matched Workstream-D embedding/reranker benchmark until the context-budget benchmark is versioned. Finish a clean D stage-2 comparison first or run compression as a separately named/receipted factor.

Better retrieval may reduce the need for aggressive compression. Safe context construction may reduce the need to escalate embedding/model size. Therefore the 4B/8B decision should consider results from the context-budget benchmark rather than assume larger models are the next step.

## Implementation sequence

1. freeze this preservation/context contract;
2. add preservation-report data model + tests;
3. implement selection-only ContextProvider baseline;
4. add content-type-aware structure-preserving reduction;
5. add optional lossy prose compressor behind an adapter only if justified;
6. extend Workstream-F receipts for context construction;
7. run matched context-budget benchmark;
8. run poisoning + lifecycle/lineage + citation regression suites;
9. run ACL/redaction tests before shared deployment;
10. accept, reject, or constrain compression with an explicit decision record.

## Non-goals

This decision does not authorize:

- replacing immutable source evidence with summaries;
- storing compressed packets as canonical snapshots of the source;
- soft-token/activation compression as durable knowledge;
- a model summarizer becoming truth authority;
- compressor access around pack/ACL rules;
- universal claims that compression is safe.
