# Current Handoff

**Date:** 2026-08-14  
**Project:** **FOSSIL — Fault-tolerant Open Semantic Store for Intellectual Lineage**  
**Repository:** `Pukujan/fossil-core`  
**Current architecture authority:** Issue #86  
**Current execution queue / claim ledger:** Issue #94  
**Current focused FOSSIL campaign:** Issue #116

## Current status

The active cross-project architecture is:

> **Cortex owns execution. FOSSIL owns durable knowledge/evidence. GitHub owns coordination/review. LiteLLM/CKFF owns provider/model/route factual transport. Infrastructure is replaceable.**

The central invariant remains:

> **Compute may disappear; truth must not.**

This handoff is intentionally subordinate to live #86/#94 state. Re-fetch both before any write, claim, rebase, merge, deployment, or acceptance conclusion.

## Read first

For a fresh autonomous session, read in this order:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. Issue #86 — current architecture authority
4. latest Issue #94 comments — current queue, claims, and closeouts
5. this file
6. Issue #116 — current visible FOSSIL SDD/TDD campaign
7. `docs/PROJECT_STATE.md`
8. `docs/DECISION_LOG.md`
9. the focused issue/PR for the currently eligible task

## Completed dependencies — do not reopen without regression evidence

### Cortex V5

- Cortex V5 is the active execution runtime.
- Published/accepted baseline: `31fde7508b8e1caddfe7f9b79dc5719c1a0df79f`.
- `V5-ACCEPTANCE` received **HUMAN PASS / CLOSED COMPLETED** on 2026-08-14.
- Mechanical acceptance evidence recorded in #94: public HumanEval/0 through the V5 HTTP API, executable verification `20/20`, `attempt_count=1`, plus local, Gravebuster HTTP 200, and Langfuse HTTP 207 observation.
- Cortex V4 is preserved/frozen historical implementation evidence. It is not current runtime authority.
- `CORTEX-02` secretless GitHub Actions WorkOrder wiring is now unblocked on V5, but it is a separate integration item. Its existence does not mean V5 acceptance is incomplete.

### LiteLLM / CKFF

- Production gateway false-success/routing repairs are merged and the repair tracker is **CLOSED COMPLETED**.
- Railway `litellm` production was reconciled healthy on 2026-08-14: liveliness 200, readiness 200 with database connected, Postgres online.
- Prior failed LIVE_STAGING/verifier attempts remain historical failures; do not retroactively call them `STAGING_GREEN`.
- Formal automated live-inference semantic probing is optional follow-up evidence unless a future gate makes it mandatory again.
- `2xx + empty/malformed/zero-usable-output` remains failure, never semantic success.
- No production authority or sensitive-data authorization is created by the health closeout.

### Trusted local execution

- Exact-SHA disposable broker path, Luna/Terra policy, fencing/cancellation, independent checks, sanitized receipts, low-privilege worker, and separate privileged verifier are complete.
- Issue #96 is closed completed.
- The local PC remains a replaceable trusted execution/credential bridge only where local-only access is genuinely required; it is not semantic authority.

## Current FOSSIL baseline

At the point this documentation branch was created:

- `main` = `27764c4ab20c196ee0bc76a0d020fc961a385c4e`.
- PR #114 was owner-merged into that baseline after the Graphiti dependency/import repair and fan-in verification.
- PR #115 was rebased/hardened at `c4432f577e6182efd4126c3bbd1171a1fb58cbbd`.
- Clean declared `[test,graphiti]` install, `pip check`, Graphiti import, receipt tests `63/63`, focused verification `91/91`, full pytest `262/262`, and `git diff --check` passed independently for #115.
- Fresh hosted Graphiti run `31850284986` nevertheless failed because the live smoke produced zero entities. This is a **new semantic live-integration failure**, not the inherited missing-`httpx` dependency issue.
- `FOSSIL-07` therefore closed BLOCKED rather than weakening acceptance; closeout comment ID `5299204005`.
- `FOSSIL-07A` is the currently claimed bounded repeatability/root-cause investigation on #115. It must distinguish reproducible failure from nondeterministic live-model/smoke behavior without accepting “rerun until green.”
- PR #115 is not merged from this state.
- #87 secretless/local-fixture work remains NOT_READY until the FOSSIL baseline permits it.

**Do not use this paragraph as a live queue.** Re-fetch #94 because Terra may have moved `FOSSIL-07A` since this handoff was written.

## Current FOSSIL campaign contract

Issue #116 is the visible implementation/verification spec. It is **not** architecture authority and does not replace #94 task identities.

Current campaign intent:

1. establish exact live state before mutation;
2. repair/verify the currently open FOSSIL branches without weakening acceptance;
3. require failed-first evidence and exact-head hosted verification where applicable;
4. prove integration on the actual merge baseline;
5. only then continue into the eligible secretless/local-fixture portion of #87.

No production deployment, secret access, automatic merge, or automatic issue closure is authorized by #116.

## Roles

### Terra — orchestrator + independent verifier

Terra owns live-state inventory, phase ordering, ambiguous root-cause localization, bounded briefs to Luna, exact-diff review, clean independent verification, and mechanical PASS / FAILED / BLOCKED decisions.

Terra does not normally become the implementation author simply because a patch is convenient.

### Luna — bounded executor

Luna owns failed-first tests/probes, the smallest bounded implementation, targeted/full regression, clean commits, and exact implementation evidence. Luna cannot self-approve completion.

### Concurrency

- one mutating FOSSIL lane at a time unless #94 explicitly declares safe parallelism;
- read-only Terra analysis may overlap Luna implementation;
- never edit the same branch/files concurrently;
- preserve existing #94 task identities.

## Engineering policy

- SDD always.
- TDD for deterministic behavior where practical.
- Integration/wiring tests where there is actual wiring.
- E2E for important real flows.
- Clean independent verification after implementation.
- Exact-head hosted CI where the PR has hosted acceptance.
- Fault injection for recovery/retry infrastructure.
- Hidden holdouts for autonomous AI/model evaluation.
- Selective mutation testing on small critical validators/gates/security/recovery logic.
- Regression test for every discovered bug.

Shorthand:

> **RED -> GREEN -> REGRESSION -> CLEAN VERIFY -> HOSTED exact-head evidence.**

Never delete, skip, xfail, loosen, suppress, or narrow a semantic gate merely to obtain green.

## Access / authority boundaries

- Ordinary PR CI remains secretless.
- Production promotion requires separate explicit human authorization.
- Role names do not widen access class.
- LiteLLM/CKFF transport health does not decide FOSSIL truth.
- Cortex execution success does not decide FOSSIL truth.
- GitHub Actions artifacts/caches are not canonical FOSSIL truth.
- Retrieval rank, reranker score, model confidence, and multi-model agreement do not create evidence authority.
- FOSSIL durable evidence/events, stable IDs, provenance, lifecycle, lineage, and accepted contracts remain semantic authority.

## Claim protocol

Before mutating work, use Issue #94:

```text
CLAIM task=<TASK_ID>
agent=<unique-agent-id>
mode=<LOCAL_CODEX|CLOUD_CODEX|CHATGPT|ACTIONS>
lease_until=<ISO-8601 UTC>
repo=<repo>
starting_ref=<branch/SHA/PR>
```

Immediately re-fetch #94. Earliest valid unexpired claim wins. Close with exact `DONE`, `BLOCKED`, or `RELEASE` evidence as required by the live ledger/task contract.

## Do not do these things

- Do not reopen Cortex V4 as runtime authority.
- Do not rerun the completed LiteLLM repair campaign absent actual new regression evidence.
- Do not merge #115 because local tests are green while the exact-head hosted semantic gate is unresolved.
- Do not classify a flaky live gate as PASS by retrying until one attempt happens to succeed.
- Do not weaken Graphiti/entity acceptance to hide model/smoke nondeterminism.
- Do not begin #87 because it is attractive; wait until the current baseline gate is truly open.
- Do not select R2 vs S3 from local-fixture results.
- Do not authorize production from agent/task text.
- Do not disclose or reverse-engineer an independent hidden holdout/mutation oracle.

## Immediate fresh-agent behavior

1. Read #86 and live #94.
2. Confirm current exact FOSSIL main/PR heads and hosted conclusions.
3. Confirm whether `FOSSIL-07A` is still active, completed, released, or blocked.
4. Follow the next eligible #94 task and the visible SDD/TDD in #116/focused issue.
5. Claim before mutation and re-fetch the ledger.
6. Work on an isolated branch/worktree.
7. Test mechanically without weakening acceptance.
8. Post exact closeout evidence.
9. Re-read #94 before taking the next item.

If no eligible task exists, stop with explicit idle/BLOCKED evidence rather than inventing work.
