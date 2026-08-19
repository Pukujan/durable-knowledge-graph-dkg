# FOSSIL Lean semantic kernel

These theorem files are Phase 5 assurance artifacts for #176. They formalize small semantic laws; they do **not** prove the Python implementation and do not replace deterministic/property tests, mutation testing, TLA+, hidden holdouts, live-provider checks, or semantic acceptance.

## Toolchain

The repository pins `leanprover/lean4:v4.30.0` in the root `lean-toolchain` file. Lean is an assurance-only development dependency and is not a runtime dependency of `fossil-core`.

## Lifecycle

`Fossil/Lifecycle.lean` defines a small claim-state model corresponding to stable lifecycle laws already enforced by `src/fossil_core/domain/lifecycle.py` and its Python oracles.

Property traceability:

- `FOSSIL-PROP-HISTORY-001`
- `FOSSIL-PROP-LIFECYCLE-DEPENDENCY-001`

Current theorem surface:

- terminal claim states are explicitly classified;
- terminal dependents remain unchanged when a premise is superseded;
- nonterminal dependents become `stalePendingReview` under that dependency-staleness operation;
- state-history updates are append-only in the formal model;
- premise supersession cannot revive a terminal dependent through the dependency-staleness operation.

The theorem file intentionally does not model event schemas, providers, storage, projection behavior, pack authority, promotion, or arbitrary lifecycle transitions beyond this bounded stable kernel. Python conformance remains established by the existing lifecycle deterministic/property tests.

## PackAccess

`Fossil/PackAccess.lean` defines provider-free authority sets corresponding to the stable pack-access boundary in `src/fossil_core/domain/pack.py` and the composed scope laws tracked by #174.

Property traceability:

- `FOSSIL-PROP-PACK-ISOLATION-001`
- `FOSSIL-PROP-PACK-MANIFEST-001`

Current theorem surface:

- every permitted write target is readable when the policy carries the `writeTargets ⊆ readMounts` invariant;
- intersecting a requested scope with mounted authority cannot widen either the mounts or the original request;
- returned scope constrained to that intersection preserves both caller request authority and mounted read authority;
- authority containment is transitive.

The theorem file intentionally does not define manifests, dependency resolution, pack locks, retrieval ranking, provider APIs, promotion semantics, or Python enforcement mechanics. Python conformance remains established by pack, authorization, and property tests.

## Promotion

`Fossil/Promotion.lean` formalizes the source-pinned cross-pack promotion kernel frozen and implemented by #111 and exercised by `src/fossil_core/domain/promotion.py`.

Property traceability:

- `FOSSIL-PROP-PROMOTION-001`

Current theorem surface:

- constructing a target promotion leaves the modeled source event unchanged;
- the target promotion copies the exact source pack/revision/event pin;
- the durable target identity remains the explicitly requested target pack;
- a valid promotion requires distinct source and target packs;
- a valid promotion pins exactly the modeled source event;
- promoted subjects remain a subset of the pinned source event's subjects.

The theorem file is a provider-free semantic kernel. Python/schema tests remain responsible for string/non-empty validation, resolver behavior, durable event-envelope conformance, and storage/authorization integration.

## Checking

From the repository root with the pinned Lean toolchain active:

```sh
lean formal/lean/Fossil/Lifecycle.lean
lean formal/lean/Fossil/PackAccess.lean
lean formal/lean/Fossil/Promotion.lean
```

The spec-triggered CI lanes perform the corresponding checks on the exact pull-request head and reject `sorry`/`admit` placeholders in the bounded theorem files.
