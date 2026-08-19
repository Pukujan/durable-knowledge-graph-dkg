# Hidden Acceptance Public Interface

Status: Phase 3 public foundation for #176. This document defines only the non-sensitive boundary between FOSSIL's public property catalog and a separately approved sealed holdout executor. It does not select, provision, or expose a private suite location, credential, access mechanism, or execution service.

## Boundary

Public FOSSIL source may define:

- which active public `FOSSIL-PROP-*` properties require hidden acceptance;
- a versioned, location-free manifest of logical suite IDs and public property coverage;
- a versioned aggregate receipt schema;
- deterministic validation of those public contracts;
- safe aggregate result counts and coarse failure classes.

Public FOSSIL source must not contain or require:

- sealed/adversarial case contents, identifiers, or counts;
- exact private oracle expectations;
- credentials, tokens, secret references, or secret-bearing configuration;
- a private bucket, repository, path, endpoint, runner, executor, or other placement/access mechanism;
- free-form notes, execution references, or failure payloads that could reconstruct private cases or leak placement.

The private placement/access decision remains a separately approved least-privilege concern. These Phase 3 public contracts do not invent it.

## Public suite manifest

Canonical public manifest schema and instance:

- `contracts/holdout/public-suite-manifest-v1.schema.json`
- `contracts/holdout/fossil-holdout-suites-v1.json`

Manifest version: `fossil.hidden-acceptance-manifest.v1`.

The manifest is only a location-free public registry. Each suite has a logical `suite_id`, active hidden-acceptance property IDs, coarse priority, and public lifecycle status. The initial entries remain `planned`; this does not claim that a private suite, executor, placement, credential, or access mechanism already exists.

The manifest intentionally omits suite size, case identifiers, case contents, private oracle details, execution references, and placement/access fields. Its receipt schema version is mechanically cross-checked against the aggregate receipt contract.

## Receipt contract

Canonical public schema:

`contracts/holdout/aggregate-receipt-v1.schema.json`

Schema version:

`fossil.hidden-acceptance-aggregate.v1`

A receipt names a public logical `suite_id`, exact public software commit, one or more public property IDs, a result (`PASS`, `FAIL`, or `BLOCKED`), aggregate case counts, and enumerated aggregate failure classes. Disclosure flags are required and fixed to `false`.

The public validator additionally requires every referenced property to be active in the property catalog with `hidden_acceptance_required: true`, enforces count/result consistency, rejects duplicate failure classes, and rejects unclassified failures.

Validator:

`python scripts/check_holdout_aggregate_receipt.py <receipt.json>`

## Result semantics

`PASS` means at least one sealed case was evaluated, all evaluated cases passed, and the aggregate failure count is zero. It is not evidence about any property outside `property_ids`.

`FAIL` means at least one sealed case failed. The receipt may expose only counts grouped into the schema's coarse public failure classes; it must not expose case-level material.

`BLOCKED` means no sealed cases were evaluated and a safe public blocker class explains why. A blocked receipt is never success and cannot contain case failure classes.

## Security and authority

The public manifest and aggregate receipt are operational assurance metadata, not new sources of semantic authority. Architecture and accepted FOSSIL property/contracts remain authoritative. A planned manifest entry or green receipt cannot weaken deterministic public oracles, mutation gates, live integration gates, or any other required acceptance surface.

The schemas intentionally use `additionalProperties: false` and have no free-form notes or execution-reference fields. This makes accidental insertion of case IDs, prompts, exact expected answers, private locations, credential references, or arbitrary text fail closed at the public boundary.

## Phase separation

This foundation is intentionally independent from mutation testing, TLA+, and Lean. It adds no production runtime behavior and does not authorize promotion work while #111 remains unresolved.

A future private executor may consume these public contracts only after its placement/access mechanism is separately approved. That executor should emit the aggregate receipt without copying sealed suite material into this repository, GitHub issue comments, PR discussions, logs, or public artifacts.
