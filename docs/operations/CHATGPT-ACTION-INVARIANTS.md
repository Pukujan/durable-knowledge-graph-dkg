# Security and behavior invariants — ChatGPT Action edge

These invariants are normative and machine-testable.

## Route and method invariants

`INV-ROUTE-01` The only public application paths are `/openapi.json`, `/actions/search`, `/actions/read`, `/actions/lineage`, and `/actions/capabilities`.

`INV-ROUTE-02` `GET /openapi.json` is the only unauthenticated success path.

`INV-ROUTE-03` Search/read/lineage accept `POST` only. Capabilities accepts `GET` only. Unsupported methods return `405` when the caller is authenticated; `POST /openapi.json` returns `405` without requiring authentication.

`INV-ROUTE-04` `/mcp`, `/ingest`, `/actions/propose`, `/actions/validate`, `/actions/commit`, `/actions/redact`, graph/Neo4j endpoints, admin endpoints, shell/filesystem endpoints, and unknown paths return `404` and never delegate to the corpus adapter.

## Authentication invariants

`INV-AUTH-01` Every `/actions/*` request requires `Authorization: Bearer <exact-token>`.

`INV-AUTH-02` Missing, empty, malformed, duplicated/smuggled, wrong-scheme, wrong-case token values, leading/trailing-token changes, and incorrect tokens fail closed with `401` and `WWW-Authenticate: Bearer`.

`INV-AUTH-03` Token comparison is constant-time via `hmac.compare_digest`.

`INV-AUTH-04` The configured token must be trimmed and at least 32 characters. It is accepted only from runtime configuration and is never emitted by `/openapi.json`, capabilities, error bodies, logs produced by the application, or example configuration.

## Request-validation invariants

`INV-REQ-01` JSON request bodies default to a maximum of 65,536 bytes and the configured maximum must be between 1 and 1,048,576 bytes.

`INV-REQ-02` Oversized declared or actual bodies return `413` before adapter invocation.

`INV-REQ-03` Invalid UTF-8/JSON, non-object JSON, invalid `Content-Length`, empty required strings, and invalid parameter types return `400` before adapter invocation.

`INV-REQ-04` Search `limit` is an integer from 1 through 100; booleans, strings, zero, negative values, and values above 100 are rejected.

`INV-REQ-05` Extra JSON keys never create new capabilities. They are not converted into filesystem paths, graph queries, MCP calls, writes, shell commands, or service configuration.

## Error invariants

`INV-ERR-01` Errors use `{ "error": { "code": string, "detail": string } }`.

`INV-ERR-02` Authorization failures are `401` or `403`; malformed requests are `400`; oversized bodies are `413`; unknown resources/routes are `404`; canonical-store unavailability is `503`; unexpected errors are generic `500` responses.

`INV-ERR-03` Unexpected/OSError responses do not expose bearer tokens, stack traces, arbitrary host paths, environment values, or internal exception text.

## Read-only data invariants

`INV-DATA-01` The standalone Action server constructs `_ReadOnlyEventStore`, not `DurableEventStore`.

`INV-DATA-02` `_ReadOnlyEventStore` provides no `commit`, `prepare`, `validate`, `redact`, `put`, `delete`, or mutation method.

`INV-DATA-03` The production container mount for `/var/lib/fossil` is documented and smoke-tested as read-only. Container smoke must fail if the application requires write access to canonical data.

`INV-DATA-04` The Action runtime does not initialize Neo4j or Graphiti and requires no Neo4j credential.

## Container invariants

`INV-CTR-01` The image executes as non-root UID/GID 10001.

`INV-CTR-02` No bearer token or real secret is present in the Dockerfile, image command, repository example values, or CI configuration.

`INV-CTR-03` The image entrypoint is `fossil-chatgpt-action`; it exposes only the Action process.

`INV-CTR-04` Production examples bind/publish only the Action port and mount canonical data read-only.

## HTTPS and proxy invariants

`INV-HTTPS-01` A production public origin is represented by `FOSSIL_ACTION_PUBLIC_BASE_URL`, which must be an origin-only `https://` URL.

`INV-HTTPS-02` When configured, `/openapi.json.servers[0].url` exactly equals `FOSSIL_ACTION_PUBLIC_BASE_URL` with no trailing slash.

`INV-HTTPS-03` Caller-supplied `Forwarded`, `X-Forwarded-Proto`, `X-Forwarded-Host`, and `X-Forwarded-Port` cannot override the configured public origin. Uvicorn proxy-header processing is disabled by the application entrypoint.

`INV-HTTPS-04` TLS termination, tunnels, DNS, and certificates are external deployment responsibilities. The repository never provisions them.

## OpenAPI / Custom GPT invariants

`INV-OAI-01` The document is OpenAPI 3.1.x and contains `info`, `paths`, `components.schemas`, and `components.securitySchemes` objects.

`INV-OAI-02` `components.schemas` is a valid object and defines explicit `ErrorDetail`, `ErrorEnvelope`, `FossilRecord`, `LineageResponse`, and `CapabilitiesResponse` schemas.

`INV-OAI-03` Every successful Action response has an explicit JSON schema with named properties or a `$ref` to such a schema; error responses use `ErrorEnvelope`.

`INV-OAI-04` Operation IDs are stable and unique: `fossilSearch`, `fossilRead`, `fossilLineage`, `fossilActionCapabilities`.

`INV-OAI-05` The generated `paths` object contains only the four authenticated Action paths. `/openapi.json` is the discovery document and is not described as an Action operation.

`INV-OAI-06` The OpenAPI security scheme is HTTP bearer and all Action operations inherit bearer security.

`INV-OAI-07` The schema contains no MCP, ingest, proposal, validation, commit, mutation, Neo4j, graph-admin, filesystem, secret, token value, or credential operation.

## Rollback invariant

`INV-RBK-01` Rollback requires only stopping/removing the Action container/process and reverting the PR/commit; canonical FOSSIL data is not migrated or mutated by this feature.
