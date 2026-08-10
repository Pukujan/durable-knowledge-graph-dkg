# Gate 2 Real-Corpus Seed Baseline Proof

Date: 2026-08-10  
Gate: 2A — representative corpus fixtures + gold/adversarial benchmark set  
Control issue: #33  
Child issue: #34  
PR: #40

## Purpose

This checkpoint proves that the existing Gate 1 retrieval controls can run against real, durable FOSSIL pack material rather than Python-only synthetic documents. It is intentionally a **seed baseline**, not the Gate 2A exit set and not a production retriever selection.

## Pinned corpus

The benchmark case set `benchmarks/gate2/real-corpus-seed-v1.json` pins exactly:

- `Pukujan/fossil-common@d583005dce06dbb499c3c0de5c22b899655eb8d2`
  - stable pack ID `pack_269099f7b2ba43b7a99b9427d64092de`
- `Pukujan/fossil-ai-systems@fd64992d4011eb55609396f6b8b194a8c679b4bd`
  - stable pack ID `pack_f024177f89a5442db84171c3dd7f58e5`
  - required dependency/read mount on common remains unchanged

The reusable pack validator previously audited these corpus objects together as:

- 3 immutable source artifacts
- 3 source snapshots
- 15 durable events
- 14 exact `fossil.citation.v1` references
- 7 claims
- 1 active cross-pack relation

That exact staged audit is recorded in workflow run `31357578598`, rerun job `93360712276`. The validator itself landed in PR #39 as `c029322e85ebca1afccbd956613c4973606a57a4`.

## Retrieval projection

`src/dkg/pack_corpus.py` builds a rebuildable retrieval-document projection from validated durable pack roots.

For claims it preserves:

- durable claim ID as retrieval document ID;
- owning stable pack ID;
- claim text from the durable `claim.proposed` event;
- current lifecycle state and full state history;
- proposed event ID;
- evidence/source-snapshot references;
- exact citation metadata when present.

For relations it preserves:

- durable relation ID as retrieval document ID;
- relation type, source and target durable refs;
- current relation state/history;
- owning pack ID;
- readable endpoint claim text as rebuildable search text.

No graph-native UUID, vector ID, or search-index ID becomes canonical identity.

## Seed case set

The first case set contains 9 retrieval cases. It currently covers:

- source/citation recovery;
- evidence/model-authority rules;
- insufficient-evidence behavior;
- false-premise control-vs-winner retrieval;
- destructive projection/rebuild ledger safety;
- deterministic temporal replay ordering;
- cross-pack lineage via the durable `DEPENDS_ON` relation;
- an adversarial false-premise case.

This tranche deliberately does **not** fabricate histories the current pack corpus does not yet contain. The following #34-required families remain open for the next evidence tranche:

- decision/lineage “why did we decide X?” depth beyond the one relation seed;
- current vs historical conclusion;
- contradiction/disagreement retrieval;
- stale/superseded assumption detection;
- conversation-lineage questions;
- broader obscure/deep-evidence recovery;
- expansion from 9 cases into the intended tens-of-cases inspected set.

## Real control run

A temporary PR-only CI step checked out the exact pinned pack commits above and executed:

```text
python scripts/run_gate2_real_retrieval_controls.py \
  --common-root .gate2-packs/common \
  --ai-root .gate2-packs/ai-systems \
  --output-dir .gate2-results
```

Proof run:

- workflow run `31358356461`
- job `93362164913`
- normal core suite: **69 passed in 0.87s**
- retrieval limit: `k=5`
- case count: 9

### BM25 control

Benchmark ID: `bench_d4fd169bbf682820ec816909`

- hit rate: **1.0**
- mean recall@5: **1.0**
- MRR: **1.0**
- mean latency: **0.966 ms**
- p95 latency: **1.748 ms**
- estimated cost: **$0.00**
- failure rate: **0.0 in every represented category**

### Hash-embedding control

Benchmark ID: `bench_2ca30d900ec3f27fbe3882e3`

- hit rate: **1.0**
- mean recall@5: **1.0**
- MRR: **0.9444444444**
- mean latency: **0.570 ms**
- p95 latency: **0.685 ms**
- estimated cost: **$0.00**
- failure rate: **0.0 in every represented category**

## Interpretation

The important result is not that either control “won.” Both controls hit all nine targets at `k=5`, and BM25 ranked every relevant target first while the hash control had one lower-ranked target. On such a small corpus, that is expected and **not sufficiently discriminative for production selection**.

This baseline instead proves the end-to-end path:

1. real versioned pack evidence/events;
2. stable pack/corpus identities;
3. integrity validation and mount enforcement;
4. rebuildable retrieval projection;
5. persistent versioned gold cases with exact target/citation metadata;
6. unchanged `fossil.benchmark.v1` execution;
7. comparable control metrics.

Gate 2A should now make the corpus harder and broader before Gate 2B introduces serious production retrieval/context candidates.

## Next work under #34

Seed real historical/disagreement/conversation evidence into the existing stable packs, then extend this case set to the remaining required families and tens-of-cases scale. Preserve the same pack IDs, citation/source semantics, and pack read/write boundaries.
