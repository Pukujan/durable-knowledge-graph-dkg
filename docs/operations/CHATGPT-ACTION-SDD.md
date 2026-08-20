# SDD — FOSSIL read-only ChatGPT Action

## 1. Architecture

```text
Private Custom GPT
        |
        | HTTPS + bearer authentication
        v
operator-managed HTTPS reverse proxy / tunnel
        |
        | HTTP to loopback/private Docker endpoint only
        v
127.0.0.1:8787 on Windows host
        |
        v
non-root fossil-chatgpt-action container
        |
        +-- /opt/fossil-core        application/contracts/skills
        +-- /var/lib/fossil         D:\...\data, bind-mounted read-only
```

The public Action is a compatibility edge over the protocol-independent FOSSIL corpus service. It does not expose the FOSSIL node's `/mcp` or `/ingest` surfaces and does not construct Graphiti or Neo4j.

## 2. Standalone composition

`chatgpt_action_server.py` loads:

1. the selected pack manifest through `KnowledgePackValidator`;
2. `PackAccess` from that manifest;
3. a `_ReadOnlyEventStore` over `data/canonical/events`;
4. the Skill registry;
5. `CorpusService`;
6. `ThinMCPAdapter` using `skill_corpus-search` provenance;
7. the dedicated Starlette Action middleware.

The event-store view exposes reads only. It never instantiates `DurableEventStore`, Graphiti, Neo4j, projector, ingestion, or write APIs.

### Lineage composition

The standalone service currently has no durable lineage mapping/provider. Consequently the Action contract deliberately excludes lineage. FOSSIL may still expose lineage over other correctly configured boundaries, including MCP/domain callers. Reintroducing `/actions/lineage` requires a real read-only standalone provider plus end-to-end tests first.

## 3. Public API contract

### Public, no bearer required

`GET /openapi.json`

Returns OpenAPI 3.1 only when a trustworthy HTTPS public origin can be established.

### Bearer-protected

`POST /actions/search`

Request:

```json
{"query":"search terms","limit":20}
```

`query` is required, non-empty, maximum 8192 characters. `limit` is optional, integer 1-100, default 20. No extra fields are accepted.

Response: JSON array of pack-authorized search result objects. Empty corpus/miss returns `[]`.

`POST /actions/read`

Request:

```json
{"event_id":"evt_exampleopaqueid123"}
```

Only a validated opaque event identifier is accepted. The result is the pack-authorized durable event. Missing or redacted events return generic 404.

`GET /actions/capabilities`

Response shape is bounded metadata with `action_capabilities` exactly `["search", "read"]` and write/ingest/MCP/graph-mutation exposure flags fixed to false.

### Non-routable

`/actions/lineage`, `/mcp`, `/ingest`, proposal, validation, commit, promotion, redaction, write/admin, graph/Neo4j, filesystem, and unknown paths are 404.

## 4. OpenAPI contract

The generated document is OpenAPI `3.1.0`. `components.schemas` is always a non-empty object. Request and response schemas use explicit object properties so the Custom GPT importer does not infer unbounded objects from missing schema structure.

The only Action operation IDs are:

- `fossilSearch`;
- `fossilRead`;
- `fossilActionCapabilities`.

`BearerAuth` is an HTTP bearer security scheme. The actual token never appears in the document.

### Public server origin

Two origin modes are supported:

**Fixed-origin mode (preferred)**

`FOSSIL_ACTION_PUBLIC_BASE_URL=https://public-name.example`

The configured origin must be HTTPS and origin-only. It is authoritative regardless of `Host`, `Forwarded`, or `X-Forwarded-*` supplied by callers.

**Trusted-proxy mode**

Leave `FOSSIL_ACTION_PUBLIC_BASE_URL` unset and configure one or more exact/narrow proxy peer networks in `FOSSIL_ACTION_TRUSTED_PROXY_CIDRS`. The request's immediate peer must match one of those networks, and the middleware must receive one unambiguous `X-Forwarded-Proto: https` and one validated `X-Forwarded-Host`.

Uvicorn itself runs with `proxy_headers=False`; application middleware performs the explicit CIDR check.

**Unsupported origin mode**

Direct HTTPS plus an arbitrary `Host` header is not authority. If neither fixed origin nor trusted-proxy origin is available, `GET /openapi.json` returns 503. The service never guesses or publishes an `http://` origin.

## 5. Request-body handling

The server checks a valid non-negative `Content-Length` when present and rejects declared oversize immediately. It then consumes `request.stream()` incrementally, counting cumulative bytes. As soon as the configured limit is exceeded it returns 413 without invoking the FOSSIL adapter.

This second check is authoritative for chunked requests, missing `Content-Length`, and deliberately understated `Content-Length`. The Action request path does not use `await request.body()`.

## 6. Redaction semantics

`_ReadOnlyEventStore.iter_events()` traverses only direct canonical event buckets and explicitly excludes `_redactions`. Tombstone JSON is metadata, never corpus content.

For every candidate event, the read-only store also checks for a matching tombstone and suppresses the event if redacted. That remains true if old event bytes still exist on disk. `get()` checks redaction before reading event bytes and raises the established `EventRedactedError`, which is normalized to generic not-found at the public Action boundary.

## 7. Environment variables

Runtime variables:

- `FOSSIL_ACTION_BEARER_TOKEN` — required, local runtime secret, minimum 32 characters;
- `FOSSIL_ACTION_HOST` — container listener, image default `0.0.0.0`;
- `FOSSIL_ACTION_PORT` — default `8787`;
- `FOSSIL_ACTION_MAX_REQUEST_BYTES` — default `65536`, server maximum 1048576;
- `FOSSIL_ACTION_PUBLIC_BASE_URL` — preferred fixed public HTTPS origin;
- `FOSSIL_ACTION_TRUSTED_PROXY_CIDRS` — optional comma-separated proxy peer networks when fixed origin is absent;
- `FOSSIL_REPOSITORY_ROOT` — image default `/opt/fossil-core`;
- `FOSSIL_DATA_ROOT` — image default `/var/lib/fossil`;
- `FOSSIL_PACK_MANIFEST` — default common-pack manifest in the image.

The committed `.env.example` contains placeholders only. A populated env file must stay outside Git.

## 8. Container contract

The image uses Python 3.12 slim, installs the project into an image-local virtual environment, and runs `fossil-chatgpt-action` as user/group `fossil` UID/GID 10001.

The Dockerfile does not bake a bearer token into an `ARG`, `ENV`, layer, or file. The canonical data mount is external and read-only.

Target Windows publication is loopback only:

```powershell
docker run -d `
  --name fossil-chatgpt-action `
  --restart unless-stopped `
  --env-file "D:\FossilBrokerWorker\chatgpt-action\secrets\chatgpt-action.env" `
  -p 127.0.0.1:8787:8787 `
  -v "D:\FossilBrokerWorker\chatgpt-action\data:/var/lib/fossil:ro" `
  fossil-chatgpt-action:<reviewed-tag>
```

This is an operator example only; the repository does not create the env file or its real values.

## 9. Docker Desktop / WSL 2 assumptions

The deployment is driven from Windows against Docker Desktop's Linux engine. Ubuntu WSL distributions do not need Docker integration enabled and the service is not started inside the Ubuntu distribution as a systemd unit. Source, data, and secret material remain on `D:`.

Expected layout:

```text
D:\FossilBrokerWorker\chatgpt-action\
  fossil-core\
  data\
    canonical\
      events\
  secrets\
    chatgpt-action.env
```

## 10. Startup validation

Before any public exposure, the local integrator should verify the reviewed SHA and run the documented Python test, OpenAPI validation, mutation, and Docker smoke suites.

After starting the local container, verify mechanically:

- image/container effective UID/GID are 10001;
- Docker `HostIp` for `8787/tcp` is `127.0.0.1`;
- `/var/lib/fossil` reports `RW=false`;
- an in-container write probe to the canonical mount fails;
- `GET /openapi.json` advertises the intended HTTPS public origin once the proxy configuration exists;
- unauthenticated Action call returns 401;
- authenticated search on the currently empty target corpus returns `200 []`;
- `/actions/lineage`, `/mcp`, `/ingest`, and mutation-like paths return 404.

Do not invent fixture corpus content on the real machine to make the empty search non-empty.

## 11. Reverse proxy / tunnel contract

The external component owns TLS, public DNS/hostname, certificate handling, rate limiting if desired, and any provider credentials. It forwards only to the loopback-bound Action port. It must not expose a Docker/Neo4j/FOSSIL admin surface.

When using trusted-proxy origin mode, configure `FOSSIL_ACTION_TRUSTED_PROXY_CIDRS` to the actual immediate proxy peer range seen by the container. Do not use `0.0.0.0/0` or `::/0` merely to make forwarded headers work.

## 12. Error behavior

Public errors are bounded JSON envelopes `{ "error": { "code": ..., "detail": ... } }`. The mapping intentionally avoids stack traces, filesystem paths, bearer tokens, redaction metadata, and local deployment details.

## 13. Operational rollback

Because the Action cannot write canonical data, rollback is operationally simple:

1. disable/remove the external route if it was configured locally;
2. stop and remove the Action container;
3. restore/run the previously reviewed image/SHA if needed;
4. leave canonical data untouched.

No data migration is required for rollback of this edge.

## 14. Verification ownership

Repository CI proves code/package invariants on a specific commit. The local integrator separately proves Windows/Docker Desktop filesystem mapping, local-only secret handling, actual HTTPS endpoint behavior, and private Custom GPT configuration. Neither side may substitute self-report for the other's evidence.
