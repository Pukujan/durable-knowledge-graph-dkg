# Current Handoff

**Date:** 2026-08-10  
**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Repository:** `Pukujan/fossil-core`  
**Status:** **Gate 1 complete. Gate 2 complete and formally closed.**

## Fresh-session transfer

Read this detailed completion checkpoint next:

`docs/handoffs/2026-08-10-chatgpt-session-handoff-gate2-complete.md`

For the Gate 2 midpoint and completed Gate 1 history, retain:

- `docs/handoffs/2026-08-10-chatgpt-session-handoff-gate2-midpoint.md`
- `docs/handoffs/2026-08-10-chatgpt-session-handoff.md`

## Gate 2 result

Gate 2A–2D are complete, landed, and closed. Decision D021 selects the evidence-based retrieval/routing policy:

- normal primary: revision-pinned BGE dense retrieval;
- semantic-runtime availability fallback: BM25, explicitly degraded;
- current/latest/accepted queries must resolve durable lifecycle/provenance rather than treating rank as truth;
- decision-lineage, supersession, disagreement, and multi-target historical/current questions use durable `lineage`/read resolution in addition to retrieval;
- citation/source identity and model-authority invariants are unchanged.

Policy proof:

`docs/implementation/2026-08-10-gate2-default-retrieval-policy.md`

Comparative proof:

- PR #44 squash commit `38aac6325cdb5b738c8a6ac5e55959affb3acfb5`;
- final Gate 2C normal CI run `31366259213`, job `93385174741`, **86 passed in 1.25s**;
- semantic proof run `31364039745`;
- artifact `9053475462`;
- digest `sha256:23c95b46f47cec5a16e0a8c0926a4f13532f283d8f4fbcc0de12ceb63db63c41`.

Gate 2D landed in PR #45 / squash commit `2d22dee9e6b176956d30005f4d7877baf68b0a3c`; final branch-independent CI run `31366800697`, job `93386832166`, **86 passed in 1.02s**.

BGE dense was selected because it was the only compared strategy with zero full retrieval misses and had the best mean recall@5 (`0.98413`). It still requires explicit temporal/current-state and multi-target-lineage safeguards. The hybrid had better MRR but fully missed the key current-architecture case.

## Repository control state

Verified on 2026-08-10:

- #34 — closed/completed;
- #35 — closed/completed;
- #36 — closed/completed;
- #37 — closed/completed;
- #33 — closed/completed;
- open GitHub issues after Gate 2 closure: **0**.

There is no active post-Gate-2 campaign. Do not invent or start a new Gate 3 merely from this handoff. New work should start with an explicit issue/campaign.

## Frozen invariants

Preserve stable pack IDs:

- `fossil-common`: `pack_269099f7b2ba43b7a99b9427d64092de`
- `fossil-ai-systems`: `pack_f024177f89a5442db84171c3dd7f58e5`

Canonical truth remains durable evidence + stable identity + append-only validated events + provenance/history. Graphiti/Neo4j, lexical/vector retrieval, context builders, models, Skills, MCP, and future databases remain replaceable services/projections. Model consensus is not external evidence. Reconstructed evidence cannot silently become verbatim. Do not casually rename `src/dkg`.

Do not reopen Issues #1–#10 or Gate 2 children merely to continue development.

## Suggested next-session prompt

> Continue my FOSSIL project from `Pukujan/fossil-core`. Read `AGENTS.md`, `ARCHITECTURE.md`, `docs/HANDOFF_CURRENT.md`, and `docs/handoffs/2026-08-10-chatgpt-session-handoff-gate2-complete.md` first. Verify GitHub state before changing anything. Gate 1 and Gate 2 are completed campaigns; preserve stable pack IDs and D021's evidence-based retrieval policy unless new committed benchmark evidence justifies reconsideration. There is no active post-Gate-2 campaign, so start new work through a new explicit issue/campaign rather than reopening old Gate 1 or Gate 2 issues.
