# FOSSIL Project State

**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Durable substrate:** **DICS — Durable Intellectual Corpus System**  
**Architecture authority:** GitHub Issue #86  
**Execution queue / claim ledger:** GitHub Issue #94  
**Current focused campaign:** GitHub Issue #116  
**Last updated:** 2026-08-15

## Current state

Milestone 0 / Gate 1 and Gate 2 are complete. The current execution focus is **FOSSIL baseline verification and continuation**, not a Cortex runtime repair, LiteLLM repair, or immediate retrieval/model bakeoff.

The cross-project boundary is:

> **Cortex owns execution. FOSSIL owns durable knowledge/evidence. GitHub owns coordination/review. LiteLLM/CKFF owns provider/model/route factual transport. Infrastructure is replaceable.**

The architecture invariant is:

> **Compute may disappear; truth must not.**

Live #86/#94 state is authoritative when this document and GitHub have diverged.

## Completed cross-project dependencies

### Cortex V5

- Cortex V5 is the active execution runtime at accepted baseline `31fde7508b8e1caddfe7f9b79dc5719c1a0df79f`.
- `V5-ACCEPTANCE` received human PASS / closed completed on 2026-08-14.
- Mechanical evidence recorded in #94: public HumanEval/0 through the V5 HTTP API, executable verification `20/20`, `attempt_count=1`, local observation, Gravebuster HTTP 200, Langfuse HTTP 207.
- Cortex V4 is preserved/frozen historical implementation evidence, not active runtime authority.
- `CORTEX-02` secretless Actions WorkOrder wiring is a separate V5 integration item and no longer blocks the truth of the completed V5 acceptance itself.

### LiteLLM / CKFF

- Gateway false-success, streaming/tool, non-stream body, Responses-routing, and failing-route repair work is closed completed.
- Railway `litellm` production was reconciled healthy on 2026-08-14 with liveliness 200, readiness 200/database connected, and Postgres online.
- `Pukujan/litellm-ckff-ops#11` is closed completed; no active repair PR existed at reconciliation.
- Prior failed verifier/LIVE_STAGING attempts remain failed historical evidence and must not be relabeled green after the fact.
- `2xx` with empty/malformed/zero-usable output remains failure.

### Trusted local execution

- Broker/verifier tracker #96 is closed completed.
- Exact-SHA execution, fencing/cancellation, low-privilege worker, separate privileged verifier, sanitized receipts, and host supervision are established foundations.

## Current FOSSIL campaign

Issue #116 carries the visible SDD/TDD for the FOSSIL-only verification campaign. It is subordinate to #86 for architecture and #94 for live execution/claims.

Fresh reconciled state:

- FOSSIL `main` = `27764c4ab20c196ee0bc76a0d020fc961a385c4e`.
- PR #114 is merged into that baseline. The inherited `graphiti_core -> httpx` dependency/import failure is repaired; clean declared installation uses real `httpx`, not a shim or skipped path.
- PR #115 head = `c4432f577e6182efd4126c3bbd1171a1fb58cbbd`, rebased onto the merged #114 baseline.
- Independent clean #115 evidence passes: declared `[test,graphiti]` install, `pip check`, Graphiti import, receipt tests `63/63`, focused tests `91/91`, full pytest `262/262`, and `git diff --check`.
- `FOSSIL-07A` completed its bounded identical-run repeatability experiment and closed **BLOCKED / NONDETERMINISTIC_GATE**.
- On the same exact SHA, three Graphiti attempts produced materially different semantic outcomes: `0 entities/0 facts`; `5 entities/0 facts` with incomplete timeout; `5 entities/2 facts` with final PASS.
- The variability is localized to the Graphiti LLM extraction/interpretation boundary, not #115 receipt/schema semantics or the repaired dependency/import path.
- The latest Graphiti workflow conclusion is green, but that one green rerun is not stable acceptance because the gate cannot yet reliably distinguish a real semantic failure from run-to-run model variance.
- PR #115 remains unmerged and must not merge until the required semantic gate is stabilized without weakening what it proves.
- #87 secretless/local-fixture storage work remains gated until the baseline is mechanically trustworthy.

The current #116 campaign also covers reconciliation of the other open FOSSIL branches on their actual live heads. Do not rely on SHAs embedded in the original #116 body without re-fetching current PR state.

## Current verification policy

For deterministic behavior changes:

1. **RED** — reproduce the defect/invariant first.
2. **GREEN** — smallest correct change.
3. **REGRESSION** — neighboring tests and full suite.
4. **CLEAN VERIFY** — independent clean worktree/environment.
5. **HOSTED EVIDENCE** — exact-head Actions where the PR has hosted acceptance.

No test deletion, skip, xfail, loosened assertion, semantic-gate reduction, conditional suppression, or narrower CI path merely to obtain green.

For a nondeterministic live semantic gate, a single later PASS does not erase earlier contradictory outcomes on the same exact input/SHA. Stabilization must make the gate reproducible enough to distinguish actual semantic regression from model variance without lowering the semantic requirement.

Terra is the normal orchestrator/independent verifier for ambiguous or campaign-level work. Luna is the normal bounded executor after scope is localized. Luna does not self-approve completion.

## Frozen architecture

Canonical FOSSIL knowledge is **immutable evidence + stable corpus IDs + append-only validated knowledge events + versioned pack/ontology contracts + provenance/history**.

Graphiti/Neo4j, lexical/vector indexes, embedding models, rerankers, context construction, planners, model services, Skills, MCP, Cortex, LiteLLM, and future databases remain replaceable projections/services around that durable truth.

Retrieved/source text is untrusted data. Retrieval rank, reranker score, model confidence, multi-model agreement, execution receipts, hosted CI artifacts, and transport health are not truth authority.

## Completed FOSSIL foundation

### Gate 1

Gate 1 proved durable events/artifacts, pack boundaries, lifecycle/disagreement/supersession, replaceable graph projection, rebuild/migration, conversation lineage, exact source/citation integrity, redaction/non-resurrection, cognitive-service contracts, and safe Agent Skill/API/MCP boundaries.

Historical proof anchors include:

- cleaned Gate 1 run `31347457485`, job `93331933728`: 51 passed;
- cognitive-service contract run `31347744797`, job `93332738616`: 56 passed.

### Gate 2

Gate 2 control #33 and children #34–#37 are closed/completed.

Evidence anchors:

- Gate 2A core commit `a028f9e328c2cbcde0185930e90b5eeb4c4efcb8`;
- Gate 2B core commit `2affde923acf196319d90bfa63f206e4a5e2f25f`;
- Gate 2C PR #44 / squash `38aac6325cdb5b738c8a6ac5e55959affb3acfb5`;
- Gate 2C semantic proof run `31364039745`, artifact `9053475462`, digest `sha256:23c95b46f47cec5a16e0a8c0926a4f13532f283d8f4fbcc0de12ceb63db63c41`;
- Gate 2D PR #45 / squash `2d22dee9e6b176956d30005f4d7877baf68b0a3c`;
- closed-state reconciliation PR #46 / squash `a614936249ff0ab201756fa54a1e89699d7b924f`.

Decision D021 remains historical/current retrieval policy until replaced by committed matched evidence: revision-pinned BGE dense is the normal primary and BM25 is explicit degraded fallback. This retrieval policy is not the current execution queue.

## Post-Gate-2 work already completed

Issue #48 produced durable hardening evidence including:

- evolving-corpus temporal/update evaluation;
- answer/citation/unsupported-claim/abstention evaluation;
- retrieval poisoning/untrusted-context structural safeguards;
- replayable query execution receipts.

Those results remain valid historical evidence. They are **not** the current task authority.

Issue #47 remains later retrieval/reranking/model-bakeoff roadmap work. Do not jump to it while the current #116 baseline campaign is blocked.

## Repository family

- `Pukujan/fossil-core` — architecture/contracts/durable core/projections/benchmarks;
- `Pukujan/fossil-common` — stable pack `pack_269099f7b2ba43b7a99b9427d64092de`;
- `Pukujan/fossil-ai-systems` — stable pack `pack_f024177f89a5442db84171c3dd7f58e5`, depending on common.

Repository/database/graph placement is physical placement, not knowledge identity.

## Continuation order

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. live Issue #86
4. latest Issue #94 comments
5. `docs/HANDOFF_CURRENT.md`
6. Issue #116
7. this file
8. `docs/DECISION_LOG.md`
9. focused issue/PR for the eligible task

The chat UI is source material, not the control plane.

## Next-state rule

The immediate next state is determined mechanically from #94. Broadly, the intended order is:

**stabilize the nondeterministic #115 Graphiti semantic acceptance path without weakening it -> exact-head repeatable acceptance -> owner-approved merge/reconciliation -> refresh and verify #112/#113 -> final clean FOSSIL baseline -> eligible secretless/local-fixture #87.**

No production promotion is authorized by this document.
