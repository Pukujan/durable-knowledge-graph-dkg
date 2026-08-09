# Durable Decision Log

This file records accepted architectural decisions, serious alternatives, and the conditions that would justify revisiting them. It is intentionally concise; detailed evidence lives in the research synthesis/ledger and implementation issues.

## D001 — Preserve meaning, not one database implementation

**State:** accepted / frozen invariant  
**Decision:** canonical durability is immutable evidence + stable IDs + append-only knowledge events + versioned schemas/ontology + provenance/history. Databases and indexes are projections.

**Why:** database technology will change; intellectual history must survive migrations.

**Reconsider only if:** a future system can provide stronger portability while preserving equivalent source evidence, history, identity, and rebuildability.

## D002 — Graphiti + Neo4j is the first living graph projection

**State:** accepted, replaceable implementation choice  
**Decision:** use Graphiti + local Neo4j first because temporal episodes/facts, provenance, custom graph types, namespaces, and hybrid retrieval reduce the amount of temporal graph machinery we must build ourselves.

**Rejected interpretation:** Graphiti/Neo4j is not the permanent source of truth.

**Competing theory:** PostgreSQL + pgvector as the canonical operational store with Neo4j as an optional graph projection.

**Reconsider when:** Graphiti projection reliability, ontology evolution, namespace behavior, performance, or operational complexity fails our benchmarks; or PostgreSQL projection proves simpler/better while retaining the durable event contract.

## D003 — Knowledge packs are logical boundaries; shards are physical placement

**State:** accepted / frozen invariant  
**Decision:** common/domain/project knowledge is separated by portable knowledge-pack identity. A pack may later move repositories, databases, partitions, shards, or servers without changing stable IDs.

**Why:** mature multi-tenant systems repeatedly separate logical ownership/tenancy from physical placement.

**Reconsider only if:** a demonstrated storage technology requires physical identity coupling and provides a stronger migration story than stable logical pack identity.

## D004 — First authoring format is one immutable event per file

**State:** accepted, implementation-level  
**Decision:** immutable JSON event files validated by JSON Schema. JSONL is import/export, not the hot concurrent authoring file.

**Why:** multiple agents appending one Git-tracked JSONL file creates merge/conflict/corruption pressure; independent event files make idempotency and validation simpler.

**Reconsider when:** event volume makes filesystem authoring measurably impractical. A future event database may become the authoring implementation, but export/rebuild compatibility must remain.

## D005 — Accepted durable event and successful graph projection are separate states

**State:** accepted / frozen invariant  
**Decision:** durable event commit occurs before asynchronous graph projection. Projection failures retry/dead-letter; they cannot erase accepted knowledge.

**Why:** model/API/database outages should not lose intellectual history.

## D006 — Disagreement and relation history are first-class data

**State:** accepted / frozen invariant  
**Decision:** claims and relations have lifecycle/history. `DISPUTED` may remain unresolved. Supersession does not delete earlier states.

**Why:** the corpus must answer how/why a conclusion changed, not only what the latest summary says.

## D007 — Model agreement is not evidence

**State:** accepted / frozen invariant  
**Decision:** multiple models may provide independent criticism, candidate conflicts, or review metadata. External sources, tests, experiments, and other truth signals determine evidentiary support.

**Why:** correlated model errors can create false consensus.

## D008 — Agent Skills and MCP/API have different jobs

**State:** accepted  
**Decision:** Agent Skills hold lazily loaded methodology/workflows. Corpus API/MCP exposes a small capability surface. Internal domain service is protocol-independent.

**Why:** this reduces context/tool surface and keeps knowledge independent of a fast-changing protocol.

**Reconsider when:** a later protocol cleanly subsumes methodology + capability without forcing the corpus format to depend on it.

## D009 — Retrieval/model infrastructure is pluggable

**State:** accepted / frozen invariant  
**Decision:** storage, retrieval, context construction, and reasoning are separate interfaces. Do not couple canonical knowledge to one embedding model, one vector DB, one chunking strategy, or one context-window assumption.

**Why:** Kimi-style long context, graph retrieval, BM25, local/static embeddings, rerankers, and future models can change retrieval economics rapidly.

## D010 — Specialized/local models earn authority by benchmarks

**State:** accepted  
**Decision:** cheap/local models may handle routing, embeddings, tagging, deduplication candidates, citation matching, contradiction screening, and other bounded tasks. High-risk truth-state changes escalate according to evidence/risk policy.

**Why:** specialization can save cost/latency but also creates orchestration and error surfaces.

**Reconsider when:** corpus-specific benchmarks demonstrate a local/specialized model is reliable enough for a broader authority class.

## D011 — Migration is a normal feature

**State:** accepted / frozen invariant  
**Decision:** dangerous structural migrations use rebuild/blue-green projections whenever practical. Preserve history and switch active projection rather than destructively editing the only copy.

**Why:** prior knowledge projects became throwaway when schema changes were tightly coupled to graph/storage structure.

## D012 — GitHub is the project/control plane, not the live graph database

**State:** accepted  
**Decision:** Git tracks architecture, schemas, ontology, small durable events/evidence, migrations, benchmarks, Skills, decisions, and project state. Runtime graph/search state remains rebuildable outside Git.

## D013 — Delay physical pack repositories until boundary contract passes

**State:** accepted / sequencing condition satisfied  
**Decision:** first prove Issue #3 knowledge-pack validation/isolation locally; then create the initial common/shared and AI-systems/plugin-harness pack repos.

**Why:** avoid freezing an untested cross-repository contract twice.

**Current result:** Issue #3 has passed, so external pack repositories are now authorized without changing their stable pack identities.

## D014 — Security is deliberately minimal for the first local build

**State:** accepted / provisional  
**Decision:** localhost-only runtime with normal database credentials and optionally one local bearer token. Do not build custom OAuth/RBAC now.

**Why:** current boundaries are primarily correctness/context boundaries, not hostile multi-user security boundaries.

**Reconsider when:** remote access, multiple users, sensitive legal/finance/private packs, or an exposed service becomes real. Prefer mature identity such as Supabase/OAuth/JWT rather than custom auth.

## D015 — Telemetry is not canonical knowledge

**State:** accepted / frozen invariant  
**Decision:** traces, token/tool events, timing, stack traces, and system metrics live in observability systems. The corpus stores durable run/trace references and knowledge-changing provenance.

## D016 — Append-only needs an explicit redaction path

**State:** accepted  
**Decision:** append-only intellectual history must not make future sensitive-data deletion impossible. Redaction/tombstone behavior is modeled separately from ordinary claim revision.

**Reconsider/refine when:** real sensitive/legal requirements exist; then define exact retention/removal policy.

## D017 — FOSSIL is the project name; DICKS is the durable substrate nickname

**State:** accepted  
**Decision:** the project is named **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**. The durable corpus substrate may be referred to internally as **DICKS — Durable Intellectual Corpus & Knowledge System**.

**Repository family:**
- `fossil-core` — architecture/contracts/core/projections/control plane;
- `fossil-common` — common research and engineering methods, preserving `pack_269099f7b2ba43b7a99b9427d64092de`;
- `fossil-ai-systems` — AI systems/plugin-harness knowledge, preserving `pack_f024177f89a5442db84171c3dd7f58e5` and depending on the common pack.

**Invariant:** repository names do not define knowledge identity. The existing stable `pack_id` values remain authoritative through renames, moves, or future physical sharding.

**Why:** FOSSIL reflects the core rebuild-from-preserved-history property while giving the repository family a durable, memorable public name. DICKS preserves a deliberately unserious internal name without changing architectural semantics.

## How to add a decision

When implementation or research changes an architectural conclusion:

1. add a new decision entry rather than deleting the old reasoning;
2. state which earlier decision it supersedes/refines/challenges;
3. link the relevant issue/benchmark/research artifact;
4. record whether the change affects a frozen invariant or only an adapter choice;
5. update `ARCHITECTURE.md` only when the contract itself changes.
