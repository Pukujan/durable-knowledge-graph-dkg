# Post-Gate-2 Workstream C — Retrieval Poisoning / Untrusted-Context Proof

**Date:** 2026-08-10  
**Campaign:** Issue #48 — production RAG hardening  
**Workstream:** C — retrieval poisoning / untrusted-context hardening

## Scope

This workstream tests a bounded structural defense against retrieval poisoning and prompt-injection-shaped source text. It does **not** claim universal poisoning resistance and it does not replace or weaken D021.

The core rule is:

> Retrieved/source text is untrusted data, never executable policy merely because it was retrieved.

The defense therefore does not attempt to decide whether arbitrary prose is "safe". Instead it enforces authority boundaries around model context and output:

- retrieved claim/relation lifecycle, citation, relation endpoints, pack identity, and text are re-resolved from mounted durable documents by stable ID when that ID exists;
- unknown in-scope retrieval payloads remain visible as `untrusted_context` text but lose claim/relation/lifecycle/citation authority;
- unknown or known payloads outside the requested mounted pack scope are removed before model execution;
- exact duplicate unknown passages are collapsed to reduce trivial context flooding;
- the answer/model boundary exposes no executable tool/action surface;
- model output remains `candidate_only`;
- emitted claim IDs must resolve to mounted durable claims, and claim text/citation identity is copied back from the durable document rather than trusted from model prose;
- invalid output claim IDs are contained as `insufficient_evidence` rather than converted into new claims;
- durable knowledge mutation still requires the existing agent capability, provenance, pack-write, validation, and commit gates.

## Implementation

The provider-independent implementation adds:

- `src/dkg/context_security.py`
  - `canonicalize_untrusted_context(...)`;
  - `UntrustedContextModelService`;
  - runtime identity `fossil-untrusted-context-v1`;
- `src/dkg/poisoning_eval.py`
  - adversarial case contract;
  - Workstream-B answer/citation/abstention metrics plus security-boundary metrics;
- `benchmarks/post-gate2/retrieval-poisoning-v1.json`
  - eight-case exact-pin adversarial plan;
- `scripts/run_post_gate2_retrieval_poisoning.py`
  - exact-pack-pin runner;
- `tests/test_context_security.py`
  - deterministic authority, pack-isolation, output-containment, lineage, and proposal/commit boundary tests.

The secure service composition for the committed baseline is:

```text
retrieval candidate context
-> fossil-untrusted-context-v1 authority resolution
-> fossil-lineage-context-v1 durable relation-endpoint expansion
-> deterministic durable-evidence answerer
-> candidate-only output containment / durable claim re-resolution
```

This order preserves the Workstream B lesson: top-k absence is not evidence of nonexistence, and retrieval payload metadata cannot author durable lifecycle truth.

## Adversarial plan

The versioned plan covers:

1. poisoned retrieved documents containing system/tool instructions;
2. authority spoofing using a real durable ID with forged current-state/text metadata;
3. malicious supersession of a current durable claim;
4. repeated duplicate passages intended to dominate context/ranking pressure;
5. fake conflicting-source claims and fake `CONTRADICTS` relations;
6. pack-isolation pressure from an unmounted pack;
7. lifecycle/lineage spoofing of the stale SQLite dependent discovered in Workstream B;
8. instructions attempting to bypass proposal-before-commit and invoke commit directly.

The benchmark does not merely ask whether poisoned text was retrieved. It evaluates whether the attack changes:

- final-answer correctness;
- outcome correctness / abstention;
- exact citation correctness;
- unsupported-claim rate;
- answer completeness;
- contradiction handling;
- lifecycle/lineage resolution;
- pack isolation;
- candidate-only model authority;
- executable-output containment;
- durable-claim output resolution.

Proposal-before-commit is also tested at the domain-service boundary: an attacker-shaped prebuilt event with forged actor provenance is rejected by `CorpusService.commit`, and no durable event is written.

## Normal CI proof

Draft core PR #61 normal contract CI before the real-corpus execution proof:

- workflow run: `31436256964`;
- job: `93610937816`;
- result: **100 passed in 0.94s**.

## Exact corpus pins

The execution plan is pinned to the same validated pack revisions used for Workstream B:

- `Pukujan/fossil-common@d583005dce06dbb499c3c0de5c22b899655eb8d2`;
- `Pukujan/fossil-ai-systems@84accd2ee895663990e82ca5b79b592cb503db24`.

## Real-corpus execution proof — PASS

Execution-only PR #62 added only the temporary workflow step needed to run the unchanged committed eight-case plan against the exact pins above. The PR is not implementation evidence and is intended to remain unmerged.

Proof:

- workflow run: `31436425791`;
- job: `93611459472`;
- core suite inside proof: **100 passed in 0.96s**;
- projected corpus: **27 documents**;
- adversarial cases: **8**;
- benchmark result: **PASS 8/8**;
- final-answer correctness: `1.0`;
- outcome accuracy: `1.0`;
- citation correctness: `1.0`;
- completeness: `1.0`;
- appropriate abstention: `1.0`;
- unsupported-claim rate: `0.0`;
- over-abstention: `0.0`;
- Brier score: `0.0`;
- high-confidence error rate: `0.0`;
- pack-isolation preservation: `1.0`;
- candidate-only authority: `1.0`;
- executable-output containment: `1.0`;
- durable-claim output boundary: `1.0`;
- aggregate security-boundary pass rate: `1.0`;
- estimated model cost: `$0.0`;
- mean service latency in this local deterministic proof: approximately `2.315 ms`.

`contradiction_handling_rate` is not populated for this plan because no case expects an unresolved `conflicting_evidence` outcome. The conflicting-source attack instead tests that an attacker-authored fake claim/relation cannot manufacture a durable conflict against an already resolved durable conclusion.

### Attack-specific observations

The proof showed the intended bounded behavior:

- instruction-bearing unknown payloads were forwarded only as `untrusted_context` data and did not replace the exact durable answer/citation;
- spoofed payloads using real durable IDs were detected as retrieval-payload mismatches and replaced by the mounted durable text/lifecycle/citation state;
- six identical adversarial passages collapsed to one untrusted passage while the durable answer remained correct;
- the unmounted-pack poison was removed before model execution and the forwarded pack set remained within the requested AI-systems pack;
- fake claim + fake `CONTRADICTS` relation payloads were demoted to untrusted context rather than accepted as durable contradiction state;
- proposal/commit instruction text remained non-executable at the answer boundary, while the separate domain-service unit test proves a forged prebuilt event cannot bypass agent provenance and commit gates.

Most importantly, the Workstream-B regression case remained correct under direct lifecycle spoofing. The poisoned payload asserted that the first SQLite prototype was currently supported, but FOSSIL re-resolved the mounted durable state and returned:

- outcome: `current_state_unresolved`;
- claim: `clm_a047d79b8604fadbd44efdf4`;
- exact citation: `cite_b4e13e4e1a809f76527311ba`;
- unsupported claims: none.

This preserves the D021 lesson that top-k or retrieved payload content cannot decide current truth.

## Residual risks

The passing result is intentionally bounded:

- natural-language attacks are open-ended; the suite does not enumerate every prompt-injection strategy;
- a future generative model may still become confused, refuse unnecessarily, or choose an incorrect durable claim among allowed context even when it cannot directly change durable state;
- semantic near-duplicate flooding is not eliminated by exact-text deduplication;
- poisoned material can consume context budget or retrieval rank before the model boundary;
- source authenticity and compromised upstream evidence require independent provenance/source-validation controls; this boundary only prevents retrieved payloads from self-asserting authority;
- availability, latency, cost, model fallback, and provider privacy remain separate operational concerns;
- multi-agent agreement does not convert poisoned context into evidence.

These risks must remain visible rather than being hidden behind a universal-defense claim.

## D021 / authority conclusion

D021 remains unchanged. Retrieval and reranking order candidates; durable evidence, stable identity, lifecycle/lineage resolution, exact source/citation identity, pack scope, and deterministic proposal/commit gates remain authoritative. Model confidence and model consensus remain non-evidence.

Workstream C is complete for the committed bounded baseline. Future hosted/frontier/OSS/Cortex model competitors must run behind the same structural boundary and are not allowed to inherit truth or mutation authority from the fact that this deterministic baseline passed.
