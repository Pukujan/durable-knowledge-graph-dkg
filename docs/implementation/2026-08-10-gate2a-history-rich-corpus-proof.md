# Gate 2A History-Rich Real Corpus Proof

Date: 2026-08-10  
Gate: 2A — representative corpus fixtures + gold/adversarial benchmark set  
Control issue: #33  
Child issue: #34  
Core PR: #42

## Exit corpus

The history-rich benchmark case set is `benchmarks/gate2/real-corpus-history-v2.json`.

It pins exactly:

- `Pukujan/fossil-common@d583005dce06dbb499c3c0de5c22b899655eb8d2`
- `Pukujan/fossil-ai-systems@cf7cf4087bde543cb247a978de2a7252b1b8e4de`

The AI history corpus was validated before merge by execution-only core PR #41 / workflow run `31359243095`, job `93364666635`:

- core suite: **69 passed in 0.86s**
- combined corpus audit: **5 artifacts, 5 source snapshots, 39 durable events, 35 exact citations, 17 claims, 4 relations**
- lifecycle replay assertions: **PASS**
  - former SQLite-canonical claim -> `superseded`
  - dependent SQLite-prototype claim -> derived `stale_pending_review`
  - replacement durable architecture -> `supported`
  - graph-canonical alternative -> `rejected`
  - operational Graphiti claim -> `supported`
  - `SUPERSEDES` and `CONTRADICTS` relations -> active
  - reconstructed conversation-recovery claims -> supported

The recovery checkpoint is explicitly preserved as reconstructed/local evidence and never promoted to verbatim chat evidence.

## Gold/adversarial set

The case set contains **21 retrieval cases** across exactly the ten Gate 2A target families:

1. exact factual lookup;
2. source/citation recovery;
3. decision/lineage questions;
4. current vs historical conclusions;
5. contradiction/disagreement retrieval;
6. stale/superseded assumption detection;
7. cross-pack/isolation cases;
8. obscure/deep-evidence recovery;
9. conversation-lineage provenance boundaries;
10. insufficient-evidence / false-premise negatives.

Each cited case declares its exact `fossil.citation.v1` object and the corresponding `gold.source_snapshot_ids`; the case-set loader rejects undeclared citation snapshots. The original 9-case seed set remains unchanged so the history-rich v2 set does not silently rewrite the earlier baseline.

Contract CI after correcting the explicit citation-to-source declaration was workflow run `31359703063`, job `93365967114`: **72 passed in 1.08s**.

## Control benchmark on exact pinned commits

The existing Gate 1 BM25 and signed-token-hash embedding implementations remain controls, not production winners. A temporary PR-only CI step checked out the exact pinned pack commits and ran the unchanged `fossil.benchmark.v1` harness at `k=5`.

Detailed proof run:

- workflow run `31359792919`
- job `93366244786`
- core suite: **72 passed in 0.76s**
- case count: **21**

### BM25 control

Benchmark ID: `bench_278e133eb6997bd34570e73f`

- hit rate: **0.9523809524**
- mean recall@5: **0.9523809524**
- MRR: **0.8174603175**
- mean latency: **2.628 ms**
- p95 latency: **3.726 ms**
- estimated cost: **$0.00**
- category failure rate:
  - `current-vs-historical`: **0.5**
  - every other represented category: **0.0**

Important observations:

- `current_architecture_after_reconsideration` is a full miss: the top five are the stale SQLite dependent, rejected graph-canonical alternative, SQLite dependency relation, unrecoverable-chat claim, and graph contradiction relation. The supported current architecture is absent.
- `former_sqlite_canonical_history` is found at rank 2.
- `sqlite_supersession_lineage` is found at rank 3.
- `sqlite_dependent_staleness` is found at rank 2.
- the three-target `historical_current_supersession_bundle` achieves recall 1.0, but the first relevant result is rank 3.

### Hash-embedding control

Benchmark ID: `bench_44825ea85b3be17adf101de5`

- hit rate: **0.9523809524**
- mean recall@5: **0.9206349206**
- MRR: **0.8373015873**
- mean latency: **0.928 ms**
- p95 latency: **1.093 ms**
- estimated cost: **$0.00**
- category failure rate:
  - `current-vs-historical`: **0.5**
  - every other represented category: **0.0**

Important observations:

- `current_architecture_after_reconsideration` is also a full miss; historical/rejected objects dominate the top five.
- `former_sqlite_canonical_history` is found at rank 3.
- `sqlite_supersession_lineage` is found at rank 4.
- `false_premise_quote_missing_chat` retrieves both required provenance-boundary claims with recall 1.0.
- the three-target `historical_current_supersession_bundle` retrieves only the `SUPERSEDES` relation: recall **0.3333333333**. The former and current conclusion claims are both absent from the top five.

## Interpretation

Gate 2A is now meaningfully harder than the 9-case seed. The controls still perform well on literal lookup, citation recovery, disagreement, staleness, isolation, deep evidence, conversation provenance, and insufficient-evidence negatives. They fail where the corpus requires **temporal/current-state discrimination across closely related historical objects**.

That failure is useful evidence, not a benchmark defect. The durable corpus intentionally preserves stale, superseded, and rejected alternatives, so a production retrieval/context policy must combine semantic relevance with lifecycle/lineage awareness rather than merely retrieving lexically or vector-similar history.

In particular, Gate 2B should test serious candidates that can improve:

- current-state retrieval without erasing historical accessibility;
- supersession-aware ranking;
- relation/claim bundle recovery for lineage questions;
- multi-target recall;
- citation-preserving context construction;
- cross-pack correctness;
- latency/cost tradeoffs under the existing benchmark contract.

The temporary external checkout/benchmark step was removed after the proof. The landing branch retains only the versioned case set, contract tests, and this proof document.

## Gate 2A conclusion

The #34 corpus/case-set exit criteria are satisfied by a real, versioned corpus with exact source/citation provenance, all required scenario families, adversarial provenance cases, real historical lifecycle transitions, and measured control weaknesses. No production retrieval winner is selected here; selection belongs to Gate 2B/#35 and later comparison/policy issues.
