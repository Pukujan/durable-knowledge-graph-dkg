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

## Checking

From the repository root with the pinned Lean toolchain active:

```sh
lean formal/lean/Fossil/Lifecycle.lean
```

The spec-triggered CI lane performs the same check on the exact pull-request head and rejects `sorry`/`admit` placeholders in the bounded theorem file.
