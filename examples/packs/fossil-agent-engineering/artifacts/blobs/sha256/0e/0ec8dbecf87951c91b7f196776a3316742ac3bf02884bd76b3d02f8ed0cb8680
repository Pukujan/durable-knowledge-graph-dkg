# FOSSIL handoff-process and AI-engineering substrate transcript

Source URL: https://chatgpt.com/share/6a820cf1-1060-83ea-9831-82a8ae4c4ddb?ogimg=plain  
Capture date: 2026-08-16  
Destination: `Pukujan/fossil-core`  
Evidence status: reconstructed

This is a normalized decision-bearing reconstruction of the shared conversation,
not a verbatim export. The raw shared-page HTML is preserved separately in the
FOSSIL evidence pack. Architectural proposals remain candidate-only until
independent repository, benchmark, and live-environment evidence promotes them.
Reported GitHub/R2 handoff state is historical conversation evidence and must be
reconciled against live repository state before action.

## Turn 0 — human

Creating a skill for every repeatable engineering methodology or deterministic
pipeline does not work. The methodology, control flow, state, tooling, and
documentation need a smarter representation.

## Turn 1 — assistant

Do not treat repeatable engineering methodology as a skill. A skill is useful as
procedural knowledge, but requirements elicitation, acceptance freezing, hidden
tests, implementation, mutation testing, fuzzing, canary, approval, provenance,
and phase closeout require an executable workflow contract with state,
transitions, gates, evidence, and durable closeout.

## Turn 2 — human

The coding agent should not start writing code from intent alone. It should ask
narrow contextual questions early, use Q/A rounds to fill checkpoints, and treat
human time as the most valuable resource. Fuzzy back-and-forth conversations can
be used as deliberate tests of whether the agent narrows intent correctly.

## Turn 3 — assistant

Put a separate Intent/Requirements Broker before implementation. It should gather
context, detect ambiguity, prioritize high-value questions, persist answers as
versioned requirements, critique the resulting specification, and reopen
clarification when tests expose a gap. The purpose is to convert vague intent
into an executable behavioral contract with checkpoints and acceptance oracles.
The broker should optimize for human-time value, not maximum conversation length.

## Turn 4 — human

Everything generated and completed should be saved to the knowledge graph for
provenance. The broader goal is an operating system for AI work, with FOSSIL as
the durable foundation rather than another temporary agent context store.

## Turn 5 — assistant

FOSSIL should not become a dumping ground for literally everything. It is the
durable knowledge/evidence plane of an AI-engineering substrate. Keep an Intent
Plane for requirements and checkpoints, an Execution Plane for ephemeral agents
and tools, and a Verification Plane for tests, evidence, and outcomes. FOSSIL
stores provenance-rich durable records across those planes without turning every
generated sentence into accepted knowledge.
FOSSIL must not write every sentence as truth.

## Turn 6 — human

The admission filter must distinguish genuine reusable knowledge from temporary
glue, closeout prose, benchmark results, user interaction, bugs, human review,
and agent-generated claims. It must answer temporal/bitemporal scope, project and
domain applicability, promotion tiers, shadow/canary success, and context-rot
prevention without changing architecture blindly.

## Turn 7 — assistant

FOSSIL already has many primitives: source evidence, observations, experiments,
claims, assumptions, decisions, lifecycle states, bitemporal event clocks, pack
boundaries, and explicit promotion. The missing enforcement boundary is a
knowledge-admission/promotion controller that qualifies observations by claim
type, scope, replication, environment, freshness, and authority before project,
domain, or common knowledge promotion. Prototype it behind an adapter rather
than rewriting the core.

## Turn 8 — assistant

Closeout lessons are proposals, not evidence; model agreement is not external
evidence; benchmark numbers, user outcomes, human validation, shadow runs, and
canary runs should remain distinguishable promotion inputs. Packs are knowledge
boundaries: project packs may mount shared/domain packs read-only, and promotion
upward is explicit. FOSSIL still needs one concrete working RAG projection and
retrieval path so agents can use it; replaceable components are not optional
runtime capability.

## Turn 9 — assistant

LiteLLM embedding/reranking is optional benchmark infrastructure rather than a
permanent FOSSIL requirement. A local FOSSIL copy remains useful, while local-PC
hosting is not mandatory infrastructure. The conversation’s reported R2 storage
proof and main-branch handoff state are operational claims to verify against the
live repository and workflow before relying on them.
