# External runtime reconciliation — 2026-08-15

This document records the **read-only external runtime state** that FOSSIL should assume when interacting with Cortex V5 and LiteLLM/CKFF. It does not authorize changes to either external repository, their workflows, deployment, routing, credentials, or model policy.

## Reconciliation rule

For this checkpoint:

- `Pukujan/cortex-v5` is **read-only external execution infrastructure** from FOSSIL's perspective.
- `Pukujan/litellm-ckff-ops` is **read-only external transport/routing infrastructure** from FOSSIL's perspective.
- FOSSIL may document and consume their observed contracts, but must not silently make either repository part of a FOSSIL repair/automation sequence.
- Any future Cortex V5 or LiteLLM code/workflow mutation requires a separate owner decision.

## Cortex V5 — observed current contract

Observed `main`:

- commit: `f29e7a2fa0584577765bfe3f437695a2cbaefcf2`;
- parent baseline: `31fde7508b8e1caddfe7f9b79dc5719c1a0df79f`;
- latest change: research-grounded model seating, BigCodeBench-Hard harness/research notes, arbitration/sandbox refinements.

Relevant current source/docs:

- `README.md`;
- `cortex_v5/litellm.py`;
- `cortex_v5/seating.py`;
- `cortex_v5/sandbox_runner.py`;
- `docs/MODEL-SEATING-RESEARCH-2026-08.md`.

### Runtime shape

V5 remains independent of Cortex V4 and legacy SSC. Its normal flow is:

1. receive a task through the local V5 HTTP API;
2. classify type/risk and select V5 methodology;
3. refresh the LiteLLM `/v1/models` catalog;
4. select an available model seat deterministically;
5. call streamed `/v1/chat/completions` with explicit tools;
6. execute only workspace-contained tools;
7. run an explicit deterministic checker/verification gate;
8. persist sanitized events and receipts.

The V5 LiteLLM transport is strict: premature/invalid SSE termination is failure, tool-call fragments are reconstructed explicitly, and the V5 client default timeout is **120 seconds**. The client does not hide alternate invocation paths inside V5.

### Current seating policy

The previous undocumented `PREFERENCE_HINTS` list was removed. Current `MODEL_TIERS` is a documented prior backed by the repository's August 2026 model-seating research. The ranking tuple is:

```text
(available, tag_overlap, -tier, success - failure, success, model)
```

Availability and task/methodology relevance outrank the research prior. Retry/backoff/failure thresholds can move a persistently failing seat out of service. Unknown catalog models share the default lowest tier and remain deterministically ordered.

The current research-grounded starter order begins with:

1. `grok-4.6`;
2. `gpt-5.6-sol`;
3. `kimi-k3`;
4. `qwen3.8-max`;
5. `gemini-3.6-flash`.

This is V5 execution policy, **not FOSSIL semantic authority**.

### Documentation assessment

V5 documentation is **substantially current** for the post-publish change:

- the new model-seating research document explains the new tier prior and evidence;
- code comments in `seating.py` match that document;
- the README still accurately describes the mechanical runtime flow and strict checker authority.

Minor gap: the README does not foreground the new `MODEL_TIERS` policy or the BigCodeBench-Hard harness, so operators should read the model-seating research document when seating behavior matters.

## LiteLLM/CKFF — observed current contract

Observed `main`:

- commit: `9520e8dffe819d97a1557fe76022ed080f0eb8d6`;
- current manual routing baseline includes `702d97f19aee786be69d538ba739145075e8ff50` (CKFF main/fallback rewrite) and `f731bb3fc1addd0bca927908863ca8a2deb3d815` (120-second LiteLLM request timeout);
- latest commit is an automated CKFF catalog refresh.

Relevant current source/docs:

- `config/config.yaml`;
- `responses_bridge.py`;
- `API-CONTRACT.md`;
- `docs/TIMEOUT-CONTRACT.md`;
- `docs/CKFF-MODEL-COMPATIBILITY-REPORT.md`;
- `docs/IMPLEMENTATION-GAP.md`.

### Direct LiteLLM routing

The current generated `config/config.yaml` gives each configured logical model two CKFF deployments:

- primary: `https://ckffai.com/v1`;
- secondary: `https://ckff.dev/v1`.

The config references credential **names** through `os.environ/...`; secret values are not repository data.

Current global controls include:

```text
LiteLLM request_timeout: 120 seconds
LiteLLM num_retries: 3
router strategy: simple-shuffle
router retries: 3
retry_after: 2 seconds
allowed_fails: 3
cooldown_time: 30 seconds
max_parallel_requests: 8
```

This aligns the LiteLLM hard request deadline with the V5 client default of 120 seconds.

### Responses bridge

`responses_bridge.py` is a separate compatibility surface for `POST /v1/responses`. It can translate Responses requests to the tested Chat Completions tool path and has an explicit cross-model fallback table.

For model-specific evaluation or audit, callers should disable bridge substitution with:

```json
{"bridge_allow_fallbacks": false}
```

When fallback is allowed, callers must record the requested model, actual model, response ID, and attempt metadata. A substituted HTTP 200 response is not evidence that the originally requested model succeeded.

The bridge's per-candidate attempt deadline is separate from the 120-second LiteLLM/V5 outer transport budget; its defaults are shorter and are intentionally bounded.

### Retrieval service surfaces

The LiteLLM operations contract currently documents:

- `POST /v1/embeddings` with `gemini-embedding-2`;
- `POST /v1/rerank` with `rerank-v4-pro`.

These remain independent service lanes. FOSSIL must fail loudly on non-2xx responses, empty vectors, empty rankings, malformed payloads, or hidden identity substitution.

### Privacy boundary

The gateway privacy warning remains advisory, not a safety proof. CKFF is not documented as verified zero-data-retention. Do not send secrets, personal data, confidential files, or protected source material merely because the gateway is reachable.

### Documentation assessment

LiteLLM documentation is **partially stale/internally inconsistent** relative to current source/config:

- `docs/TIMEOUT-CONTRACT.md` correctly records the LiteLLM and V5 client deadlines as **120 seconds**.
- `docs/CKFF-MODEL-COMPATIBILITY-REPORT.md` still states an operational LiteLLM timeout of **90 seconds** in one section; current `config/config.yaml` is 120 seconds.
- `docs/IMPLEMENTATION-GAP.md` still says `ckffai.com` is absent from generated config; current `config/config.yaml` uses `ckffai.com` as the primary deployment for the configured model set, with `ckff.dev` as secondary.
- the README still contains historical candidate-deployment wording that predates later production reconciliation.

Therefore, until the LiteLLM repository documentation is reconciled by its owner, FOSSIL should use the following precedence for current operational facts:

1. current exact source/config at the inspected LiteLLM SHA;
2. current executable/API contract code;
3. current timeout contract where it agrees with source/config;
4. dated compatibility/gap reports as historical evidence, not current configuration truth.

## FOSSIL integration posture

FOSSIL must keep the boundary explicit:

- Cortex V5 owns execution policy and model seating.
- LiteLLM/CKFF owns transport, provider route, timeout, and capability facts.
- FOSSIL owns durable evidence, accepted semantic state, lifecycle, lineage, redaction semantics, and canonical storage contracts.
- Model agreement, model tier, route success, or gateway fallback never becomes semantic authority.

## Change boundary

This reconciliation deliberately makes **no change** to:

- Cortex V5 code;
- Cortex V5 workflows;
- Cortex V5 model policy;
- LiteLLM code;
- LiteLLM workflows;
- LiteLLM production routing/deployment;
- CKFF credentials;
- FOSSIL runtime/workflows associated with the active `OBJECT_STORE_LIVE` lane.

Re-check exact SHAs before relying on these facts in a later session.