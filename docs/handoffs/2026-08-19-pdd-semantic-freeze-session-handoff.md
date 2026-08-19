# FOSSIL PDD / #111 Session Handoff — 2026-08-19

This is the durable transfer record for the next ChatGPT/Codex/Claude session. The prior chat was intentionally stopped because the session had become too long/stale. Continue from GitHub state, not from assumptions about the old conversation.

## 0. One-line state

**The public Property-Driven Development assurance campaign is substantially landed; the #111 semantic target is now accepted and merged, but its implementation is not complete. The next bounded public implementation slice is #111 Step 1: characterize and add the event-type contract/evidence-policy registry + fail-closed accepted-commit gate. Do not jump directly to Promotion mutation/Lean.**

Verified stop baseline on `main`:

`e14ef747547e86add2d3e819a537c1a8d2b35294` — `[ARCH] Accept issue #111 semantic freeze (#221)`

PR #221 exact head before merge:

`1fccf944d206835fe9054161f1f194a5b484b757`

Exact-head DKG run for #221:

`32265652732` — SUCCESS

The previous implementation claim `FOSSIL-111-STEP1-EVENT-CONTRACT-REGISTRY-20260819` was explicitly **RELEASED** when the user requested this handoff. Characterization only was performed; **no Step 1 repository files were changed and no Step 1 implementation PR was created**.

Do not treat any SHA or lease in this document as a live lock. Re-fetch Issue #94 and current `main` before any write.

---

## 1. Control plane and authority

Repository:

- `Pukujan/fossil-core`

Read these live before changing anything:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. Issue #86 — architecture authority
4. latest comments in Issue #94 — execution queue / claim ledger
5. Issue #111 — epistemic integrity semantic/implementation authority
6. Issue #176 — PDD/formal-assurance campaign
7. `docs/HANDOFF_CURRENT.md`
8. this dated handoff
9. `contracts/properties/fossil-properties-v1.json`
10. `docs/architecture/property-driven-assurance.md`
11. `docs/architecture/2026-08-19-issue-111-semantic-freeze-proposal.md`

The repository and live GitHub issues are authoritative. The prior chat thread is not the control plane.

---

## 2. Coordination protocol — mandatory

Before **any GitHub mutation**:

1. Post a unique `CLAIM` in Issue #94 with task, agent, mode, lease, repo, starting ref, and bounded scope.
2. Immediately re-fetch #94.
3. Earliest valid unexpired non-parallel claim wins.
4. Never write to another agent's active lane/branch/PR.
5. Close work with exact `DONE`, `BLOCKED`, or `RELEASE` evidence.

One active mutating owner per FOSSIL repo lane unless the task explicitly says `parallel_safe=yes`.

The previous session encountered a real claim race on PR #221, released its losing duplicate claim, waited for the winning review-readiness owner to finish, then reclaimed the lane only after the prior owner posted `DONE/RELEASE`. Preserve that behavior.

Before merge, re-check:

- exact PR head SHA;
- exact-head required CI;
- current `main`;
- mergeability;
- changed-file scope;
- reviews;
- unresolved review threads;
- conversation blockers;
- active #94 ownership.

Use SHA-fenced merge (`expected_head_sha`) for bounded assurance/architecture PRs.

---

## 3. #176 PDD campaign — landed state

### Phase 0 / Phase 1

Public property catalog and behavioral property oracles are landed.

Representative merged work includes:

- #177 — property catalog foundation;
- #178 — identity properties;
- #179 — lifecycle properties;
- #180 — pack properties;
- #181 — source/citation properties;
- #182 — filesystem/S3 contract parity properties;
- #183 — rebuild/temporal properties;
- #186 — pack-scoped query reconciliation.

The catalog uses stable `FOSSIL-PROP-*` IDs and keeps hidden acceptance cases outside the public repository.

### Phase 2 — mutation assurance

Completed bounded mutation lanes include:

- #187 lifecycle + pack: `167/180` killed = **92.78%**, 13 survivors, 0 no-test;
- #188 source + citation: `438/471` = **92.99%**, 33 survivors, 0 no-test;
- #198 identity: `5/6` = **83.33%**, one equivalent UTF-8 survivor, 0 no-test;
- #199 query/context security: `441/496` = **88.91%**, 55 survivors, 0 no-test;
- #200 filesystem event store: `207/236` = **87.71%**, 29 survivors, 0 no-test;
- #201 filesystem artifact store: `208/226` = **92.04%**, 18 survivors, 0 no-test;
- #202 architecture boundary checker: `185/195` = **94.87%**, 10 survivors, 0 no-test;
- #203 S3 storage: `526/576` = **91.32%**, 50 reviewed equivalent/non-contract survivors, 0 no-test;
- #204 agent authorization: `100/102` = **98.04%**, 2 message-only survivors, 0 no-test.

These lanes were evidence-backed and did not widen production semantics merely to increase mutation scores.

**Promotion mutation is still not ready.** The accepted #111 freeze explicitly sequences Promotion mutation only after the new promotion law is implemented, including its packset/source-pin prerequisites.

### Phase 3 — hidden-holdout public boundary

Public-only foundation is landed:

- #205 — versioned aggregate hidden-holdout receipt/interface contract;
- #206 — location-free public suite manifest.

The owner later approved the **abstract** least-privilege hidden-holdout mechanism:

- sealed adversarial cases stay off-repo;
- establish non-sensitive content commitments before use;
- execute the exact candidate commit read-only under a separate clean verifier identity;
- ordinary coding agents/general credentials do not receive sealed-suite access;
- return only the existing safe aggregate FOSSIL receipt publicly.

Still unresolved/out-of-band:

- concrete private placement;
- concrete verifier identity/provisioning;
- actual sealed execution and ordinary-agent non-access proof.

Therefore public suite entries remain `planned`; **no private holdout PASS is claimed**. Never commit sealed cases, exact private oracles, credentials, private paths/URLs, or verifier identity into this public repository.

### Phase 4 / Phase 5 / Phase 6 formal assurance

The public formal-assurance foundations are landed:

- DurableStore and ProjectionLifecycle TLA+ models, CI, and catalog traceability;
- Lifecycle and PackAccess Lean kernels, CI, and catalog traceability;
- TLA CI hygiene (#212);
- Lean CI hygiene (#213);
- TLA catalog invariant traceability (#214);
- fail-closed TLA path/symbol validation (#216);
- Lean theorem/toolchain catalog traceability (#217);
- fail-closed Lean theorem-reference validation (#219).

The catalog now mechanically verifies landed TLA refs name real spec symbols and landed Lean refs name concrete theorem declarations. Future bare formal refs remain allowed only while the corresponding file genuinely does not exist.

Identity Lean is optional/lower priority, not a required #176 exit item. Do not invent it solely to keep the queue busy.

---

## 4. #111 semantic freeze — accepted and merged

PR #221 was documentation-only and merged as:

`e14ef747547e86add2d3e819a537c1a8d2b35294`

The semantic acceptance was also recorded directly in Issue #111 because GitHub correctly prevents the repository owner from formally `APPROVE`-reviewing their own PR.

The accepted six-law target is:

### Law 1 — Proposal != accepted durable commit

A proposal can be cheap and syntactically valid without being accepted knowledge. Consequential accepted writes must pass applicable deterministic event/pack/provenance/evidence/ontology gates before durable commit.

### Law 2 — Event-type contracts are explicit and fail closed

Every consequential event type needs a versioned payload contract plus evidence policy. The registry must answer mechanically which payload schema, proposal/accepted eligibility, evidence refs, provenance, ontology constraints, property IDs, and executable oracles apply.

Unknown consequential types may remain proposal-only, but must not silently enter the accepted path.

Existing `dkg.event.v1` envelope compatibility and historical replay must remain intact.

### Law 3 — Ontology definitions own relation endpoint validity

Relation endpoint kinds resolve from the pinned ontology definition. Missing/unresolvable ontology data fails closed for accepted commit rather than falling back to a permissive generic relation.

### Law 4 — Mounted pack sets are exact portable revision sets

Stable `pack_id` remains logical identity. A mounted set additionally pins exact immutable revisions, manifest/content digest, resolved dependency edges, required/optional status, cycle rejection, and dependency-layer validation.

Default layering is `common -> domain -> project` in dependency semantics: project may depend on domain/common; domain may depend on common; no downstream edge or cycle.

Proposed contract name: `dkg.packset-lock.v1`.

### Law 5 — Promotion pins source meaning without mutating source

A new promotion is a new target-pack event; it never rewrites the source pack.

New accepted promotion must durably retain at least:

- source `pack_id`;
- exact source pack revision from the mounted pack set;
- stable source `event_id`;
- target `pack_id` equal to the durable event's `pack_id`;
- stable subject refs;
- evidence and review/provenance refs.

The source event must resolve at the pinned source revision at acceptance. Missing/redacted/unresolvable source fails closed. Historical old-format promotions remain historical data and are not silently upgraded.

### Law 6 — Reviewed evidence ingest is provenance-first

Preserve source bytes/artifacts first when available; keep source evidence separate from synthesis; propose by default; validate pack/event/provenance/evidence/ontology contracts; require explicit review/promotion for accepted shared authority; do not ingest raw CI/log noise wholesale; emit a compact validation/ingest receipt.

Receipts/summaries/model output/projections do not become evidence merely because they exist.

### Explicit non-goals of the freeze

The freeze does **not**:

- claim #111 implementation complete;
- authorize production promotion;
- authorize a database/storage rewrite;
- change historical event identity;
- authorize or reveal private holdout material/location/credentials/verifier identity;
- claim Lean proves Python implementation.

---

## 5. #111 required implementation order after the freeze

The merged freeze gives this sequencing:

1. **Event-type contract/evidence-policy registry + deterministic accepted-commit gates.**
2. **`dkg.packset-lock.v1` + exact revision locking + cycle/layer validation + replay/portability tests.**
3. **Versioned promotion payload with source revision/event pin + source-resolvability tests.**
4. Longitudinal epistemic benchmark against the frozen laws.
5. Reviewed evidence ingestion + compact receipt.

Promotion mutation testing and Promotion Lean proof begin only **after** the Promotion law is implemented. Do not skip Steps 1–3 just because the semantic freeze is now accepted.

Issue #111 itself remains open because its implementation/evidence checklist is not complete.

---

## 6. Exact stop point: Step 1 characterization already performed

The next session does not need to rediscover the first few facts, but should verify them against current `main` before implementing.

### Current generic event envelope

`schemas/events/v1.schema.json` is `dkg.event.v1`.

It validates the envelope shape and includes:

- `schema_version`;
- `event_id`;
- `event_type`;
- timestamps;
- `pack_id`;
- actor;
- non-empty `subject_refs`;
- optional causal/correlation/idempotency fields;
- optional evidence/source-snapshot refs;
- optional `payload_schema` URI reference;
- generic object `payload`;
- optional provenance metadata.

Important current gap: `payload` is only `type: object`; `payload_schema` is optional. The envelope does not itself select or enforce a registered event-type payload contract/evidence policy.

### Current filesystem accepted-write behavior

`src/fossil_core/adapters/filesystem/event_store.py`:

- `prepare()` assigns deterministic identity when `pack_id + idempotency_key` exist, otherwise creates a new ID, then validates only with the configured envelope validator;
- `validate()` delegates to `prepare()`;
- `commit()` delegates to `prepare()`, enforces redaction non-resurrection and immutable/idempotent write semantics, then publishes.

There is currently no event-type registry in this adapter.

### Current agent-facing accepted-write boundary

`src/fossil_core/agent.py` / `CorpusService`:

- `propose()` requires the `propose` skill capability and pack write authorization, injects durable agent provenance, builds a generic event, and calls `event_store.prepare()`;
- `validate()` requires `validate`, pack write authorization, exact actor/session provenance match, then calls `event_store.validate()`;
- `commit()` requires `commit`, pack write authorization, exact actor/session provenance match, then calls `event_store.commit()`.

So pack authorization + actor provenance are already enforced at the agent boundary, while event-type payload/evidence/ontology acceptance remains generic.

### Current tests that demonstrate the existing semantics

`tests/test_agent_boundary.py` currently shows, among other things:

- `claim.proposed` with `payload={"claim_text": ...}` can be proposed, validated, and committed;
- pack boundaries and skill capabilities gate mutation;
- forged agent provenance is rejected;
- `knowledge.promoted` is currently built and committed as a target-pack event through the existing promotion path.

Do not change these historical/characterization facts casually. Step 1 should add the new accepted-commit semantic gate without silently reinterpreting existing durable events.

### Step 1 claim that was released

Released task:

`FOSSIL-111-STEP1-EVENT-CONTRACT-REGISTRY-20260819`

Released agent:

`chatgpt-sol-sync-111-step1-20260819`

Reason:

user requested session stop + durable handoff.

Result:

- characterization only;
- no branch/file implementation from that task;
- no implementation PR;
- restart from live current `main`, not from an assumed local branch.

---

## 7. Safest Step 1 restart plan

A new session should:

1. Re-fetch #94 and current `main`.
2. Confirm no newer implementation owner/PR exists for Step 1.
3. Re-read #111 and the merged semantic-freeze document.
4. Search all current `event_type` production/test fixtures and all direct `DurableEventStore.commit()` callers before designing the initial registry.
5. Characterize which event types are currently proposal-only versus already relied upon as accepted durable events.
6. Add deterministic behavioral oracles **before** widening implementation.
7. Implement one versioned registry/evidence-policy seam that the actual accepted-commit path consumes; do not create a decorative registry unused by commit.
8. Preserve historical replay: old durable events must remain readable/rebuildable; do not silently migrate/upgrade their payloads.
9. Make unknown **consequential new accepted writes** fail closed or remain proposal-only according to the frozen law; avoid breaking unrelated historical/system fixtures by accident.
10. Keep this PR bounded to Step 1. Explicitly exclude packset-lock, promotion-v2/source revision pin, holdout, mutation, TLA+, Lean, storage/provider/projection rewrites, and production deployment.
11. Run focused tests first, then exact-head DKG/required CI.
12. Review changed files, reviews/threads/comments, exact head and current main before merge.
13. Post `DONE/RELEASE` with exact evidence.
14. Only then claim Step 2 from fresh `main`.

A useful design question for the new session is **where the semantic gate belongs so all accepted-write paths share it without coupling durable storage adapters to policy-specific agent/session state**. Characterize all direct store callers before choosing that boundary.

Do not solve this by sprinkling duplicated hard-coded required-field checks across callers; the accepted freeze explicitly requires a registry to be the source of validation truth.

---

## 8. Hard boundaries that remain in force

Do not:

- weaken acceptance to make tests/CI green;
- widen runtime semantics merely to improve mutation score;
- expose sealed holdout cases/private exact oracles;
- invent a private holdout storage location or verifier identity in public code/docs;
- commit credentials or secret values;
- conflate mutation, holdout, TLA+, and Lean in one slice;
- claim formal models prove the Python implementation;
- silently upgrade historical durable events;
- rewrite source packs during promotion;
- authorize production promotion/deployment;
- treat projections/model agreement/retrieval scores as truth;
- touch unrelated open PRs merely because the queue is otherwise quiet.

Keep private holdout execution separate from public PDD code. Keep #111 semantic implementation separate from #176 mutation/formal evidence until prerequisites are actually implemented.

---

## 9. Recurring automation state

The prior recurring PDD/overnight runners were disabled when the public queue reached its dependency boundary. The current work was performed synchronously. Do not assume an automation will continue this handoff.

If a new session wants recurring monitoring later, inspect live task/automation state first rather than assuming an old runner is active.

---

## 10. Suggested first prompt for the next session

> Continue FOSSIL from GitHub, not from prior chat memory. Read `AGENTS.md`, `ARCHITECTURE.md`, Issue #86, latest Issue #94 comments, Issue #111, Issue #176, `docs/HANDOFF_CURRENT.md`, and `docs/handoffs/2026-08-19-pdd-semantic-freeze-session-handoff.md`. Re-fetch current `main` before any mutation. The #111 semantic freeze is accepted/merged, but implementation is not complete. The previous Step 1 event-contract-registry claim was released with characterization only and no implementation PR. Claim the smallest safe Step 1 lane only if unowned, characterize all event types/direct durable-store callers, then implement the versioned event-type contract/evidence-policy registry plus fail-closed accepted-commit gate without breaking `dkg.event.v1` historical replay. Do not start Promotion mutation/Lean until packset/source-pin Promotion implementation prerequisites have landed. Keep private holdout material off-repo and follow #94 claim/CI/review/SHA fences strictly.

---

## 11. Stop condition for the next session

If live GitHub state contradicts this document, **live GitHub wins**.

If another agent owns the Step 1 lane, do not duplicate it. Either do read-only review/evidence work explicitly marked parallel-safe or stop with `BLOCKED/RELEASE`.

If no bounded eligible task is available, stop rather than inventing scope.
