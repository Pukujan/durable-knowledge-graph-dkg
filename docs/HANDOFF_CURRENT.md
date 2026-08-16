# Current Handoff

**Date:** 2026-08-16  
**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Repository:** `Pukujan/fossil-core`  
**Architecture authority:** Issue #86  
**Execution queue / claim ledger:** Issue #94

## Current status

FOSSIL operates under the invariant:

> **Compute may disappear; truth must not.**

Current subsystem boundary:

> **Cortex V5 owns execution policy. FOSSIL owns durable knowledge/evidence. GitHub owns source/coordination/review. LiteLLM/CKFF owns provider/model/route transport facts. Infrastructure and projections are replaceable.**

Do not treat any SHA in this file as a live lock. Re-fetch Issue #94 and current GitHub state before any write, merge, credentialed proof, or task claim.

## Immediate checkpoint — OBJECT_STORE_LIVE / R2

Current verified FOSSIL `main` checkpoint:

`f3f439bc994f081ef9550f99ebc8002a128c19f4`

This is the merge of PR #130, **Fix R2 object-scoped access preflight**.

PR #130 resolved the live R2 compatibility blocker without broadening credentials or weakening acceptance:

- replaced bucket-level `HeadBucket` with a proof-prefix-scoped `ListObjectsV2` probe;
- keeps the probe under the unique `fossil-live-proof/<run>/<attempt>/` prefix;
- malformed list responses remain fail-closed;
- regression coverage forbids reintroducing `HeadBucket` into this proof path;
- local validation reported `280 passed, 1 skipped`;
- exact-head DKG `31956846177` SUCCESS;
- final-main DKG `31958886746` SUCCESS.

### Live proof is still NOT PASS

The latest credentialed live run is historical only:

- workflow run `31924177103`;
- old target SHA `9f9f426a192342042b42f189a11bbb53079b6b92`;
- attempt 1 failed closed because endpoint/bucket variables were absent;
- attempt 2 proved the GitHub environment variables and S3 credential secrets were loading, then old code failed on R2 `HeadBucket` HTTP 400;
- rebuild did not run.

Do **not** reuse or rerun that old-SHA run as #124 acceptance after PR #130. The next valid evidence must be a **fresh `workflow_dispatch` from trusted default-branch code against the exact current `main` SHA** with confirmation `OBJECT_STORE_LIVE`.

If `main` has moved, use the newly fetched exact main SHA instead of the checkpoint above.

## R2 configuration checkpoint

GitHub Environment for the proof is deliberately:

`r2-proof`

Current non-secret environment variables have been configured:

- `R2_ENDPOINT`
- `R2_BUCKET`

Existing environment secrets remain the S3 runtime credentials:

- `FOSSIL_R2_ACCESS_KEY_ID`
- `FOSSIL_R2_SECRET_ACCESS_KEY`

The workflow accepts both `R2_*` and `FOSSIL_R2_*` naming where wired by PR #129. Never print, copy, or move secret values into GitHub issues, chat, logs, receipts, or repository files.

Cloudflare API verification during the PR #130 diagnosis confirmed the intended R2 bucket exists, uses the default jurisdiction, and the configured endpoint shape is appropriate. The prior HTTP 400 was traced to the bucket-level probe, not to a need for broader credentials.

### Local Cloudflare access for Codex

Owner/local Codex has a newly created **account-owned Cloudflare API token scoped only to `Workers R2 Storage Read`**, verified active and able to access the FOSSIL R2 bucket. It is available only in the owner's local environment for diagnostics. It is **not** the R2 S3 Access Key ID / Secret Access Key used by the GitHub live proof.

Do not inspect, echo, log, commit, or copy that API token. Credential rotation and any temporary transfer-document cleanup are owner-local hygiene, not repository evidence; keep token values and transfer links out of GitHub.

## Next valid execution path

A fresh session should do this in order:

1. Re-read Issue #94 and verify there is no winning unexpired claim for the same FOSSIL lane.
2. Re-fetch `main` and Issue #124.
3. Confirm normal DKG remains green on the exact main SHA.
4. Dispatch a **new** `OBJECT_STORE_LIVE` run from the trusted default-branch workflow using:
   - `ref=<exact current main SHA>`
   - `confirmation=OBJECT_STORE_LIVE`
5. Inspect bounded evidence for all three jobs: preflight, writer, rebuild.
6. Claim PASS only if the full #124 contract passes: exact checkout, immutable/idempotent/conflict semantics, deterministic events, fresh-runner reconstruction twice, exact surviving artifact verification, redaction/non-resurrection, negative controls, sanitized receipts, and same-head normal DKG.
7. If provider behavior fails again, classify from evidence instead of weakening the proof:
   - missing/invalid auth or required configuration → `BLOCKED_CREDENTIAL`;
   - provider/S3 compatibility mismatch → `BLOCKED_PROVIDER_COMPATIBILITY`;
   - FOSSIL semantics/code failure → actual test failure requiring repair.
8. After a real #124 PASS, update/close #124 with exact evidence, then finish Issue #87 closeout using the existing latency/recovery evidence and projection architecture. Do not automatically start Issue #111 until its sequencing is reconciled.

No production deployment is authorized by this handoff.

## Provider-neutral storage anchors

The storage lane preceding the live proof remains authoritative:

- PR #121: provider-neutral S3-compatible artifact/event adapters with immutable/idempotent/conflict semantics.
- PR #123: real disposable S3-compatible MinIO proof with no cloud credentials and successful fresh reconstruction.
- PR #125: manual `OBJECT_STORE_LIVE` harness with fresh-runner artifact/event verification and redaction non-resurrection.
- PR #128: fixed hosted-runner workflow planning/context handling.
- PR #129: reconciled the workflow to existing GitHub Environment `r2-proof` and current/legacy variable-secret names.
- PR #130: replaced the R2-incompatible bucket-level preflight with the required object/prefix-scoped probe.

R2 remains the first live candidate only. The provider-neutral `S3ArtifactStore` / `S3DurableEventStore` contract is architecture truth.

## External runtime posture — read only

The owner has explicitly requested that **Cortex V5 and LiteLLM/CKFF not be modified as part of this FOSSIL continuation**. Inspect them when needed to understand current behavior; do not change their repositories or workflows unless the owner separately authorizes that work.

Detailed reconciliation snapshot:

`docs/operations/EXTERNAL-RUNTIME-RECONCILIATION-2026-08-15.md`

Operational summary:

- Cortex V5 is the active execution-policy runtime; V4/SSC are historical, not current authority.
- Cortex V5 uses deterministic task/risk/methodology classification, live LiteLLM model-catalog refresh, explicit model selection, streamed Chat Completions, contained tools, deterministic verification, and sanitized receipts.
- Retry/model switches are distinct attempts; no synthetic health call establishes task success.
- LiteLLM/CKFF is transport/routing infrastructure, not FOSSIL truth authority.
- Dated LiteLLM prose can lag source/config; current exact source/config is operational fact.

## Read first

For a fresh session:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. Issue #86
4. latest Issue #94 comments
5. this file
6. `docs/PROJECT_STATE.md`
7. Issue #124
8. Issue #87
9. `docs/operations/EXTERNAL-RUNTIME-RECONCILIATION-2026-08-15.md`
10. `docs/DECISION_LOG.md`
11. the focused issue/PR for the eligible task

## Frozen authority rules

- FOSSIL durable evidence/events, stable IDs, provenance, lifecycle, lineage, redaction, and accepted contracts remain semantic authority.
- Retrieval rank, reranker score, model confidence, model tier, and multi-model agreement are not truth.
- Graphiti/Neo4j, search/vector indexes, models, Cortex, LiteLLM, Skills, MCP, dashboards, and CI artifacts remain replaceable services/projections.
- A fallback response is not evidence that the requested model itself succeeded.
- `2xx` with empty/malformed/truncated/zero-usable output is failure.
- Reconstructed evidence cannot silently become verbatim evidence.
- Ordinary PR CI remains secretless.
- Production promotion always requires separate explicit human authorization.
- Never weaken acceptance merely to obtain green.

## Claim protocol

Before mutating work, use Issue #94:

```text
CLAIM task=<TASK_ID>
agent=<unique-agent-id>
mode=<LOCAL_CODEX|CLOUD_CODEX|CHATGPT|ACTIONS>
lease_until=<ISO-8601 UTC>
repo=<repo>
starting_ref=<branch/SHA/PR>
```

Immediately re-fetch #94. Earliest valid unexpired claim wins. One active mutating owner per repo lane unless the task explicitly declares safe parallelism.

Close with exact `DONE`, `BLOCKED`, or `RELEASE` evidence.

## Immediate fresh-agent behavior

1. Read #86, #94, #124, and #87 live.
2. Confirm current `main`, active PR heads, review state, environment/config state, and claim ownership.
3. Treat Cortex V5 and LiteLLM/CKFF as read-only unless the owner explicitly opens separate mutation work.
4. Do not use the old `31924177103` run as acceptance for the post-PR-130 main.
5. Take only an eligible task matching access and collision rules.
6. Work on an isolated branch/target for code/doc mutation.
7. Test mechanically and record exact evidence.
8. Post `DONE`, `BLOCKED`, or `RELEASE`.
9. Re-read #94 before taking another task.

If no eligible task exists, stop with explicit idle/BLOCKED evidence rather than inventing work.
