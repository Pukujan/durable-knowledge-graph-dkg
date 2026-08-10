# FOSSIL ChatGPT Session Handoff — 2026-08-10

This document is a durable transfer record for a **new ChatGPT/Codex/Claude session**. It exists specifically so continuation does not depend on the previous chat thread.

## 0. One-line state

**Milestone 0 is complete. Gate 1 is 15/15 complete. Issues #1–#10 are closed completed. There are no open pull requests or issues. The next phase has intentionally not been opened yet.**

Repository state was verified before this handoff at `main` commit:

`239335ed5a8b23fb34aa9a80afb7faf62e3caffe` — `docs: reconcile final Milestone 0 closure`

This handoff document is committed on top of that verified state.

---

## 1. Project identity

**FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**

Durable corpus substrate:

**DICS — Durable Intellectual Corpus System**

Repository family:

- `Pukujan/fossil-core` — architecture, contracts, durable core, projections, benchmark/control plane;
- `Pukujan/fossil-common` — shared/common pack, stable ID `pack_269099f7b2ba43b7a99b9427d64092de`;
- `Pukujan/fossil-ai-systems` — AI systems/project pack, stable ID `pack_f024177f89a5442db84171c3dd7f58e5`, with a required dependency on the common pack.

**Never replace those pack IDs because a repository, graph, database, or directory moves.** Logical identity and physical placement are deliberately separate.

---

## 2. Read this repository in this order

A fresh agent/session should read:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/HANDOFF_CURRENT.md`
4. `docs/PROJECT_STATE.md`
5. this dated handoff
6. `docs/DECISION_LOG.md`
7. `docs/implementation/2026-08-09-gate1-core-proof.md`
8. `docs/implementation/2026-08-09-gate1-live-graphiti-proof.md`
9. `docs/implementation/2026-08-09-gate1-rebuild-blue-green-proof.md`
10. `docs/implementation/2026-08-09-gate1-conversation-lineage-proof.md`
11. `docs/implementation/2026-08-09-gate1-agent-boundary-proof.md`
12. `docs/implementation/2026-08-10-gate1-source-provenance-redaction-proof.md`
13. `docs/implementation/2026-08-10-retrieval-model-benchmark-contract-proof.md`
14. closed GitHub Issue #1 and child Issues #2–#10 only when detailed issue history is useful.

Do **not** use the previous chat thread as the project control plane. The repository and GitHub state are authoritative for continuation.

---

## 3. Frozen architectural contract

Canonical FOSSIL knowledge is:

**immutable evidence + stable corpus-owned IDs + append-only validated knowledge events + versioned pack/ontology contracts + provenance/history**.

The following are replaceable projections/services, not canonical truth:

- Graphiti;
- Neo4j;
- lexical/vector indexes;
- embeddings and embedding models;
- rerankers;
- context-construction strategies;
- local/frontier models;
- Agent Skills;
- MCP or another agent protocol;
- future storage engines.

Critical invariant:

> A graph deletion must never delete irreplaceable intellectual history.

Other frozen rules:

- durable event commit precedes replaceable projection;
- stable pack identity is independent of repository/database placement;
- ordinary intellectual revision is append-only;
- unresolved disagreement is valid durable data;
- model agreement is metadata, not external evidence;
- reconstructed evidence can never silently become verbatim evidence;
- exact citations resolve to immutable observed bytes/spans when available;
- source quality is multidimensional rather than one universal tier;
- privacy/legal erasure is an explicit exceptional tombstone-before-delete path with non-resurrection;
- Skills contain methodology, not canonical truth;
- protocol adapters do not become the durable knowledge model;
- small/local model output remains candidate-only unless independent evidence/risk policy permits downstream authority.

Do not casually rename `src/dkg`; the internal module/API namespace was deliberately left stable when the public project became FOSSIL.

---

## 4. Milestone 0 / Gate 1 completed work

All original child issues are complete:

- #2 durable event + artifact store;
- #3 knowledge-pack boundaries, mounts, dependencies, promotion;
- #4 Graphiti + Neo4j projection adapter/queue and real live materialization;
- #5 destructive rebuild + blue/green migration;
- #6 lifecycle, disagreement, supersession, stale propagation;
- #7 pluggable retrieval/model service + benchmark contract;
- #8 Agent Skills + thin corpus API/MCP boundary;
- #9 conversation ingestion + intellectual-lineage reconstruction;
- #10 source snapshots, citation provenance/quality, redaction/non-resurrection.

Control Issue #1 is also closed completed.

### Gate 1 = 15/15

1. immutable validated events — complete;
2. deterministic invalid/duplicate rejection — complete;
3. content-addressed immutable artifacts — complete;
4. knowledge-pack boundaries/dependencies — complete;
5. provenance-preserving cross-pack promotion — complete;
6. claim/relation lifecycle, disagreement, supersession, staleness — complete;
7. replaceable Graphiti adapter — complete;
8. projection retry/failure ledger — complete;
9. projection build metadata — complete;
10. live Graphiti + Neo4j materialization — complete;
11. destructive rebuild from durable data — complete;
12. second projection comparison + guarded blue/green switch — complete;
13. conversation ingestion + intellectual-lineage benchmark — complete;
14. source snapshots/exact citations/quality/lifecycle/redaction integrity — complete;
15. safe Agent Skill/API/MCP boundary — complete.

---

## 5. Important observed proof runs

### Live Graphiti / Neo4j

Run `31338875226` proved:

- Graphiti `0.29.3`;
- Neo4j `5.26.29`;
- stable FOSSIL `pack_id -> Graphiti group_id` namespace;
- durable-first materialization;
- runtime/build metadata;
- projection failure preservation;
- idempotent replay.

The local OpenAI-compatible Ollama integration required structured output mode `json_schema`. Earlier `json_object` extraction allowed malformed field shapes such as `Edges` instead of required `edges`.

### Destructive rebuild / blue-green

Run `31339930551` proved:

- a candidate graph could be destroyed to zero;
- the same durable event source remained intact;
- a fresh build-scoped projection ledger rebuilt the candidate;
- current and candidate projections could coexist;
- semantic comparison used stable FOSSIL identities, not graph-native UUID equality;
- active switch was recorded only after checks passed.

**Critical migration invariant:** every physically new/rebuilt projection gets a **fresh build identity and applied ledger**. Reusing an old applied ledger after deleting a graph can silently suppress all replay because every event appears already applied.

Rebuild ordering is `(recorded_at, event_id)`.

### Conversation lineage

Run `31340924480`, job `93314435997` proved immutable source bytes/spans, stable message order/parentage, explicit `verbatim` vs `reconstructed`, derived lineage provenance, opposing-position queries, current conclusions, and historical path reconstruction.

Recovered chat-loss material is explicitly reconstructed. Never present it as a verbatim lost transcript.

### Safe agent boundary

Run `31341456769`, job `93315824532`: **39 passed in 0.51s**.

Implemented:

- progressive-disclosure Skills;
- protocol-independent `CorpusService`;
- allowlisted `search/read/lineage/propose/validate/commit/manage` capabilities;
- pack/Skill-gated mutation proposals;
- actor/model/harness/skill provenance;
- durable commit before downstream projection;
- no normal Cypher/Graphiti mutation escape hatch.

### Source provenance + redaction

Deterministic run `31345462801`, job `93326450028`: **51 passed in 1.40s**.

Real live redaction run `31346791333`, job `93330095684` proved:

- Graphiti `0.29.3` + Neo4j `5.26.29`;
- AI-systems pack `pack_f024177f89a5442db84171c3dd7f58e5`;
- event `evt_416e5c516581c8dea8c5c54025361960` materialized as one episode + one entity;
- a minimal non-sensitive tombstone existed before canonical event bytes were physically removed;
- republication of the same deterministic event identity was blocked;
- active Graphiti episode/entity materialization was purged to zero;
- a fresh rebuild produced no receipts and did not resurrect erased knowledge.

Proof artifact ID: `9047631921`.

### Final clean Gate 1 state

Run `31347457485`, job `93331933728`: **51 passed in 0.82s** after temporary proof plumbing had been removed and normal CI restored.

### Cognitive-service / benchmark contract

Run `31347744797`, job `93332738616`: **56 passed in 0.70s**.

Current inspectable controls:

- `BM25Retriever`;
- `HashEmbeddingProvider`;
- `EmbeddingRetriever`;
- `TokenOverlapReranker`;
- `BudgetedContextProvider`;
- `CallableCandidateModelService`;
- `RiskEscalationPolicy`;
- `PolicyVerificationService`.

These are **benchmark baselines/controls, not chosen production winners**.

Benchmark contract (`fossil.benchmark.v1`) measures:

- retrieval hit rate / recall / MRR;
- bounded-model task quality;
- mean/p95 latency;
- peak Python allocation memory;
- estimated provider cost;
- category/domain-specific failure rates;
- provider/model/runtime/implementation identity.

Review-event provenance can include provider/runtime/model-service/benchmark identity.

---

## 6. Current workflow state and operational notes

### Fast CI

`.github/workflows/ci.yml` is the normal fast contract suite.

### Live Graphiti workflow

`.github/workflows/graphiti-live.yml` contains reusable real Graphiti/Neo4j materialization and redaction/non-resurrection smoke coverage.

A previous workflow registration problem was traced to `${{ runner.temp }}` being used in **job-level** `env`, where the runner context is unavailable. Runner-dependent proof paths are now scoped to individual steps.

The permanent workflow currently names `deepseek-r1:7b` + `nomic-embed-text` with `json_schema`. The successful final redaction proof itself used the faster `qwen2.5:3b` + `nomic-embed-text` configuration through trusted CI. Treat model choice here as test/runtime configuration, not canonical architecture.

Graphiti/Neo4j may log benign `EquivalentSchemaRuleAlreadyExists` messages while initializing already-equivalent indexes. The observed live proofs still completed successfully; do not confuse those messages with failed materialization without checking job conclusion/proof output.

GitHub Actions also emitted Node runtime deprecation warnings for older action versions; these were warnings, not Gate failures. Future maintenance may bump action versions independently of knowledge architecture.

---

## 7. Current code surfaces to know

Durable core:

- `src/dkg/event_store.py`
- `src/dkg/artifact_store.py`
- `src/dkg/pack.py`
- `src/dkg/promotion.py`
- `src/dkg/lifecycle.py`
- `src/dkg/source.py`

Projection/migration:

- `src/dkg/projection/graphiti.py`
- `src/dkg/projection/ledger.py`
- `src/dkg/projection/migration.py`

Conversation/lineage:

- `src/dkg/conversation.py`
- `schemas/conversation/`
- `schemas/conversation-lineage/`

Agent boundary / Skills:

- `src/dkg/corpus_service.py` and related agent-facing modules in `src/dkg/`;
- repository Skill definitions documented by the Gate 1 agent-boundary proof.

Cognitive services / benchmarks:

- `src/dkg/contracts.py`
- `src/dkg/services.py`
- `src/dkg/benchmark.py`
- `schemas/benchmark/v1.schema.json`
- `tests/test_cognitive_services_benchmark.py`

Live proof scripts:

- `scripts/live_graphiti_smoke.py`
- `scripts/live_redaction_smoke.py`

---

## 8. What the next session should NOT do

Do not:

1. reopen Issues #1–#10 merely to continue development;
2. mint new pack IDs for `fossil-common` or `fossil-ai-systems`;
3. rename `src/dkg` as cleanup;
4. make Graphiti/Neo4j canonical truth;
5. call knowledge-pack repositories "database shards";
6. grant small/local models truth-changing authority because multiple models agree;
7. silently treat reconstructed chat recovery as verbatim evidence;
8. weaken redaction/non-resurrection or migration assertions to make a provider pass;
9. copy whole `fossil-core` implementation into pack repositories;
10. choose a retrieval/model stack because it is fashionable instead of because it wins the corpus benchmark.

---

## 9. Natural next campaign: Gate 2 — Real Corpus + Retrieval/Model Bakeoff

This next campaign is recommended but **intentionally not yet opened**. The previous session stopped at a clean milestone boundary rather than silently inventing a new roadmap.

The first act of the new session should be to inspect the current state and, if the user still wants to proceed, open a **new control issue/milestone** rather than extending closed Milestone 0.

Recommended Gate 2 goal:

> Put representative real FOSSIL material through competing retrieval/context/model strategies and select defaults from measured corpus behavior while preserving canonical durability and authority boundaries.

### Recommended child work

#### A. Representative corpus + gold benchmark

Use material from `fossil-common` and `fossil-ai-systems` to create a modest but genuinely difficult benchmark corpus.

Gold cases should include:

- exact factual lookup;
- source/citation recovery;
- "why did we decide X?" lineage;
- current conclusion vs historical conclusion;
- contradiction/disagreement retrieval;
- stale/superseded assumption detection;
- cross-pack lookup respecting read boundaries;
- obscure evidence buried deep in source material;
- conversation-lineage questions;
- cases where the correct answer is "insufficient evidence".

Start with tens of cases, not millions of documents. Quality of adversarial cases matters more than volume at this stage.

#### B. Real retrieval/context adapters

Add a small number of serious competitors behind existing interfaces, for example categories such as:

- lexical/BM25 control;
- real semantic/vector retrieval;
- lexical + vector hybrid;
- reranked hybrid;
- Graphiti/graph expansion;
- direct long-context/contextual retrieval;
- one or two corpus-relevant combinations.

Do not redesign canonical schemas to accommodate one provider.

#### C. Comparative benchmark execution

Run the same gold set through competitors and persist `fossil.benchmark.v1` outputs for:

- retrieval quality;
- answer/citation quality where applicable;
- latency;
- memory;
- estimated cost;
- category-specific failure behavior.

Record environment/provider/model/runtime versions so results can be compared later.

#### D. Default-policy selection

Choose defaults only after evidence. A plausible outcome might be a policy such as:

- lexical + semantic hybrid by default;
- graph expansion for lineage/relationship tasks;
- reranking only when measured quality gain earns its latency/cost;
- long-context path only above defined retrieval uncertainty;
- expensive/frontier verification only on high-risk or unresolved cases.

That is an example of the *kind* of result Gate 2 should produce, not a preselected answer.

### Gate 2 exit criteria

A strong exit would include:

- representative real corpus fixtures;
- a versioned gold benchmark set;
- at least two materially different real retrieval strategies compared with controls;
- reproducible benchmark outputs with provider/runtime identity;
- documented failure taxonomy;
- one default routing/retrieval policy selected from measured evidence;
- no change to canonical FOSSIL knowledge identity/durability merely to suit a benchmark winner;
- updated `DECISION_LOG.md`, `PROJECT_STATE.md`, `HANDOFF_CURRENT.md`, and the new Gate 2 issue(s).

---

## 10. Suggested first prompt for a new ChatGPT session

The user can paste something like:

> Continue my FOSSIL project from GitHub. Use `Pukujan/fossil-core` as the control plane. Read `AGENTS.md`, `ARCHITECTURE.md`, `docs/HANDOFF_CURRENT.md`, `docs/PROJECT_STATE.md`, and `docs/handoffs/2026-08-10-chatgpt-session-handoff.md` before changing anything. Verify current GitHub state. Milestone 0 / Gate 1 is complete; do not reopen completed Issues #1–#10. Continue by proposing/opening the next tracked Gate 2 for real-corpus retrieval/model benchmarking, preserving all frozen invariants and stable pack IDs.

A capable connected session should then verify the repository rather than relying solely on this summary.

---

## 11. End-of-session protocol for the next agent

After substantial future work:

- update `docs/HANDOFF_CURRENT.md`;
- update `docs/PROJECT_STATE.md` when the gate changes;
- update the active GitHub issue(s);
- commit material benchmark/proof evidence;
- update `docs/DECISION_LOG.md` when a decision changes;
- preserve prior reasoning rather than rewriting history;
- leave enough repository state that the next session does not need the chat transcript.
