# Holdout plan — FOSSIL read-only ChatGPT Action

## Purpose

The committed suite at `tests/holdout/test_chatgpt_action_holdout.py` is a black-box behavioral holdout separated from focused implementation tests. A PR cannot make committed tests literally hidden from its author, so downstream integrators should treat this file as the public holdout specification and may keep additional equivalent cases private/out-of-tree.

The holdout judges only externally observable security/compatibility behavior plus deployment artifacts that can be inspected without relying on private helper logic.

## Required cases

### Authentication

- no `Authorization` header;
- empty value;
- wrong scheme (`Basic`, raw token);
- `Bearer` without token;
- incorrect token;
- exact token with trailing/embedded whitespace;
- duplicate `Authorization` headers;
- mixed-case `Bearer` scheme succeeds with the exact token;
- token value remains case-sensitive.

Expected: all invalid forms return `401` + `WWW-Authenticate: Bearer`; no token is reflected.

### Proxy and HTTPS origin

Fixed-origin mode:

- send forged `Forwarded`, `X-Forwarded-Proto`, `X-Forwarded-Host`, and host headers;
- expected schema server remains the configured fixed HTTPS origin.

Trusted-proxy mode:

- forwarded HTTPS headers from an untrusted peer -> `503`;
- trusted peer + missing proto -> `503`;
- trusted peer + `http` proto -> `503`;
- trusted peer + missing host -> `503`;
- comma-separated proto/host chains -> `503`;
- host containing whitespace, path, userinfo, or invalid port -> `503`;
- trusted peer + exactly one HTTPS proto and one valid host -> `200`, HTTPS server URL;
- no case may emit `http://` in `servers`.

### Request framing and validation

- declared body above limit;
- actual body above limit;
- malformed/negative `Content-Length`;
- invalid UTF-8/JSON;
- JSON array/scalar instead of object;
- extra fields attempting `commit`, `mcp`, filesystem path, or Cypher-like graph mutation;
- empty or >8192-char search query;
- boolean/string/zero/negative/>100 search limit;
- path-like event/conversation/node identifiers.

Expected: `400` or `413` before corpus invocation, never `500` and never a mutation.

### Route/method surface

For both GET and POST where meaningful, probe:

- `/mcp`;
- `/ingest`;
- `/actions/propose`;
- `/actions/validate`;
- `/actions/commit`;
- `/actions/redact`;
- `/actions/write`;
- `/admin`;
- `/neo4j`;
- `/graph`;
- `/filesystem`;
- arbitrary unknown path.

Expected: `404` even with valid bearer auth.

Probe allowed paths with unsupported methods. Expected: authenticated Action operations return `405`; `POST /openapi.json` returns `405` without auth.

### Empty canonical corpus

With an existing, empty `canonical/events` directory, authenticated search returns exactly `200 []`. No event file may be created and no fallback data source may fabricate content.

### OpenAPI / private GPT compatibility

Validate the live schema with an independent OpenAPI 3.1 validator and assert:

- `components.schemas` is non-empty;
- named request schemas exist;
- successful response schemas resolve to objects with explicit properties;
- `ErrorEnvelope` is used for errors;
- exactly four Action paths exist;
- operation IDs are unique/stable;
- HTTP bearer security is declared;
- no prohibited operation/path appears;
- every advertised server URL is HTTPS;
- no token/config/credential value appears.

### Container/deployment holdout

Against a built image/container, independently inspect:

- effective UID/GID are 10001;
- Docker host publication is exactly `127.0.0.1:8787`;
- `/var/lib/fossil` mount reports `RW=false`;
- an in-container write probe fails and creates no host file;
- image config/history contain no runtime credential;
- application logs do not contain the runtime credential;
- empty authenticated search returns `[]`;
- prohibited routes remain `404`;
- trusted-proxy test network can produce the intended HTTPS origin only from the explicitly trusted client IP.

## Out-of-tree/private extensions

A local integrator may add private holdouts for:

- unusual duplicate-header normalization by the selected reverse proxy;
- IPv6 trusted proxy CIDRs;
- non-default HTTPS ports;
- malformed Unicode host/query values;
- container restart/reboot behavior under Docker Desktop;
- tunnel-specific header normalization.

Those tests should preserve the same normative invariants and must never embed a real credential.
