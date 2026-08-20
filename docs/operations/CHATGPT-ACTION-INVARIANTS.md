# Security and behavior invariants — FOSSIL ChatGPT Action

These invariants are normative and must be covered by automated tests or container inspection.

## Route and method invariants

`INV-ROUTE-01` The externally reachable application-path allowlist is exactly `/openapi.json`, `/actions/search`, `/actions/read`, `/actions/lineage`, and `/actions/capabilities`.

`INV-ROUTE-02` `GET /openapi.json` is the only unauthenticated success path and is not listed as an Action operation inside `paths`.

`INV-ROUTE-03` Search/read/lineage accept `POST` only. Capabilities accepts `GET` only. Authenticated unsupported methods return `405`; `POST /openapi.json` returns `405` without authentication.

`INV-ROUTE-04` `/mcp`, `/ingest`, proposal, validation, commit, redaction, write, admin, Neo4j/graph, filesystem/shell, and every unknown path return `404` and never delegate to the corpus adapter.

## Authentication invariants

`INV-AUTH-01` Every `/actions/*` request requires exactly one `Authorization: Bearer <token>` header.

`INV-AUTH-02` Missing, empty, duplicated, smuggled, wrong-scheme, whitespace-mutated, and incorrect credentials return `401` with `WWW-Authenticate: Bearer`. Bearer scheme matching is case-insensitive; token bytes are exact.

`INV-AUTH-03` Token comparison uses `hmac.compare_digest`.

`INV-AUTH-04` The configured token is trimmed, at least 32 characters, runtime-only, and never appears in OpenAPI, responses, application logs, image layers, committed configuration, documentation examples, or PR metadata.

## Request/identifier invariants

`INV-REQ-01` JSON bodies default to a maximum of 65,536 bytes; configured size must be 1..1,048,576 bytes.

`INV-REQ-02` Oversized declared or actual bodies return `413` before adapter invocation.

`INV-REQ-03` Invalid UTF-8/JSON, non-object JSON, invalid/negative `Content-Length`, missing required fields, extra fields, invalid types, and invalid ranges return `400` before adapter invocation.

`INV-REQ-04` Search `limit` is an integer 1..100; booleans and numeric strings are rejected. Search query is non-empty and at most 8,192 characters.

`INV-REQ-05` Event/conversation/node identifiers are bounded opaque identifiers with no slash, backslash, whitespace, URL, or path-traversal syntax. The filesystem event-store layer independently validates durable event IDs before constructing a path.

`INV-REQ-06` Caller fields cannot create filesystem paths, graph queries, MCP calls, writes, shell commands, configuration changes, or new capabilities.

## Error invariants

`INV-ERR-01` JSON errors use `{ "error": { "code": string, "detail": string } }`.

`INV-ERR-02` Auth failures are `401`/`403`; malformed requests `400`; oversized bodies `413`; unknown routes/resources `404`; unsupported methods `405`; unavailable canonical storage or HTTPS schema origin `503`; unexpected failures generic `500`.

`INV-ERR-03` Error bodies do not expose bearer values, stack traces, Windows or Linux host paths, environment values, exception internals, tunnel credentials, or Custom GPT credentials.

## Read-only data invariants

`INV-DATA-01` The standalone Action server constructs `_ReadOnlyEventStore`, not `DurableEventStore`.

`INV-DATA-02` `_ReadOnlyEventStore` has no `commit`, `prepare`, `validate`, `redact`, `put`, `delete`, or equivalent mutation operation.

`INV-DATA-03` Production/container examples mount `/var/lib/fossil` read-only. Container CI inspects the mount as `RW=false` and verifies a write attempt fails.

`INV-DATA-04` The Action runtime does not initialize Graphiti/Neo4j and requires no Neo4j credential or network access.

`INV-DATA-05` An existing but empty `canonical/events` directory is valid; authenticated search returns `200 []` and no synthetic content is created.

## Container and Windows-host invariants

`INV-CTR-01` The image and running process use UID/GID 10001, never root.

`INV-CTR-02` The image entrypoint is `fossil-chatgpt-action`; liveness uses the private TCP listener and adds no unauthenticated health route.

`INV-CTR-03` The Docker image contains no bearer token or real secret. CI verifies the synthetic runtime token is absent from `docker history` and image configuration.

`INV-CTR-04` The Windows/Docker Desktop launch contract publishes container 8787 only as `127.0.0.1:8787`; container inspection must report host IP `127.0.0.1`.

`INV-CTR-05` Persistent source, data, and secrets remain under `D:\FossilBrokerWorker\chatgpt-action\`; Docker Desktop's Linux engine is the runtime. Podman/systemd are not required.

## HTTPS and proxy invariants

`INV-HTTPS-01` A fixed `FOSSIL_ACTION_PUBLIC_BASE_URL`, when present, is an origin-only `https://` URL and is authoritative.

`INV-HTTPS-02` Fixed public origin cannot be overridden by `Forwarded`, `X-Forwarded-Proto`, `X-Forwarded-Host`, or `X-Forwarded-Port`.

`INV-HTTPS-03` Without a fixed origin, direct HTTPS may define the schema origin.

`INV-HTTPS-04` On an internal HTTP hop, forwarded HTTPS origin is accepted only when the request peer matches one of the explicit `FOSSIL_ACTION_TRUSTED_PROXY_CIDRS`, `X-Forwarded-Proto` is exactly one HTTPS value, and `X-Forwarded-Host` is exactly one syntactically valid host value.

`INV-HTTPS-05` Forwarded headers from untrusted peers, wildcard/spoof chains, comma-separated values, missing headers, `http` proto, malformed host, or ambiguous proxy data are ignored. If no trusted HTTPS origin remains, `/openapi.json` returns `503`; it never publishes `http://`.

`INV-HTTPS-06` Uvicorn global proxy-header processing remains disabled (`proxy_headers=False`). Application code performs the bounded source-CIDR check.

`INV-HTTPS-07` Tunnel/DNS/TLS/provider credentials and provisioning are outside this repository and are never created by CI.

## OpenAPI / Custom GPT invariants

`INV-OAI-01` Generated OpenAPI is 3.1.x and validates with `openapi-spec-validator`.

`INV-OAI-02` `components.schemas` is a non-empty object defining explicit request, error, search-result, durable-event, lineage-node/citation/response, and capability schemas.

`INV-OAI-03` Every successful response resolves to an object schema with declared properties (or an array of such objects); error responses resolve to `ErrorEnvelope`.

`INV-OAI-04` Operation IDs are stable and unique: `fossilSearch`, `fossilRead`, `fossilLineage`, `fossilActionCapabilities`.

`INV-OAI-05` `paths` contains only the four authenticated Action paths and no discovery/private/mutation path.

`INV-OAI-06` The security scheme is HTTP bearer and every Action operation inherits bearer security.

`INV-OAI-07` OpenAPI contains no token value, secret example, MCP/ingest/propose/validate/commit/redact/graph/filesystem/admin operation, or HTTP public server URL.

## Rollback invariant

`INV-RBK-01` Rollback consists of stopping/removing the Action container and reverting the image/PR commit. No canonical-data migration or reverse migration is required because this feature is read-only.
