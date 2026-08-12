# D024 — Outbound local Codex broker supersedes public-repo self-hosted dispatch

**State:** accepted / provisional execution-topology refinement  
**Date:** 2026-08-12  
**Refines:** D022  
**Authority/evidence:** issue #86; issue #96; issue #94 `INFRA-03` / `INFRA-04`; PR #98.

## Decision

Keep D022's trusted-local boundary but change the scheduling mechanism.

The owner's PC remains a replaceable trusted execution/credential bridge while some Railway/provider/telemetry/object-store access is local-only. However, the current implementation **does not attach a self-hosted GitHub Actions workflow from the public `fossil-core` repository to that PC**.

Instead, a local **outbound polling broker** reads the trusted #94 queue and independently decides whether a task is executable. A local model WorkOrder requires a trusted-author `TASK` with `state=READY`, an allowlisted repository, exact 40-character `starting_ref`, exact secretless access class and explicit `local_role=terra|luna`. The broker must claim and re-read the ledger before launching.

A PR, fork, arbitrary issue comment or repository workflow therefore cannot directly invoke the PC.

## Local Codex boundary

For an accepted secretless engineering WorkOrder:

1. create an isolated exact-SHA disposable worktree;
2. launch a fresh non-interactive ephemeral Codex process with a dedicated worker `HOME` / `CODEX_HOME`;
3. do not inherit GitHub, Railway, provider, API-key-like or interactive-home credentials into the Codex child;
4. run independent parent checks after the model process exits;
5. only the parent broker may commit/push/open a checked draft PR;
6. publish sanitized mechanical WorkOrder/terminal evidence to #94;
7. reject stale generations, duplicate/terminal attempts, cancellation and historical completed/BLOCKED tasks unless a new trusted READY directive explicitly reopens the task.

Terra and Luna are execution roles/model choices, not authorities or secret-access grants.

## Privileged verifier boundary

Credential-bearing Railway/provider/telemetry/object-store work remains a separate deterministic verifier lane. It may load only the minimum local credential environment after exact-reviewed-SHA authorization. A model/Codex process does **not** receive those infrastructure credentials.

Production promotion remains separately forbidden unless explicitly authorized.

## Why this refines D022

INFRA-03 proved the fail-closed WorkOrder/worktree/sanitizer foundation, but its first self-hosted Actions workflow would have made persistent credential-adjacent local infrastructure directly schedulable from a public-repository workflow surface. INFRA-04 review rejected that control-plane shape before merge.

Outbound polling gives the desired autonomous local execution without requiring runner enrollment, an inbound webhook/public port, or public-repo workflow scheduling of the PC.

## Supersedes

- the first PR #98 implementation idea of `.github/workflows/trusted-local-workorder.yml` targeting a `trusted-local` self-hosted runner;
- manual per-session Terra/Luna/Codex dispatch as the intended normal operating model once the local broker proof is green.

It does **not** supersede:

- D022's invariant that the local PC is replaceable execution/credential infrastructure rather than semantic truth;
- ordinary secretless GitHub-hosted PR CI;
- exact-reviewed-SHA privileged verification for local-only credentials.

## Remaining proof

Repository tests/hosted CI may establish deterministic broker policy, but final acceptance requires one physical-PC proof with the dedicated Codex worker profile:

- broker starts;
- one benign exact-SHA secretless task is claimed;
- real `codex exec` runs in the isolated worktree;
- independent checks pass;
- a draft PR and sanitized #94 closeout are produced;
- infrastructure credentials are absent from the Codex child;
- privileged verifier remains separate and production is untouched.

## Reconsider when

A managed executor or strongly restricted runner group demonstrates equal or stronger control-plane isolation, exact-SHA gating, credential separation and recovery with lower operational burden, or when no local-only privileged access remains.
