# Human + agent engineering operating model research — 2026-08-11

**Status:** OPEN RESEARCH / OPERATING-MODEL SYNTHESIS  
**Authority:** research evidence only unless a section explicitly points to an already-accepted architecture contract.  
**Do not treat this document as a replacement for `ARCHITECTURE.md`, `docs/DECISION_LOG.md`, or merged ownership contracts.**

## Purpose

Preserve the broader research and reasoning from the 2026-08-11 sessions about how the owner should study, orchestrate AI-assisted software work, debug distributed systems, enforce engineering foundations before builds, organize observability, track cross-repo work, and keep AI-agent execution mechanically bounded.

This note exists because these findings affect future working style, not only one implementation task. It intentionally separates:

- human learning and orchestration support;
- agent preflight methodology;
- project-management/control-plane ownership;
- runtime/inference ownership;
- observability/debugging patterns;
- scope-control rules;
- accepted current boundaries;
- unresolved executor questions.

## Core problem observed

The recurring failure pattern is:

1. start from an idea;
2. use AI coding agents to iterate quickly;
3. implementation velocity outpaces architecture/reliability review;
4. ownership, contracts, state semantics, recovery, observability, and dependency boundaries are discovered late;
5. stale summaries or historical architecture are later treated as current truth;
6. debugging becomes cross-service and expensive;
7. major retrofits or discarded projects result.

The target operating model should preserve fast experimentation while making foundational engineering questions repeatable, visible, and mechanically enforceable where appropriate.

---

# 1. Human Study OS / engineering compass

## Goal

Create a personal, portable, visual study system that answers:

> What am I forgetting before I build, debug, deploy, scale, connect, or redesign this?

This is **not FOSSIL itself**. FOSSIL is durable knowledge/evidence infrastructure. The personal Study OS is a human-facing educational layer, expected to live in `Pukujan/private-study-log` or a dedicated derived site.

## Preferred interaction model

Start from a task, not from a textbook taxonomy:

- build a new system;
- add a feature;
- debug a failure;
- add a database;
- connect two services;
- design an API;
- deploy something;
- scale a service;
- add AI/agents;
- store durable data;
- add observability.

Each task should surface a small relevant checklist and link each question to a 2–5 minute lesson.

## Bite-size lesson template

Each lesson should consistently provide:

1. why the concept matters;
2. a visual mental model;
3. a worked example;
4. a concrete failure example;
5. questions to ask before building;
6. red flags / stop conditions;
7. a debugging/isolation pattern;
8. related concepts and breadcrumbs;
9. a retrieval question so the learner must answer from memory;
10. later spaced review.

## Curriculum map considered useful

- operating systems;
- networking;
- databases;
- software architecture;
- distributed systems;
- testing and SRE;
- observability;
- security;
- release engineering;
- performance/capacity;
- AI-assisted engineering.

## Learning-science basis considered

The study design should favor worked examples for complex schema acquisition plus retrieval practice and spacing rather than passive rereading.

Primary/research references considered in this session family:

- retrieval practice / spacing review: https://www.nature.com/articles/s44159-022-00089-1
- worked examples / instructional research discussed through academic literature references during the session.

## Site implementation candidate

Docusaurus is a candidate because it provides React-based custom pages, Markdown/MDX lessons, generated navigation, and Mermaid diagrams while building deployable static pages. This remains a product implementation choice, not an architecture invariant.

---

# 2. Universal human pre-build checklist

Before substantial work, the human or agent should be able to answer:

1. What exact outcome are we building?
2. Who owns each behavior?
3. What state is canonical/durable, projected, cached, working, telemetry, or project state?
4. What public contract changes?
5. Which dependencies are replaceable adapters?
6. What mechanically counts as success?
7. How can this partially fail?
8. Who owns retries and each timeout?
9. Is each retried mutation idempotent?
10. How is the path observable and correlated?
11. How do rollback, recovery, and rebuild work?
12. What evidence is required before merge/promotion?

For trivial tasks, only the relevant minimal subset should apply.

## False-success firewall

Do not accept these as success without semantic validation:

- HTTP 2xx + empty body when usable content is required;
- malformed expected JSON;
- completed stream with zero usable payload;
- agent completion with zero usable content/tool action;
- success without required durable state mutation;
- hidden fallback/substitution that is not represented in evidence.

The LiteLLM/OpenCode staging incident is a concrete motivating case for this rule.

---

# 3. Agent engineering preflight

## Principle

Do not rely on the human or agent remembering every engineering question. Encode a small universal constitution plus **risk-triggered** domain checks and require a structured preflight receipt before gated implementation.

Git/source control should contain the minimum offline-capable constitution/schema/validator. FOSSIL may provide deeper current standards, incident evidence, ADRs, and project-specific context.

## Universal kernel

Every substantial task should cover:

- requested outcome;
- behavior owner;
- touched state classification;
- contract impact;
- mechanical success/failure semantics;
- tests/evidence;
- recovery/rollback impact;
- unresolved assumptions.

## Risk-triggered packs

Candidate facets:

- new service;
- cross-service call;
- durable write;
- database/schema change;
- async/background work;
- queue/event stream;
- external dependency;
- auth/security-sensitive change;
- AI/model call;
- deployment/infrastructure;
- migration/backfill;
- performance/capacity;
- observability change;
- cross-repo contract change.

A CSS/copy edit must not trigger distributed-systems theater. A durable cross-service write should trigger idempotency, partial-failure, timeout/retry, durability, reconciliation, compatibility, recovery, security, and correlation checks.

## Mandatory bounded control stages considered

```text
preflight
  -> validation
  -> one bounded adversarial critique
  -> adjudication if needed
  -> scope gate
  -> implementation
  -> closeout validation
```

Newly discovered work should be classified as:

- `required-now`;
- `bounded-experiment`;
- `follow-up`;
- `reject`.

Only the first two may expand current scope.

## Anti-horizontal-expansion invariant

A concern does not automatically justify new infrastructure. A new service, queue, cache, database, framework, policy engine, dashboard, or agent layer requires a triggered requirement, observed/measured failure, or explicit acceptance criterion.

## Industry/official patterns used as research basis

### OpenAI Codex harness engineering

Source: https://openai.com/index/harness-engineering/

Relevant pattern: large monolithic agent instructions become stale/context-heavy; prefer a small map into structured repository knowledge, progressive disclosure, and mechanical checks.

### GitHub Spec Kit

Sources:

- https://github.com/github/spec-kit
- https://github.com/github/spec-kit/blob/main/docs/reference/workflows.md

Relevant pattern: constitution -> specification -> clarification -> plan -> checklist/analysis -> tasks -> implementation, with extensibility and multiple agent integrations.

### Google SRE / Production Readiness Review

Sources:

- https://sre.google/sre-book/evolving-sre-engagement-model/
- https://sre.google/sre-book/launch-checklist/
- https://sre.google/resources/practices-and-processes/production-launch-planning/

Relevant pattern: operational-readiness checks should be service-specific, based on dependencies and production experience, and surfaced earlier rather than only after implementation.

### NIST SSDF / OWASP ASVS

Sources:

- https://csrc.nist.gov/pubs/sp/800/218/final
- https://owasp.org/www-project-application-security-verification-standard/

Relevant pattern: secure-development requirements should be integrated into the normal development lifecycle rather than bolted on later.

### AWS/Azure Well-Architected frameworks

Sources:

- https://docs.aws.amazon.com/wellarchitected/latest/userguide/waf.html
- https://learn.microsoft.com/en-us/azure/well-architected/

Relevant pattern: architecture review should cover operational, reliability, security, performance, cost, and related quality dimensions while making requirement-driven tradeoffs rather than maximizing every dimension unconditionally.

### Backstage golden paths/catalog

Sources:

- https://backstage.io/docs/features/software-templates/
- https://backstage.io/docs/features/software-catalog/
- https://backstage.io/docs/overview/technical-overview/

Relevant pattern: encode reusable project/component starting paths and ownership metadata; a portal can aggregate and deep-link to existing systems instead of reimplementing all of them.

### JSON Schema / policy separation

Sources:

- https://json-schema.org/understanding-json-schema/reference/conditionals
- https://www.openpolicyagent.org/docs/integration

Relevant pattern: structured receipts can start with JSON Schema and small validators; policy definition and enforcement can remain separate. OPA is not required for v1.

---

# 4. Debugging operating pattern

Distributed debugging should prioritize **fault isolation**, not exhaustive log reading.

Recommended sequence:

1. freeze the exact symptom/input/environment/version;
2. reduce to the smallest reproducing path;
3. call the downstream dependency directly as a control;
4. bypass one layer at a time;
5. compare A/B/C paths;
6. validate semantic success, not transport/process status alone;
7. identify the exact timeout/retry/cancel/fallback owner;
8. inject one controlled failure;
9. encode the bug class as a regression test/probe.

The 2026-08-11 LiteLLM/OpenCode investigation is a concrete example: direct Responses succeeded while generic Chat/Models returned HTTP 200 with empty bodies, isolating the staging gateway path rather than proving a model/provider or OpenCode lifetime failure.

---

# 5. Observability and one-place navigation

## Do not build a giant custom observability/product-management application first

Separate authority by question:

- GitHub Issues/Projects: what human work exists, owner, status, blockers, dependencies;
- V4 or execution engine: what machine work is executing, attempts, checkpoints, terminal state;
- Grafana/metrics: service health, rate, errors, latency, resources, queue/projection lag;
- Langfuse/tracing: deep LLM/agent request traces;
- logs: exact events/errors;
- FOSSIL: durable semantic knowledge/evidence, not operational telemetry truth.

A future Control Room should preferably be a thin portal/deep-link layer over these systems, not another source of truth.

## Correlation spine

Carry shared IDs where applicable:

```text
project_issue_id
work_order_id
task_id
session_id
attempt_id
request_id
trace_id
checkpoint_id
commit_sha
deployment_id
```

The goal is correlation, not one giant database.

## Preferred telemetry flow

```text
applications
    |
   OTEL
    |
    +--> metrics --> Prometheus-compatible backend --> Grafana
    +--> traces  --> Langfuse / trace backend
    +--> logs    --> log backend
```

Prometheus/Grafana remain observability tools, not project trackers.

---

# 6. Project tracking vs machine orchestration

## Human/project layer

GitHub Issues/Projects should remain the durable cross-repo engineering tracker for now.

Examples of tracked relationships:

- master tracker: `fossil-core#73`;
- observability/control-room lane: `#74`;
- Tailscale/GitHub control plane: `#79` / PR `#80`;
- architecture hardening: `#81`;
- `dkg` -> `fossil_core`: `#82`;
- engineering preflight: `#84`.

Jira is not currently required merely to duplicate this state.

## Runtime execution layer

A task/work-order execution engine is conceptually different from project management:

```text
GitHub issue/project
    = what humans intend to build

execution WorkOrder/session
    = bounded machine computation to perform
```

Do not turn V4 into Jira or GitHub Issues into runtime execution state.

---

# 7. Current distributed ownership map

The following is based on accepted/current project boundaries unless superseded by canonical architecture docs:

- CKFF: cheap/free provider/model availability source;
- LiteLLM/CKFF ops: inference transport/gateway and factual route/model capability inventory; does not own application model selection policy;
- Cortex V4: candidate owner of dynamic execution policy such as model selection/seating, cross-family rules, retries/fallback/recovery, budget/context policy, and execution receipts; final generic workflow/executor boundary remains under research;
- OpenCode: execution substrate candidate; suitability remains unproven after the false-success gateway incident;
- Aider: alternative executor candidate requiring matched testing;
- FOSSIL: durable semantic knowledge/evidence/lineage and engineering-research provenance;
- GitHub Actions: reproducible CI/sync/deployment/contract/evidence control plane;
- Gravebuster: observability/projection host boundary where needed;
- Langfuse/OTEL/Grafana: observation surfaces;
- SSC: historical/retired source material, not current V4 runtime authority unless explicitly re-approved.

---

# 8. V4 methodology and executor status

## Methodology

The current leading hypothesis is to **reuse established spec/planning methodology where possible** and keep V4 focused on genuinely unique mechanical control such as dynamic model-family selection, seating, budgets, retries/fallback/recovery, long-running execution semantics, and evidence.

However this is **not yet a final V4 boundary decision**.

## Executor

**UNDECIDED.** Candidates include:

- OpenCode persistent server/session model;
- Aider bounded task process / architect-editor mode;
- direct model/tool execution;
- Spec Kit workflow integration;
- another adapter satisfying the same executor contract.

Required matched bakeoff should test tiny edits, multi-file work, mandatory mutation, long tasks, timeout, malformed/empty false-success, restart/resume, cross-family roles, parallel independent tasks, abort/cancel, and monolithic vs granular task decomposition.

Do not summarize current evidence as “OpenCode is bad.” The observed path failed, but the immediate root cause isolated in staging was the LiteLLM generic gateway's empty-body 2xx behavior.

---

# 9. Dependency/release maintenance pattern

For Python repositories, the candidate standard discussed is:

- `pyproject.toml` for declared dependencies;
- `uv.lock` for reproducible exact resolution;
- `uv` for sync/locking/upgrades;
- Dependabot for version/security update PRs;
- `pip-audit` / dependency review for known vulnerabilities;
- CI for lint/type/unit/architecture/contract/integration checks;
- staging + smoke/contract probes before promotion;
- immutable/reproducible releases and rollback rather than mutating live environments.

External service compatibility must be checked with scheduled contract probes because lockfiles cannot detect behavioral regressions in LiteLLM, OpenCode, CKFF, Langfuse, Tailscale, etc.

---

# 10. State classification rule

Before storage or architecture decisions, classify state:

- canonical/durable;
- projection;
- cache;
- working/session state;
- telemetry;
- project-management state.

Do not let cache/projection/telemetry/project state silently become durable semantic authority.

---

# 11. Human + agent shared operating loop

```text
idea / intent
   |
   v
spec / issue
   |
   v
foundation preflight
   |
   +--> universal engineering kernel
   +--> risk-triggered checks
   +--> current FOSSIL evidence/ADRs/incidents when available
   |
   v
bounded validation / critique / scope gate
   |
   v
implementation executor (UNDECIDED)
   |
   v
CI / staging / live evidence
   |
   v
closeout receipt
   |
   +--> GitHub project evidence
   +--> FOSSIL candidate lesson / research trace
   +--> Study OS derived human lesson when useful
```

The human Study OS and FOSSIL should be connected conceptually but remain separate authority surfaces. The Study OS may derive educational pages from reviewed concepts; product CI must not depend on the personal learning UI.

---

# 12. What is accepted, provisional, and open

## Already accepted elsewhere; this note only references them

- FOSSIL durable truth/provenance/lifecycle boundaries;
- compression is a temporary execution view, not canonical truth;
- SSC retired as new V4 runtime authority;
- LiteLLM factual gateway role separated from V4 application routing policy;
- GitHub-hosted Actions + Tailscale as preferred narrow control-plane direction;
- no default Kubernetes/cluster/self-hosted-runner requirement.

Canonical merged docs/PRs remain authority for these.

## Strong research-backed operating principles, not yet universal contracts

- use task/risk-triggered engineering review rather than giant checklists;
- use a small agent map + progressive disclosure + mechanical checks;
- favor golden paths/templates for repeated project foundations;
- separate project tracking, execution state, telemetry, and durable knowledge;
- use semantic-success validation and explicit false-success tests;
- prefer deep-link correlation over rebuilding every tool in one dashboard;
- preserve research/incident lineage so later agents can distinguish historical, proposed, current, stale, and superseded material.

## Open / unresolved

- final V4 methodology boundary;
- final executor choice;
- whether OpenCode persistent sessions outperform bounded disposable execution;
- whether Aider's architect/editor split is useful enough for this stack;
- ideal task granularity;
- exact Spec Kit integration depth;
- exact human Study OS framework/site implementation;
- final observability backend composition;
- when/if richer policy engines are justified.

---

# 13. Retrieval guidance for future sessions

A future session asking “how should we work?” should read this note as a **research map**, then follow canonical sources for any accepted architecture claim.

A future session asking “what should the agent ask before building?” should also inspect `fossil-core#84` and its comments.

A future session asking “which executor should V4 use?” should read:

- `docs/research/2026-08-11-agent-engineering-methodology-and-executor-options.md`;
- `docs/handoffs/2026-08-11-agent-methodology-executor-research-handoff.md`;
- the matched bakeoff evidence once it exists.

A future session asking “what should the owner study?” should use the Study OS design section here as the bridge to the human learning repository, not as a replacement for curated lessons.

## Final research rule

Do not promote this entire synthesis into one monolithic “truth” object. Preserve claim-level status, provenance, and supersession. When individual findings become accepted policy or architecture, link them to the specific decision/contract that accepted them.