# Current Handoff

**Date:** 2026-08-10  
**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Durable substrate:** **DICS — Durable Intellectual Corpus System**  
**Repository:** `Pukujan/fossil-core`  
**Status:** **Milestone 0 / Gate 1 complete. Gate 2 is active under Issue #33; current work is #34 with draft PR #38.**

## Fresh-session transfer record

The detailed Milestone 0 transfer remains:

`docs/handoffs/2026-08-10-chatgpt-session-handoff.md`

That dated handoff is authoritative for completed Gate 1 proof runs, operational quirks, and frozen do-not-change rules. This file is now authoritative for the newer Gate 2 continuation point.

Milestone 0 handoff tip commit: `b87b573c9d7514787c904836b48547a10a45d6bc`.

## Repository family

- `Pukujan/fossil-core` — architecture/contracts/core/projections/benchmark/control plane;
- `Pukujan/fossil-common` — stable pack `pack_269099f7b2ba43b7a99b9427d64092de`;
- `Pukujan/fossil-ai-systems` — stable pack `pack_f024177f89a5442db84171c3dd7f58e5`, depending on common.

Repository/database/graph placement is not knowledge identity. Never mint replacement pack IDs because placement changes.

## Fresh-session order

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. this file
4. `docs/PROJECT_STATE.md`
5. Gate 2 control Issue #33 and active children #34–#37
6. current PRs, especially draft PR #38 while #34 is active
7. `docs/DECISION_LOG.md`
8. `docs/handoffs/2026-08-10-chatgpt-session-handoff.md` for completed Gate 1 detail
9. proof docs under `docs/implementation/`
10. closed Issue #1 and children #2–#10 only when detailed implementation history is useful

The chat UI is source material, not the control plane.

## Architecture that must not be casually changed

Canonical truth is immutable evidence + stable corpus IDs + append-only validated knowledge events + versioned pack/ontology contracts + provenance/history.

Graphiti/Neo4j, lexical/vector indexes, context construction, models, Skills, MCP, and future databases remain replaceable projections/services.

**A graph deletion must never delete irreplaceable intellectual history.**

Additional frozen invariants:

- durable commit precedes projection;
- new/rebuilt physical projection => fresh build-scoped applied ledger;
- rebuild replay order is `(recorded_at, event_id)`;
- migration compares stable FOSSIL semantics, not graph-native UUID equality;
- reconstructed evidence cannot silently become verbatim;
- exact citations bind to immutable observed source bytes/spans where available;
- ordinary intellectual revision remains append-only;
- privacy/legal erasure is exceptional tombstone-before-delete with non-resurrection;
- Skills contain methodology, not canonical truth;
- protocol adapters cannot become the durable knowledge model;
- model consensus is not external evidence;
- small/local model output is candidate-only until evidence/risk policy permits downstream authority.

Do not casually rename the internal `src/dkg` namespace.

## Completed Gate 1 proof stack

- **#4 live Graphiti/Neo4j:** run `31338875226` — Graphiti `0.29.3` + Neo4j `5.26.29`, stable pack namespace, durable-first materialization, projection-failure preservation, idempotent retry.
- **#5 destructive rebuild + blue/green:** run `31339930551` — graph candidate destroyed to zero, rebuilt from durable source using a fresh build-scoped ledger, semantic comparison matched, active switch guarded.
- **#9 conversation lineage:** run `31340924480`, job `93314435997` — immutable source bytes/spans, `verbatim` vs `reconstructed`, opposing/current/historical lineage queries.
- **#8 Agent Skills/API/MCP:** run `31341456769`, job `93315824532` — **39 passed in 0.51s**, protocol-independent `CorpusService`, pack/Skill-gated mutations, no arbitrary graph mutation path.
- **#10 source provenance + redaction:** deterministic run `31345462801`, job `93326450028`; live run `31346791333`, job `93330095684` — tombstone-before-delete, active Graphiti purge, zero-state fresh rebuild/non-resurrection.
- **#7 retrieval/model benchmark contract:** run `31347744797`, job `93332738616` — **56 passed in 0.70s**; versioned cognitive interfaces and benchmark result contract.

The current BM25/hash-embedding/token-overlap stack is a **control**, not a production winner.

## Gate 2 — active campaign

Control: **#33 — Real Corpus + Retrieval/Model Bakeoff**.

Children:

1. **#34** representative real corpus fixtures + versioned gold/adversarial benchmark set;
2. **#35** real retrieval/context adapters behind existing interfaces;
3. **#36** reproducible comparative bakeoff + failure taxonomy;
4. **#37** evidence-based default retrieval/routing policy.

Do not reopen Issues #1–#10 for this work.

### #34 discovery: the pack repositories are scaffolds

Verified `fossil-common` and `fossil-ai-systems` before writing benchmark fixtures.

- `fossil-common` current seed commit `94fd576286ee359f1929b31bbba99e0ca54d4b41` contains the stable pack manifest, contract/policy pointers, empty `artifacts/manifest.jsonl`, and `events/.gitkeep`.
- `fossil-ai-systems` current seed commit `cfd03e08c36f00a5eb25c8de4c1463d06877e015` has the same scaffold-only shape.

Therefore Gate 2A must **seed representative canonical evidence/events into the existing stable packs first**, then derive gold/adversarial cases from those durable objects. Do not fabricate benchmark-only prose and call it real corpus material.

The AI-systems pack may read common + itself and write only itself. The common pack reads/writes itself. Use this real dependency boundary in cross-pack benchmark cases.

### #34 implementation checkpoint: draft PR #38

Branch: `agent/gate2-benchmark-case-set`.

PR: **#38 — Gate 2: persist benchmark case sets**.

Purpose: Gate 1 versioned benchmark results but kept gold cases as Python fixtures. Gate 2 needs a persistent case-set contract so every provider runs against the same pinned corpus and evidence targets.

Current PR contents:

- `schemas/benchmark/case-set-v1.schema.json` — `fossil.benchmark-case-set.v1`;
- `src/dkg/benchmark_cases.py` — schema/semantic loader + conversion into existing benchmark case types;
- `tests/test_benchmark_case_set.py` — contract coverage;
- case-set corpus entries pin exact repository commit SHAs;
- retrieval cases cannot mount packs not pinned by the case set;
- duplicate case IDs are rejected;
- gold metadata stores exact `fossil.citation.v1` citation objects, including byte span and passage hash, plus declared source snapshots;
- citation gold referring to an undeclared snapshot is rejected.

First trusted PR CI run before the citation follow-up:

- run `31356440481`
- job `93356916077`
- **60 passed in 0.69s**

The branch has follow-up citation-contract and continuity-doc commits after that run. **Check the latest PR CI before merging.**

### Next implementation step

After PR #38 is current/green:

1. seed a modest representative evidence set into `fossil-common` and `fossil-ai-systems` through the existing artifact/source/event contracts rather than hand-written ad hoc objects;
2. use immutable `repository_ref` locators and exact source commit SHAs for imported FOSSIL proof/policy material;
3. derive exact citations from source bytes and persist those citation objects in Gate 2 gold cases;
4. include cases for source/citation recovery, lineage, historical/current distinction, disagreement, stale/superseded assumptions, cross-pack boundaries, obscure evidence, conversation lineage, and insufficient evidence;
5. only then proceed to #35 provider competitors.

Good initial source material already inspected in `fossil-core` includes:

- `policies/source-quality-v1.md` for shared/common source methodology;
- `docs/implementation/2026-08-10-retrieval-model-benchmark-contract-proof.md` for provider/control and authority boundaries;
- `docs/implementation/2026-08-09-gate1-rebuild-blue-green-proof.md` for rebuild/ledger/history semantics;
- other Gate 1 lineage/redaction proofs as needed for difficult cases.

Do not assign fake universal quality tiers. Source snapshots preserve independent quality dimensions and exact repository version metadata.

## Gate 2 exit criteria

- representative real corpus fixtures exist using both stable packs;
- versioned gold/adversarial benchmark set exists;
- at least two materially different real retrieval strategies are compared with controls;
- reproducible `fossil.benchmark.v1` outputs record provider/runtime/model/implementation identity;
- quality, latency, memory, estimated cost, and category-specific failures are captured;
- failure taxonomy is documented;
- one default routing/retrieval policy is selected from measured evidence;
- canonical FOSSIL identity/durability does not change merely to suit a benchmark winner;
- `docs/DECISION_LOG.md`, `docs/PROJECT_STATE.md`, and this handoff reflect the Gate 2 result.

## End-of-session rule

After substantial future work:

- update this file;
- update `docs/PROJECT_STATE.md` when gate/work state changes;
- update active GitHub issues;
- commit material benchmark/proof evidence;
- update `docs/DECISION_LOG.md` when an actual architectural/default decision changes;
- preserve prior reasoning rather than rewriting history;
- never rely on the chat UI as the only durable project record.
