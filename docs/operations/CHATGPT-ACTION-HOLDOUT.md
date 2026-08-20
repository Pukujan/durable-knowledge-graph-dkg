# Holdout plan — FOSSIL read-only ChatGPT Action

## Purpose

`tests/holdout/test_chatgpt_action_holdout.py` is a black-box behavioral suite separated from focused implementation tests. Because committed tests are visible to the implementation author, downstream integrators may maintain additional equivalent cases privately; this document defines the required behavior without coupling to helper names or internal control flow.

## Required holdout families

### Authentication

- absent authorization;
- empty authorization;
- wrong scheme;
- `Bearer` without a token;
- incorrect token;
- trailing/embedded token whitespace;
- duplicate authorization headers;
- mixed-case bearer scheme with exact token succeeds;
- token value remains case-sensitive.

Expected invalid result: 401 plus `WWW-Authenticate: Bearer`; no credential reflection.

### Truthful public route contract

The only public schema path set is:

- `/actions/search`;
- `/actions/read`;
- `/actions/capabilities`.

`/actions/lineage` must return 404 and must not appear in OpenAPI or capability metadata because the standalone composition has no lineage provider. `/mcp`, `/ingest`, write/mutation/admin/graph/filesystem and unknown paths are also 404.

### OpenAPI / Custom GPT compatibility

- OpenAPI 3.1 validates with `openapi-spec-validator`;
- `components.schemas` is present and non-empty;
- successful response object schemas declare properties;
- all operation IDs are unique;
- only search/read/capabilities are advertised;
- capabilities schema is fixed to `["search", "read"]`;
- no HTTP server URL, runtime token, local path, lineage route, mutation route, MCP route, or graph/database escape hatch appears.

### HTTPS origin authority

Fixed-origin mode:

- forged `Host`, `Forwarded`, and `X-Forwarded-*` values cannot change the configured HTTPS origin.

No-origin/direct-HTTPS mode:

- direct HTTPS plus caller-controlled `Host` without fixed origin or trusted proxy must return 503;
- caller-controlled host value must not be reflected.

Trusted-proxy mode:

- untrusted source peer -> 503;
- missing/wrong proto -> 503;
- missing/malformed/ambiguous host -> 503;
- comma-chained forwarded values -> 503;
- trusted peer + exactly one HTTPS proto + valid host -> 200 with that HTTPS origin.

### Streaming request-size enforcement

With a small configured body limit, exercise:

- declared oversized `Content-Length`;
- actual body larger than the limit;
- absent `Content-Length` with streamed/chunked body;
- deliberately understated `Content-Length` with streamed body;
- malformed JSON;
- non-object JSON.

All oversize variants return 413. Focused tests additionally prove the adapter is never invoked after the limit is exceeded.

### Input confusion / smuggling

- path-traversal-like event IDs;
- Windows paths and `file://` identifiers;
- extra `cypher`, `commit`, mutation, or capability-looking fields;
- boolean/string/out-of-range search limits;
- unsupported HTTP methods.

Expected: fail closed with bounded 400/405 behavior, never adapter capability widening.

### Redaction behavior

Construct both an event file and its redaction tombstone to model a partial/forensic state, plus an unrelated visible event. Prove:

- search for text only in redacted event bytes returns `[]`;
- search for text only in the tombstone returns `[]`;
- the unrelated visible event remains searchable;
- read of the redacted event returns generic 404;
- response does not reveal redaction reason/tombstone metadata.

This prevents both `_redactions` path leakage and stale event-byte leakage.

### Empty corpus

An empty canonical event directory is valid. Authenticated search returns exactly `200 []` and never fabricated corpus content.

### Secret/configuration non-leakage

Across schema, capabilities, authentication failures, malformed input, missing event reads, and redaction failures, responses must not contain the synthetic test token, temporary filesystem root, local `D:` deployment path, or environment variable names that disclose secret placement.

## Container holdout

The container workflow is a separate deployment-shaped holdout. It builds the real image and proves:

- effective UID/GID 10001;
- Docker host publication is `127.0.0.1` only;
- canonical mount reports `RW=false` and rejects a write probe;
- fixed-origin schema resists forged headers;
- search/read honor a redaction negative-control fixture;
- lineage and mutation routes remain 404;
- trusted-proxy HTTPS origin works only from the configured Docker-network peer;
- synthetic runtime token is absent from image history/config and application logs.

## Mutation relationship

The targeted mutation runner executes this holdout plus architecture checks against one deliberate defect at a time. The run fails if any mutant survives or an anchor cannot be applied. New security behavior is not considered covered until an independently stated holdout kills the corresponding mutant.
