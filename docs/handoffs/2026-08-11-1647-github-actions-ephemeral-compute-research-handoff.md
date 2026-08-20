# Research continuation handoff — GitHub Actions as disposable compute

Timestamp: 2026-08-11 16:47 America/New_York
Status: OPEN RESEARCH / UNDECIDED
Branch: `research/human-agent-operating-model-20260811`
Related draft PR: #85

## Purpose

This handoff is for a fresh ChatGPT/Codex session to continue the **latest research direction only**. A separate ChatGPT Work session is already handling ingestion of the complete original conversation transcript into Fossil. Do **not** duplicate transcript-ingestion work here.

The immediate question is whether the current infrastructure can be simplified so that most AI/software-engineering compute is disposable GitHub-hosted work rather than requiring a permanently running local PC/VPS.

## Current hypothesis

Potential target:

```text
You / ChatGPT / GitHub Issue
          |
          v
     GitHub Actions
    ephemeral runner
          |
          +-- engineering preflight / contracts
          +-- agent/executor candidate
          +-- tests / probes / builds
          +-- Fossil ingestion / rebuild jobs
          +-- PR / evidence publication
          |
          v
     durable managed services
```

Possible managed durable plane:

```text
GitHub            code / issues / PRs / CI evidence
LiteLLM/CKFF      inference gateway + provider/model facts
R2/S3-compatible  Fossil canonical artifacts/events
Vercel            static/web UI
Langfuse Cloud    AI traces
(optional DB/API) only if interactive Fossil querying requires it
```

Desired property:

> **Compute may disappear; truth must not.**

Ask of every component:

> Does this component need to exist when no task is running?

If no, it is a candidate for GitHub-hosted ephemeral execution.
If yes, identify the smallest durable/always-on managed service that actually owns that requirement.

## What GitHub Actions may plausibly replace

Research candidate only; verify with current official docs and actual tests:

- local Codex/agent worker machines for bounded jobs;
- V4/controller processes that do not need permanent residency;
- scheduled CKFF/LiteLLM catalog probes;
- integration-test environments;
- temporary Postgres/other test services;
- Fossil validation, rebuild, migration, and ingestion jobs;
- build/test/review/repair workers;
- deployment jobs;
- synthetic observability probes;
- bounded multi-agent fan-out work.

It should **not** automatically be treated as the home for:

- canonical Fossil knowledge/state;
- a database whose contents must survive the job;
- a truly always-on inference/API service;
- permanent OpenCode sessions;
- real-time scheduler obligations requiring precise execution timing;
- indefinite daemons.

## Important architectural reframing

Do not ask:

> Can GitHub Actions run literally everything?

Ask:

> Can every compute process be disposable, with explicit durable state elsewhere?

This may remove the need for:

- Windows/local always-on PC;
- Fossil PC as mandatory durable host;
- Gravebuster PC as mandatory host;
- permanent self-hosted GitHub runner;
- Kubernetes/local cluster;
- generic VPS solely for workers.

Do not assume those components are removable yet. Treat this as a candidate topology requiring proof.

## Executor/V4 state remains UNDECIDED

Do not select an executor yet.

Current candidates/questions include:

- OpenCode persistent server/session model;
- Aider bounded/disposable process model;
- direct/simple model+tool executor;
- Spec Kit for generic specification/workflow mechanics;
- V4 for dynamic execution policy;
- monolithic vs granular/checkpointed tasks.

Known evidence from the earlier experiment:

- the tested OpenCode staging path failed end-to-end;
- the immediate observed fault was LiteLLM returning HTTP 200 with an empty body on generic chat/model routes;
- OpenCode converted that false-success into `finish=unknown`, zero-token/no-mutation completion;
- `/v1/responses` reached working LiteLLM/CKFF behavior;
- therefore the experiment does **not** prove OpenCode itself is unsuitable;
- granular task flow would not have fixed an upstream `200 + empty body`; it could still improve isolation/retry/checkpoint behavior for other failure classes.

Before choosing an executor, run a matched bakeoff after the LiteLLM gateway repair.

Suggested bakeoff:

```text
                SAME TASK CONTRACT
                       |
          +------------+------------+
          |            |            |
          v            v            v
      OpenCode       Aider      direct/simple
          |            |            |
          +------------+------------+
                       |
                same LiteLLM route
                same model when possible
                       |
                       v
                objective checker
```

Test at least:

1. tiny deterministic file edit;
2. multi-file task;
3. mandatory mutation/tool evidence;
4. longer bounded task;
5. forced timeout;
6. empty/malformed 2xx;
7. executor/process restart;
8. cross-family architect/editor or planner/coder/reviewer;
9. parallel independent tasks;
10. abort/cancel;
11. monolithic vs granular/checkpointed version of the same medium task.

Measure correctness, mutation evidence, recovery, latency, token/cost usage, context loss, observability, and operational complexity.

## Candidate V4 boundary

Do not treat this as decided.

Leading hypothesis:

```text
V4 = vendor-independent dynamic AI execution/control policy
```

Possible responsibilities:

- classify execution requirements;
- consume current LiteLLM factual model catalog;
- select model/family/route;
- cross-family seating;
- decide parallelism/decomposition;
- budget/context policy;
- retry/fallback/recovery ownership;
- checkpoint/attempt semantics;
- required execution evidence;
- telemetry/correlation semantics;
- drive an `ExecutorPort` whose implementation remains replaceable.

Generic software-development methodology should be evaluated against existing systems such as GitHub Spec Kit rather than automatically rebuilt in V4.

LiteLLM should remain factual transport/catalog infrastructure, not hidden application model-policy owner.

Fossil should remain durable semantic/research truth, not runtime model-policy owner.

## GitHub Actions and task granularity

This is an important research direction.

A disposable-runner architecture may favor workflows such as:

```text
work order
   |
   v
job 1: inspect / preflight
   |
   v
commit + receipt
   |
   v
job 2: bounded implementation
   |
   v
commit + tests
   |
   v
job 3: independent review
   |
   v
job 4: repair / closeout
```

Git commit + structured task receipt + test evidence may be sufficient durable checkpoints for many coding tasks, avoiding a requirement that one agent process/session stay alive for hours or days.

But granularity adds calls, latency, context handoffs and coordination. Do not assume finer is always better; test it.

## Fossil implications

A major candidate simplification is:

```text
canonical Fossil artifacts/events -> durable object store
                          |
                          +-> temporary projections/rebuilds on Actions
                          +-> optional always-on query service only if needed
```

This is compatible with the existing principle that projections are replaceable and durable canonical evidence/events are authoritative.

Research whether an interactive always-on Fossil query/API is actually required for the user's normal workflow, or whether many operations can be on-demand jobs plus a small managed query service.

Do not redesign Fossil around GitHub Actions until durability/recovery semantics and latency requirements are proven.

## Human learning context

The user is also building a separate personal Study OS. Recent learning focus is understanding where technologies sit by responsibility/layer rather than memorizing names.

Useful classification lens:

- storage;
- compute;
- communication;
- application logic;
- orchestration;
- observability;
- deployment/control.

Recent examples discussed:

- GitHub Actions -> automation/control plane;
- Data Lake -> storage;
- Spark -> distributed compute;
- Databricks -> data/AI platform;
- ETL -> data-processing pattern;
- RAG -> retrieval/generation architecture pattern;
- AI Search -> retrieval;
- model API -> inference;
- LangChain/CrewAI -> AI application/orchestration frameworks.

The Study OS itself is separate from Fossil: Fossil may retain sourced engineering knowledge/lineage; Study OS is the human educational representation.

## Existing larger research context

Read, but do not blindly promote:

- `docs/research/2026-08-11-human-agent-engineering-operating-model.md`
- `docs/handoffs/2026-08-11-human-agent-engineering-operating-model-handoff.md`
- the agent methodology/executor research trace from the same date;
- Fossil #84 engineering preflight research;
- draft PR #85;
- Fossil #79 / PR #80 control-plane work;
- Fossil #81/#82 architecture hardening/package-boundary work;
- experimental Cortex V4 / LiteLLM / Fossil executor PRs.

A separate ChatGPT Work session is ingesting the original shared transcript into Fossil. Prefer that exact transcript artifact as evidence once available; this file is a continuation handoff, not the primary transcript.

## Research questions for the next session

Research first; do not immediately implement.

1. **How far can GitHub-hosted Actions safely replace persistent worker infrastructure?**
   - current time/runtime/concurrency/storage/network limits;
   - workflow chaining/checkpoint patterns;
   - private networking and managed-service connectivity;
   - cost/quotas for the user's likely workload.

2. **What truly needs to remain always on?**
   - LiteLLM gateway;
   - Fossil interactive API/query service;
   - observability ingestion;
   - any session runtime.

3. **Can GitHub-native durable primitives cover orchestration state without becoming the knowledge database?**
   - commits/branches/PRs/issues/artifacts/caches/environments;
   - where each is appropriate and where it is unsafe.

4. **Executor bakeoff design:** OpenCode vs Aider vs direct/simple executor.

5. **Does Spec Kit remove generic methodology/workflow responsibilities from V4 while preserving V4's unique cross-vendor dynamic execution policy?**

6. **Can a work-order architecture survive runner death at every boundary?**
   - define checkpoints, idempotency and late/duplicate execution semantics.

7. **What is the minimal managed-services topology with no personally maintained VPS/PC?**

8. **What would force us back to an always-on worker/server?**
   - low latency;
   - long interactive state;
   - high frequency;
   - exact scheduling;
   - heavy compute;
   - private data/network requirements.

## Scope control

Do not turn this research into:

- Kubernetes;
- Kafka;
- Redis;
- a custom Temporal clone;
- a new dashboard platform;
- a new agent framework;
- automatic multiwriter Fossil;
- an assumption that GitHub Actions is a database;
- an assumption that all workloads belong in Actions.

Any new persistent component must be justified by a concrete requirement or measured failure.

## Desired next-session output

Produce a source-backed comparison and candidate architecture, not an implementation PR yet.

At minimum return:

- current official GitHub Actions capabilities/limits relevant to this architecture;
- durable-vs-ephemeral component table;
- managed-services-only candidate topology;
- executor bakeoff protocol;
- V4 responsibility candidate vs responsibilities better delegated to existing tools;
- risks/failure modes;
- what can be deleted from the current infrastructure if the hypothesis proves true;
- explicit `KNOWN`, `CANDIDATE`, and `UNDECIDED` labels.

The central question is:

> **Can we make compute disposable and preserve only explicit durable truth, so the user no longer needs to maintain a VPS/local machine for ordinary AI/software-engineering work?**
