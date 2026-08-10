# Post-Gate-2 Evolving-Corpus / Temporal Benchmark Proof

**Date:** 2026-08-10  
**Campaign:** Issue #48 — production RAG hardening  
**Workstream:** A — evolving-corpus / temporal benchmark  
**Status:** PASS

## Scope

This proof exercises FOSSIL's real durable corpus through historical cutoffs instead of evaluating only a frozen final snapshot.

The benchmark rebuilds a retrieval projection from durable events at each phase, then checks lifecycle state and retrieval behavior. Retrieval rank is never allowed to become truth authority; durable lifecycle/lineage state remains authoritative under D021.

The baseline intentionally uses dependency-free BM25 plus the existing lifecycle-intent reranker. Hosted embedding/reranker/model comparisons remain a separate #47 / Workstream D concern.

## Exact corpus inputs

- `Pukujan/fossil-common@d583005dce06dbb499c3c0de5c22b899655eb8d2`
- `Pukujan/fossil-ai-systems@84accd2ee895663990e82ca5b79b592cb503db24`

The runner verifies these Git heads before execution.

## Durable transition under test

The benchmark replays the real architecture-history sequence already present in the AI-systems pack:

- former SQLite canonical premise: `clm_643b698b7e9e6aee6a16c48c`;
- SQLite-dependent prototype claim: `clm_a047d79b8604fadbd44efdf4`;
- accepted durable-core claim: `clm_7f5c691c564c30e1b61f8dc0`;
- active dependency relation: `rel_0996c7d4b845cf3a3fc6bdf8`;
- active supersession relation: `rel_e0102ade0b5fad5cc2668ccd`.

The durable history records the SQLite premise as supported before the replacement architecture arrives. The accepted durable-core claim is later supported, the SQLite premise is explicitly superseded, and the active dependent claim becomes `stale_pending_review` through lifecycle replay.

## Execution proof

Execution-only core PR #55 was closed without merge after the proof.

Workflow run `31431113829`, job `93594491275`:

- core suite: **88 passed in 0.84s**;
- temporal benchmark ID: `post-gate2-evolving-corpus-v1`;
- phase count: **3**;
- overall result: **PASS**.

### Phase 1 — SQLite premise current

Cutoff: `2026-08-10T05:26:04Z`

- projected documents: **11**;
- projection rebuild: **25.28 ms** on this runner;
- SQLite premise: `supported`;
- SQLite-dependent prototype: `supported`;
- dependency relation: `active`;
- current SQLite query: relevant claim rank **1**, recall@5 **1.0**.

### Phase 2 — durable core after supersession

Cutoff: `2026-08-10T05:26:08Z`

- projected documents: **13**;
- projection rebuild: **23.77 ms**;
- SQLite premise: `superseded`;
- SQLite-dependent prototype: `stale_pending_review`;
- accepted durable-core claim: `supported`;
- dependency relation: `active`;
- supersession relation: `active`;
- current durable-core query: relevant claim rank **1**, recall@5 **1.0**;
- historical SQLite query: relevant claim rank **1**, recall@5 **1.0**;
- no stale/superseded result appeared ahead of the current relevant result.

The phase transition added two projected objects and correctly changed the old premise and its dependent claim without deleting history.

### Phase 3 — later corpus growth

Cutoff: latest landed corpus

- projected documents: **27**;
- projection rebuild: **23.68 ms**;
- document count increased by **14** after later history/research ingestion;
- SQLite premise remained `superseded`;
- dependent prototype remained `stale_pending_review`;
- accepted durable-core claim remained `supported`;
- the ingested production-RAG research claim `clm_b9cec2a2d1753db24f59ff1309d31656` is `supported`;
- current durable-core query remained rank **1**, recall@5 **1.0**;
- historical SQLite query remained rank **1**, recall@5 **1.0**;
- repeated-query stability reported full recall with no current-state leakage.

## Update stability / cost observations

The benchmark records rebuild and query latency for every evolving-corpus phase rather than reporting frozen-corpus retrieval alone.

On this GitHub runner:

- projection rebuild stayed approximately **23.68–25.28 ms** across 11–27 projected documents;
- the current durable-core query measured about **0.94 ms** at 13 documents and **2.66 ms** at 27 documents;
- the historical SQLite query measured about **0.67 ms** at 13 documents and **2.04 ms** at 27 documents;
- correctness remained stable while the corpus more than doubled from the post-supersession phase.

These timings are baseline observations from one CI runner, not provider-selection evidence and not a reason to revise D021. Future hosted retrieval/reranker bakeoffs should use the same versioned corpus and matched measurement contract.

## Contract landed by PR #54

- historical/as-of projection support in `dkg.pack_corpus`;
- reusable `dkg.temporal_benchmark` phased runner;
- versioned plan `benchmarks/post-gate2/evolving-corpus-temporal-v1.json`;
- CLI `scripts/run_post_gate2_temporal_benchmark.py` with exact Git pin verification;
- deterministic unit tests for lifecycle transitions, current/history retrieval, dependent staleness, and later-corpus stability.

## Conclusion

Workstream A's initial exit requirements are satisfied for the real pinned FOSSIL corpus:

1. the benchmark executes a knowledge transition through time;
2. current-state correctness and historical reconstruction are both verified;
3. corpus-growth stability and baseline rebuild/query cost are measured;
4. D021 lifecycle/lineage authority is preserved.

This does **not** prove hosted embedding/reranker superiority, final-answer reliability, poisoning resistance, adaptive routing, or multi-user security readiness. Those remain later Issue #48 workstreams.
