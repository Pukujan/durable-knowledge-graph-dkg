# SDD — Read-only ChatGPT Action edge

## Architecture

```text
Private Custom GPT
      |
      | HTTPS + Bearer
      v
operator-managed TLS proxy/tunnel
      |
      | HTTP on loopback/private container network
      v
fossil-chatgpt-action (non-root)
      |
      | ThinMCPAdapter used only as an internal protocol adapter
      v
CorpusService + PackAccess + SkillRegistry
      |
      v
_ReadOnlyEventStore
      |
      | read-only mount
      v
canonical/events
```

The Action process is independent of the private FOSSIL Node transport. It does not publish MCP and does not initialize Graphiti/Neo4j. The use of `ThinMCPAdapter` is internal code reuse only; no MCP endpoint or MCP wire protocol is reachable.

## Public API contract

### `GET /openapi.json`

- unauthenticated by design;
- returns OpenAPI 3.1 JSON;
- advertises only the authenticated Action operations;
- contains no bearer value or host-local secret;
- when `FOSSIL_ACTION_PUBLIC_BASE_URL` is configured, `servers[0].url` equals that exact HTTPS origin;
- unsupported methods return `405`.

### `POST /actions/search`

Bearer required. Body:

```json
{"query":"text", "limit":20}
```

`query` is a non-empty string. `limit` is an integer 1..100. Returns an array of authorized FOSSIL records.

### `POST /actions/read`

Bearer required. Body:

```json
{"event_id":"evt_..."}
```

Returns one pack-authorized durable event or `404`.

### `POST /actions/lineage`

Bearer required. Body:

```json
{"conversation_id":"conv_...", "node_id":"optional"}
```

Returns the canonical lineage view authorized by the existing FOSSIL service.

### `GET /actions/capabilities`

Bearer required. Returns explicit metadata showing only `search`, `read`, and `lineage` capabilities and Boolean false values for durable writes, ingestion, MCP exposure, and arbitrary graph mutation.

## Prohibited network surface

The Action ASGI app has no routes for `/mcp`, `/ingest`, proposal, validation, commit, redaction, graph mutation, Neo4j, filesystem access, admin operations, shell execution, or arbitrary query languages. Unknown paths are `404`.

## OpenAPI design

The schema is produced by `chatgpt_action_openapi_schema` and uses OpenAPI 3.1. It contains:

- `components.schemas.ErrorDetail`;
- `components.schemas.ErrorEnvelope`;
- `components.schemas.FossilRecord` with explicit common event properties;
- `components.schemas.LineageResponse` with explicit lineage properties;
- `components.schemas.CapabilitiesResponse` with explicit read-only flags;
- `components.securitySchemes.BearerAuth` using HTTP bearer;
- stable unique operation IDs.

The `paths` object contains only the four authenticated Action paths. OpenAPI discovery itself is intentionally outside `paths` so importing the document does not cause ChatGPT to treat schema discovery as a callable Action.

## Environment variables

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `FOSSIL_ACTION_BEARER_TOKEN` | yes | none | runtime-only bearer secret, minimum 32 chars |
| `FOSSIL_ACTION_HOST` | no | `127.0.0.1` | listen host inside local/container deployment |
| `FOSSIL_ACTION_PORT` | no | `8787` | listen port |
| `FOSSIL_ACTION_MAX_REQUEST_BYTES` | no | `65536` | body-size limit; bounded to 1..1048576 |
| `FOSSIL_ACTION_PUBLIC_BASE_URL` | production | none | origin-only `https://` URL emitted in OpenAPI |
| `FOSSIL_REPOSITORY_ROOT` | no | current directory | schemas/skills/package root |
| `FOSSIL_DATA_ROOT` | no | `<repo>/data` | root containing `canonical/events` |
| `FOSSIL_PACK_MANIFEST` | no | common example manifest | pack authorization manifest |

No variable is populated with a real value in Git. `config/chatgpt-action.env.example` contains placeholders only.

## Container behavior

The Dockerfile:

- builds the package with the node runtime dependency set;
- creates UID/GID 10001;
- runs as user `fossil`, not root;
- uses `fossil-chatgpt-action` as entrypoint;
- contains no credential;
- expects `/var/lib/fossil` to be supplied at runtime;
- is verified with a read-only canonical-data mount in CI.

The Action-specific `_ReadOnlyEventStore` never creates directories and exposes no mutation methods. This is deliberate: the process must boot with canonical data mounted read-only.

## Reverse proxy / tunnel assumptions

The repository does not choose or provision a reverse proxy, tunnel, hostname, DNS record, TLS certificate, or external provider credential.

The external component has one responsibility: terminate HTTPS and forward only the Action origin to the internal Action listener. The application does not trust `Forwarded`/`X-Forwarded-*` to determine its public URL. Instead, the operator sets:

```text
FOSSIL_ACTION_PUBLIC_BASE_URL=https://<public-action-origin>
```

Uvicorn is launched with `proxy_headers=False`. Therefore forged forwarded headers cannot rewrite the generated schema. This also makes deployments behind Cloudflare Tunnel, Caddy, nginx, a managed reverse proxy, or another HTTPS edge deterministic: the externally visible origin comes from explicit local configuration, not from caller-controlled headers.

## Windows / WSL `D:` deployment handoff

This repository prepares but does not execute deployment. A local integrator can use a layout such as:

```text
Windows: D:\fossil\fossil-core
Windows: D:\fossil\data
WSL:     /mnt/d/fossil/fossil-core
WSL:     /mnt/d/fossil/data
```

Example verification from WSL after cloning/checking out the PR:

```bash
cd /mnt/d/fossil/fossil-core
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test,node]'
pytest -q tests/test_chatgpt_action.py tests/test_chatgpt_action_server.py tests/holdout/test_chatgpt_action_holdout.py
```

Container build only:

```bash
docker build -f docker/chatgpt-action/Dockerfile -t fossil-chatgpt-action:local .
```

A real deployment must use a host-local env/secret source, a read-only canonical mount, and a local port binding. Real values are intentionally omitted here.

## Operational runbook

1. Clone/check out the exact PR SHA.
2. Run the focused and holdout verification commands.
3. Build the container.
4. Inspect image user and entrypoint.
5. Prepare a host-local environment file outside Git; never paste the real bearer value into source, issues, CI, or chat.
6. Mount only the canonical FOSSIL data required by the Action, read-only.
7. Bind the Action listener to loopback/private container networking where practical.
8. Configure the external HTTPS edge to forward only to the Action listener.
9. Set the explicit HTTPS public base URL locally.
10. Verify `/openapi.json`, unauthenticated `401`, authenticated search/read/lineage/capabilities, `404` prohibited routes, and forged forwarded-header resistance.
11. Only after those checks should a private Custom GPT import the schema and use the same locally managed bearer credential.

## Rollback

There is no schema migration and no Action-side durable write. Rollback is: stop/remove the Action process/container, remove the external route, and revert/checkout the previous repository SHA. Canonical events and projections require no rollback because this feature never mutates them.
