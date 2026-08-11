# Cross-session handoff — agent methodology and executor research — 2026-08-11

**Status:** RESEARCH HANDOFF / OPEN QUESTIONS  
**Do not treat as architecture authority.**

## Start here

Read, in order:

1. `docs/research/2026-08-11-agent-engineering-methodology-and-executor-options.md`
2. `examples/research-trace/2026-08-11-agent-methodology-executor-options.json`
3. `docs/research/RESEARCH_TRACE_CONTRACT.md`
4. GitHub issue `Pukujan/fossil-core#84`
5. Draft execution candidates: `Pukujan/cortex-v4#10`, `Pukujan/litellm-ckff-ops#7`, `Pukujan/fossil-core#78`

## What is decided

Very little from this research pass is decided. Existing accepted FOSSIL/V4/LiteLLM ownership contracts remain in force until explicitly superseded.

## What is intentionally undecided

- final V4 methodology boundary;
- whether V4 owns generic workflow stages or delegates them to Spec Kit-style tooling;
- coding executor selection;
- OpenCode vs Aider vs direct execution vs another adapter;
- whether persistent sessions outperform smaller idempotent task units;
- ideal task granularity;
- final cross-family architect/editor/worker/reviewer topology.

## Critical factual correction

Do not summarize the 2026-08-11 execution investigation as “OpenCode failed.”

The observed OpenCode end-to-end task did fail to produce useful output/file mutation, but direct controls isolated an HTTP 200 + empty-body defect on the staging LiteLLM generic Chat Completions/models proxy, while the Responses route produced valid JSON. Therefore executor suitability remains unproven until the guarded gateway is deployed and the candidates are tested on matched tasks.

## Why this handoff exists

The owner wants another ChatGPT/Codex session to be able to reconstruct the research path without relying on chat memory or stale summaries. This handoff points to durable source-controlled research artifacts and explicitly separates open research from accepted architecture.
