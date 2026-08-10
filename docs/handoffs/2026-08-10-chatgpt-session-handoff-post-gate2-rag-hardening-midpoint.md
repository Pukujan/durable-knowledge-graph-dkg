# FOSSIL session handoff — post-Gate-2 RAG hardening midpoint

**Date:** 2026-08-10  
**Status:** safe midpoint; stop here and continue in a fresh session  
**Active campaign:** `Pukujan/fossil-core` Issue #48  
**Related model/retrieval workstream:** Issue #47

## Read first in the next session

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `docs/HANDOFF_CURRENT.md`
4. this handoff
5. `docs/PROJECT_STATE.md`
6. `docs/research/2026-08-10-production-rag-hardening-research-trace.md`
7. Issue #48
8. Issue #47
9. D021 in `docs/DECISION_LOG.md`

## What was completed in this session

### 1. Current RAG research review completed

A review of 2025–2026 RAG papers and current production patterns was mapped against FOSSIL. The durable conclusion was **harden the existing architecture rather than redesign the durable core**.

The research focused on:

- evolving/versioned knowledge and temporal retrieval;
- final-answer/citation/refusal evaluation rather than retrieval metrics alone;
- uncertainty and confident-error behavior under noisy retrieval;
- hybrid retrieval and real reranking;
- adaptive routing only when it beats simple baselines;
- poisoning/untrusted-context risks;
- strong long-context/direct-source baselines;
- observable/replayable query execution receipts;
- ACL/redaction propagation before shared/cloud deployment.

Core invariants were not changed. D021 remains approved until new committed FOSSIL benchmark evidence justifies reconsideration.

### 2. Post-Gate-2 campaign #48 created

Issue #48 is open:

`Post-Gate-2 campaign: production RAG hardening and evidence-driven retrieval evolution`

It contains workstreams for:

- evolving-corpus temporal benchmarks;
- end-to-end answer/citation/abstention evaluation;
- poisoning/untrusted-context hardening;
- embedding/hybrid/reranker bakeoff, with #47 as the candidate-model workstream;
- conservative adaptive routing;
- replayable query execution receipts;
- ACL/redaction readiness.

Gate 1 and Gate 2 remain closed/completed. Do not reopen them merely to continue.

### 3. Research trace landed in fossil-core

PR #49 — `Post-Gate-2: record production RAG hardening research and activate campaign` — was merged.

- merged core commit: `6799b2db743d91b004b1e16b5129285a582f8847`
- research trace: `docs/research/2026-08-10-production-rag-hardening-research-trace.md`
- CI run: `31395512960`
- job: `93477303856`
- result: **86 passed in 0.96s**

PR #49 also updated `AGENTS.md`, `docs/HANDOFF_CURRENT.md`, and `docs/PROJECT_STATE.md` so fresh sessions see #48 as active.

The research trace is explicitly a **local derived synthesis**. It must not be confused with the external papers/vendor pages themselves. Full research-trace ingestion should later capture those original external sources as separate source snapshots.

## Research-to-corpus ingestion: current exact state

The next task was to ingest the merged local research synthesis into the existing `fossil-ai-systems` pack using the same durable artifact/snapshot/event machinery already proven in Gate 2.

Stable AI-systems pack ID remains:

`pack_f024177f89a5442db84171c3dd7f58e5`

### Authoritative source being ingested

Core source snapshot target:

`Pukujan/fossil-core@6799b2db743d91b004b1e16b5129285a582f8847:docs/research/2026-08-10-production-rag-hardening-research-trace.md`

Verified source bytes:

- byte size: `17269`
- SHA-256: `b030642ff65f883ff467529c73cbb6e502deca28f4c3dece0c2879bf690d3b15`
- artifact ID: `art_b030642ff65f883ff467529c73cbb6e5`

### IMPORTANT: two AI-systems branches exist

**Use this branch only:**

`agent/post-gate2-rag-research-seed-v2`

Latest verified head at handoff time:

`10627d9a376a6af8d50406333609227487197134`

That commit is `Index production RAG research artifact`.

**Do not merge this earlier branch:**

`agent/post-gate2-rag-research-seed`

The first attempt used arbitrary IDs and omitted an artifact blob. `PackFixtureAudit` inspection showed that FOSSIL requires its exact deterministic identity functions for event/source/citation IDs and requires actual content-addressed blob bytes. The first branch should be treated as abandoned/invalid scratch work.

### What is already on the valid v2 branch

The v2 branch was restarted cleanly from `fossil-ai-systems/main` and contains:

- the exact 17,269-byte research markdown as a content-addressed blob under `artifacts/blobs/sha256/...`;
- immutable artifact manifest for `art_b030642ff65f883ff467529c73cbb6e5`;
- a source snapshot pointing to the immutable core commit above, using FOSSIL's `SourceSnapshotStore` identity derivation;
- six high-signal research claims, each represented as a `claim.proposed` event followed by a separate `claim.state_changed` to `supported`;
- exact byte-span citations and passage hashes into the research artifact;
- event IDs generated with `deterministic_event_id(pack_id, idempotency_key)`;
- citation/source IDs generated with the same `_stable_id` rules used by the core implementation;
- the pack-wide `artifacts/manifest.jsonl` updated to index the new artifact.

The six extracted topics are intentionally small/high-signal rather than a claim dump:

1. temporal/version state must not be inferred from semantic similarity alone;
2. final-answer reliability must be evaluated independently from retrieval;
3. reranking deserves a real FOSSIL bakeoff but stays replaceable;
4. uncertainty/abstention must be explicit answer behavior;
5. retrieved content must be treated as untrusted data, with poisoning as a distinct threat model;
6. the reviewed evidence supports hardening FOSSIL's existing durable core rather than replacing it.

## CRITICAL: what has NOT been completed

**The v2 corpus branch has not yet passed the full cross-pack `PackFixtureAudit`.**

Therefore:

- do **not** call research-to-corpus ingestion complete yet;
- do **not** merge `agent/post-gate2-rag-research-seed-v2` yet;
- no AI-systems PR has been opened for the v2 branch yet;
- Issue #48's corpus-ingestion exit item should remain incomplete until validation + merge are done.

## Exact next steps

### Step 1 — verify current GitHub state

Verify:

- core main still contains merged PR #49 / `6799b2db...` or later compatible commits;
- Issue #48 remains active;
- `fossil-ai-systems` branch `agent/post-gate2-rag-research-seed-v2` still exists and points at `10627d9a...` or a known descendant;
- no one has already opened/merged an equivalent AI-systems PR.

### Step 2 — run the same pack audit used for Gate 2

Use the current `fossil-core` implementation of:

`dkg.pack_fixture.validate_pack_fixtures`

Audit `fossil-common` together with the **v2** AI-systems branch, because cross-pack ownership/mount rules matter.

The earlier proven pattern was:

```python
from pathlib import Path
from dkg.pack_fixture import validate_pack_fixtures

report = validate_pack_fixtures(
    [Path('.packs/common'), Path('.packs/ai-systems')],
    schemas_root=Path('schemas'),
)
print(report)
```

Use `fossil-common/main` (or the current stable equivalent) and clone/check out `fossil-ai-systems@agent/post-gate2-rag-research-seed-v2`.

The audit must verify at least:

- artifact blob hash and byte size;
- artifact index equals immutable manifests;
- source ID/snapshot ID deterministic identity;
- source snapshot ↔ artifact consistency;
- event schema validity;
- deterministic event IDs from idempotency keys;
- event path identity;
- exact citation span bounds/hash/ID;
- mount-aware cross-pack references;
- lifecycle replay of proposed → supported claims.

### Step 3 — fix v2 only if the audit finds anything

Do not patch the invalid first branch. Make all fixes on:

`agent/post-gate2-rag-research-seed-v2`

Preserve the stable pack ID and existing main history.

### Step 4 — open the AI-systems corpus PR

Once the audit passes, open a PR from v2 to `fossil-ai-systems/main` explaining:

- source core commit `6799b2db...`;
- artifact SHA-256 / artifact ID;
- six derived claims + exact citations;
- research synthesis remains distinct from original external sources;
- validation command and audit result.

Then merge only after validation is green.

### Step 5 — reconcile core campaign state

After the AI-systems PR lands:

- add a proof comment to core Issue #48;
- check/update the research-trace-ingested criterion where appropriate;
- record the landed AI-systems commit as the new pack source pin for later benchmarks;
- update `docs/HANDOFF_CURRENT.md` if the active continuation point has materially moved.

Do **not** mark the entire #48 campaign complete; only the research-trace/corpus-seed portion will be complete.

## Current architectural guardrails

Preserve:

- canonical truth = immutable evidence + stable corpus IDs + append-only validated events + versioned contracts + provenance/history;
- stable `fossil-common` pack ID `pack_269099f7b2ba43b7a99b9427d64092de`;
- stable `fossil-ai-systems` pack ID `pack_f024177f89a5442db84171c3dd7f58e5`;
- D021 as current retrieval policy until new committed corpus-specific evidence supersedes it;
- retrieval rank/reranker score/planner/model output as candidate ordering/context, not truth;
- original external research sources distinct from local derived synthesis;
- retrieved text as untrusted data, not executable policy;
- Graphiti/Neo4j, embeddings, rerankers, planners, models and context builders as replaceable services/projections;
- no casual `src/dkg` rename.

## Suggested next-session prompt

> Continue FOSSIL from the post-Gate-2 RAG hardening midpoint. Read `AGENTS.md`, `ARCHITECTURE.md`, `docs/HANDOFF_CURRENT.md`, and `docs/handoffs/2026-08-10-chatgpt-session-handoff-post-gate2-rag-hardening-midpoint.md` first. Verify GitHub state. PR #49 / core commit `6799b2db743d91b004b1e16b5129285a582f8847` already landed the research trace and activated Issue #48. Resume the unfinished research-to-corpus ingestion from `Pukujan/fossil-ai-systems` branch `agent/post-gate2-rag-research-seed-v2` at `10627d9a376a6af8d50406333609227487197134` or its known descendant. Do not merge or use the abandoned `agent/post-gate2-rag-research-seed` branch. First run `validate_pack_fixtures` jointly over `fossil-common` and the v2 AI-systems branch; only after that audit passes should you open/merge the AI-systems PR and update Issue #48. Preserve stable pack IDs and D021 unless new committed benchmark evidence justifies reconsideration.
