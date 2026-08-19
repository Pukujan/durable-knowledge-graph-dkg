# Property-Driven Assurance

Status: Phase 0 foundation for #176. This document adds assurance traceability only; it does not change FOSSIL runtime or durable semantics.

## Authority

`ARCHITECTURE.md`, accepted decisions/contracts, and the semantic issues that own a change remain architecture authority. The property catalog is a machine-readable index of those laws and their verification surfaces; it must not silently invent or weaken semantic authority.

Canonical Phase 0 artifacts:

- `contracts/properties/property-catalog-v1.schema.json`
- `contracts/properties/fossil-properties-v1.json`
- `tests/test_property_catalog.py`

## Property-Driven Development rule

For semantic work, use this order:

```text
property
-> executable oracle
-> implementation/change
-> adversarial assurance
-> real integration/live evidence where applicable
```

A property has a stable `FOSSIL-PROP-*` identifier. IDs are durable traceability handles; changing wording does not justify casually renumbering an existing property.

Every active critical/high property must have at least one public deterministic oracle. Later phases may add generated/property-based oracles, targeted mutation testing, sealed holdout acceptance, TLA+ specifications, or Lean theorems according to the failure mode.

## Selecting the assurance mechanism

- Property-based/generative tests: input/state-space exploration for deterministic Python behavior.
- Mutation testing: test the oracle by deliberately damaging critical implementation logic.
- Hidden holdouts: adversarial examples that should not be visible to ordinary coding agents. Properties stay public; sealed cases stay outside this public repository.
- TLA+: retry, ordering, failure, concurrency, redaction, rebuild, and other temporal protocols.
- Lean: small stable semantic laws such as lifecycle and pack-authority invariants.
- Existing deterministic, hosted, provider-live, rebuild, semantic, and security gates remain required implementation/reality evidence.

Formal models do not by themselves prove the Python implementation. TLA+ checks the modelled protocol; Lean checks the formal definitions/theorems. Conformance and live tests connect those models back to FOSSIL behavior.

## Pull-request traceability

A semantic PR should include:

```text
Properties: FOSSIL-PROP-...
Property impact: PRESERVE | STRENGTHEN | CHANGE
Oracle: <tests/checks>
Mutation/holdout/formal impact: <refs or N/A with reason>
```

Rules:

- `PRESERVE`: refactor/move/adapter work must leave the named property semantics unchanged.
- `STRENGTHEN`: the change adds enforcement without weakening prior valid behavior/authority.
- `CHANGE`: the semantic law itself changes and therefore requires explicit architecture/decision authority plus catalog/oracle updates.
- A behavior-preserving modularization PR should normally use `PRESERVE`.
- Do not weaken an oracle or formal model merely to make a change pass.

## Hidden acceptance

The public catalog records `hidden_acceptance_required`; it does not contain private cases, credentials, or exact private oracles. Private holdout placement and access must use a separately approved least-privilege mechanism. Public receipts should reveal only safe aggregate/failure-class evidence unless explicit disclosure is intended.

## Planned formal references

Phase 0 may record future `formal/tla/...` and `formal/lean/...` references before those files exist. This is deliberate roadmap traceability, not a claim that model checking or theorem proving has already happened. `tests/test_property_catalog.py` therefore validates public modules/oracles/source references while permitting future formal paths.

## Coordination

- #82: behavior-preserving modularization; add property traceability without turning file moves into proof projects.
- #111: semantic authority for commit-gate, pack-lock/promotion, longitudinal-history, and reviewed-ingest hardening.
- #174 / PR #175: immediate pack-scope property consumer after composition lands.
- #47/#48: empirical retrieval/model evaluation; use safety properties and sealed decision-critical holdouts rather than attempting to prove ranking quality.
- #88/#89: integrate reusable assurance checks without creating a second control plane.

Phase 1 of #176 introduces property-based implementation oracles. Mutation, hidden holdouts, TLA+, and Lean follow as separately bounded phases.
