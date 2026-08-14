# Current Handoff

**Date:** 2026-08-14
**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Repository:** `Pukujan/fossil-core`  
**Current architecture authority:** Issue #86  
**Current execution queue / claim ledger:** Issue #94

## Current status

The project has moved from a local-machine-centered architecture to **disposable ordinary compute + durable truth**, with one narrow trusted-local exception for credentials that currently exist only on the owner's PC.

The current invariant is:

> **Compute may disappear; truth must not.**

The current subsystem boundary is:

> **Cortex owns execution. FOSSIL owns durable knowledge/evidence. GitHub owns coordination/review. LiteLLM/CKFF owns provider/model/route factual transport. Infrastructure is replaceable.**

The owner's PC may act as a **trusted self-hosted execution/credential bridge**, but it is not semantic authority and is not required for ordinary secretless PR CI.

## Latest ingestion continuation — 2026-08-14

Draft PR #113 (`agent/ingest-shared-chat-reconstructions`) now carries three
reconstructed public shared-chat checkpoints in the shared-chat ingestion
manifest. The third checkpoint is `Experiment Comparison Inquiry` and records
the rendered proposal for intent, epistemic, and influence firewalls, including
canonical semantic projection before embedding. The public page exposed a
rendered conversation and unnamed uploaded files only; no uploaded file or
external paper mentioned in the chat was promoted to captured source evidence.

The importer and lineage tests pass with `180 passed`. The checkpoints remain
explicitly `reconstructed`, with immutable artifact/span/event handling and
idempotent replay. If raw exports become available, ingest them as separate
verbatim sources rather than replacing these checkpoints.

## Read first

For a fresh autonomous session, read in this order:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. this file
4. Issue #86 — current architecture reconciliation
5. Issue #94 — current execution queue and append-only claim ledger
6. `docs/DECISION_LOG.md`
7. `docs/architecture/2026-08-12-trusted-local-runner-boundary.md`
8. `docs/architecture/2026-08-10-cortex-fossil-ownership-boundary.md`
9. `docs/architecture/2026-08-10-context-construction-compression-boundary.md`
10. Issue #96 — trusted local autonomous WorkOrder runner
11. Cortex issue #1 / current Cortex queue refs
12. LiteLLM issue #11 / current LiteLLM queue refs

Verify live GitHub state immediately before any write, merge, rebase, deploy or task claim.

## Frozen authority rules

- Retrieval rank is candidate ordering, not truth.
- Reranker score is not truth.
- Model confidence is not truth.
- Multi-model agreement is not external evidence.
- GitHub Actions artifacts/caches are not canonical FOSSIL truth.
- FOSSIL durable evidence/events, stable IDs, provenance, lifecycle, lineage and accepted contracts remain semantic authority.
- Cortex owns task/execution policy, WorkOrder lifecycle, retries, fencing, fan-out/fan-in, deadlines and closeout.
- LiteLLM/CKFF owns provider/model/route/capability/timeout/health factual transport state; callers own selection policy.
- Ordinary PR CI remains secretless.
- Production promotion requires a separate explicit authorization.

## Legacy SSC — RETIRED / SUPERSEDED

Legacy `stupidly-simple-cortex` (SSC) is **not a current runtime, memory, RAG, ontology/current-state, project-state, orchestration or Cortex authority**.

Cortex V4 must operate with SSC absent.

Do not use as current authority:

- SSC living ontology/current-state values;
- SSC BM25/vector ranking output;
- generated conclusions/summaries;
- historical project/task state;
- model consensus/judge conclusions;
- old SSC research prose merely because SSC labeled it accepted/current;
- private-SSC compatibility tests as a merge/runtime requirement.

The retirement is evidence-backed by known noisy/false-positive corpus behavior and historical retrieval/index/stale-artifact failures. Treating those outputs as authority can degrade decisions by turning retrieval/system errors into apparent truth.

Potentially useful old eval/checker assets may survive only after **independent standalone extraction and revalidation** with exact source revision/path, bytes/hash, actual row counts, provenance/license, checker/test dependencies and holdout/leakage controls.

Do not revive SSC runtime merely to preserve an old asset.

Durable retirement decision: D023 in `docs/DECISION_LOG.md`.

## Trusted local autonomous runner

Manual per-session Terra/Luna/Codex dispatch is superseded as the normal local operating model.

Current plan: Issue #96 / #94 `INFRA-03`.

The local PC may run a dedicated self-hosted GitHub Actions runner because some Railway/provider/telemetry credentials currently remain local-only.

### Security invariant

> **A pull request must never be able to cause its own mutable code or workflow definition to execute on the credential-bearing local runner.**

Therefore:

- ordinary `pull_request` workflows do not target the trusted-local runner;
- do not use `pull_request_target` to run PR-controlled code with secrets;
- trusted-local dispatch comes from reviewed/default-branch-controlled workflow/dispatcher code;
- credential-bearing verification requires an exact reviewed SHA;
- local `.env` values are never uploaded, printed or copied into GitHub/FOSSIL receipts;
- Terra/Luna role names never imply secret access.

### Local lanes

**Secretless local engineering worker**

- disposable worktree/process per attempt;
- code/test/lint/mutation/fault work;
- credentials unloaded;
- mechanical PASS/FAILED/BLOCKED closeout;
- Git commit + structured receipt checkpoint where sufficient.

**Privileged verifier**

- exact reviewed SHA only;
- local env may be loaded only for the explicitly authorized credential set;
- isolated Railway staging / protected telemetry / future object-store verification;
- sanitized receipts only;
- no implicit production promotion.

The verifier is deliberately a separate model-free Docker service. `fossil-privileged-secrets` is a root-only Docker volume in the local Docker Desktop WSL data store (`D:\DockerDesktopWSL`) containing the owner-provided SSC `.env` copy; `codexworker` access was mechanically denied. Queue records select only a locally owned `verifier_action`; they cannot supply commands, secret names, or values. See D026 and `docs/operations/TRUSTED_LOCAL_RUNNER.md` before configuring a staging action.

### Agent roles

- **Terra:** complex/root-cause, architecture-sensitive, and explicitly trusted local/infra tasks.
- **Luna:** cheaper/mechanical regressions, reproductions, lint/test loops, evidence collection and bounded implementation.

Roles are execution policy, not authority.

Durable runner decision: D022 in `docs/DECISION_LOG.md`.

## Completed foundation

### FOSSIL

- FOSSIL-01 merged PR #93 — baseline repair; GitHub DKG 112/112.
- FOSSIL-02 merged PR #92 — status-aware build-context/preflight packet; GitHub DKG 119/119.
- FOSSIL-03 merged PR #91 — disposable rebuild proof; GitHub DKG 122/122.
- FOSSIL-04 merged PR #95 — reusable assurance; GitHub DKG + engineering assurance green.

Build-context v1 now fails closed on unresolved authority/current-state conflict and retrieval rank never creates authority.

### Study OS

- STUDY-01 merged private-study-log PR #56; validation green; no transcript duplication.

### LiteLLM / Railway

- Secretless catalog + semantic-contract work on LiteLLM PR #12 reached code-green before live staging.
- Isolated Railway staging exists and was proven separately from production.
- Production was independently restored/verified on its intended main revision after a source-connection action briefly showed shared-source risk; no production semantic request occurred during the incident.
- Live staging found two real semantic failures:
  1. Chat streaming can return HTTP 200 with zero usable bytes.
  2. Forced-tool Responses can fail with HTTP 502.

These are tracked by `LITELLM-05` and must remain fail-closed.

### Cortex

- WorkOrder recovery PR #12 has targeted recovery tests 10/10 green.
- The old full-suite blocker was polluted by remaining SSC-dependent tests/adapters.
- `CORTEX-03` SSC-compatibility CI plan was explicitly released/superseded.
- `CORTEX-04` is the current Cortex task: remove SSC from the normal Cortex runtime/merge-critical path and replace legacy tests only with equivalent V4-owned invariants.
- PR #13 must not be merged merely to preserve SSC compatibility.

## Current READY / active task order

### P0 — LITELLM-05

Repair the two live gateway failures:

- HTTP 200 empty/zero-usable stream;
- forced-tool Responses failure.

Requirements:

- failed-first deterministic regressions;
- smallest code/config fix;
- secretless ordinary PR CI;
- baseline Chat/Responses/embeddings/rerank unchanged;
- requested-vs-actual model/route and usage preserved;
- exact-reviewed-SHA isolated staging verification before merge/promotion claims;
- production untouched.

### P1 — CORTEX-04

Make Cortex V4 fully independent of SSC:

- Cortex starts/runs with SSC unavailable;
- remove legacy SSC runtime/corpus dependency from normal execution;
- classify SSC adapters/tests as migration debt;
- replace/remove legacy assertions with V4-owned invariant tests, never skip to fake green;
- preserve WorkOrder recovery/fencing/idempotency semantics;
- hosted secretless full suite green.

### P1.5 — INFRA-03 / Issue #96

Build the trusted local autonomous WorkOrder runner:

1. WorkOrder schema/validator;
2. claim/repo/access/generation/deadline validation;
3. disposable worktree/process per attempt;
4. Terra/Luna role selection;
5. secretless worker wrapper;
6. fault tests for death/duplicate/stale/malformed/timeout/cancel/late result;
7. trusted/default-branch dispatch workflow;
8. local runner registration/runbook;
9. no-secret end-to-end WorkOrder proof;
10. separate privileged exact-SHA verifier;
11. exact-SHA isolated staging proof with sanitized receipts.

### Next after those gates

- finish/land Cortex WorkOrder recovery chain;
- wire disposable GitHub Actions WorkOrders using validated build-context v1;
- run CAMPAIGN-01: first bounded real-model campaign, flat max parallel <=4, objective tests, deliberate kill/retry, no production deploy;
- only after campaign evidence consider matched executor bakeoff (OpenCode vs Aider vs direct/simple).

## Access classes

- `CLOUD_SECRETLESS` — ordinary code/test/PR CI, no protected credentials.
- `LOCAL_INFRA` — trusted local PC required.
- `TRUSTED_SECRET_WORKFLOW` — reviewed/trusted workflow only, never arbitrary PR code.
- `LIVE_STAGING` — isolated non-production endpoint.
- `OBJECT_STORE_LIVE` — narrowly scoped non-production object-store credential.

A task's role does not widen its access class.

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

Immediately re-fetch #94 comments. Earliest valid unexpired claim wins. One active mutating owner per repo lane unless the task explicitly declares safe parallelism.

Close with `DONE`, `BLOCKED` or `RELEASE` using exact refs/tests/evidence.

Do not invent architecture or bypass dependencies when no eligible READY task exists.

## Engineering policy

- SDD always.
- TDD for deterministic code behavior where practical.
- Infra/config: spec first -> failing verification/probe -> smallest change -> passing verification.
- Wiring/integration tests for boundaries.
- E2E for important actual flows.
- Hidden holdouts for autonomous AI/model evaluation.
- Mutation testing selectively on small critical validators/gates/recovery/security logic.
- Fault injection mandatory for recovery/retry infrastructure.
- Explicit security checks at secret/deployment boundaries.
- Regression test for every discovered bug.

Shorthand:

> **SDD always, TDD for code behavior, wiring/E2E when there is actual wiring, hidden holdouts for AI evaluation, and mutants only on the small pieces where a false green would hurt us.**

## Forbidden premature conclusions

Do not select without matched evidence:

- OpenCode vs Aider vs direct/simple executor;
- R2 vs S3;
- final Spec Kit vs V4 methodology boundary;
- persistent-service topology;
- large model matrix.

Do not promote production from the current queue.

## Immediate fresh-agent behavior

1. Read #86 and #94 live.
2. Confirm SSC retirement / D023.
3. Confirm trusted-local boundary / #96 / D022.
4. Find an eligible READY task matching access.
5. Claim and re-fetch ledger.
6. Work on an isolated branch/worktree.
7. Test mechanically and fault-inject where required.
8. Post exact closeout evidence.
9. Re-read queue and take the next eligible task.

If no eligible task exists, stop with explicit idle/BLOCKED evidence rather than inventing work.
