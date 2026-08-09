# Gate 1 Live Graphiti + Neo4j Proof

Date: 2026-08-09
Issue: #4 — Graphiti + Neo4j projection adapter and projection queue

This checkpoint records the first real end-to-end projection proof for FOSSIL. It is durable project evidence, not a claim based on mocks.

## Result

**PASS.** A schema-valid FOSSIL durable event existed on disk before projection, was materialized by Graphiti 0.29.3 into a real Neo4j 5.26.29 graph under the stable pack namespace, and an idempotent replay did not create a duplicate episode.

The successful proof ran in the repository's ordinary trusted GitHub Actions CI workflow on disposable execution-only PR #17:

- workflow: `DKG contract tests`
- run number: 70
- workflow run ID: `31338875226`
- job ID: `93309155019`
- CI merge SHA used for the proof: `960dc1c9b9b12ac6ed8763c9f68932da925aab29`
- final test result: `19 passed in 715.45s`

PR #17 was deliberately an execution harness and is not intended to be merged.

## Runtime/build manifest

```json
{
  "graphiti_version": "0.29.3",
  "neo4j_version": "5.26.29",
  "llm_provider": "ollama-openai-compatible",
  "llm_base_url": "http://127.0.0.1:11434/v1",
  "model_id": "deepseek-r1:7b",
  "small_model_id": "deepseek-r1:7b",
  "embedding_model_id": "nomic-embed-text",
  "embedding_dim": 768,
  "structured_output_mode": "json_schema",
  "ontology_version": "1.0.0",
  "software_commit": "960dc1c9b9b12ac6ed8763c9f68932da925aab29"
}
```

## Durable-first evidence

Accepted event:

`evt_27769393996d2827172f6abc0aa086dc`

Stable pack / Graphiti group:

`pack_269099f7b2ba43b7a99b9427d64092de`

The proof asserted that the immutable event file existed and was readable from `DurableEventStore` **before** Graphiti projection began. The graph therefore was not the only copy of the knowledge being tested.

## Real graph observation

After the first projection:

- projection receipt: `applied`
- matching real `Episodic` nodes: **1**
- episode UUID: `83fb3baf-3d7b-4600-be3a-7774d8dd38c9`
- Graphiti `group_id`: exactly the stable FOSSIL `pack_id`
- projected episode content contained the durable `event_id`
- mentioned entities extracted: **2**
- observed `RELATES_TO` fact edges in this tiny smoke input: **0**

The zero fact-edge count is recorded deliberately. This gate proves durable-first materialization, namespace correctness, live Graphiti/Neo4j operation, and replay idempotency. It is not a relation-extraction quality benchmark.

## Replay/idempotency evidence

The same durable event was submitted to `GraphitiProjectionAdapter` again.

- second receipt: `skipped`
- detail: `already applied`
- matching episode count after retry: **1**
- matching episode UUID after retry: unchanged

The projection ledger's applied record retained the same stable `group_id` and the runtime build manifest.

## Runtime failure that improved the configuration

The first real attempt used Graphiti's OpenAI-compatible client with `structured_output_mode=json_object`.

That run reached the real model/Graphiti extraction path but failed because the local model emitted a top-level field named `Edges` while Graphiti's `ExtractedEdges` contract required `edges`.

Evidence from the failed run:

- workflow run ID: `31338381257`
- job ID: `93307864744`
- durable event had already been committed successfully
- Neo4j and Graphiti were live
- projection receipt was correctly recorded as `failed`
- Pydantic rejected the malformed structured output instead of silently accepting it

The retry changed only the provider's structured-output enforcement to `json_schema`; no FOSSIL correctness assertion was weakened. The same end-to-end proof then passed.

Therefore the reusable local live-smoke configuration now defaults to `json_schema` for this OpenAI-compatible/Ollama path.

## Gate conclusion

Issue #4's real-integration conditions are satisfied:

1. Graphiti calls remain isolated behind `GraphitiProjectionAdapter`.
2. Durable event acceptance precedes graph materialization.
3. Graphiti and Neo4j run against real services rather than fakes.
4. The stable `pack_id` is preserved as the projection `group_id`.
5. Runtime/model/ontology/code versions are captured in the projection build manifest.
6. A real graph episode is observed after projection.
7. Replay is idempotent and does not duplicate the episode.
8. A failed model extraction remained a projection failure rather than corrupting or deleting canonical durable knowledge.

The next Gate 1 work is Issue #5: destructive rebuild and blue/green migration from the same durable evidence/events.
