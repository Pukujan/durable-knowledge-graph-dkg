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

## D021 — Gate 2 default retrieval is pinned BGE dense with explicit BM25 degraded fallback

**State:** accepted, replaceable evidence-based implementation policy  
**Decision:** use revision-pinned BGE dense retrieval (`BAAI/bge-small-en-v1.5@5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`) as the normal primary retriever. If the optional semantic runtime is unavailable, use BM25 as an explicitly degraded availability fallback; do not silently substitute the hash control or claim semantic retrieval remains active.

Current/latest/accepted queries must resolve durable lifecycle/provenance before presenting a current conclusion; retrieval rank is candidate ordering, not truth. Decision-lineage, supersession, disagreement, and multi-target historical/current queries must use durable `lineage`/read resolution in addition to retrieval. Citation-bearing answers must still resolve immutable source snapshots/spans/hashes. None of this changes model authority: model agreement remains non-evidence and small/local model output remains candidate-only unless separate evidence/risk policy permits more.

**Why:** on the 21-case history-rich Gate 2 corpus, BGE dense is the only compared strategy with zero full retrieval misses and has the best mean recall@5 (`0.98413`). The hybrid has better MRR (`0.86667`) but fully misses the key current-architecture case, so aggregate ranking does not outweigh a decision-critical miss. BGE still ranks the correct current architecture only fifth behind rejected/history material and retrieves only 2/3 targets in the multi-target supersession bundle, which is why lifecycle and lineage safeguards are mandatory rather than optional tuning.

**Fallback distinction:** BM25 is an availability fallback, not a quality-equivalent replacement. Quality/configuration rollback returns to the last known benchmark-passing BGE profile; an operational semantic outage temporarily activates explicit BM25 degraded mode.

**Hard rollback conditions:** pack isolation violation; unaudited provider/model/runtime substitution; weakened citation/source semantics; current-state safeguards allowing stale/rejected/superseded material to become current without durable lifecycle resolution; a full miss on the frozen Gate 2 reference set where the approved BGE profile had none; or changing canonical identity/provenance/authority merely to improve retrieval scores.

**Reconsider when:** the corpus/case set materially changes; BGE/runtime identity changes; a competitor eliminates the observed current-state and multi-target-lineage weaknesses without decision-critical misses; deployment latency/memory/cost becomes unacceptable; a new recurring failure class appears; degraded BM25 mode becomes frequent; or new committed benchmarks remove BGE's zero-full-miss/best-quality advantage.

**Evidence:** Issue #36 / PR #44 / squash commit `38aac6325cdb5b738c8a6ac5e55959affb3acfb5`; exact-head semantic proof run `31364039745`, artifact `9053475462`, digest `sha256:23c95b46f47cec5a16e0a8c0926a4f13532f283d8f4fbcc0de12ceb63db63c41`; `benchmarks/gate2/results/2026-08-10-comparative/comparison-summary.json`; `docs/implementation/2026-08-10-gate2-comparative-bakeoff-proof.md`; `docs/implementation/2026-08-10-gate2-default-retrieval-policy.md`; Issue #37.

## D022 — Trusted local runner is a credential bridge, not normal truth-bearing compute

**State:** accepted / provisional execution topology  
**Decision:** ordinary pull-request CI remains secretless and should use disposable GitHub-hosted compute where practical. Because trusted Railway/provider/telemetry and related credentials currently remain local-only, the owner's PC may run a narrowly trusted self-hosted GitHub Actions runner for versioned WorkOrders and a separate privileged verifier lane. The local node is replaceable execution infrastructure, not semantic authority.

A pull request must never be able to cause its own mutable code or workflow definition to execute on the credential-bearing local runner. Trusted-local dispatch must originate from reviewed/default-branch-controlled workflow or dispatcher code. Credential-bearing verification may load local secrets only for an exact reviewed SHA and an explicitly authorized access class. Ordinary engineering WorkOrders keep those secrets unloaded.

Each local WorkOrder uses an isolated disposable worktree/process, explicit task/attempt/generation identity, bounded deadlines, claim verification, stale/duplicate/late-result rejection, objective checks, sanitized receipts and mechanical terminal closeout. Terra and Luna are execution roles only; role selection does not confer authority or implicit secret access.

**Supersedes/refines:** manual per-session local Codex launch/dispatch as the normal operating model; the earlier #86 sequencing assumption that all self-hosted-runner work should wait until the final persistent-extras phase. It does **not** reintroduce a self-hosted runner as a prerequisite for ordinary secretless PR CI and does not change the invariant that durable truth outlives compute.

**Evidence/contract:** Issue #96; issue #94 `INFRA-03`; issue #86 2026-08-12 plan revision; `docs/architecture/2026-08-12-trusted-local-runner-boundary.md`.

**Reconsider when:** local-only credentials move to a protected managed secret runner; no trusted local hardware/service access remains; or a managed executor demonstrates equal/stronger isolation, exact-SHA gating, secret protection and WorkOrder recovery with lower operational burden.

## D023 — Legacy SSC is retired/superseded and cannot supply current semantic or runtime authority

**State:** accepted / frozen retirement boundary  
**Decision:** legacy `stupidly-simple-cortex` (SSC) is **RETIRED / SUPERSEDED** as a live memory, RAG, ontology/current-state, project-state, orchestration or Cortex runtime authority. Cortex V4 must operate with SSC absent. FOSSIL must not ingest SSC ranking output, generated conclusions/summaries, ontology/current-state values, model consensus, historical project state, or old research prose as current truth merely because SSC stored or labeled it.

The retirement is evidence-backed: the legacy runtime has known noisy/false-positive corpus behavior, while historical reviews also found retrieval/index coverage failures and stale/inconsistent artifact metadata. Treating those outputs as authority can degrade decision quality by turning retrieval/system errors into apparent state or truth. Historical material therefore remains historical/provenance evidence unless independently revalidated.

Potentially useful old eval/checker assets may survive only through a **standalone extracted archive** with exact source revision/path, byte/content hash, actual row counts, provenance/license status, checker/test dependency, holdout/leakage controls and independent revalidation. An extracted asset is not an SSC runtime dependency.

**Supersedes:** any remaining Cortex tests/adapters, queue tasks or local procedures that treat private-SSC compatibility as a merge/runtime requirement. Such code is migration debt unless a current independently justified contract says otherwise.

**Evidence:** `docs/research/2026-08-10-legacy-ssc-engineering-retrospective.md`; `docs/research/2026-08-10-legacy-ssc-evaluation-estate-inventory.md`; historical tracker #73; `Pukujan/stupidly-simple-cortex` PR #70; Cortex issue #1 / boundary PR #7; issue #94 CORTEX-04 correction.

**Reconsider only if:** a specific historical asset is independently validated under the extraction policy. This does not authorize reviving SSC itself.

## How to add a decision

When implementation or evidence changes an architectural conclusion:

1. add/refine a durable decision rather than deleting old reasoning;
2. state which prior decision it refines/challenges/supersedes;
3. link the issue/benchmark/proof;
4. distinguish frozen invariant from replaceable adapter choice;
5. update `ARCHITECTURE.md` when the architectural contract itself changes.
