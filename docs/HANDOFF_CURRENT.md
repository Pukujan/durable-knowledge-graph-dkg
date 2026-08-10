# Current Handoff

**Date:** 2026-08-10  
**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Repository:** `Pukujan/fossil-core`  
**Status:** **Gate 1 complete. Gate 2 active: #34 and #35 complete; #36 is current; #37 follows.**

## Fresh-session transfer

Read this detailed checkpoint next:

`docs/handoffs/2026-08-10-chatgpt-session-handoff-gate2-midpoint.md`

For completed Gate 1 history and original frozen architecture context, retain:

`docs/handoffs/2026-08-10-chatgpt-session-handoff.md`

## Current GitHub checkpoint

At the time this pointer was updated:

- Gate 2 control **#33** — open;
- **#34** — closed/completed;
- **#35** — closed/completed;
- **#36** — open/current;
- **#37** — open/next;
- draft PR **#44** — open and mergeable;
- PR branch: `agent/gate2-comparative-bakeoff`;
- PR head: `1f71b981feb9ff10636901c61bfb16e677a9f258`;
- exact-head normal CI: run `31364039714`, job `93378520755`, **86 passed in 0.97s**;
- exact-head comparative proof: run `31364039745`, success.

Verify GitHub before relying on these values.

## Current technical conclusion

The 21-case real history-rich corpus and real retrieval adapters are already landed. A same-environment four-strategy bakeoff has been run and raw result JSONs are committed on PR #44.

Dense BGE is the leading **candidate** because it is the only compared strategy with zero full retrieval misses and has the best mean recall, but it still has temporal/ranking and multi-target-lineage weaknesses. The hybrid has higher MRR but completely misses the key current-architecture case. Therefore **no default has been selected yet**; Issue #37 owns that policy decision.

## Immediate next work

Finish #36 / PR #44 before starting #37:

1. persist/verify compact comparison + provenance/proof evidence;
2. keep `selection.selected = null` in #36 artifacts;
3. remove the temporary `.github/workflows/gate2-comparative-proof.yml` workflow;
4. run final branch-independent CI;
5. merge PR #44 and close #36 with exact proof references.

Then complete #37 by selecting and documenting the default retrieval/routing policy, fallback/rollback behavior, temporal safeguards, and reconsideration triggers from committed evidence. Update `docs/DECISION_LOG.md`, `docs/PROJECT_STATE.md`, and this handoff before closing #37 and #33.

## Frozen invariants

Preserve stable pack IDs:

- `fossil-common`: `pack_269099f7b2ba43b7a99b9427d64092de`
- `fossil-ai-systems`: `pack_f024177f89a5442db84171c3dd7f58e5`

Canonical truth remains durable evidence + stable identity + append-only validated events + provenance/history. Graphiti/Neo4j, lexical/vector retrieval, context builders, models, Skills, MCP, and future databases remain replaceable services/projections. Model consensus is not external evidence. Reconstructed evidence cannot silently become verbatim. Do not casually rename `src/dkg`.

Do not reopen Issues #1–#10 for Gate 2 work.

## Suggested next-session prompt

> Continue my FOSSIL project from `Pukujan/fossil-core`. Read `AGENTS.md`, `ARCHITECTURE.md`, `docs/HANDOFF_CURRENT.md`, and `docs/handoffs/2026-08-10-chatgpt-session-handoff-gate2-midpoint.md` first. Verify GitHub state, especially #33, #36, #37, and PR #44. Finish #36 cleanly, then complete #37’s evidence-based retrieval/routing/fallback/rollback policy. Do not reopen Gate 1 or change stable pack IDs/invariants.
