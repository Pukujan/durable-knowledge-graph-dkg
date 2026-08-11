# Agent engineering methodology and executor-options research trace — 2026-08-11

**Status:** OPEN RESEARCH / UNDECIDED  
**Authority:** research evidence only; **not** an architecture decision, runtime contract, or approval to replace V4/OpenCode/Spec Kit.  
**Related:** `#73`, `#84`, `cortex-v4#10`, `litellm-ckff-ops#7`, `fossil-core#78`.

## Research question

How should future AI-assisted projects automatically surface missing software-engineering foundations before implementation, while keeping scope proportional to the task; and what, if anything, should Cortex V4 own after accounting for existing agent-development tooling and executor candidates?

A linked unresolved execution question is:

> What coding-agent execution substrate should V4 use, if any: OpenCode persistent server, Aider, direct model/tool execution, Spec Kit workflow execution, or another adapter?

No executor is selected by this note.

## Why this research was opened

The owner repeatedly observed a pattern:

1. start from a product idea;
2. use AI coding agents to iterate quickly;
3. local feature implementation advances faster than foundational engineering review;
4. ownership/state/contracts/recovery/observability/dependency boundaries are discovered late;
5. stale or misleading architectural material can contaminate later agents;
6. major retrofits or discarded projects result.

The desired outcome is not a universal giant checklist. It is a repeatable method that asks the *relevant* questions early and fails loudly on high-risk unknowns.

## Evidence classes

This note intentionally separates:

- **external primary/official sources** — behavior or methodology documented by the project/vendor;
- **repository-local evidence** — what the current/legacy Cortex/FOSSIL code and experiments actually did;
- **inference** — design implications drawn from those facts;
- **open questions** — claims not yet justified by a comparative execution bakeoff.

## External primary/official sources inspected

### GitHub Spec Kit

- Repository/docs: https://github.com/github/spec-kit
- Workflow reference: https://github.com/github/spec-kit/blob/main/docs/reference/workflows.md
- Current docs describe a spec-driven sequence with project constitutions, specification, planning, tasks, analysis/checklists, implementation, extensions/presets, and multi-agent integrations.
- Current workflow support includes commands, prompts, shell steps, human gates, conditional branches, loops, fan-out/fan-in, persisted workflow state, and pause/resume.
- The workflow runner stores `state.json`, `inputs.json`, and `log.jsonl` under the project for resumable workflow-stage execution.
- Security note from the official workflow docs: shell steps run with local privileges; workflow `requires` is advisory, not a runtime sandbox.

### OpenAI harness engineering / Codex

- Harness engineering: https://openai.com/index/harness-engineering/
- OpenAI reports that a large monolithic `AGENTS.md` became counterproductive because it consumed context, made guidance equally salient, became stale, and was difficult to verify. The reported pattern shifted toward a small navigation/map layer, structured repository knowledge, progressive disclosure, and mechanical checks.
- This supports using agent instructions as a discovery hook rather than the sole enforcement mechanism.

### Google SRE / production readiness

- Production-readiness / evolving SRE engagement: https://sre.google/sre-book/evolving-sre-engagement-model/
- The production-readiness pattern evaluates operational concerns based on the service and its dependencies rather than applying every possible question indiscriminately.
- The design implication considered here is risk-triggered engineering review and earlier engagement, not a one-size-fits-all checklist.

### OpenCode

- Server: https://dev.opencode.ai/docs/server/
- Providers: https://dev.opencode.ai/docs/providers
- OpenCode exposes a headless HTTP server (`opencode serve`) with OpenAPI, persistent sessions, session status, message history, async prompt submission (`/session/:id/prompt_async`), and programmatic interaction.
- OpenCode supports OpenAI-compatible custom providers and configurable `baseURL`, making a LiteLLM-compatible gateway technically plausible.
- Official provider docs distinguish OpenAI-compatible Chat Completions and Responses-style provider packages; exact compatibility must be tested against the selected gateway/model path.

### Aider

- Docs: https://aider.chat/docs/
- Scripting: https://aider.chat/docs/scripting.html
- Chat/architect modes: https://aider.chat/docs/usage/modes.html
- OpenAI-compatible APIs: https://aider.chat/docs/llms/openai-compat.html
- Aider can run a single scripted message and exit, or be driven repeatedly through its Python API; its Python scripting API is explicitly described as not officially supported/stable.
- Aider has `code`, `ask`, and `architect` modes. Architect mode can use a separate architect model and editor model, which is directly relevant to cross-family role separation.
- Aider supports arbitrary OpenAI-compatible endpoints using `OPENAI_API_BASE` and an `openai/<model>` model name, so LiteLLM/CKFF compatibility is technically plausible.

## Repository-local evidence: what V4/SSC summon actually did

Current V4 migration-era evidence shows that `SSCSummonAdapter` did **not** itself execute a model. It delegated seat resolution, dispatch-chain lookup, tool registries, and mutation policy back into the legacy SSC runtime. See `cortex_v4/adapters/ssc_summon.py` and `cortex_v4/adapters/ssc_dispatch.py` on the pre-retirement V4 baseline.

The live V4/LiteLLM script `scripts/run_v4_live_litellm.py` imported `cortex_core.model_summon.summon_agent` from SSC and submitted one bounded but relatively large task prompt to a selected seat/model with:

- one workspace;
- one write set;
- a high output-token allowance;
- multiple requested artifact writes;
- read-back verification instructions;
- an objective checker after the summoned run.

In other words, the live `summon_agent` experiment was closer to **one agentic task invocation** than a fine-grained workflow of independently checkpointed engineering steps.

The 2026-08-05 V4 replay note explicitly says the A/B/C/D summon migration replay moved only the control boundary and did not use a live provider request as the deterministic migration oracle. The real provider test was separate.

## OpenCode failure classification from the 2026-08-11 investigation

Do **not** record “OpenCode failed” as an established conclusion.

The observed end-to-end OpenCode staging probes produced zero-token / `finish: unknown` behavior and no file mutation. However, direct gateway controls isolated a more specific failure:

- Chat Completions through the staging generic proxy returned HTTP 200 with an empty body;
- `/v1/models` on the same generic proxy path also returned HTTP 200 with an empty body;
- `/v1/responses` returned a real JSON response with usage;
- therefore OpenCode was given a malformed false-success transport outcome on the failing path.

Candidate gateway fixes in `litellm-ckff-ops#7` reject empty/malformed 2xx responses and guard streaming first payloads. Candidate persistent OpenCode execution is in `cortex-v4#10`; the Fossil executor contract is in `fossil-core#78`.

**Research interpretation:** this evidence proves the tested end-to-end path failed. It does *not* yet prove OpenCode is unsuitable as an executor. A repaired gateway must be tested before attributing the failure to OpenCode.

## Would finer-grained task flow have solved that failure?

**No for the identified empty-2xx defect.** Splitting the task into smaller steps does not make an invalid HTTP 200/empty-body response valid.

**Possibly for other failure classes.** A granular workflow can reduce the blast radius of:

- long model turns;
- context growth;
- retrying a whole task after one late-stage failure;
- ambiguous progress;
- difficult checkpoint/recovery;
- inability to compare executor behavior at a small unit of work.

This must be tested rather than assumed. A granular design can also add overhead, coordination errors, context loss, and excessive model calls.

## Candidate architecture boundary — research hypothesis only

A useful provisional decomposition to test is:

```text
Engineering method / task specification
  Spec Kit-style constitution + spec + plan + checks
  established external engineering standards
                |
                v
Task/risk policy
  small mechanical rules
  project-specific current knowledge from FOSSIL
                |
                v
V4 control policy (candidate)
  dynamic task classification
  model/capability selection from current LiteLLM facts
  cross-family seating/review rules
  budgets / retry / fallback / recovery policy
  execution receipt requirements
                |
                v
ExecutorPort (UNDECIDED implementation)
  OpenCode | Aider | direct tool loop | Spec Kit agent step | other
                |
                v
LiteLLM / CKFF
  exact-model transport + factual route/capability/health inventory
```

This is a **candidate test boundary**, not an accepted V4 architecture.

## Executor candidates to compare

### Candidate A — OpenCode persistent server

Potential strengths to test:

- explicit persistent server/session API;
- async prompt dispatch;
- status/messages/diff/abort surfaces;
- programmatic OpenAPI/SDK surface;
- OpenAI-compatible custom providers;
- potentially suitable for long-running sessions whose lifetime is not one caller HTTP request.

Known concerns / required tests:

- must retest only after guarded LiteLLM gateway promotion;
- completion/liveness semantics must be validated, not inferred from one status field;
- must verify actual file mutation and tool behavior across CKFF model families;
- must measure resume/recovery behavior, session persistence, context growth, and false-success handling.

### Candidate B — Aider

Potential strengths to test:

- mature code-editing specialization;
- direct CLI scripting for one bounded instruction;
- architect/editor separation can naturally express cross-family planning vs editing;
- OpenAI-compatible endpoint support;
- git-centric editing workflow.

Known concerns / required tests:

- CLI `--message` is intentionally one instruction then exit, so persistence semantics differ from OpenCode;
- Python scripting API is documented as unsupported/unstable, so it should not become a hard production contract without isolation behind an adapter;
- model/edit-format compatibility may be sensitive to weaker/free models;
- need explicit status/checkpoint/abort/receipt behavior if V4 requires these capabilities.

### Candidate C — direct V4 model/tool loop

Potential strengths to test:

- maximum mechanical control over routing, retries, timeouts, tool contracts, telemetry, and semantic success;
- no executor-specific hidden lifecycle.

Risks:

- reimplements a coding-agent harness: repository context, edit application, tool safety, file selection, recovery, git integration, prompting, model quirks;
- high maintenance burden and likely duplication of mature tooling;
- greatest risk of horizontal scope growth.

### Candidate D — Spec Kit workflow + configured coding-agent integration

Potential strengths to test:

- existing resumable workflow-stage state;
- conditions, loops, fan-out/fan-in, gates and shell steps;
- strong fit for methodology/specification stages;
- avoids building generic workflow primitives in V4.

Risks / boundary uncertainty:

- Spec Kit's workflow state is not automatically equivalent to coding-agent session persistence;
- model/provider selection and cross-vendor routing are not established as its responsibility;
- prompt/shell steps may delegate important semantics to the configured agent and local environment;
- shell execution has no built-in capability sandbox according to official docs.

## Required executor bakeoff

Do not select an executor from feature lists. Run matched tasks through candidates behind the same `ExecutorPort`-shaped contract.

Minimum matched tasks:

1. **tiny deterministic edit** — one file, objective exact checker;
2. **multi-file implementation** — bounded contract + tests;
3. **tool-required task** — must inspect files and make a verifiable mutation;
4. **long task** — multiple checkpoints / deliberate interruption;
5. **forced model/API timeout** — must not produce false success;
6. **empty/malformed 2xx** — must fail loudly;
7. **executor restart / caller restart** — measure what state survives;
8. **cross-family architect/editor or worker/reviewer** — explicit model identities;
9. **parallel independent tasks** — bounded fan-out;
10. **abort/cancel** — terminal state must be inspectable.

Capture for every run:

- requested and actual model/provider/route;
- task/session/run IDs;
- tool calls and changed files;
- objective checker result;
- latency and token/cost facts;
- retry/fallback cause and owner;
- timeout provenance;
- executor process/session lifetime;
- checkpoint/resume behavior;
- terminal reason;
- raw trace/evidence reference.

## Granularity experiment

Run the same medium task in at least two shapes:

**Monolithic:** one agent instruction owns the full bounded implementation.

**Granular:** preflight -> inspect -> plan/contract -> implement subtask(s) -> test -> repair -> closeout, with machine-verifiable artifacts between stages.

Evaluate:

- objective success;
- total tokens/cost;
- wall-clock time;
- recovery after injected failure;
- redundant work;
- context loss;
- number of model calls;
- observability quality;
- human diagnosability.

The purpose is to determine where granularity earns reliability rather than assume that more orchestration is automatically better.

## FOSSIL role in engineering-method knowledge

The existing `RESEARCH_TRACE_CONTRACT.md` already requires preserving questions, sources, claims, critiques, alternatives, uncertainties, decisions, implementation actions, and supersession lineage. This research should therefore enter FOSSIL as a research trace rather than as an accepted architecture decision.

Candidate future engineering knowledge classes:

- approved current engineering standard;
- explanatory/reference material;
- historical project architecture;
- incident evidence;
- proposed lesson/pattern;
- stale/unverified material.

Agent/model-generated interpretation must not silently promote itself into approved current policy.

## Personal Study OS relationship

The owner's `private-study-log` is a separate human learning surface. It can later present bite-size lessons, diagrams, worked examples, retrieval questions, breadcrumbs, prerequisites and progress. It should be able to reference shared concept IDs or reviewed sources, but product/runtime CI must not depend on the personal Study OS.

## Current open questions

1. After the guarded LiteLLM staging gateway is deployed, does OpenCode pass the matched executor suite?
2. Does Aider produce more reliable edits across the actual CKFF/free model catalog?
3. Does Aider architect/editor mode provide useful cross-family separation at acceptable cost/latency?
4. Which executor can survive caller/process interruption with the least custom state machinery?
5. Is persistent session state actually necessary, or do small idempotent tasks + git/checkpoint artifacts outperform persistent sessions?
6. Where should Spec Kit workflow state stop and V4 execution state begin?
7. Which generic methodology concepts can V4 delete because Spec Kit or established engineering standards already supply them?
8. Which V4 mechanics remain uniquely valuable: dynamic factual-catalog routing, cross-family seating, fallback/recovery, budget/context policy, execution receipts?
9. Does a granular task flow improve real success after controlling for the gateway defect?
10. What is the smallest stable `ExecutorPort` contract that lets candidates be replaced without rewriting V4 policy?

## Decision state

**OPEN.**

Do not merge a conclusion into `ARCHITECTURE.md` or `docs/DECISION_LOG.md` until the matched execution bakeoff and scope review are complete.

## Proposed next evidence

1. Deploy/test the guarded staging LiteLLM candidate first; reject false-success at the transport boundary.
2. Freeze a small executor test contract independent of OpenCode/Aider.
3. Run OpenCode vs Aider vs a minimal direct control on identical tasks and models where possible.
4. Add monolithic-vs-granular task-shape comparison.
5. Only then decide the V4 executor boundary and which methodology responsibilities remain.
