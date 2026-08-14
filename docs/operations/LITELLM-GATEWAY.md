# LiteLLM gateway for FOSSIL agents

FOSSIL may use the shared LiteLLM/CKFF gateway for routine, non-sensitive model work. The gateway is a **replaceable transport service**, not FOSSIL semantic authority.

## Current status — 2026-08-14

The gateway repair campaign is **closed completed** in `Pukujan/litellm-ckff-ops#11`.

Completed/reconciled state:

- CKFF streaming/tool-routing and subsequent false-success/Responses repairs are merged.
- Railway `litellm` production was observed healthy on 2026-08-14: liveliness HTTP 200, readiness HTTP 200 with database connected, Postgres online.
- No LiteLLM repair PR was active at the reconciliation point.
- Earlier failed LIVE_STAGING/verifier attempts remain historical failed evidence; do not retroactively call them `STAGING_GREEN`.
- A future formal live-inference semantic probe may add evidence, but the old repair campaign is not an active FOSSIL task unless a new regression reopens it.

Cross-project authority remains:

- FOSSIL Issue #86 — architecture authority;
- FOSSIL Issue #94 — execution/claim ledger;
- LiteLLM/CKFF — provider/model/route/capability/timeout/health **transport facts**;
- callers — model-selection policy and semantic acceptance.

## Gateway interface

- URL: `https://litellm-production-8656.up.railway.app/v1`
- Default execution model recorded by this repository: `qwen3-coder-next`
- GitHub Actions secret: `LITELLM_PROXY_KEY`
- GitHub Actions variables: `LITELLM_URL`, `LITELLM_MODEL`
- Embeddings: `POST /v1/embeddings`, recorded model `gemini-embedding-2`
- Reranking: `POST /v1/rerank`, recorded model `rerank-v4-pro`

Treat model/route availability as live transport state: refresh/probe when a task actually depends on a specific route, and record requested versus actual identity in benchmark/verification receipts.

## Fail-closed semantic rules

A transport-level success code is not enough. Treat all of the following as **failure**:

- empty or malformed `2xx` response bodies;
- a completed stream with zero usable payload;
- zero usable content/tool calls when the task requires them;
- empty embedding vectors;
- empty rerank results.

Chat requests may fall back to another configured provider/model. Check requested model, actual model, route/attempt diagnostics, and usable output before recording benchmark success. A fallback response is not evidence that the requested model itself succeeded.

Embedding and reranking lanes are independent of chat fallback routing. Probe the lane actually required by the task and fail loudly on non-2xx or semantically empty output.

## Data and authority safety

The gateway emits `X-LiteLLM-Data-Privacy-Warning`, and bridged Responses may include `metadata.data_privacy_warning`. This is advisory, not a block. CKFF has not been established here as a universal zero-data-retention destination; agents must not send secrets, personal data, or confidential documents merely because the gateway is healthy.

Production health does **not** authorize:

- production mutation or deployment;
- secret disclosure;
- sensitive-data routing;
- widening a FOSSIL/Cortex task's access class;
- treating model output or gateway telemetry as durable evidence authority.

OpenCode Zen/free-provider routes remain subject to their own live access/privacy evidence before use. Do not infer provider readiness from catalog presence alone.
