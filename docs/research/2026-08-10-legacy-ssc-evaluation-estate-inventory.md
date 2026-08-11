# Legacy SSC Evaluation Estate — Verified Inventory

**Date:** 2026-08-10  
**Source repository:** `Pukujan/stupidly-simple-cortex`  
**Source revision inspected:** `3b6668eff7a1859c37f1aa50c565f0387fdc4ffe`  
**Status:** discovery inventory only; no live dependency and no semantic-truth authority

## Purpose

The legacy `stupidly-simple-cortex` runtime is being retired as a live corpus/memory/ontology authority. Before retirement, verify which evaluation assets are actually committed and worth extracting into a standalone archive.

This document records **observed repository bytes and paths**, not SSC's claims about itself. It exists so future work can extract the useful evaluation estate without mounting or querying SSC at runtime.

## High-level result

A substantial evaluation estate **is committed on GitHub**. It includes:

- checker-decided hard-gold JSONL datasets;
- deterministic objective-lane checkers;
- frozen tests tied to those lanes;
- third-party-derived benchmark slices;
- live/trainable hard-gold sets and some holdout sets;
- semi-truth / provisional judgment datasets;
- rubrics and calibration anchors;
- reusable checker cores and domain resolvers;
- oracle adapters, cross-validation machinery, and health reports;
- promotion/quarantine conventions and results-ledger specs;
- durable artifact indexes pointing to the above.

The estate should be extracted and independently revalidated. It should **not** be treated as FOSSIL knowledge merely because it lived in SSC.

## Verified objective-lane surface

`docs/OBJECTIVE-LANES.md` at the inspected revision is generated and reports **73 objective lanes**. It declares that each lane's verdict path is deterministic and that `judge_in_verdict_path` is `false`.

Examples present in the generated manifest include:

- tool calling — BFCL AST checker;
- coding — subprocess test execution;
- architecture — static import graph/AST;
- authorization bypass — reference policy-engine execution;
- cryptographic misuse — functional/known-answer/property execution;
- CWE patch execution — functional + exploit regression execution;
- datetime correctness — stdlib datetime recomputation;
- GSM-style math — exact numeric answer;
- ledger balances — double-entry arithmetic checker;
- PII redaction — deterministic PII pattern detector;
- prompt-injection trace — trace-invariant checker;
- RAG evaluation — deterministic grounding match;
- SQL correctness and many other structured/executable domains.

Each manifest row names the checker/verdict module, frozen test, label authority, promotion source, and judge-in-verdict-path flag.

## Verified hard-gold bytes

Concrete committed hard-gold files found include, among many others:

- `evals/objective_tool_calling/hard_gold.jsonl`;
- `evals/objective_coding/hard_gold.jsonl`;
- `evals/objective_security/hard_gold.jsonl`;
- `evals/objective_research/hard_gold.jsonl`;
- `evals/objective_architecture/hard_gold.jsonl`;
- `evals/objective_pii_redaction/hard_gold.jsonl`;
- `evals/objective_dockerfile_lint/hard_gold.jsonl`;
- `evals/objective_ledger_balances/hard_gold.jsonl`;
- `evals/objective_secret_detection/hard_gold.jsonl`;
- `evals/objective_number_grounding/hard_gold.jsonl`;
- `evals/objective_tenant_isolation/hard_gold.jsonl`;
- many additional `evals/objective_*/hard_gold.jsonl` lanes listed in `docs/OBJECTIVE-LANES.md`.

The tool-calling hard-gold file was directly inspected and contains rows with fields such as:

- `objective_verdict`;
- `label_authority: bfcl_ast_checker`;
- exact checker path;
- error type/details;
- perturbation type;
- source/case ID;
- `provenance_tier: hard_gold`;
- cross-checker agreement;
- reproducibility metadata including ground-truth hash.

This is materially different from model-judged prose and is worth preserving subject to license/source/reproduction verification.

## Verified third-party-derived objective slices

The legacy durable-artifact index points to and current GitHub bytes confirm at least some third-party-derived hard-gold datasets under `evals/hf_datasets/`.

One directly inspected example:

- `evals/hf_datasets/gsm_plus/hard_gold.jsonl` — contains task IDs, prompts, reference solutions, and reference answers.

The historical artifact index also names additional paths such as HumanEval, CRUXEval, DS1000, MBPP, APPS, BigCodeBench, code contests, and others. **Do not assume every historical count is still correct; verify each file and its license/source metadata during extraction.**

## Verified semi-ground / provisional judgment data

Semi-ground/provisional material also exists and must remain clearly lower-authority.

Directly inspected:

- `evals/fable_capture/prompt_evals_semitruth.jsonl` — rows explicitly label themselves `fable_semi_ground_truth`, `fable_provisional (pending human verification)`, `authority: candidate`, `human_reviewed: false`, and `ground_truth_for_now: false`.

Other paths named by the durable-artifact index include:

- `evals/fable_capture/rubric_evals_semitruth.jsonl`;
- `evals/fable_capture/deep_eval_semitruth.jsonl`;
- `evals/fable_capture/golden_deep_audit.jsonl`.

These are useful for judge calibration, disagreement analysis, rubric design, or future re-labeling. They are **not hard gold** and should not silently become training/evaluation authority.

## Verified rubrics and calibration material

Committed rubric/evaluation-design assets include examples such as:

- `evals/fable_capture/tdd_rubric_spec.md`;
- `evals/fable_capture/handoff_rubric_spec.md`;
- `evals/fable_capture/code_quality_rubric_spec.md`;
- `evals/fable_capture/agentic_task_state_rubric.md`;
- `evals/fable_capture/cybersecurity_rubric_spec.md` and expanded variant;
- `evals/rubrics/rubric_c_layer1.py`;
- `evals/objective_security/rubric_access.json`;
- `evals/objective_rubric_grading/run.py` and `gold.py`;
- `calibration/rubrics/` material;
- `calibration/anchors/` soft-anchor packets and checker-design documents referenced by the durable-artifact index.

Rubrics are methodology/evaluation assets, not semantic truth. Their future executable/current versions belong with the evaluation/harness system; FOSSIL may preserve provenance about them when useful.

## Verified checker/oracle machinery

Committed deterministic/oracle-related machinery includes:

- `evals/oracle_adapter.py`;
- `cortex_core/oracle_crossval.py`;
- `cortex_core/oracle_report.py`;
- `evals/objective_tool_calling/checker.py` and `run_bfcl.py`;
- many `evals/objective_*/checker*.py` modules named by the generated lane manifest;
- frozen tests under `tests/test_objective_*.py`;
- `evals/checker_cores/` reusable deterministic primitives;
- `evals/resolvers/` domain-specific resolvers;
- external oracle adapters under `evals/external/` referenced by the durable-artifact index;
- reports including `evals/reports/ORACLE_HEALTH.md` and strength reports.

The legacy `docs/DURABLE-ARTIFACTS-INDEX.md` describes five reusable checker cores:

- differential execution;
- mutation/seeded-error checking;
- resolver joins/recomputation;
- schema presence;
- lexicon/grammar rules.

These may be valuable code assets, but future use should freeze exact versions and rerun their tests rather than trusting historical reports.

## Verified promotion/training/evidence infrastructure

Committed support material includes:

- `evals/RESULTS-LEDGER-SPEC.md`;
- promotion consolidation/check scripts;
- evidence-bundle checks;
- training export machinery;
- live hard-gold sets referenced by `docs/DURABLE-ARTIFACTS-INDEX.md`;
- promotion/quarantine conventions and manifests;
- stage reports and oracle-health reports.

Some live-gold lanes also reference holdout files. Extraction must decide whether those holdouts remain sealed. A dataset intended to test future builders should not be casually exposed to those builders merely because it is being archived.

## Critical reliability caveat: SSC indexes are stale in places

Do **not** use `evals/FABLE_DURABLE_ARTIFACT_INDEX.md`, README counts, reports, or search-index summaries as the extraction manifest without checking bytes.

Observed example:

- the legacy artifact index reports `evals/hf_datasets/halu_eval/semi_ground.jsonl` with 500 rows;
- direct read of that path on `main` at the inspected revision returned an empty file.

Similarly, `evals/README.md` contains an older build-status statement saying no gold had been produced yet, while later commits clearly contain hard-gold datasets and a 73-lane generated objective manifest.

Therefore the authoritative extraction unit is:

```text
repository commit + exact path + blob hash + actual byte/row count + license/source metadata + checker/test dependency
```

Narrative documents are orientation only.

## Recommended standalone archive structure

Do not make FOSSIL or Cortex depend on the legacy SSC repository at runtime.

Create a standalone content-addressed evaluation estate, for example conceptually:

```text
legacy-eval-estate/
  MANIFEST.jsonl
  hard_gold/
  semi_ground/
  rubrics/
  checkers/
  frozen_tests/
  resolvers/
  manifests/
  quarantine/
  reports/
  source_license/
```

Each manifest row should record at minimum:

- asset ID;
- class (`hard_gold`, `semi_ground`, `rubric`, `checker`, `frozen_test`, `resolver`, `quarantine`, `report`, etc.);
- source repo and exact commit;
- original path;
- content hash;
- byte count and row count where applicable;
- source benchmark/dataset;
- license/redistribution status;
- label authority;
- checker implementation/version;
- required frozen test(s);
- trainable/eval-only/holdout status;
- verification status;
- extraction date;
- notes about missing dependencies or stale historical claims.

## Authority policy after extraction

### Hard-gold candidate

A legacy row may retain a `hard_gold` classification only when the extraction can establish:

- the bytes exist;
- the claimed checker exists;
- the checker/test path is reproducible enough to rerun or independently validate;
- source/license provenance is recorded;
- no judge/model was the sole verdict authority;
- any required reference data is available and hashed.

If any of those fail, downgrade the archive classification rather than preserving the old label by trust.

### Semi-ground / judged material

Keep as provisional/calibration material. Never use it as final correctness authority without a new validation step.

### Reports and research prose

Keep only if useful for historical orientation. Reports do not override the underlying data/checker outputs and should not be ingested into normal FOSSIL semantic memory automatically.

## Relationship to FOSSIL and Cortex

- **FOSSIL:** may store provenance about benchmark assets and durable benchmark results. It should not mount this estate as normal semantic-memory RAG.
- **Cortex:** may use versioned evaluation assets/checkers when evaluating agents/models, but should reference the standalone archive/version rather than the retired SSC runtime.
- **Legacy SSC:** after extraction verification, remains a cold historical source and is not required for live operation.

## Next extraction gate

Before deleting/archiving access to SSC locally:

1. enumerate all relevant files from the exact source revision;
2. compute hashes/actual row counts;
3. resolve license/source metadata;
4. pair hard-gold files with checker + frozen tests + manifests;
5. identify empty/missing/stale-index entries;
6. decide holdout sealing policy;
7. copy verified assets into a standalone archive;
8. run integrity/reproduction smoke tests from the archive without importing SSC runtime code implicitly;
9. record the archive root hash/version;
10. only then declare SSC unnecessary for evaluation recovery.
