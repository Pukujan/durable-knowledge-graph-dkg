# Overnight disposable-Actions implementation handoff — 2026-08-12 01:50 America/New_York

**Status:** CURRENT EXECUTION HANDOFF / implementation sequencing checkpoint  
**Architecture authority:** `fossil-core#86` plus accepted merged architecture contracts; this handoff does not promote undecided candidates into architecture truth.  
**Do not duplicate transcript ingestion.** The earlier shared ChatGPT transcript and the later reconstructed architecture-reconciliation continuation are already preserved in `Pukujan/fossil-ai-systems`. Preserve only a small continuation after a meaningful new implementation milestone.

## Read first

1. `Pukujan/fossil-core#86` — current disposable-compute architecture reconciliation tracker.
2. Latest #86 comment titled `Overnight execution handoff checkpoint — 2026-08-12 01:50 America/New_York`.
3. `Pukujan/fossil-core#84` — universal engineering preflight + risk-triggered foundation checks; read its latest build-context-packet comment.
4. `Pukujan/fossil-core#88` — GitHub Actions engineering assurance lane.
5. `Pukujan/cortex-v4#11`, plus Cortex #2 and #5.
6. `Pukujan/litellm-ckff-ops#9`, #10, #11 and draft PR #8.
7. `Pukujan/fossil-core#87`.
8. `Pukujan/private-study-log#55` only for the non-blocking Study OS lane.

Verify live GitHub state before changing code. GitHub may be fresher than the latest FOSSIL ingestion.

## Current invariant

> **Compute may disappear; truth must not.**

Current working boundary:

- GitHub Actions = default bounded disposable engineering compute candidate/control plane.
- GitHub Issues/PRs/code = human/project coordination and source/review state.
- FOSSIL = durable semantic evidence/knowledge/lifecycle/lineage; not the scheduler.
- Cortex V4 = execution policy, attempts, retries/recovery/evidence; not provider factual truth.
- LiteLLM/CKFF ops = provider/model/route/capability/timeout/observed-health/account factual transport plane; caller owns model-selection policy.
- Langfuse/OTEL/GitHub summaries = observability surfaces; not semantic truth.
- Actions artifacts/caches = temporary/rebuildable, never canonical FOSSIL truth.

## Local prerequisite report — sanitized

The owner/local Codex reported:

```text
V4_LITELLM_BASE=PRESENT
V4_CALLER_KEY=PRESENT
TELEMETRY_READ_GITHUB=PRESENT
TELEMETRY_READ_RAILWAY=PRESENT
STAGING=NOT_CONNECTED
```

Additional local findings:

- current GitHub plan does not provide the desired Environment protection/approval rules for this private repository;
- current Railway LiteLLM deployment uses one source branch across environments;
- PR #8 cannot be deployed as staging-only without a distinct staging service/preview mechanism;
- Railway production was restored to `main`;
- queued PR deployments were canceled.

Never request or print the actual secret values.

## Security consequence

Until a distinct isolated staging/protected path exists:

- **ordinary PR CI must be secretless**;
- do not execute arbitrary PR/agent branch code with CKFF account, provider, telemetry-read, LiteLLM admin, deployment, or production credentials;
- privileged secret-using workflows should be trusted/default-branch/manual and narrowly scoped;
- no live Railway staging result may be claimed unless an actual isolated non-production target exists;
- do not merge PR #8 merely to expose a `workflow_dispatch` if merge also implicitly promotes production without the agreed live-proof path.

The lack of staging is `BLOCKED_TOPOLOGY`, not evidence that PR #8 code is wrong.

## Precondition for meaningful unattended implementation

Before a real autonomous coding WorkOrder is dispatched, implement/use **build-context packet v1** from #84:

```text
FOSSIL lifecycle/status-aware retrieval
        +
live GitHub issue/PR/branch/CI state
        +
universal SWE kernel + selected risk packs
        |
        v
validated task-specific build-context packet
        |
        v
WorkOrder
```

Minimum packet sections:

- task/outcome;
- current/accepted authority;
- current implementation state from GitHub;
- candidates under test;
- undecided items;
- relevant superseded/historical material;
- contradictions / `current_state_unresolved`;
- selected SWE/distributed-systems/security/release checks;
- stable evidence/provenance IDs + GitHub refs;
- freshness/version state;
- unresolved assumptions/blockers;
- required tests/fault probes/closeout evidence.

Retrieval/reranker rank must never determine what is current. Material unresolved authority conflicts block implementation or become bounded research/experiment WorkOrders.

## Overnight objective

Advance the architecture through **safe, independent, secretless implementation/proof lanes**. Produce draft PRs and mechanical evidence. Do not auto-promote production and do not select final executor/storage/service architecture from incomplete evidence.

## Parallel lane A — LiteLLM #11 false-success repair

Can run now without Railway staging:

- reproduce/localize generic gateway failure from current code and PR #7 evidence;
- implement/refine smallest guarded repair;
- semantic fixtures for `2xx + empty`, malformed JSON, zero-payload streams, no-content/no-tool completion, empty embedding/rerank results;
- run gateway ephemerally in Actions/local test process where practical;
- validate model inventory/chat/responses/tools/embeddings/rerank semantics using secretless fixtures/mocks;
- preserve requested/actual identity and timeout ownership in receipts;
- design live probes for later isolated staging.

Must **not** claim `STAGING_GREEN` or deploy production tonight solely from ephemeral/fixture evidence.

## Parallel lane B — LiteLLM #9 CKFF factual catalog automation

- discover structured/public CKFF metadata/API sources before scraping HTML;
- preserve provider-stated facts separately from observed facts;
- normalize IDs/prices/routes/base URLs/timeout/streaming/capability claims with provenance/freshness;
- extend the existing versioned model-catalog work rather than create competing registries;
- generate candidate LiteLLM config from normalized facts + secret placeholders;
- validate generated config deterministically;
- expose stable factual read contract for V4/FOSSIL/clients;
- no model-selection policy in the catalog.

Use public/provider facts and secretless fixtures first. Avoid account-wide aggressive live probing.

## Parallel lane C — LiteLLM #10 / PR #8 telemetry

Phase A provider telemetry is substantially implemented in draft PR #8. Overnight work may:

- review tests/contracts/security boundaries;
- add secretless endpoint/auth/cache/error fixtures if gaps remain;
- ensure telemetry failure cannot gate inference;
- ensure provider quota units are preserved without inventing USD/balance semantics;
- document current `BLOCKED_TOPOLOGY` live-Railway acceptance state.

Do not close #10 after Phase A. Phase B remains:

- LiteLLM-attributed consumer usage;
- time-window/correlation reconciliation against CKFF provider-reported usage;
- discrepancy/freshness reporting;
- no new billing database unless later justified.

## Parallel lane D — FOSSIL #84 build-context packet + engineering preflight

Implement the minimal autonomous-execution prerequisite before sophisticated methodology work:

- versioned `preflight-v1`/`closeout-v1` contract and validator where not already present;
- status-aware build-context packet v1;
- live GitHub state resolver/read step;
- universal kernel;
- selected risk facets;
- stale/superseded/current/unknown distinction;
- fail closed on material `current_state_unresolved`;
- task-scoped foundation retrieval, not giant context dumps.

### Foundation coverage

Universal kernel:

- outcome;
- behavior owner;
- state classification;
- public contract impact;
- semantic/mechanical success and failure;
- evidence/tests;
- recovery/rollback;
- unresolved assumptions.

Risk-triggered packs should cover relevant subsets of:

- API/service boundaries;
- networking/DNS/TLS/private-vs-public;
- durable writes/transactions/idempotency;
- databases/schema/migrations/isolation/backups/restore;
- async/background/queues/events/delivery/ordering/backpressure;
- timeouts/retries/late completion/reconciliation;
- dependency/provider compatibility;
- authentication/authorization/secrets/input trust;
- deployment/release/rollout/rollback;
- performance/capacity/rate limits;
- observability/correlation;
- AI/model/tool/context/semantic-success failure modes;
- cross-repo contracts.

Trivial edits must not trigger distributed-systems theater.

## Parallel lane E — FOSSIL #88 engineering assurance Actions

Implement small reusable, secretless mechanical jobs first:

- engineering preflight/closeout schema validation;
- dependency integrity / clean reproducible install / lightweight vulnerability audit where applicable;
- risk-triggered security checks informed by OWASP ASVS/NIST SSDF;
- semantic false-success fixture;
- cross-repo contract validation;
- least-privilege workflow permissions and safe third-party Action usage;
- compact correlated GitHub job summary/receipt.

OWASP/NIST are reference/requirement sources, not executable giant compliance checklists. No new security SaaS/policy platform is required.

## Parallel lane F — Cortex #11 disposable WorkOrder harness

Build the **deterministic/fixture execution substrate first**, without requiring live model secrets:

- versioned WorkOrder/stage/attempt contract;
- work-order/task/attempt/generation/checkpoint IDs;
- separate whole-task/turn/provider/tool/queue deadlines;
- isolated branch/patch destination per mutation attempt;
- idempotency key/fencing;
- flat bounded fan-out;
- mechanical fan-in/adjudication;
- runner/process death at every meaningful boundary;
- duplicate replay reconciliation;
- late-generation rejection;
- terminal PASS/FAILED/BLOCKED independent of model-authored text;
- Git commit + structured receipt checkpoint where sufficient;
- correlation spine through GitHub summaries.

Do not start a large real-model swarm yet. Real model fan-out comes after build-context packet v1 and trustworthy gateway semantic acceptance.

## Parallel lane G — FOSSIL #87 S3-compatible durability proof

No live R2 credential is needed for the first overnight work:

- freeze filesystem reference semantics;
- implement/verify S3-compatible storage port/adapter boundaries;
- local/service-container/fixture write-read-hash-enumerate tests;
- immutable/unique canonical key behavior;
- duplicate idempotent put;
- conflicting bytes loud failure;
- timeout/5xx/corruption/missing-object behavior;
- destroy all local projection/cache state;
- rebuild from canonical fixture evidence/events only;
- runner-death/restartable rebuild test;
- measure rebuild duration/request/byte metrics from fixtures.

Live R2/S3 proof waits for a narrowly scoped bucket credential. R2 vs S3 remains undecided until evidence.

## Parallel lane H — Study OS #55

Non-blocking, safe parallel work:

- task-first index/content structure;
- first reviewed evidence-derived lessons;
- include the LiteLLM `200 + empty body` incident;
- canonical vs projection/cache lesson;
- timeout/retry/idempotency lesson;
- debugging/fault-isolation lesson;
- retrieval question + review metadata + source-status links.

Generated lessons are drafts/proposals, not architecture authority.

## Observability requirement across all lanes

Carry where applicable:

```text
project_issue_id
work_order_id
task_id
attempt_id
generation
request_id
trace_id
checkpoint_id
commit_sha
deployment_id
```

Use GitHub summaries/receipts first. LiteLLM telemetry and direct Langfuse/OTEL may be added where safely available. Do not build the deferred Control Room/Supabase/dashboard just to start execution.

## Do not run yet

Blocked/deferred until prerequisites pass:

- full OpenCode vs Aider vs direct executor bakeoff;
- large model/task matrix;
- production gateway promotion without an agreed live-proof path;
- live R2 proof without scoped credentials;
- custom Control Room/dashboard database;
- Gravebuster/Tailscale/self-hosted runner as prerequisites;
- persistent OpenCode server as a prerequisite;
- Kubernetes/Kafka/Redis/Temporal-like orchestration infrastructure;
- final R2-vs-S3, executor, granularity, Spec-Kit/V4, LiteLLM-proxy-vs-SDK, or persistent-FOSSIL-query-service decisions.

## Gate to begin real overnight model fan-out

Require all of:

1. build-context packet v1 mechanically available and fail-closed on material stale/unresolved authority;
2. WorkOrder/attempt/checkpoint/recovery harness passes deterministic runner-death campaign;
3. LiteLLM semantic acceptance path is trustworthy for the routes used;
4. secret-using workflow runs from a trusted path that cannot be modified by arbitrary unreviewed PR code;
5. each writing attempt has isolated mutation scope and independent objective acceptance tests.

Then start small, flat, bounded parallelism (for example max 4), measure correctness/recovery/cost/latency/telemetry, and only later run the matched executor bakeoff.

## Morning closeout contract

Return one sanitized campaign summary with:

- exact repos/branches/SHAs/PRs;
- lanes attempted;
- tests/probes and exact pass/fail counts;
- `PASS` / `FAILED` / `BLOCKED` per lane;
- blocker category (`CODE`, `TOPOLOGY`, `CREDENTIAL`, `EXTERNAL`, `UNRESOLVED_AUTHORITY`, etc.);
- requested/actual model/provider only if actually used;
- token/cost facts only if measured;
- GitHub run/trace/receipt refs;
- security/secret-handling observations;
- decisions **not** made;
- next dependency order.

Do not claim a task is complete solely from model text, HTTP status, process exit, or a green unit test when the required operational/user-facing semantic surface has not been proven.
