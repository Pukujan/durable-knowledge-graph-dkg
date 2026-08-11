# Legacy Evaluation Estate — Deduplication and Dataset Integrity Policy

**Date:** 2026-08-10  
**Status:** accepted extraction policy; execution pending  
**Applies to:** legacy SSC eval assets plus any later owner-supplied eval/gold archive

## Purpose

The retired `stupidly-simple-cortex` repository contains useful evaluation assets, but the source estate is noisy, historically layered, and may contain duplicate or near-duplicate cases across Fable capture, objective lanes, imported benchmark slices, live-generation sets, promotion outputs, and historical exports.

Future owner-supplied assets may contain additional rows not present on GitHub.

The extraction process therefore needs a **deduped evaluation view without destroying the raw source estate or laundering conflicting labels.**

## Core rule

**Preserve raw bytes first. Deduplicate into derived views second. Never overwrite source rows merely because two cases appear equivalent.**

A deduped dataset is a projection with provenance, not the canonical raw archive.

## Archive layers

The standalone evaluation estate should expose at least four logical layers:

```text
raw/
  immutable extracted/uploaded source assets

normalized/
  schema-normalized rows with source-preserving IDs

deduped/
  exact/near-duplicate-aware evaluation views

splits/
  train/dev/eval/holdout views after leakage analysis
```

Checkers, frozen tests, rubrics, quarantine records, manifests, and license/source metadata remain versioned beside the data rather than being flattened into one dataset file.

## Source identity

Every raw asset and every normalized row must retain provenance sufficient to reconstruct origin.

At minimum:

- archive asset ID;
- source repository/upload bundle;
- source commit/version when applicable;
- original path/file name;
- file content hash;
- row number or source-native case ID;
- source dataset/benchmark name;
- label authority;
- source/license metadata;
- extraction/import timestamp;
- parent asset ID.

Normalization must mint archive-owned row IDs without discarding source-native IDs.

## Exact deduplication

Exact duplicates should be detected using more than one representation where practical:

1. exact raw-row byte/content hash;
2. canonical JSON hash for structured rows with deterministic key ordering;
3. task-content hash after explicitly versioned normalization of irrelevant formatting.

Exact duplicate detection must not simply delete all but one row. Instead create a duplicate cluster containing:

- canonical cluster ID;
- all member row IDs;
- source origins;
- labels/verdicts;
- checker authorities;
- selected representative row for a particular derived view;
- reason the members are considered exact duplicates.

If exact duplicates carry conflicting labels or materially different authorities, the conflict is preserved and surfaced rather than silently choosing one.

## Near-duplicate / semantic-overlap detection

Near duplicates are more dangerous because they can cause train/eval leakage while looking superficially different.

Detect candidate overlap using separately recorded methods such as:

- normalized text fingerprints;
- n-gram/MinHash or equivalent lexical similarity;
- AST/signature comparison for code tasks;
- normalized tool/function schema + argument task identity;
- reference-answer/task-template signatures;
- embedding similarity as a **candidate clustering signal only**;
- benchmark-native IDs and known mutation/perturbation relationships.

Embedding similarity or model judgment must never by itself authorize deletion or declare two tasks semantically identical.

Near-duplicate clusters require explicit method/version/threshold metadata and should default to `candidate_overlap` until deterministically or manually resolved.

## Mutation families are not ordinary duplicates

Many objective datasets intentionally contain related cases:

- canonical pass case;
- wrong-value mutation;
- missing-required-field mutation;
- adversarial/poisoned variant;
- security mutant;
- perturbation or counterexample;
- positive/negative pair.

These belong to a **case family**, not a duplicate-removal bucket.

Family relationships must be retained because collapsing them can destroy the evaluator's ability to test boundaries and failure detection.

The archive manifest should support fields such as:

- `family_id`;
- `parent_case_id`;
- `variant_type`;
- `mutation_type`;
- `expected_relation_to_parent`.

## Label conflicts

When duplicate/overlapping rows disagree, do not majority-vote them into one truth label.

Record:

- each label;
- each label authority;
- checker/model/human source;
- checker version;
- whether the underlying source/reference changed;
- conflict classification.

Recommended classifications:

- `same_case_same_label_same_authority`;
- `same_case_same_label_different_authority`;
- `same_case_conflicting_label`;
- `source_revision_changed`;
- `checker_revision_changed`;
- `semi_ground_vs_hard_gold`;
- `candidate_vs_verified`;
- `unknown_conflict`.

A lower-authority semi-ground label must not overwrite a reproducible deterministic hard-gold verdict. Conversely, an old `hard_gold` string is not privileged if its checker/provenance cannot be reproduced.

## Hard-gold handling

A deduped hard-gold view may include one representative per exact duplicate cluster only after the cluster's authority has been revalidated.

Preserve separately:

- raw member rows;
- checker outputs;
- reference inputs;
- checker/test versions;
- quarantine/disagreement records.

Hard-gold counts reported after extraction must distinguish:

- raw rows;
- exact-unique rows;
- family-unique tasks;
- revalidated hard-gold rows;
- unresolved/quarantined rows.

This prevents inflated counts from duplicate or mutation-heavy corpora.

## Semi-ground and rubric data

Semi-ground, Fable-provisional, cross-vendor synthetic, rubric-anchor, and judge-calibration rows remain separate classes.

Deduplication may reduce repeated examples for a derived calibration set, but their provisional authority remains unchanged.

Never promote a semi-ground row to hard gold because it is duplicated across several files or several models agreed with it.

## Cross-dataset contamination

The extraction pipeline must scan for overlap across:

- hard-gold lanes;
- imported third-party benchmark slices;
- Fable/generated candidate sets;
- live-generated training gold;
- training exports;
- evaluation sets;
- holdouts;
- any later owner-supplied archive.

The key question is not only “is this row duplicated?” but also **“did an evaluation/holdout case leak into training or prompt/rubric construction?”**

## Train/eval/holdout leakage policy

Before creating final splits:

1. build exact duplicate clusters across the entire estate;
2. build candidate near-duplicate/family clusters;
3. group all members of a case family before splitting;
4. ensure the same case/family does not cross train and evaluation boundaries unless a benchmark explicitly defines that relationship;
5. treat sealed holdout membership as sensitive benchmark metadata;
6. record contamination findings rather than quietly removing evidence of them.

If a historical holdout has already been exposed in the old public/private repository to builders being evaluated, label it `historically_exposed` and do not pretend it remains unseen.

## Deduped view reproducibility

Every deduped dataset release must have a manifest containing:

- raw archive root/version;
- normalization policy version;
- dedupe algorithm/version;
- thresholds/settings;
- cluster IDs and member mappings;
- representative-selection rule;
- excluded/quarantined rows and reasons;
- raw/normalized/deduped row counts;
- family counts;
- leakage findings;
- split policy/version;
- output hashes.

A future release must be reproducible from the raw archive plus the manifest/code.

## Representative selection

Representative selection should be deterministic and policy driven, for example preferring in order:

1. reproducible deterministic-checker row with complete source/license metadata;
2. higher-fidelity source/reference representation;
3. newer explicitly superseding checker/data revision when documented;
4. otherwise a stable lexical/ID ordering.

Selection does not delete the other cluster members.

## Future owner-supplied missing assets

Additional assets supplied later should enter as a **new raw source bundle**, not be manually pasted over the SSC extraction.

For each bundle:

- hash the bundle/files before normalization;
- record source/context supplied by the owner;
- mark whether source commit/history is known or unknown;
- run the same classification/dedup/leakage pipeline;
- merge only at the derived manifest/view layer;
- preserve source-bundle boundaries permanently.

This lets the project recover assets that never reached GitHub without making them indistinguishable from committed historical bytes.

## Relationship to FOSSIL

The raw/deduped evaluation estate is **not normal FOSSIL semantic memory**.

FOSSIL may store:

- archive version/root hash;
- benchmark provenance;
- benchmark run receipts/results;
- decisions derived from evaluated evidence.

Normal semantic RAG should not retrieve arbitrary gold/holdout rows as factual knowledge.

## Relationship to Cortex

Cortex may consume explicit versioned evaluation views when benchmarking agents/models/checkers.

Cortex must not:

- train/evaluate on a hidden holdout in the same run path;
- infer `hard_gold` from filename alone;
- use dedupe similarity score as label authority;
- silently mix provisional and deterministic labels;
- mutate the raw estate during evaluation.

## Minimum acceptance tests for the extractor

Before the standalone estate is trusted:

- exact duplicate test with stable cluster IDs;
- conflicting-label duplicate test;
- mutation-family preservation test;
- train/eval leakage detection test;
- holdout exposure flag test;
- empty/stale historical manifest entry test;
- source-bundle separation test;
- reproducible output-root hash test;
- hard-gold downgrade test when checker/provenance is missing;
- round-trip row provenance test from deduped representative back to every raw source member.

## Non-goal

The purpose of deduplication is dataset integrity, not maximizing a headline row count. A smaller, traceable, leakage-aware evaluation set is preferable to a larger set whose duplicates and authority cannot be explained.
