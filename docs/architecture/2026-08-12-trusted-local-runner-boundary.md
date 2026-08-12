# Trusted Local Runner Boundary — Autonomous WorkOrders Without Secret Leakage

**Date:** 2026-08-12  
**Status:** current architecture / implementation contract  
**Authority:** refines Fossil issue #86; implementation tracked by issue #96 and queue task `INFRA-03` in issue #94

## Decision

The owner should no longer manually launch and dispatch ordinary local Codex sessions as the normal operating model.

Instead, the local PC may run a narrowly trusted self-hosted GitHub Actions worker that receives versioned WorkOrders from trusted/default-branch-controlled GitHub coordination and launches fresh isolated local agent processes.

This does **not** make the PC canonical truth and does **not** make a self-hosted runner a prerequisite for ordinary pull-request CI. The local node exists because some trusted credentials currently remain local-only.

The governing split is:

- ordinary PR/build/test work: secretless, disposable, GitHub-hosted where practical;
- local engineering WorkOrders: trusted local runner, secrets unloaded by default;
- credential-bearing verification: separate privileged local verifier, exact reviewed SHA only;
- durable semantic/evidence authority: FOSSIL;
- execution/recovery policy: Cortex V4;
- provider/model/route factual transport: LiteLLM/CKFF;
- coordination/review: GitHub Issues/PRs.

The central invariant remains:

> **Compute may disappear; truth must not.**

A trusted local runner is a replaceable execution/credential bridge, not a truth store.

## Why this revises the previous plan

Issue #86 correctly rejected the assumption that a permanent self-hosted runner was required for ordinary compute before the disposable-compute hypothesis had been tested.

Subsequent execution established a narrower requirement: the owner currently keeps Railway/provider/telemetry and related trusted credentials only on the local PC. Ordinary GitHub PR workflows intentionally remain secretless. Therefore a trusted local execution path is justified for narrowly privileged work even while normal engineering compute remains disposable.

This revision supersedes:

- manual per-session Terra/Luna/Codex dispatch as the normal local operating model;
- the sequencing assumption that **all** self-hosted-runner work belongs only after every disposable-compute proof.

It does not supersede:

- secretless ordinary PR CI;
- exact-SHA review before credential-bearing verification;
- disposable WorkOrder recovery/fencing requirements;
- the rule that production promotion requires separate explicit authorization.

## Security invariant

> **A pull request must never be able to cause its own mutable code or workflow definition to execute on the credential-bearing local runner.**

Consequences:

1. Ordinary `pull_request` workflows MUST NOT target the trusted-local runner label.
2. Do not use `pull_request_target` to execute PR-controlled code with local, repository, provider, Railway, telemetry, object-store, or production credentials.
3. Trusted-local dispatch MUST originate from workflow/dispatcher code already present on a reviewed/default branch or another explicitly trusted immutable revision.
4. The target repository revision MUST be an immutable reviewed SHA when a task may load credentials.
5. Local `.env` values MUST NOT be copied into GitHub, FOSSIL receipts, chat output, workflow artifacts, or PR logs.
6. A role name such as `terra` or `luna` does not grant secret access. Access is an explicit WorkOrder property.

## Two local trust lanes

### Lane A — secretless local engineering worker

Purpose:

- code changes;
- deterministic regression work;
- tests, lint, compile, mutation checks and fault injection;
- repository-local evidence collection;
- branch/commit/PR production.

Rules:

- local credential environment is not loaded;
- each attempt gets a fresh isolated worktree/process;
- WorkOrder mutation scope is explicit;
- results are mechanically classified and sanitized before posting;
- a failed or killed process is disposable and recoverable from Git + structured receipts.

### Lane B — privileged verifier

Purpose:

- exact-SHA Railway staging deployment;
- bounded live LiteLLM semantic probes;
- protected account/telemetry reads;
- future narrowly scoped object-store proofs;
- other tasks whose access class explicitly requires local trusted credentials.

Rules:

- exact reviewed SHA required;
- trusted/default-branch dispatcher required;
- local credential environment loaded only inside this lane;
- mutation scope is narrow and declared;
- production promotion is never implied by successful verification;
- secret values are never printed, copied, returned, or stored in receipts.

## WorkOrder contract

A trusted-local WorkOrder must carry enough identity and policy to be recovered and audited without conversational state.

Required fields:

```text
project_issue_id
work_order_id
task_id
attempt_id
generation
repo
starting_ref
role
access_class
mutation_scope
selected_checks
deadline
closeout_contract
```

The common correlation spine remains:

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

Not every field is populated for every secretless engineering attempt, but IDs must not be silently reused for a different generation or target revision.

## Dispatcher contract

Before launching an agent, the local dispatcher must:

1. read the current #94 coordination ledger;
2. verify that the WorkOrder's task has a valid winning claim or is explicitly assigned by a trusted dispatcher policy;
3. validate schema and required identity fields;
4. verify repository and task allowlists;
5. verify immutable `starting_ref`;
6. reject stale generations, duplicate terminal attempts, cancelled work and malformed inputs;
7. verify requested access class against the chosen local lane;
8. create an isolated worktree/process;
9. set a bounded deadline and cancellation path;
10. provide only the minimum task context needed by the agent.

After execution it must:

1. run the objective selected checks independently of model prose;
2. record commit/checkpoint identity where applicable;
3. reject late results from superseded generations;
4. sanitize stdout/stderr/receipts;
5. emit a mechanical terminal `PASS`, `FAILED`, or `BLOCKED` disposition;
6. post the compact result back to #94 / the owning issue or PR;
7. destroy the disposable worktree/process after terminal closeout unless retained for an explicitly recorded investigation.

## Agent role policy

### Terra

Default use:

- complex/root-cause engineering;
- architecture-sensitive implementation;
- difficult multi-file changes;
- explicitly authorized trusted local/infra verification.

### Luna

Default use:

- cheaper/mechanical regression cases;
- reproductions;
- lint/compile/test loops;
- evidence collection;
- bounded implementation where the objective contract is already clear.

Neither role is an authority source. Neither role may widen task scope, promote production, or acquire secrets merely because it runs locally.

## GitHub Actions boundary

The self-hosted runner should have dedicated labels, for example:

```text
self-hosted
trusted-local
windows   # or the actual host OS label
```

A trusted dispatch workflow may target those labels only from a trusted/default-branch-controlled definition.

Ordinary PR workflows should continue to use GitHub-hosted runners and `contents: read` unless a separate task explicitly justifies more.

No inbound public port or webhook on the PC is required. The GitHub Actions runner maintains the runner-side connection to GitHub.

## Registration and local secret handling

Runner enrollment is a `LOCAL_INFRA` step and is deliberately not performed by ordinary PR code.

The implementation runbook must:

- register a dedicated self-hosted runner identity for this project/trust class;
- use labels that cannot be confused with ordinary runners;
- install it under a dedicated local account/service boundary where practical;
- keep registration tokens and local `.env` values out of Git history;
- ensure the worker lane starts with credentials absent from its process environment;
- provide a separate wrapper for the privileged verifier that loads only the required credential set;
- document disable/unregister/revoke procedures.

The durable repo should store the procedure, never the credential values.

## Required verification

### Deterministic contract tests

- malformed WorkOrder rejected;
- unauthorized repo/task rejected;
- access-class mismatch rejected;
- duplicate attempt rejected or returned idempotently;
- stale generation rejected;
- cancelled task does not start;
- late completion from an older generation cannot win;
- secretless lane environment does not expose protected variables;
- sanitizer rejects/strips credential-like output before receipt publication;
- terminal state is mechanical rather than inferred from agent text.

### Fault injection

- kill agent process before commit;
- kill after commit but before receipt;
- kill runner/dispatcher between checkpoint and closeout;
- retry same attempt;
- retry with newer generation;
- timeout/cancel during execution;
- GitHub/API read failure during claim verification;
- privileged verifier failure before and after remote effect observation.

Recovery must preserve the project invariant:

> **Compute may disappear; truth must not.**

## Integration with Cortex V4

The local runner is an execution substrate, not a replacement for Cortex.

Cortex owns:

- WorkOrder lifecycle;
- retry/fencing policy;
- generation handling;
- flat bounded fan-out/fan-in;
- deadlines;
- evidence requirements;
- mechanical closeout expectations.

The trusted local dispatcher should consume the same versioned WorkOrder/recovery semantics as disposable GitHub Actions workers wherever practical.

This keeps the local PC replaceable: moving credentials later to a protected managed runner should not require redefining the WorkOrder contract.

## Integration with SSC retirement

Legacy `stupidly-simple-cortex` is not part of this runner design.

The trusted local runner MUST NOT treat SSC runtime, corpus retrieval, ontology/current-state values, generated summaries, model consensus, or historical project state as authority. Cortex V4 must remain independently operable with SSC absent.

Any historically useful SSC eval/checker asset may be used only after separate extraction, hashing, provenance/license review and independent revalidation under the standalone eval-estate policy.

## Implementation sequence

1. Land this architecture decision and issue #96 contract.
2. Add a versioned WorkOrder schema/validator for trusted-local dispatch.
3. Add deterministic dispatcher tests and fault fixtures.
4. Add a trusted/default-branch dispatch workflow that cannot be triggered by arbitrary PR workflow code.
5. Add the local registration/runbook and secretless worker wrapper.
6. Register the runner locally and prove a no-secret mechanical WorkOrder end to end.
7. Add the separate privileged verifier wrapper.
8. Prove exact-reviewed-SHA isolated staging verification without secret disclosure.
9. Connect Terra/Luna role selection to the queue policy.
10. Use the path for CAMPAIGN-01 credential-bearing steps while ordinary compute remains disposable.

## Reconsideration / removal condition

The local trusted runner is replaceable infrastructure.

Reconsider or remove it when:

- local-only credentials migrate to a protected managed secret runner;
- no trusted local hardware/service access remains;
- a managed runner can provide equal or stronger isolation, secret protection, exact-SHA gating and recovery evidence;
- operational burden outweighs the measured value.

No migration of the runner may change FOSSIL semantic authority or Cortex WorkOrder identity/recovery semantics.
