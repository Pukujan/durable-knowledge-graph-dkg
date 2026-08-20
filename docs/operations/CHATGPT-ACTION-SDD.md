# SDD — FOSSIL read-only ChatGPT Action

## 1. Architecture

```text
Private Custom GPT
        |
        | HTTPS + bearer token
        v
Operator-managed HTTPS reverse proxy / tunnel
        |
        | forwards only to Windows loopback
        v
127.0.0.1:8787 on Windows
        |
        | Docker Desktop WSL2 Linux engine
        v
fossil-chatgpt-action container (UID/GID 10001)
        |
        +-- /opt/fossil-core       immutable image content
        +-- /var/lib/fossil        host D:\...\data, read-only bind mount
                 |
                 +-- canonical/events
```

The Action service is a protocol adapter over existing FOSSIL read semantics. It is not the FOSSIL Node network service and does not mount MCP, ingest, projector, Graphiti, Neo4j, or write/admin routes.

### Module boundaries

- `src/fossil_core/runtime/chatgpt_action.py`
  - exact HTTP route allowlist;
  - bearer authentication;
  - bounded request parsing and identifier validation;
  - trusted HTTPS public-origin derivation;
  - OpenAPI 3.1 generation;
  - dispatch only to `fossil.search`, `fossil.read`, and `fossil.lineage`.
- `src/fossil_core/runtime/chatgpt_action_server.py`
  - runtime environment parsing;
  - trusted proxy CIDR validation;
  - canonical read-only event-store composition;
  - `CorpusService` + read-only skill context;
  - Uvicorn startup with global proxy-header trust disabled.
- `docker/chatgpt-action/Dockerfile`
  - non-root Linux image;
  - no secret baked into image;
  - Action-only entrypoint;
  - TCP liveness without a new HTTP route.
- `config/chatgpt-action.env.example`
  - field-name and non-secret placeholder template only.

## 2. Public API contract

### Public discovery — `GET /openapi.json`

- unauthenticated;
- succeeds only when a trusted public HTTPS origin can be derived;
- returns OpenAPI 3.1 JSON;
- never contains a real bearer token/runtime secret;
- `paths` describes only the four authenticated Action operations;
- unsupported methods return `405`.

### Authenticated operations

Every `/actions/*` request requires exactly one:

```text
Authorization: Bearer <opaque runtime token>
```

The scheme is case-insensitive; token bytes are exact and compared with `hmac.compare_digest`.

#### `POST /actions/search`

```json
{
  "query": "authentication decision",
  "limit": 20
}
```

- `query`: required non-empty string, max 8,192 characters;
- `limit`: optional integer 1..100;
- additional properties are rejected;
- success: array of explicit `SearchResult` objects;
- existing-but-empty canonical event directory: `200 []`.

#### `POST /actions/read`

```json
{
  "event_id": "evt_exampleopaqueidentifier"
}
```

- event ID is a bounded opaque identifier with no path separators/whitespace/URL syntax;
- the filesystem adapter independently validates FOSSIL event-ID format before path construction;
- success: explicit `FossilEvent`;
- missing/redacted resource: generic `404`.

#### `POST /actions/lineage`

```json
{
  "conversation_id": "conv_example",
  "node_id": "ln_example"
}
```

- `conversation_id` required;
- `node_id` optional;
- both bounded opaque identifiers;
- success: explicit `LineageResponse` with typed nodes and citations.

#### `GET /actions/capabilities`

Structurally fixed success body:

```json
{
  "service_version": "1",
  "action_capabilities": ["search", "read", "lineage"],
  "durable_writes_exposed": false,
  "ingestion_exposed": false,
  "mcp_exposed": false,
  "arbitrary_graph_mutation": false
}
```

### Prohibited network surface

`/mcp`, `/ingest`, proposal, validation, commit, redaction, write/admin, Neo4j/graph, filesystem/shell, and unknown paths return JSON `404` and never delegate to the corpus adapter.

## 3. Error contract

```json
{
  "error": {
    "code": "machine_code",
    "detail": "sanitized message"
  }
}
```

Status mapping:

- `400`: malformed/invalid request;
- `401`: missing/invalid bearer credential;
- `403`: FOSSIL pack/capability denial;
- `404`: missing resource or prohibited/unknown route;
- `405`: unsupported method on an allowed route;
- `413`: body over configured limit;
- `500`: unexpected internal failure, generic text only;
- `503`: canonical storage unavailable or no trusted HTTPS schema origin.

No response includes stack traces, local Windows/Linux paths, environment data, token values, or provider credentials.

## 4. OpenAPI / private Custom GPT compatibility

The document is OpenAPI `3.1.0` and is validated with `openapi-spec-validator`.

Compatibility contract:

- `components.schemas` is a non-empty object;
- request schemas are named: `SearchRequest`, `ReadRequest`, `LineageRequest`;
- success response schemas have declared object properties: `SearchResult`, `FossilEvent`, `LineageNode`, `Citation`, `LineageResponse`, `CapabilitiesResponse`;
- errors use `ErrorEnvelope`;
- operation IDs are stable/unique: `fossilSearch`, `fossilRead`, `fossilLineage`, `fossilActionCapabilities`;
- security is HTTP bearer;
- no private or mutation route appears in `paths`;
- `servers[0].url` is HTTPS only.

Event-type-specific `payload` and `provenance` remain explicitly declared object properties whose inner keys vary by durable event type. The Action response itself is never an anonymous property-less object.

## 5. HTTPS and reverse-proxy behavior

Uvicorn runs with:

```text
proxy_headers=False
```

The application performs all proxy-origin trust decisions.

### Mode A — fixed public origin (preferred when known)

```text
FOSSIL_ACTION_PUBLIC_BASE_URL=https://<public-origin>
```

Requirements:

- HTTPS;
- origin only: no path/query/fragment/userinfo;
- authoritative;
- forwarded headers cannot override it.

### Mode B — explicit trusted proxy CIDRs

Leave the fixed origin unset and configure:

```text
FOSSIL_ACTION_TRUSTED_PROXY_CIDRS=<comma-separated peer CIDRs>
```

Only a request whose actual peer IP is in one configured network may supply:

```text
X-Forwarded-Proto: https
X-Forwarded-Host: <single valid host>
```

Comma-separated/chained values, `http`, missing host/proto, whitespace, path/userinfo syntax, malformed ports, or headers from untrusted peers do not define the public origin.

Origin precedence:

1. fixed `FOSSIL_ACTION_PUBLIC_BASE_URL`;
2. direct HTTPS request origin;
3. validated trusted-proxy HTTPS origin;
4. otherwise `/openapi.json` returns `503` rather than emitting internal HTTP.

Never use `0.0.0.0/0` or `::/0` merely to accept forwarded headers.

## 6. Environment variables

| Variable | Required | Default | Contract |
|---|---|---|---|
| `FOSSIL_ACTION_BEARER_TOKEN` | yes | none | trimmed, >=32 chars, runtime-only |
| `FOSSIL_ACTION_HOST` | no | `127.0.0.1` | image sets `0.0.0.0`; Windows publish remains loopback-only |
| `FOSSIL_ACTION_PORT` | no | `8787` | 1..65535 |
| `FOSSIL_ACTION_MAX_REQUEST_BYTES` | no | `65536` | 1..1048576 |
| `FOSSIL_ACTION_PUBLIC_BASE_URL` | conditional | none | fixed origin-only HTTPS URL |
| `FOSSIL_ACTION_TRUSTED_PROXY_CIDRS` | conditional | empty | exact proxy peer networks; used only when fixed origin absent |
| `FOSSIL_REPOSITORY_ROOT` | no | cwd | image: `/opt/fossil-core` |
| `FOSSIL_DATA_ROOT` | no | `<repo>/data` | image: `/var/lib/fossil` |
| `FOSSIL_PACK_MANIFEST` | no | common example manifest | read-pack authorization |

A deployment needs a fixed origin, direct HTTPS, or a valid trusted-proxy origin before `/openapi.json` is importable.

## 7. Container behavior

PowerShell build from the required host layout:

```powershell
Set-Location 'D:\FossilBrokerWorker\chatgpt-action\fossil-core'
docker build --file docker/chatgpt-action/Dockerfile --tag fossil-chatgpt-action:pr235 .
```

Image invariants:

- Docker Desktop Linux image;
- runtime UID/GID 10001;
- entrypoint `fossil-chatgpt-action`;
- no real token/provider credential in image config/layers;
- no unauthenticated health route;
- canonical data supplied only at runtime.

Deployment shape (documentation only; real env file is created by the local integrator):

```powershell
docker run --detach `
  --name fossil-chatgpt-action `
  --restart unless-stopped `
  --env-file 'D:\FossilBrokerWorker\chatgpt-action\secrets\chatgpt-action.env' `
  --publish 127.0.0.1:8787:8787 `
  --mount 'type=bind,source=D:\FossilBrokerWorker\chatgpt-action\data,target=/var/lib/fossil,readonly' `
  fossil-chatgpt-action:pr235
```

The host publication must remain `127.0.0.1`; the external HTTPS component is the only public exposure.

## 8. Windows / Docker Desktop / WSL 2 runbook

Required layout:

```text
D:\FossilBrokerWorker\chatgpt-action\
  fossil-core\
  data\canonical\events\
  secrets\chatgpt-action.env
```

Create non-secret directories in PowerShell:

```powershell
New-Item -ItemType Directory -Force 'D:\FossilBrokerWorker\chatgpt-action\data\canonical\events' | Out-Null
New-Item -ItemType Directory -Force 'D:\FossilBrokerWorker\chatgpt-action\secrets' | Out-Null
```

Docker commands run from Windows against Docker Desktop's WSL2 engine. Docker integration inside Ubuntu/Ubuntu-22.04 is not required.

Optional Python verification from WSL (no Docker command required there):

```bash
cd /mnt/d/FossilBrokerWorker/chatgpt-action/fossil-core
python3 -m venv .venv-linux
. .venv-linux/bin/activate
pip install -e '.[test,node]'
pytest -q tests/test_chatgpt_action.py tests/test_chatgpt_action_server.py tests/test_chatgpt_action_architecture.py tests/holdout/test_chatgpt_action_holdout.py
python scripts/run_chatgpt_action_mutations.py
```

## 9. Startup/operational checks

Before connecting a private Custom GPT, verify:

1. effective container UID is 10001;
2. Docker host binding is exactly `127.0.0.1:8787`;
3. `/var/lib/fossil` has `RW=false`;
4. an in-container write attempt under `/var/lib/fossil` fails;
5. no Neo4j credential/connectivity is required;
6. unauthenticated Action request is `401`;
7. authenticated search against the current empty corpus is `200 []`;
8. prohibited routes are `404`;
9. `/openapi.json` validates and advertises only the intended HTTPS origin;
10. forged forwarded headers cannot alter a fixed origin, and trusted-proxy mode rejects untrusted peers;
11. image history/application logs contain no real credential.

## 10. Rollback

1. disable the external HTTPS route if configured;
2. stop/remove `fossil-chatgpt-action`;
3. restore the previous image/tag or checkout the prior commit;
4. leave `D:\...\data` unchanged;
5. remove/rotate the local secret separately if desired.

No database migration, projection rebuild, or reverse data migration is required.

## 11. Known limitations

- This package does not provision/test a real tunnel provider, DNS name, TLS certificate, or Custom GPT account configuration.
- Trusted-proxy mode requires the integrator to configure the actual proxy peer CIDR observed by the container; Docker Desktop network addressing can vary.
- The target canonical event directory is currently empty, so deployment smoke proves empty read behavior but not semantic retrieval quality until real canonical events exist.
