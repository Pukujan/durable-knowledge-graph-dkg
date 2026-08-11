# Cross-session handoff — human + agent engineering operating model — 2026-08-11

**Status:** RESEARCH HANDOFF / OPEN QUESTIONS  
**Do not treat this handoff as architecture authority.**

## Start here

Read in this order:

1. `docs/research/2026-08-11-human-agent-engineering-operating-model.md`
2. `examples/research-trace/2026-08-11-human-agent-engineering-operating-model.json`
3. `docs/research/RESEARCH_TRACE_CONTRACT.md`
4. `Pukujan/fossil-core#84` for the engineering-preflight experiment
5. `docs/research/2026-08-11-agent-engineering-methodology-and-executor-options.md` for executor-specific research
6. canonical `ARCHITECTURE.md` / `docs/DECISION_LOG.md` for accepted FOSSIL architecture

## What this handoff preserves

- the owner's personal Study OS / engineering-compass concept;
- the task-first bite-size study/checklist model;
- the universal pre-build questions;
- the agent preflight + risk-triggered pack model;
- validation, bounded critique, adjudication, and scope gate;
- debugging by isolation and semantic-success validation;
- observability ownership: Grafana/metrics, Langfuse/traces, logs, GitHub project state, execution state, FOSSIL knowledge;
- the thin-control-room/deep-link idea;
- the shared correlation-ID spine;
- GitHub Issues/Projects vs runtime orchestration separation;
- distributed ownership across CKFF/LiteLLM/V4/executor/FOSSIL/GitHub Actions/Gravebuster/OTEL;
- dependency/release automation concepts;
- source-backed references used to reach these ideas;
- unresolved V4 methodology and executor questions.

## Important status rule

Do not flatten the research into one conclusion.

Use these classes when answering from it:

- accepted elsewhere / canonical — follow the linked architecture or decision contract;
- strong research-backed operating principle — useful guidance but not automatically a runtime invariant;
- candidate — requires an experiment or implementation decision;
- open / undecided — do not silently resolve;
- historical — preserve for lineage but not current authority.

## Human Study OS boundary

The personal Study OS should be a human-facing learning/navigation surface, likely in `Pukujan/private-study-log` or another personal repo. FOSSIL should retain the provenance-rich engineering concepts and research history, but product CI should not depend on the personal study UI.

## Agent preflight boundary

`fossil-core#84` is the bounded experiment for a small universal engineering constitution + risk-triggered checks + machine-validated receipts. It is not permission to build a giant checklist or a new platform.

## Executor boundary

Still undecided. OpenCode, Aider, direct execution, and other adapters require matched testing. Do not claim OpenCode itself was disproven by the 2026-08-11 staging failure; the immediate observed root cause was the LiteLLM generic gateway's empty 2xx response path.

## Retrieval question for future sessions

If asked, “How should the owner and AI agents work so engineering foundations are not forgotten?”, answer from the umbrella research note first, then distinguish human learning, agent preflight, project tracking, runtime execution, observability, and FOSSIL knowledge as separate responsibility planes.