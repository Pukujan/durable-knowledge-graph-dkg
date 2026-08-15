# LiteLLM gateway for FOSSIL agents

This document records how FOSSIL may consume the shared LiteLLM/CKFF gateway. It does **not** authorize changes to the LiteLLM repository, its workflows, routing, deployment, or credentials.

Exact external-runtime reconciliation for this checkpoint:

`docs/operations/EXTERNAL-RUNTIME-RECONCILIATION-2026-08-15.md`

## Current observed external baseline

Observed LiteLLM repository:

- repo: `Pukujan/litellm-ckff-ops`;
- main: `9520e8dffe819d97a1557fe76022ed080f0eb8d6`.

Observed Cortex V5 repository:

- repo: `Pukujan/cortex-v5`;
- main: `f29e7a2fa0584577765bfe3f437695a2cbaefcf2`.

FOSSIL should read its gateway URL/key from its configured environment/secret boundary. Do not treat a URL copied into prose as stronger authority than the actual runtime configuration.

## Direct Chat Completions path

Cortex V5 uses strict streamed OpenAI-compatible Chat Completions through LiteLLM:

- `GET /v1/models` for the live catalog;
- `POST /v1/chat/completions` for model/tool execution;
- streaming required by the V5 execution loop;
- V5 client default timeout: **120 seconds**;
- LiteLLM `request_timeout`: **120 seconds**.

V5 rejects premature/invalid SSE instead of silently treating an empty/truncated 2xx response as success.

The current generated LiteLLM config gives configured logical models two CKFF deployments:

- primary: `https://ckffai.com/v1`;
- secondary: `https://ckff.dev/v1`.

Current router controls include bounded retries/cooldown and `max_parallel_requests: 8`.

Do not infer that a healthy gateway or endpoint means every model/channel is healthy. Model/channel availability remains time- and credential-specific.

## Responses bridge

The gateway also exposes:

`POST /v1/responses`

The current bridge can translate Responses function tools into the tested Chat Completions path and has an explicit cross-model fallback table.

For routine non-model-specific work, fallback may be acceptable if the caller records the substitution. For model-specific evaluation, benchmarking, audit, or acceptance, disable bridge substitution:

```json
{
  "bridge_allow_fallbacks": false
}
```

When fallback is allowed, record at minimum:

- requested model;
- actual model;
- response ID;
- attempt list/reasons;
- elapsed time.

A substituted HTTP 200 response is **not** evidence that the requested model itself succeeded.

The bridge has shorter per-candidate attempt bounds than the 120-second outer LiteLLM/V5 deadline. Do not collapse a candidate timeout, a gateway timeout, and a provider/channel failure into one undifferentiated error class.

## Embeddings and reranking

The current LiteLLM operations contract documents:

- `POST /v1/embeddings` with model `gemini-embedding-2`;
- `POST /v1/rerank` with model `rerank-v4-pro`.

These are separate service lanes from chat/model fallback behavior.

Before a retrieval benchmark/job:

1. probe the required lane;
2. fail loudly on non-2xx;
3. fail loudly on malformed output;
4. fail loudly on empty embedding vectors or empty rerank results;
5. record requested and actual service/model identity when observable;
6. do not reinterpret fallback/substitution as requested-model success.

## Privacy boundary

The gateway emits an advisory data-privacy warning. That warning is not a safety proof.

CKFF is not documented as verified zero-data-retention. Do not send:

- secrets;
- personal data;
- confidential files;
- protected source material;
- credentials or `.env` contents.

Ordinary non-sensitive agent tasks may use the gateway within their task-specific authorization.

## Current documentation precedence

The LiteLLM repository currently contains some dated documentation that no longer matches current source/config. Until its owner reconciles those files, FOSSIL should use this precedence for operational facts:

1. current exact LiteLLM source/config at the inspected SHA;
2. current executable bridge/API code;
3. current timeout contract where it agrees with source/config;
4. dated compatibility/gap reports as historical evidence.

Known inconsistencies at `9520e8d...`:

- `docs/TIMEOUT-CONTRACT.md` correctly records LiteLLM/V5 at **120 seconds**;
- `docs/CKFF-MODEL-COMPATIBILITY-REPORT.md` still mentions a **90-second** LiteLLM timeout in its operational-configuration section;
- `docs/IMPLEMENTATION-GAP.md` still claims `ckffai.com` is absent from generated config, while current `config/config.yaml` uses `ckffai.com` as the primary deployment and `ckff.dev` as secondary for configured models;
- the LiteLLM README retains older candidate-deployment wording that predates later production reconciliation.

Do not edit the LiteLLM repo from a FOSSIL task merely to fix those documentation gaps.

## FOSSIL authority boundary

LiteLLM/CKFF provides transport facts. It does not decide FOSSIL truth.

The following remain non-authoritative execution metadata:

- model availability;
- route priority;
- gateway fallback;
- latency/cost;
- model confidence;
- model tier/ranking;
- multi-model agreement.

FOSSIL durable evidence/events, stable IDs, provenance, lifecycle, lineage, redaction and accepted contracts remain semantic authority.

## Operational rule of thumb

For a FOSSIL agent run:

- use the configured gateway rather than hard-coded private endpoints;
- prefer strict semantic success over HTTP status alone;
- record exact requested/actual identity;
- keep benchmark/model-specific tasks fallback-free unless the test explicitly studies fallback behavior;
- keep sensitive data off the gateway unless a future reviewed privacy contract explicitly changes that boundary;
- never change LiteLLM/Cortex as a side effect of a FOSSIL repair task.
