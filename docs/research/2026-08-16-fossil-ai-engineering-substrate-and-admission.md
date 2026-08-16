# FOSSIL — AI-engineering substrate and knowledge admission

Source conversation: [shared ChatGPT transcript](https://chatgpt.com/share/6a820cf1-1060-83ea-9831-82a8ae4c4ddb?ogimg=plain)  
Intake pack: `pack_fossil_agent_engineering_20260816`  
Status: reconstructed architectural synthesis and historical handoff evidence

## Evidence boundary

The source conversation is preserved as reconstructed evidence in
`docs/recovery/2026-08-16-fossil-handoff-process-transcript.md`. This document
distills its design arguments; it is not an independent research review and
does not promote its claims into FOSSIL truth. Repository state, issue status,
R2 results, package status, and referenced external research require direct
verification before implementation or operational action.

## Core design correction

Repeatable engineering methodology should not be represented as “a skill for
everything.” A skill is a useful procedural knowledge artifact: guidance,
pitfalls, examples, and verification advice. A repeatable engineering pipeline
also needs executable state and control:

```text
workflow definition
    → state
    → allowed transitions
    → gates and evidence requirements
    → bounded tool actions
    → approval/canary policy
    → durable closeout
```

This separation prevents methodology, control flow, state, tools, and
documentation from collapsing into prompt text. The exact runtime engine is an
implementation question; the durable contract and evidence model are the
important boundary.

## Intent/Requirements Broker

The coding agent is being asked to implement too early when a human request is
underspecified. Add a pre-implementation Intent/Requirements Broker as a
separate subsystem or bounded workflow.

Its responsibilities are:

1. gather relevant context;
2. detect ambiguity and missing constraints;
3. select the smallest high-value question set;
4. record answers as versioned requirements;
5. compile requirements into behavioral checkpoints and acceptance oracles;
6. critique the resulting contract for contradictions and missing cases;
7. reopen clarification when implementation or tests reveal a gap.

The broker should optimize for human-time value, not maximum conversation
length. Q/A itself becomes testable behavior: scenario generators can vary
ambiguity, context, terminology, and constraints, then measure whether the
agent asks useful questions early enough and avoids wasting interaction rounds.

The output is not “the agent understood the user.” It is an explicit contract
with requirements, assumptions, unresolved questions, checkpoints, forbidden
interpretations, success/failure conditions, and a revision history.

## AI-engineering planes

FOSSIL should be the durable knowledge/evidence plane of a larger AI-engineering
substrate, not an undifferentiated store of every generated artifact:

```text
Human intent
     ↓
Intent Plane       requirements / checkpoints / invariants / acceptance
     ↓
Execution Plane    ephemeral Codex / Claude / Luna agents and brokered tools
     ↓
Verification Plane tests / replay / mutation / fuzz / human outcomes / evidence
     ↓
FOSSIL             provenance-rich durable knowledge and evidence records
```

The planes are conceptual boundaries, not permission to add infrastructure
without evidence. The key invariant is that execution context may be temporary,
while evidence and accepted knowledge remain durable, attributable, and
re-evaluable.

FOSSIL must not write every sentence as truth. It should retain source artifacts,
observations, experiments, claims, assumptions, decisions, proposals, tests,
and outcomes as distinguishable record types with provenance and lifecycle.

## Knowledge admission and promotion

The conversation identifies a missing enforcement boundary rather than a reason
to rewrite FOSSIL’s ontology. Existing primitives already separate many useful
states; the candidate addition is a promotion/admission controller behind an
adapter.

The controller should evaluate at least:

- claim type and epistemic class;
- project, domain, and general applicability scope;
- observed versus recorded time, freshness, and supersession;
- environment and dependency compatibility;
- independent evidence and replication;
- benchmark, user-outcome, human-review, shadow, and canary results;
- authority level and permitted downstream use;
- contradiction, circular evidence, duplicate amplification, and poisoning
  risk.

Potential promotion flow:

```text
raw source / event
    → observation
    → candidate claim or experiment
    → project-local proposal
    → verified project knowledge
    → domain promotion
    → common knowledge or executable policy
```

Promotion is not implied by retrieval, model agreement, a successful closeout,
or a high benchmark score. Closeout lessons are proposals about what to try or
remember; they are not themselves proof of the underlying outcome. A benchmark
result is evidence with a scope and protocol, not universal truth. User-facing
success, human validation, shadow success, and canary success should remain
separate evidence dimensions rather than being flattened into one quality tier.

The promotion controller should be designed as a policy/admission module that
can be tested independently before changing canonical storage semantics. It
should support shadow evaluation and canary promotion with explicit rollback or
quarantine on regression.

## Packs and working RAG

Knowledge packs are the natural boundary for project/domain/common scope. A
project pack can mount shared packs read-only; writing into a broader pack is an
explicit promotion operation. This prevents one agent or project from silently
poisoning shared knowledge.

The architecture still needs one concrete, usable RAG path for agents. The fact
that graph, vector, and retrieval projections are replaceable means they can be
reconstructed or swapped; it does not mean FOSSIL can remain only a schema and
rebuild exercise. A working path must demonstrate:

```text
pack events → accepted lifecycle state → projection/index → retrieval
           → context construction → citations/abstention → agent preflight
```

The first working path should be small, source-backed, lifecycle-aware, and
measured against poisoning, temporal, lineage, and citation benchmarks. New
retrieval infrastructure should remain optional until it beats an existing
baseline on corpus-specific evidence.

## Model and hosting boundaries

Hosted LiteLLM embedding/reranking routes are benchmark candidates, not a
permanent FOSSIL dependency. Local semantic models or other adapters may be
used when they satisfy the current contract. A local FOSSIL installation is a
useful product capability, but the owner’s PC must not become mandatory semantic
or infrastructure authority.

The conversation’s reported package, main-branch, issue, workflow, and R2
storage states are preserved as historical handoff observations in the intake
pack. They are intentionally not copied into `ARCHITECTURE.md` as current
facts. A live GitHub/CI/R2 reconciliation is required before any operational
continuation.

## Verification agenda

The candidate architecture should be tested with:

- ambiguity-to-question scenarios for the Intent/Requirements Broker;
- hidden holdout requirements and adversarial paraphrases;
- mutation tests that alter requirements, gates, or promotion decisions;
- property/state-machine tests for workflow transitions;
- provenance and bitemporal replay;
- stale, superseded, contradictory, duplicated, and poisoned memories;
- shadow/canary promotion and rollback;
- pack read/write boundary violations;
- concrete RAG retrieval, citation, abstention, and context-budget behavior;
- live handoff verification that separately checks current GitHub, CI, and R2
  state.

The central falsifiable hypothesis is that explicit intent compilation and
evidence admission reduce wrong-but-coherent agent work without creating a
larger coordination framework than the problem itself.

