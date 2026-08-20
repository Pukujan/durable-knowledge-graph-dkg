# PDD — FOSSIL read-only ChatGPT Action

## Status

This document describes the standalone Custom GPT Action deployed from PR #235. It is a security boundary, not a general FOSSIL HTTP API.

## Problem statement and intended users

A private ChatGPT Custom GPT needs a narrow, auditable retrieval interface to FOSSIL without receiving durable-write, ingestion, MCP, graph-mutation, shell, or arbitrary-filesystem capability. The intended operator is a local integrator running `Pukujan/fossil-core` with Docker Desktop's WSL 2 Linux engine on Windows and exposing only the loopback-bound Action service through an independently managed HTTPS reverse proxy or tunnel.

The user-visible behavior is intentionally small: search readable durable FOSSIL events, read one known durable event, and inspect bounded capability metadata.

## Product scope

The standalone public contract is exactly:

- public, unauthenticated `GET /openapi.json`;
- bearer-authenticated `POST /actions/search`;
- bearer-authenticated `POST /actions/read`;
- bearer-authenticated `GET /actions/capabilities`.

The Action uses the existing pack/Skill-gated `ThinMCPAdapter` / `CorpusService` read boundary, but it does not expose MCP itself.

### Lineage decision

FOSSIL's domain service and MCP boundary support lineage when a lineage provider is configured. The standalone Action composition in this release has no durable lineage provider. Therefore `/actions/lineage` is deliberately **not** part of the public Action contract, OpenAPI schema, capabilities response, or route allowlist.

A future release may add lineage only after a real read-only lineage source is wired into the standalone composition and exercised end to end. An advertised route that deterministically cannot succeed is prohibited.

## Non-goals and prohibited capabilities

This service must not expose:

- `/mcp` or any MCP transport;
- `/ingest`;
- proposal, validation, commit, promotion, redaction, write, or administrative operations;
- Graphiti or Neo4j mutation/query escape hatches;
- arbitrary graph mutation;
- arbitrary filesystem reads or path-based retrieval;
- shell/command execution;
- runtime configuration, environment-variable dumps, bearer tokens, tunnel credentials, or Custom GPT credentials;
- current-project orchestration state or other mutable application state.

The service is not an ingestion API, knowledge-management UI, FOSSIL node replacement, or generic remote-control surface.

## Data semantics

The canonical durable event store remains authoritative. Graph/search projections remain rebuildable downstream representations and are not required by this standalone Action composition.

Search iterates only canonical event objects from normal event buckets. `_redactions` is metadata and is never a search corpus. If a redaction tombstone exists for an event, the event is suppressed from search even if its old bytes still exist because of a partial or forensic filesystem state. A read of a redacted event returns the same bounded not-found behavior used for unavailable resources and does not disclose redaction metadata.

An empty canonical events directory is valid. Authenticated search against an empty corpus returns HTTP 200 with `[]`; the service must never fabricate content to make a smoke test non-empty.

## Target deployment assumptions

Target host:

- Windows;
- Docker Desktop using its WSL 2 Linux engine;
- no Podman requirement;
- no assumption that the application runs as a Linux-native systemd service;
- source, canonical data, and local secret file retained on `D:`.

Expected local layout:

```text
D:\FossilBrokerWorker\chatgpt-action\
  fossil-core\
  data\
    canonical\
      events\
  secrets\
    chatgpt-action.env
```

The container publishes `8787/tcp` only as `127.0.0.1:8787` on the Windows host. Canonical data is bind-mounted at `/var/lib/fossil` read-only. The container executes as a non-root user.

## Public HTTPS assumption

The container itself serves HTTP on the loopback/private side. A separately managed HTTPS reverse proxy or tunnel is the only intended public exposure point.

OpenAPI discovery must advertise an HTTPS public origin. Origin authority is fail-closed:

1. preferred: a fixed `FOSSIL_ACTION_PUBLIC_BASE_URL=https://...`; or
2. advanced: validated `X-Forwarded-Proto: https` + `X-Forwarded-Host` from a peer whose source address matches an explicit `FOSSIL_ACTION_TRUSTED_PROXY_CIDRS` entry.

A direct HTTPS request's `Host` header is not trusted as public-origin authority. Without a fixed origin or trusted proxy-derived origin, `/openapi.json` returns 503.

## Trust boundaries

### Boundary A — Custom GPT / public Internet to HTTPS edge

Untrusted input includes paths, methods, headers, authorization text, JSON bodies, forwarded headers, host headers, and request framing. Only the documented route/method allowlist is processed.

### Boundary B — HTTPS edge to loopback Action container

The proxy/tunnel should forward only to `127.0.0.1:8787`. The Docker port must not be published on all interfaces. Forwarded origin headers are trusted only when the immediate peer address is explicitly configured as trusted.

### Boundary C — Action process to canonical data

The process sees canonical data through a read-only bind mount and an application object exposing only `get`, `iter_events`, and redaction-state checks required for reads. No event commit/redact method is present on the Action store view.

### Boundary D — Action adapter to FOSSIL domain service

Pack read permissions and the `skill_corpus-search` capability gate remain in force. Transport code cannot bypass pack authorization or gain arbitrary projection/database mutation.

### Boundary E — local operator secret material

The real bearer token and any tunnel/provider credentials are local deployment state. They are not repository artifacts and must not appear in source, fixtures, image layers, logs, OpenAPI examples, PR comments, or generated responses.

## Threat model

Threats explicitly addressed include:

- unauthenticated or malformed bearer requests;
- duplicate/confused authorization headers;
- accidental route widening;
- write-capability smuggling through extra JSON fields;
- path traversal through event identifiers;
- oversized, chunked, or under-declared request bodies;
- forged `Host`, `Forwarded`, or `X-Forwarded-*` metadata;
- accidental HTTP public origin in the GPT Action schema;
- redaction tombstone or redacted-event leakage through search/read;
- root container execution;
- writable canonical-data mounts;
- non-loopback host publication;
- runtime secret reflection in responses or logs;
- OpenAPI regressions that make the GPT editor misinterpret response shapes.

## Request-size policy

The default request body limit is 64 KiB and is configurable only within the bounded server settings. A declared `Content-Length` above the limit is rejected immediately. Independently, body chunks are counted while streaming and the request is rejected as soon as the accumulated bytes exceed the limit. This prevents absent, chunked, or understated `Content-Length` from forcing full-body buffering before rejection.

## Error philosophy

Errors are bounded JSON envelopes. Authorization failures return 401 with `WWW-Authenticate: Bearer`. Unauthorized packs/capabilities return 403. Missing or redacted resources return a generic 404. Malformed input returns 400, oversized bodies 413, and missing trustworthy HTTPS origin 503. Internal filesystem paths, token values, redaction reasons, and stack traces are not returned.

## Acceptance boundary

This package is build-ready only when focused, standalone integration, architecture, container, holdout, OpenAPI validation, and mutation-assurance checks pass on the exact PR head. Passing CI does not deploy the service, create a real secret, establish a tunnel, or configure a Custom GPT; those remain local integrator actions.
