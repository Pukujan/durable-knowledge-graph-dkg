# FOSSIL read-only ChatGPT Action — operator entrypoint

This PR packages a private, bearer-authenticated, read-only GPT Action edge. It does **not** deploy, create secrets, create tunnels, or configure a Custom GPT.

Design and verification documents:

- `CHATGPT-ACTION-PDD.md` — product boundary, threat model, trust boundaries, Windows target;
- `CHATGPT-ACTION-INVARIANTS.md` — normative machine-testable invariants;
- `CHATGPT-ACTION-SDD.md` — architecture, API, origin handling, Docker Desktop contract, runbook;
- `CHATGPT-ACTION-HOLDOUT.md` — independent black-box holdout specification;
- `CHATGPT-ACTION-VERIFICATION.md` — commands, CI evidence template, limitations and rollback.

## Public contract

Unauthenticated discovery:

- `GET /openapi.json`

Bearer-protected operations:

- `POST /actions/search`
- `POST /actions/read`
- `GET /actions/capabilities`

`/actions/lineage` is intentionally **not** exposed by this standalone release. FOSSIL lineage remains a domain/MCP capability, but the standalone Action composition has no durable lineage provider; advertising a route that cannot succeed is prohibited.

Also unavailable: `/mcp`, `/ingest`, propose, validate, commit, promote, redact, write/admin, arbitrary graph/Neo4j mutation, arbitrary filesystem access, and shell execution.

## Target host

The intended local runtime is Windows + Docker Desktop's WSL 2 Linux engine. Do not require Podman or a Linux systemd service. Keep persistent material under:

```text
D:\FossilBrokerWorker\chatgpt-action\
  fossil-core\
  data\
    canonical\
      events\
  secrets\
    chatgpt-action.env     # local only; never commit
```

The Docker service is published only to `127.0.0.1:8787`, runs as UID/GID 10001, and mounts `D:\FossilBrokerWorker\chatgpt-action\data` at `/var/lib/fossil:ro`.

## HTTPS/OpenAPI origin

Preferred mode is a fixed origin-only `FOSSIL_ACTION_PUBLIC_BASE_URL=https://...`. Advanced mode leaves that unset and trusts forwarded HTTPS host/proto only from explicit `FOSSIL_ACTION_TRUSTED_PROXY_CIDRS` peers.

A direct HTTPS request's `Host` header is not public-origin authority. If neither fixed origin nor trusted proxy origin is available, `/openapi.json` returns 503 rather than publishing an attacker-controlled server URL.

## Redaction behavior

Search traverses canonical event buckets only. `_redactions` tombstones are never normal search documents. If an event has a tombstone, search suppresses the event even when stale bytes remain and read returns generic 404 without exposing tombstone metadata.

## Request-size behavior

The Action enforces the request limit both from a declared `Content-Length` and while streaming chunks. Chunked, absent-length, or understated-length oversized bodies are rejected with 413 before adapter invocation.

## Local verification before deployment

From the reviewed checkout:

```bash
pip install -e '.[test,node]'
pytest -q tests/test_chatgpt_action.py tests/test_chatgpt_action_server.py tests/test_chatgpt_action_architecture.py tests/holdout/test_chatgpt_action_holdout.py
python scripts/run_chatgpt_action_mutations.py
```

Build the exact reviewed image with:

```powershell
docker build -f docker/chatgpt-action/Dockerfile -t fossil-chatgpt-action:local .
```

The repository CI container workflow is the reference for non-root, loopback, read-only-mount, redaction, route-isolation, and trusted-proxy smoke checks.

## Empty corpus

The current target canonical event directory may legitimately be empty. An authenticated search must return `200 []`; do not create fake knowledge just to make a smoke test return content.

## Secret boundary

Only the local integrator creates the real bearer token and any reverse-proxy/tunnel or Custom GPT credentials. Do not commit, log, paste into issues/PRs, or bake those values into the image.

## Rollback

Disable the external route if configured, stop/remove the Action container, and restore the previous reviewed image/SHA. Canonical data requires no rollback because this edge has no write capability.
