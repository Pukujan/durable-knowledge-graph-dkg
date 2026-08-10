# Current Handoff

**Date:** 2026-08-10  
**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Durable substrate:** **DICS — Durable Intellectual Corpus System**  
**Repository:** `Pukujan/fossil-core`  
**Status:** **Milestone 0 complete. Gate 1 = 15/15. Issues #1–#10 are closed completed. No PRs or issues are open.**

## Fresh-session transfer record

For a new ChatGPT/Codex/Claude session, read the detailed dated transfer first after the core contracts:

`docs/handoffs/2026-08-10-chatgpt-session-handoff.md`

That file contains the verified proof runs, code surfaces, operational quirks, do-not-change rules, and the recommended shape of the next campaign.

The repository was verified immediately before the transfer at `main` commit `239335ed5a8b23fb34aa9a80afb7faf62e3caffe`; the handoff documentation commits follow that clean state.

## Repository family

- `Pukujan/fossil-core` — architecture/contracts/core/projections/benchmark/control plane;
- `Pukujan/fossil-common` — stable pack `pack_269099f7b2ba43b7a99b9427d64092de`;
- `Pukujan/fossil-ai-systems` — stable pack `pack_f024177f89a5442db84171c3dd7f58e5`, depending on common.

Repository/database/graph placement is not knowledge identity. Never mint replacement pack IDs because placement changes.

## Fresh-session order

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. this file
4. `docs/PROJECT_STATE.md`
5. `docs/handoffs/2026-08-10-chatgpt-session-handoff.md`
6. `docs/DECISION_LOG.md`
7. proof docs under `docs/implementation/`
8. closed Issue #1 and child Issues #2–#10 when detailed issue history is useful.

The chat UI is source material, not the control plane.

## Architecture that must not be casually changed

Canonical truth is immutable evidence + stable corpus IDs + append-only validated knowledge events + versioned pack/ontology contracts + provenance/history.

Graphiti/Neo4j, lexical/vector indexes, context construction, models, Skills, MCP, and future databases remain replaceable projections/services.

**A graph deletion must never delete irreplaceable intellectual history.**

Additional frozen invariants:

- durable commit precedes projection;
- new/rebuilt physical projection => fresh build-scoped applied ledger;
- rebuild replay order is `(recorded_at, event_id)`;
- migration compares stable FOSSIL semantics, not graph-native UUID equality;
- reconstructed evidence cannot silently become verbatim;
- exact citations bind to immutable observed source bytes/spans where available;
- ordinary intellectual revision remains append-only;
- privacy/legal erasure is exceptional tombstone-before-delete with non-resurrection;
- Skills contain methodology, not canonical truth;
- protocol adapters cannot become the durable knowledge model;
- model consensus is not external evidence;
- small/local model output is candidate-only until evidence/risk policy permits downstream authority.

Do not casually rename the internal `src/dkg` namespace.

## Completed proof stack

### Durable core / packs / lifecycle

Issues #2, #3, #6: atomic immutable publication, deterministic idempotency, content-addressed evidence, pack read/write boundaries/dependencies, provenance-preserving promotion, disagreement/supersession/staleness replay.

### #4 live Graphiti/Neo4j

Run `31338875226`: Graphiti `0.29.3` + Neo4j `5.26.29`, stable pack namespace, durable-first materialization, build metadata, projection-failure preservation, idempotent retry.

`json_schema` is the proven local structured-output mode; an earlier `json_object` attempt allowed malformed structured field names.

### #5 destructive rebuild + blue/green

Run `31339930551`: candidate destroyed to zero, rebuilt from the same durable source with a fresh build-scoped ledger, semantic comparison matched, active switch recorded only after checks.

Critical invariant: **new/rebuilt physical projection => fresh build-scoped applied ledger**.

### #9 conversation lineage

Run `31340924480` / job `93314435997`: immutable source bytes/spans, stable message ordering/parentage, explicit `verbatim` vs `reconstructed`, derived intellectual lineage with exact provenance, opposing/current/historical queries.

Recovered chat-loss material remains reconstructed, never a verbatim transcript.

### #8 Agent Skills/API/MCP

Run `31341456769` / job `93315824532`: **39 passed in 0.51s**. Six progressive-disclosure Skills, protocol-independent `CorpusService`, pack/Skill-gated mutations, actor/model/harness/skill provenance, no arbitrary Cypher/Graphiti mutation path.

### #10 source provenance + redaction

Deterministic run `31345462801` / job `93326450028`: **51 passed in 1.40s**.

Live run `31346791333` / job `93330095684`: exceptional tombstone-before-delete removed canonical event bytes, blocked same-ID resurrection, purged active Graphiti episode/entity state to zero, and remained absent on a fresh rebuild. Proof artifact `9047631921`.

Normal intellectual revision remains append-only. Privacy/legal erasure is an explicit exceptional path.

### #7 retrieval/model benchmark contract

Run `31347744797` / job `93332738616`: **56 passed in 0.70s**.

Versioned service controls:

- `BM25Retriever`
- `HashEmbeddingProvider`
- `EmbeddingRetriever`
- `TokenOverlapReranker`
- `BudgetedContextProvider`
- `CallableCandidateModelService`
- `RiskEscalationPolicy`
- `PolicyVerificationService`

The benchmark schema/harness measures quality, latency, peak Python allocation memory, estimated provider cost, and category-specific failure rates. Provider/model/runtime/benchmark provenance can be committed to review events.

These are **controls, not production winners**. Future providers must compete behind the interfaces.

## CI / workflow state

Final clean Gate 1 run `31347457485` / job `93331933728`: **51 passed in 0.82s**.

Expanded post-#7 run `31347744797` / job `93332738616`: **56 passed in 0.70s**.

`.github/workflows/ci.yml` is the normal fast suite.

`.github/workflows/graphiti-live.yml` contains reusable real Graphiti/Neo4j materialization + redaction/non-resurrection coverage. Runner-dependent temporary paths are step-scoped; the earlier invalid job-level `${{ runner.temp }}` usage is fixed.

Operational nuance: the permanent live workflow currently names `deepseek-r1:7b`; the successful final live redaction proof used `qwen2.5:3b`. Model choice in this workflow is replaceable test/runtime configuration, not architecture.

## Milestone closure

All original children #2–#10 and control Issue #1 are closed completed. At this checkpoint GitHub has **zero open issues and zero open pull requests**.

Do not reopen those completed issues just to start the next development phase.

## Natural next phase — intentionally not opened automatically

Recommended next campaign:

**Gate 2 — Real Corpus + Retrieval/Model Bakeoff**

Goal: use representative `fossil-common` and `fossil-ai-systems` material to compare the current controls against selected real semantic/vector/graph/long-context providers under the existing benchmark contract.

A fresh session should first verify current GitHub state, then—if the user still wants to proceed—open a **new tracked Gate 2 control issue** and a small set of child issues rather than extending closed Milestone 0.

Suggested Gate 2 work:

1. representative real corpus + gold/adversarial benchmark cases;
2. a few materially different real retrieval/context adapters behind existing interfaces;
3. reproducible comparative benchmark runs for quality, latency, memory, estimated cost, and failure categories;
4. evidence-based default routing/retrieval policy selection.

Do not build a model zoo. Do not choose providers by novelty. Let measured corpus performance choose adapters.

See `docs/handoffs/2026-08-10-chatgpt-session-handoff.md` for proposed Gate 2 exit criteria and a ready-to-paste continuation prompt.

## End-of-session rule

After substantial future work:

- update this file;
- update `docs/PROJECT_STATE.md` when the gate changes;
- update the active GitHub issue(s);
- commit material benchmark/proof evidence;
- update `docs/DECISION_LOG.md` when a decision changes;
- preserve prior reasoning rather than rewriting history;
- never rely on the chat UI as the only durable project record.
