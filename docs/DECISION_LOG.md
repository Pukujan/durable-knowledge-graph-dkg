# Durable Decision Log

This file records accepted architectural decisions, serious alternatives, and the conditions that would justify revisiting them. Detailed evidence lives in research/proof documents and implementation issues.

## D001 — Preserve meaning, not one database implementation

**State:** accepted / frozen invariant  
**Decision:** canonical durability is immutable evidence + stable IDs + append-only knowledge events + versioned schemas/ontology + provenance/history. Databases/indexes are projections.

## D002 — Graphiti + Neo4j is the first living graph projection

**State:** accepted, replaceable implementation choice  
**Decision:** use Graphiti + local Neo4j first for temporal episodes/facts, provenance, namespaces, and hybrid retrieval. It is not the permanent source of truth.

**Reconsider when:** projection reliability, ontology evolution, namespace behavior, performance, operational complexity, or a competing projection wins measured benchmarks.

## D003 — Knowledge packs are logical boundaries; shards are physical placement

**State:** accepted / frozen invariant  
**Decision:** common/domain/project knowledge is separated by stable portable `pack_id`. Repository/database/partition/shard placement may change without redefining identity.

## D004 — First authoring format is one immutable event per file

**State:** accepted, implementation-level  
**Decision:** immutable JSON event files validated by JSON Schema. JSONL is import/export, not the concurrent authoring hot path.

**Reconsider when:** event volume makes filesystem authoring measurably impractical; replacement storage must retain export/rebuild compatibility.

## D005 — Accepted durable event and successful graph projection are separate states

**State:** accepted / frozen invariant  
**Decision:** durable event commit occurs before projection. Projection failure/retry state cannot erase accepted knowledge.

## D006 — Disagreement and relation history are first-class data

**State:** accepted / frozen invariant  
**Decision:** claims/relations preserve lifecycle and history. `DISPUTED` may remain unresolved. Supersession does not delete earlier states.

## D007 — Model agreement is not evidence

**State:** accepted / frozen invariant  
**Decision:** models may provide criticism/candidates/review metadata. External sources, tests, experiments, and other truth signals determine evidentiary support.

## D008 — Agent Skills and MCP/API have different jobs

**State:** accepted  
**Decision:** Skills contain lazily loaded methodology/workflows. The corpus domain service owns a small capability surface; MCP/API is a replaceable adapter. Canonical knowledge does not depend on the protocol.

**Gate 1 result:** `CorpusService` exposes `search/read/lineage/propose/validate/commit/manage`; normal agent access has no arbitrary Cypher/Graphiti mutation path, and agent proposals preserve actor/model/harness/skill provenance.

**Evidence:** `docs/implementation/2026-08-09-gate1-agent-boundary-proof.md`, Issue #8.

## D009 — Retrieval/model infrastructure is pluggable

**State:** accepted / frozen invariant  
**Decision:** storage, retrieval, context construction, and reasoning are separate interfaces. Canonical knowledge cannot depend on one embedding model, vector DB, chunking strategy, or context-window assumption.

## D010 — Specialized/local models earn authority by benchmarks

**State:** accepted  
**Decision:** small/local models may perform bounded tasks and propose candidates. They do not receive truth-changing authority unless corpus-specific benchmark evidence and risk policy justify it.

## D011 — Migration is a normal feature

**State:** accepted / frozen invariant  
**Decision:** dangerous structural migrations use rebuild/blue-green projections where practical. Preserve history and switch active projection rather than destructively editing the only copy.

## D012 — GitHub is the project/control plane, not the live graph database

**State:** accepted  
**Decision:** Git tracks architecture, schemas, ontology, small durable events/evidence, migrations, benchmarks, Skills, decisions, and project state. Runtime graph/search state remains rebuildable outside Git.

## D013 — Delay physical pack repositories until boundary contract passes

**State:** accepted / sequencing condition satisfied  
**Decision:** prove pack validation/isolation before splitting physical repositories.

**Result:** the repository family now exists as `fossil-core`, `fossil-common`, and `fossil-ai-systems` without changing the stable pack identities.

## D014 — Security is deliberately minimal for the first local build

**State:** accepted / provisional  
**Decision:** localhost-first runtime with ordinary database credentials and optionally one local bearer token. Do not build custom OAuth/RBAC yet.

**Reconsider when:** remote access, multiple users, sensitive packs, or exposed services become real. Prefer mature identity systems rather than custom auth.

## D015 — Telemetry is not canonical knowledge

**State:** accepted / frozen invariant  
**Decision:** token/tool traces, timing, stack traces, and metrics live in observability systems. The corpus stores durable run/trace references and knowledge-changing provenance.

## D016 — Append-only history has an exceptional tombstone-before-delete redaction path

**State:** accepted / frozen redaction invariant  
**Decision:** normal intellectual revision remains append-only, but privacy/legal erasure is a separate exceptional operation. FOSSIL must persist a minimal non-sensitive tombstone before physically deleting sensitive artifact or durable-event bytes.

For content-addressed artifacts, the tombstone preserves identity/hash and audit metadata but not the erased bytes; the same redacted content identity cannot silently be rehydrated.

For a durable event whose payload itself contains sensitive text, the tombstone preserves only stable event ID, pack ID, event type, recorded time, canonical hash, and redaction authority/reason/request reference. It deliberately excludes payload, subject refs, evidence refs, and provenance that could repeat sensitive content. The same deterministic event identity cannot be republished after redaction.

Active projections and exports must respect redaction. Projection-applied history remains immutable operational audit history; redaction is recorded separately. A projection may retain a build-local graph object UUID solely as an operational purge handle, never as canonical knowledge identity.

Event-redaction tombstones plus build-scoped applied ledgers must support cleanup after a crash between canonical erasure and projection purge. A fresh rebuild must not resurrect intentionally erased canonical knowledge.

**Why:** append-only intellectual history must not trap future sensitive/legal/private data forever, while deletion itself must remain explainable and auditable without preserving the sensitive payload.

**Evidence:** `docs/implementation/2026-08-10-gate1-source-provenance-redaction-proof.md`, Issue #10. Real Graphiti/Neo4j proof run `31346791333` showed active episode/entity removal and zero-state fresh rebuild after canonical event erasure.

**Reconsider only if:** a stronger deletion/cryptographic-erasure mechanism preserves equivalent auditability, non-resurrection, projection cleanup, and privacy semantics.

## D017 — FOSSIL is the project name; DICS is the durable substrate name

**State:** accepted  
**Decision:** project name: **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**. Durable corpus substrate: **DICS — Durable Intellectual Corpus System**.

Repository family:
- `fossil-core` — architecture/contracts/core/projections/control plane;
- `fossil-common` — stable `pack_269099f7b2ba43b7a99b9427d64092de`;
- `fossil-ai-systems` — stable `pack_f024177f89a5442db84171c3dd7f58e5`, depending on common.

**Invariant:** repository names do not define knowledge identity.

## D018 — Physical projection builds have separate operational identity

**State:** accepted / frozen migration invariant  
**Decision:** every destructive rebuild/blue-green candidate receives a fresh projection build identity and build-scoped applied ledger. Migration comparison uses projection-independent semantic snapshots; active changes are append-only switch records only after checks pass.

**Why:** deleting a graph while reusing an old applied ledger can make every event appear already materialized and silently produce an empty rebuild. Graph-native UUID equality is also not a valid migration contract.

**Evidence:** `docs/implementation/2026-08-09-gate1-rebuild-blue-green-proof.md`, Issue #5.

## D019 — Conversation evidence status is durable provenance

**State:** accepted / frozen evidence invariant  
**Decision:** conversation source artifacts, byte spans, messages, and derived lineage explicitly distinguish `verbatim` from `reconstructed`. A reconstructed recovery artifact cannot silently become verbatim evidence; verbatim messages resolve exactly to immutable source bytes/spans.

**Evidence:** `docs/implementation/2026-08-09-gate1-conversation-lineage-proof.md`, Issue #9.

## D020 — Source role and quality remain explicit instead of collapsing into one score

**State:** accepted / frozen evidence invariant  
**Decision:** source snapshots preserve source role (`primary`, `secondary`, `local`, `derived`, `reconstructed` as applicable), derivation parents, immutable observed version, and independent quality dimensions. A derived/reconstructed source cannot satisfy a primary-source requirement merely because its prose is confident or cites another source.

**Why:** a universal source tier or opaque confidence score encourages citation laundering and hides which quality dimension is weak.

**Evidence:** `docs/implementation/2026-08-10-gate1-source-provenance-redaction-proof.md`, Issue #10.

## How to add a decision

When implementation or evidence changes an architectural conclusion:

1. add/refine a durable decision rather than deleting old reasoning;
2. state which prior decision it refines/challenges/supersedes;
3. link the issue/benchmark/proof;
4. distinguish frozen invariant from replaceable adapter choice;
5. update `ARCHITECTURE.md` when the architectural contract itself changes.
