# Cortex–FOSSIL Ownership Boundary

**Date:** 2026-08-10  
**Status:** accepted architecture boundary, pending implementation wiring  
**Scope:** Cortex v4, FOSSIL, Gravebuster/local-PC deployment, and retirement of the legacy `stupidly-simple-cortex` runtime

## One-sentence invariant

**Cortex owns execution. FOSSIL owns knowledge. FOSSIL projections retrieve knowledge. Infrastructure runs the components. Models propose; deterministic gates commit.**

A second rule prevents future overlap:

**Cortex may decide when and why to ask memory; it cannot decide what durable memory means. FOSSIL may use replaceable models/retrievers internally; it cannot decide what an agent is allowed to do next.**

## Why this boundary exists

The legacy `stupidly-simple-cortex` system combined corpus/RAG, living ontology/current-state graph, audit/write paths, task coordination, project state, evaluation machinery, and harness behavior in one workspace. Cortex v4 has already moved toward a narrower role by owning live-session classification, preflight, gating, and closeout while treating the old SSC corpus as a dependency.

FOSSIL was designed around the opposite durability rule: immutable evidence, stable corpus-owned identities, append-only knowledge-changing events, provenance, lifecycle/lineage, and reconstructable projections. Graph databases, indexes, embedding models, rerankers, model services, and harnesses are replaceable.

The new architecture must not recreate the old monolith by allowing Cortex and FOSSIL to become competing memory systems.

## Ownership table

| Concern | Owner | Boundary |
|---|---|---|
| Agent session / mission state | Cortex | Operational and resumable; not canonical knowledge |
| Task classification / methodology selection | Cortex | Executable control policy belongs to the harness |
| Tool/risk gates / preflight / retries | Cortex | FOSSIL does not schedule or authorize agent actions |
| Model/worker dispatch | Cortex | Models remain replaceable workers |
| Context-window budget | Cortex | Chooses budget and whether compression/decomposition is needed |
| Compression/decomposition strategy | Cortex | May transform temporary context but may not rewrite FOSSIL evidence |
| Immutable source evidence | FOSSIL | Canonical durable bytes + stable identity |
| Persistent semantic memory | FOSSIL | Claims, relations, provenance, lifecycle, lineage, disagreement |
| Stable claim/source/citation IDs | FOSSIL | Survive database/model/machine changes |
| Lifecycle / supersession / current-state semantics | FOSSIL | Never inferred solely from retrieval rank or Cortex state |
| Knowledge packs / read-write scope | FOSSIL | Logical identity independent of physical placement |
| Proposal validation / durable commit | FOSSIL | Deterministic gate owns knowledge-changing transaction |
| Retrieval semantics | FOSSIL | Corpus-specific retrieval policy, lineage/lifecycle resolution, citation semantics |
| BM25/vector/reranker implementations | FOSSIL projection/service layer | Replaceable and benchmarked; scores are not truth |
| Graphiti/Neo4j knowledge graph | FOSSIL projection layer | Rebuildable view, never canonical identity/truth |
| Gravebuster / local PC / future nodes | Infrastructure | Host services/projections; hosting does not confer semantic authority |
| Legacy `stupidly-simple-cortex` | Retired migration source | No new runtime or truth authority |

## Memory classes

### Cortex working memory

Examples:

- active task and task class;
- current mission/sub-agent assignments;
- preflight status;
- tool calls and gate outcomes;
- retry/decomposition state;
- selected context budget;
- temporary compressed context;
- local pending proposals while FOSSIL is unavailable.

This state may be checkpointed, compressed, resumed, or discarded. It is not durable truth merely because it persisted on disk.

### FOSSIL persistent memory

Examples:

- immutable evidence/source snapshots;
- claims and relationships;
- explicit provenance;
- accepted/rejected/disputed/superseded/retracted state;
- historical lineage and intellectual path;
- exact citations/spans/hashes;
- pack identity and dependencies;
- redaction/suppression state;
- knowledge-changing audit/provenance events.

This state survives agents, models, indexes, graphs, and physical machines.

### Operational telemetry

High-volume traces, token/tool events, stack traces, timing, CPU/GPU measurements, and verbose provider diagnostics stay outside canonical knowledge. FOSSIL may retain durable run/trace references and knowledge-changing provenance where appropriate.

## Retrieval responsibility: prevent double routing

Cortex and FOSSIL must not both independently implement semantic retrieval policy.

Cortex may specify **intent and constraints**, for example:

- task/query class;
- readable pack scope;
- risk class;
- latency/resource preference;
- desired context budget;
- whether direct-source reading or decomposition is acceptable.

FOSSIL owns **knowledge retrieval semantics**, including:

- the approved retrieval profile (currently D021 until superseded by evidence);
- lexical/dense/hybrid/reranker execution behind replaceable interfaces;
- lifecycle/provenance resolution for current/latest/accepted questions;
- lineage/read-state resolution for history/disagreement/supersession questions;
- exact citation/source identity;
- pack isolation;
- fallback identity and degraded-mode disclosure.

Cortex must not bypass those semantics by directly querying a vector index or graph and treating its result as authoritative knowledge.

## Cortex → FOSSIL durable-memory promotion

An agent saying “remember this” does not create truth.

The normal path is:

```text
Cortex session / model
    -> structured proposal
    -> source/session/run references
    -> evidence/provenance
    -> FOSSIL schema + stable-reference validation
    -> pack/write-scope validation
    -> evidence/risk/policy gate
    -> atomic durable FOSSIL event
    -> asynchronous projection update
```

A Cortex closeout, research result, compressed context packet, or multi-model consensus remains candidate material unless it passes this path.

If FOSSIL is unavailable, Cortex may retain a visibly **pending/uncommitted proposal**. It must never claim that a durable memory write succeeded.

## Compression boundary

Cortex owns the decision to fit a task into a model context window. FOSSIL owns the evidence identities that must survive intact.

Required rules:

- source snapshots are never replaced by summaries;
- claim/source/citation IDs and required citation spans are protected;
- numbers/code identifiers/provenance IDs may be designated protected spans;
- a compression result is temporary untrusted context, not canonical evidence;
- loss of required protected material fails closed;
- if safe compression cannot meet the budget, Cortex must raise the budget, direct-read, or decompose rather than silently over-compress;
- any durable summary produced from compression is a new derived proposal with provenance, never a replacement for its source.

The legacy SSC protected-span/fail-closed compressor is useful prior art, not a component FOSSIL must import or trust.

## Cluster topology: Gravebuster + local PC

For the first persistent deployment, use **one logical FOSSIL commit authority** rather than independent multi-master semantic writers.

Gravebuster and the local PC may independently host:

- Neo4j/Graphiti projections;
- BM25/vector indexes;
- embedding/reranking services;
- LiteLLM/model services;
- caches;
- benchmark workers;
- backup/replica copies.

These are physical placements. Stable FOSSIL pack/claim/source identity does not change when a projection or service moves machines.

Failure rules:

- graph loss -> rebuild from durable events/evidence;
- vector/index loss -> rebuild or use explicit degraded retrieval;
- model/reranker loss -> route/fallback with requested-vs-actual identity visible;
- Cortex crash -> resume/reconstruct operational state;
- FOSSIL durable-write outage -> no false durable-memory success; queue/persist only an explicit pending proposal;
- loss of FOSSIL durable evidence/events -> actual memory loss and therefore the primary backup/recovery concern.

Multi-writer/multi-master durable commits require a separate concurrency/consensus decision and proof; they are not implied by running FOSSIL on multiple machines.

## Legacy `stupidly-simple-cortex` retirement

The legacy SSC runtime is **not** a third live authority.

Retire as active architecture:

- SSC corpus/RAG service;
- SSC living ontology/current-state graph;
- SSC BM25/vector indexes;
- SSC generated current-state conclusions;
- SSC project/task state as system authority;
- SSC memory sidecars;
- any direct Cortex-v4 dependency on SSC for persistent memory after FOSSIL wiring lands.

Do not migrate old SSC ontology/current-state values as FOSSIL truth. If historically useful, preserve them only as source artifacts/candidates with explicit provenance.

### Legacy SSC evaluation estate is different

SSC contains potentially valuable evaluation assets that are **not semantic memory**:

- checker-decided `hard_gold` datasets;
- third-party-derived objective benchmark slices;
- semi-ground / semi-truth judgment datasets;
- rubrics and calibration anchors;
- deterministic oracle/checker implementations;
- frozen tests;
- promotion/quarantine manifests;
- checker cores and resolvers;
- reproducibility manifests and durable evaluation artifacts.

These assets should be **extracted into a standalone, content-addressed legacy-evaluation archive** rather than queried through SSC at runtime.

Extraction rules:

1. inventory actual committed bytes; do not trust SSC narrative counts;
2. hash every file and record repository commit + path + license/source metadata;
3. distinguish checker-decided hard gold from human/judge/semi-ground labels;
4. preserve checker implementation and frozen tests beside data when required for reproducibility;
5. preserve quarantine/negative cases rather than only successful rows;
6. keep hidden/holdout integrity policy explicit if any holdout is intended to remain unseen by future builders;
7. no eval row, rubric, or old research note becomes FOSSIL semantic truth merely by being archived;
8. future use must rerun/validate the relevant checker and record the exact asset version.

FOSSIL may store provenance *about* the archive and benchmark results derived from it, but normal FOSSIL RAG should not mount the legacy evaluation archive as knowledge.

## Old SSC research prose

Treat old SSC research prose, generated conclusions, and handoff claims as **historical/unverified source material only** unless independently revalidated.

It may be useful for discovery (“there may be prior work on X”) but cannot satisfy a current evidence requirement merely because SSC once labeled it research, reviewed, accepted, gold, or current.

No automatic ingestion of SSC research prose into live FOSSIL knowledge is required for retirement.

## Allowed interface shape

```text
CORTEX -> FOSSIL
  search(intent, scope, constraints)
  read(stable_id)
  lineage(stable_id/query)
  context(request)
  propose(candidate + provenance)
  validate(proposal)
  commit(validated proposal; gated)

FOSSIL -> CORTEX
  evidence/source snapshots
  stable IDs
  lifecycle + lineage state
  exact citations
  bounded context
  explicit degraded/fallback identity
  query execution receipts

CORTEX MUST NOT
  mutate graph/vector projections directly as knowledge authority
  author lifecycle/current-state truth outside FOSSIL
  activate retrieved instructions as control policy
  persist compressed context as replacement evidence
  report an uncommitted pending proposal as durable memory

FOSSIL MUST NOT
  schedule agents
  choose agent tool permissions
  own mission orchestration
  make Cortex methodology executable merely because it was retrieved
  couple durable knowledge semantics to Cortex internals
```

## Security/readiness dependency

Before multi-user/shared/cloud use, FOSSIL must finish route-level ACL/redaction propagation proof. Retrieval, reranking, context construction, compression, graph/vector projections, exports, and replicas must not bypass suppression or resurrect redacted material.

Cortex must pass the caller/pack/sensitivity constraints through rather than inventing its own weaker security semantics.

## Reconsideration triggers

Revisit this boundary only if committed evidence shows one of the following:

- a responsibility cannot be implemented without unsafe duplication;
- a distributed-write topology requires a new durable-authority design;
- a new memory class does not fit working/semantic/telemetry separation;
- a projection becomes impossible to reconstruct from durable FOSSIL state;
- Cortex requires persistent state that changes semantic truth independently of FOSSIL;
- security/latency requirements force a materially different trust boundary.

Any revision must be explicit in both Cortex and FOSSIL documentation; do not let implementation drift redefine ownership silently.
