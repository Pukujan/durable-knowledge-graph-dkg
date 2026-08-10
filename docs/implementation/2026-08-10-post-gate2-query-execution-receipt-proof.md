# Post-Gate-2 Workstream F — Reproducible Query Execution Receipt Proof

**Date:** 2026-08-10  
**Campaign:** Issue #48 — production RAG hardening  
**Workstream:** F — reproducible query execution receipt

## Scope

Workstream F adds a compact, versioned execution receipt for important FOSSIL queries and proves that the receipt can distinguish a true execution/configuration change from telemetry-only replay noise while preserving the existing durable answer/citation authority model.

The receipt is explicitly:

`execution_observability_only`

It is **not** a durable knowledge event, does not become canonical truth merely because it is recorded, and cannot grant retrieval/model output mutation authority.

D021 is unchanged.

## Receipt contract

The versioned contract is:

`fossil.query-execution-receipt.v1`

Implementation:

- `src/dkg/execution_receipt.py`;
- `schemas/query-execution-receipt/v1.schema.json`;
- `tests/test_execution_receipt.py`;
- `scripts/run_post_gate2_query_receipt.py`.

Observability-only diagnostics were also added to the existing deterministic boundaries:

- `src/dkg/answer_pipeline.py` now reports `fossil-lineage-context-v1` input/expanded/final stable IDs;
- `src/dkg/context_security.py` now reports the stable IDs forwarded by `fossil-untrusted-context-v1`.

Neither change alters the resolver's authority behavior.

## Recorded fields

The compact receipt records:

- human-debuggable query text and query ID;
- normalized query text plus deterministic SHA-256 identity;
- mounted stable pack IDs and exact revisions;
- explicit retrieval pack scope, separately from mounted packs;
- projection name/version/build identity;
- route ID and retrieval-policy identity;
- requested and actual provider/model/service implementation identity;
- bounded fallback/attempt diagnostics;
- ordered retrieved candidate stable IDs, pack IDs, ranks, and scores;
- optional base-retrieval and reranker scores when present;
- reranker service identity when present;
- deterministic context-security and lineage resolver identities;
- stable IDs resolved/added/removed and final model-bound context IDs;
- exact citation IDs and emitted durable claim IDs;
- final answer/abstention outcome, confidence, and candidate-only authority;
- aggregate latency/cost plus trace/run references;
- an execution-identity hash and result-identity hash.

Raw source text is not copied into the compact retrieval-candidate section.

## Execution identity versus telemetry

`execution_identity_sha256` is intentionally independent of timing/run-reference noise. It covers the logical query, exact corpus mounts and scope, projection identity, route/policy, requested/actual service identities and bounded attempts, and resolver identities.

`result_sha256` covers the ordered retrieval candidates, resolver effects, model-bound context IDs/citations, and final result.

`recorded_at`, trace/run references, latency, and cost remain telemetry. They may differ across exact replays without falsely changing the execution identity.

The replay comparator reports changes separately across:

- query;
- corpus revision;
- pack scope;
- projection;
- policy;
- services/fallback identity;
- retrieval candidates;
- resolver behavior;
- final context;
- result;
- telemetry.

This is intended to make later Workstream D/#47 comparisons inspectable rather than silently conflating model/retriever changes with corpus drift.

## Requested versus actual provider/model identity

The service invocation record distinguishes requested identity from actual identity and marks fallback usage. Bounded attempt diagnostics can record provider/model/implementation, outcome, error type, and fallback reason.

This preserves the existing LiteLLM rule: a fallback response is not proof that the requested model succeeded.

Credential-shaped fields are removed recursively from retained runtime/attempt diagnostics using key-name filtering for API keys, authorization, cookies, credentials, passwords, secrets, and tokens. This is a compact receipt safeguard, not a general DLP system.

## Normal CI proof

Draft core PR #64 normal contract CI before the exact-pin execution proof:

- workflow run: `31437380214`;
- job: `93614423141`;
- result: **104 passed in 2.49s**.

## Exact corpus pins

The replay proof uses the same validated pack revisions as Workstreams B and C:

- `Pukujan/fossil-common@d583005dce06dbb499c3c0de5c22b899655eb8d2`;
- `Pukujan/fossil-ai-systems@84accd2ee895663990e82ca5b79b592cb503db24`.

Stable mounted pack IDs:

- `pack_269099f7b2ba43b7a99b9427d64092de`;
- `pack_f024177f89a5442db84171c3dd7f58e5`.

The proof's deterministic pack-fixture projection identity was:

- name: `pack-fixture-retrieval-documents`;
- version: `1`;
- build ID: `packfix_59b82d8d50ab38ea68402db7`.

## Real-corpus replay execution proof — PASS

Execution-only PR #65 added only the temporary workflow step needed to clone the exact pack pins and run the unchanged receipt/replay proof. It is not implementation evidence and is intended to remain unmerged.

Proof:

- workflow run: `31437447245`;
- job: `93614630416`;
- core suite inside proof: **104 passed in 2.41s**;
- projected corpus: **27 documents**;
- Workstream-B benchmark queries replayed: **6**;
- receipts emitted: **18** — baseline, exact replay, and controlled service/policy variant for every query;
- overall proof result: **PASS**;
- answer correctness rate: `1.0`;
- exact replay identity rate: `1.0`;
- resolver recording rate: `1.0`;
- semantic result stability rate: `1.0`;
- service-change visibility rate: `1.0`.

### Exact replay behavior

For every query, the exact replay preserved:

- the normalized logical query;
- exact corpus revisions;
- retrieval pack scope;
- projection identity;
- route/policy identity;
- service identity;
- execution identity hash;
- result identity hash;
- durable answer/citation result.

At the same time, trace references and measured latency changed as expected. The replay comparator therefore reported:

- `changed_dimensions: []`;
- `execution_identity_match: true`;
- `result_identity_match: true`;
- `telemetry_changed: true`;
- `same_logical_query: true`;
- `same_corpus_revision: true`;
- `same_pack_scope: true`.

This is the key replay property: ordinary timing/run-reference variance does not masquerade as a semantic execution change.

### Controlled service/policy change

For every query, the third execution changed only controlled execution identity inputs:

- route changed from `d021-answer-baseline-v1` to `workstream-f-service-version-probe`;
- retriever implementation version changed from `answer-reliability-baseline-v1` to `query-receipt-replay-probe-v2`;
- corpus revisions, pack scope, projection, underlying retrieval algorithm, deterministic resolvers, and model answer semantics remained fixed.

The receipt comparison correctly reported:

- `execution_identity_match: false`;
- `result_identity_match: true`;
- `same_logical_query: true`;
- `same_corpus_revision: true`;
- `same_pack_scope: true`;
- changed dimensions including `policy` and `services`;
- semantic durable result stability for all six cases.

This proves the receipt can expose a retriever/policy implementation-identity change without incorrectly reporting corpus drift or result drift.

### Deterministic authority/resolver trace

Every execution recorded both structural resolver identities:

- `fossil-untrusted-context-v1`;
- `fossil-lineage-context-v1`.

The receipt includes their stable-ID effects and the final model-bound context IDs. This preserves the Workstream-B/C authority model rather than asking provider/model telemetry to reconstruct it after the fact.

The six answer cases remained correct across all 18 executions. In particular, the Workstream-B stale-lineage regression remained governed by durable lifecycle/lineage resolution rather than top-k alone.

## What the proof does not establish

This proof is intentionally bounded:

- the deterministic baseline does not establish that hosted/frontier/OSS providers are deterministic;
- exact historical provider/model replay can become impossible if a provider removes or silently changes an implementation, even though the receipt still identifies what was requested and what actually ran;
- key-name credential filtering is not a general-purpose DLP or privacy scanner;
- compact receipts intentionally omit verbose provider telemetry, so detailed debugging may still require the referenced external trace while that trace is retained;
- trace/run references can outlive or outlast the referenced telemetry store unless retention is managed separately;
- provider costs may be estimates rather than invoice-grade accounting when only estimated per-call metadata is available;
- floating-point scores, provider implementations, hardware/runtime changes, or nondeterministic generation can change result identity on a future replay;
- JSON hashes provide identity/integrity cues inside this contract but do not by themselves provide trusted signing, timestamping, or globally durable receipt storage;
- future Cortex/multi-worker execution may need child invocation IDs and causal parent/worker links rather than flattening every worker into one service record;
- a receipt records what an execution did; it does not make retrieval rank, reranker score, model confidence, or agent consensus into evidence;
- a receipt cannot authorize knowledge mutation and must not bypass proposal-before-commit or deterministic validation/policy gates.

## D021 / authority conclusion

D021 remains unchanged.

The receipt makes retriever/reranker/model/projection execution choices inspectable and replay-comparable, but authority remains with immutable evidence, stable pack/corpus identity, durable lifecycle/lineage, exact citations, context-security boundaries, and deterministic commit policy.

Workstream F is complete for the committed deterministic baseline once PR #64 lands with this proof. The receipt is now suitable as the observability substrate for Workstream D / Issue #47 model/retriever/reranker comparisons without granting those services truth authority.
