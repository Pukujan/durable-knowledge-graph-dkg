# Hidden Acceptance Public Interface

Status: Phase 3 public foundation for #176. This document defines only the non-sensitive boundary between FOSSIL's public property catalog and a separately approved sealed holdout executor. It does not select, provision, or expose a private suite location, credential, access mechanism, or execution service.

## Boundary

Public FOSSIL source may define:

- which active public `FOSSIL-PROP-*` properties require hidden acceptance;
- a versioned aggregate receipt schema;
- deterministic validation of that receipt;
- safe aggregate result counts and coarse failure classes.

Public FOSSIL source must not contain or require:

- sealed/adversarial case contents or identifiers;
- exact private oracle expectations;
- credentials, tokens, secret references, or secret-bearing configuration;
- a private bucket, repository, path, endpoint, runner, or other placement/access mechanism;
- free-form notes, execution references, or failure payloads that could reconstruct private cases or leak placement.

The private placement/access decision remains a separately approved least-privilege concern. This Phase 3 slice does not invent it.

## Receipt contract

Canonical public schema:

`contracts/holdout/aggregate-receipt-v1.schema.json`

Schema version:

`fossil.hidden-acceptance-aggregate.v1`

A receipt names a public logical `suite_id`, exact public software commit, one or more public property IDs, a result (`PASS`, `FAIL`, or `BLOCKED`), aggregate case counts, and enumerated aggregate failure classes. Disclosure flags are required and fixed to `false`.

The public validator additionally requires every referenced property to be active in the property catalog with `hidden_acceptance_required: true`, enforces count/result consistency, and rejects unclassified failures.

Validator:

`python scripts/check_holdout_aggregate_receipt.py <receipt.json>`

## Result semantics

`PASS` means at least one sealed case was evaluated, all evaluated cases passed, and the aggregate failure count is zero. It is not evidence about any property outside `property_ids`.

`FAIL` means at least one sealed case failed. The receipt may expose only counts grouped into the schema's coarse public failure classes; it must not expose case-level material.

`BLOCKED` means no sealed cases were evaluated and a safe public blocker class explains why. A blocked receipt is never success and cannot contain case failure classes.

## Security and authority

The aggregate receipt is operational acceptance evidence, not a new source of semantic authority. Architecture and accepted FOSSIL property/contracts remain authoritative. A green receipt cannot weaken deterministic public oracles, mutation gates, live integration gates, or any other required acceptance surface.

The schema intentionally uses `additionalProperties: false` and has no free-form notes or execution-reference field. This makes accidental insertion of case IDs, prompts, exact expected answers, private locations, credential references, or arbitrary text fail closed at the public boundary.

## Phase separation

This foundation is intentionally independent from mutation testing, TLA+, and Lean. It adds no production runtime behavior and does not authorize promotion work while #111 remains unresolved.

A future private executor may consume this public contract only after its placement/access mechanism is separately approved. That executor should emit the aggregate receipt without copying sealed suite material into this repository, GitHub issue comments, PR discussions, logs, or public artifacts.
