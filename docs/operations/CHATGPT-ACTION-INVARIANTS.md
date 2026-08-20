# Security and behavior invariants — FOSSIL ChatGPT Action

These are normative, machine-testable release invariants for the standalone Custom GPT Action.

## Public surface

1. The complete routable surface is exactly `GET /openapi.json`, `POST /actions/search`, `POST /actions/read`, and `GET /actions/capabilities`.
2. `/openapi.json` is the only unauthenticated route.
3. `/actions/lineage` is not routable or advertised until the standalone composition has a genuine read-only lineage provider.
4. `/mcp`, `/ingest`, propose, validate, commit, promote, redact, write, admin, graph, Neo4j, filesystem, shell, and unknown paths return 404 for authenticated and unauthenticated callers.
5. Unsupported methods on an allowlisted path return 405 and do not invoke the adapter.

## Authentication

6. Every `/actions/*` route requires exactly one `Authorization` header with the HTTP bearer scheme and the exact opaque token.
7. The bearer scheme comparison is case-insensitive; the token comparison is case-sensitive and constant-time.
8. Missing, duplicate, wrong-scheme, whitespace-confused, or incorrect credentials return 401 plus `WWW-Authenticate: Bearer`.
9. Authentication failures never reflect the token or runtime configuration.

## Request validation and resource bounds

10. Request JSON must be a UTF-8 object; malformed JSON and non-object JSON return 400.
11. Search accepts only `query` and optional integer `limit`; read accepts only `event_id`. Extra fields are rejected.
12. Search query is non-empty and at most 8192 characters. Limit is a non-boolean integer from 1 through 100.
13. Event IDs must match the opaque identifier grammar before filesystem lookup; traversal/path syntax is rejected.
14. `FOSSIL_ACTION_MAX_REQUEST_BYTES` defaults to 65536 and is bounded by server configuration.
15. A declared `Content-Length` above the limit is rejected before adapter invocation.
16. Independently of `Content-Length`, chunks are counted as they are read; the request is rejected immediately when cumulative bytes exceed the limit.
17. Absent, chunked, or understated `Content-Length` cannot bypass the body limit. Oversize rejection returns 413 and the adapter is not invoked.
18. Production Action request handling does not call `await request.body()`.

## Canonical-data and redaction invariants

19. The standalone event-store view has read methods only; it exposes no commit, prepare, validate, redact, put, delete, publish, or write method.
20. Canonical data is mounted into the production container read-only.
21. `_redactions` directories and tombstone JSON are never yielded as normal events or search results.
22. If an event has a redaction tombstone, search suppresses it even if the old event bytes remain on disk.
23. Read of a redacted event returns generic 404 and does not expose redaction reason, authority, tombstone contents, or the fact pattern beyond not-found.
24. An empty canonical event store is valid and authenticated search returns `200 []` without fabricated content.

## OpenAPI / Custom GPT compatibility

25. `/openapi.json` emits OpenAPI 3.1 and passes `openapi-spec-validator`.
26. `components.schemas` exists and is a non-empty object.
27. Successful object response schemas declare explicit properties; schema references resolve.
28. OpenAPI paths are exactly search, read, and capabilities; lineage and all mutation routes are absent.
29. The capabilities schema and runtime response both report exactly `action_capabilities: ["search", "read"]` and all write/ingest/MCP/graph-mutation flags as false.
30. Operation IDs are unique.
31. The schema contains no bearer-token value, local filesystem path, credential example, HTTP public server URL, MCP route, mutation route, or graph/database escape hatch.

## HTTPS origin and proxy trust

32. A configured `FOSSIL_ACTION_PUBLIC_BASE_URL` must be an origin-only `https://` URL and is authoritative over request headers.
33. When no fixed public origin is configured, only validated forwarded HTTPS origin metadata from a peer inside an explicit `FOSSIL_ACTION_TRUSTED_PROXY_CIDRS` network may define `servers[0].url`.
34. Uvicorn global proxy-header trust remains disabled.
35. A direct HTTPS request's `Host` header is never public-origin authority by itself.
36. Forged, ambiguous, comma-chained, malformed, or untrusted forwarded host/proto metadata cannot influence the schema origin.
37. If no trustworthy HTTPS origin exists, `/openapi.json` returns 503 and does not emit an HTTP or caller-controlled server URL.

## Container / host boundary

38. The production image runs as non-root UID/GID 10001.
39. Docker Desktop publication is exactly loopback-only `127.0.0.1:8787:8787` in the documented target command/workflow.
40. The canonical host data mount is `:ro`; an in-container write probe to it fails.
41. No real runtime credential is present in image history, image configuration, repository examples, documentation examples, application responses, or application logs.
42. The HTTPS reverse proxy/tunnel is external to the container; the repository does not create or manage real tunnel credentials.

## Mutation assurance

43. The targeted mutation runner must fail the release if any defined security mutant survives or any mutation anchor cannot be applied.
44. Mutants cover bearer bypass, route widening, lineage reintroduction, write-route exposure, declared and streaming size-check removal, validation weakening, proxy over-trust, direct-Host trust, HTTP schema origin, OpenAPI schema regressions, redaction re-inclusion, mutable store methods, root container execution, writable canonical mount, and non-loopback publication.
