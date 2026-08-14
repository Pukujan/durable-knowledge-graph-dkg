# Engineering preflight v1

A deliberately small, Git-versioned contract for bounded implementation work. It
is progressive disclosure, not a giant checklist: every substantial task answers
the universal kernel; a classifier adds risk-triggered check packs only for the
facets the task actually touches; everything else is explicitly `not_applicable`
with a rationale.

## Files

- `engineering-constitution-v1.yaml` — the universal kernel and the source-distinction
  rules every task must satisfy.
- `task-trigger-matrix-v1.yaml` — the risk-facet to check-pack mapping and the
  progressive-disclosure principle (trivial edits get the kernel only).
- `preflight-v1.schema.json` — JSON Schema for a preflight receipt (identifiers,
  risk facets + rationale, required checks with `answered`/`not_applicable`,
  sources with freshness/version, unresolved assumptions, planned fault probes,
  required closeout evidence).
- `closeout-v1.schema.json` — JSON Schema for a closeout receipt (what changed,
  contracts changed, tests + exact results, live/staging evidence, observed
  failure, rollback/rebuild proof, new operational dependency, assumptions, and
  lessons as `PROPOSAL`).
- `examples/` — three scope-differentiated receipts that all validate:
  `trivial-edit.json` (kernel only), `new-api.json` (kernel + API/service/
  deployment/observability), `durable-cross-service-write.json` (kernel +
  durability/transaction/idempotency/timeout-retry/partial-failure/compatibility/
  recovery/security/observability).
- `control-plane-contract-v1.json` — FOSSIL/Cortex/LiteLLM ownership and
  correlation spine shared with the assurance workflow.

## How agents and CI use it

The schemas validate offline and never require a live FOSSIL service, a model, or
a secret. JSON Schema handles structure; `scripts/preflight_validate.py` adds the
fail-closed semantic checks, most importantly that a stale or historical source is
never silently treated as current authority.

CLI:

```sh
python scripts/preflight_validate.py contracts/engineering/examples/*.json
```

The Python module `dkg.engineering_preflight` builds a task-scoped packet and
returns `dispatch_status: BLOCKED` when material current-state is unresolved, and
`READY_FOR_BOUNDED_WORKORDER` otherwise. FOSSIL retrieval and the live GitHub read
are supplied as evidence; retrieval rank is never an authority field. The GitHub
reader is intentionally unauthenticated by default.

The canonical schema filenames (`preflight-v1.schema.json`,
`closeout-v1.schema.json`) are stable and are referenced by downstream assurance
workflows; do not rename them.