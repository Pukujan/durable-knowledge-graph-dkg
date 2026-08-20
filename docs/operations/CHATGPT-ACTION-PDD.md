# PDD — Read-only ChatGPT Action edge

## User-visible problem

A private ChatGPT Custom GPT needs a narrow, auditable way to retrieve knowledge from FOSSIL without gaining any durable write, ingestion, MCP, database, graph-mutation, or filesystem capability. The integration must be deployable by a local integrator while preserving FOSSIL as the canonical authority and keeping all credentials host-local.

## Scope

The Action edge provides exactly five user-visible capabilities:

1. unauthenticated OpenAPI discovery at `GET /openapi.json`;
2. bearer-authenticated search at `POST /actions/search`;
3. bearer-authenticated durable-event read at `POST /actions/read`;
4. bearer-authenticated lineage read at `POST /actions/lineage`;
5. bearer-authenticated capability metadata at `GET /actions/capabilities`.

The edge reuses FOSSIL pack authorization and corpus read semantics. It does not introduce a second semantic authority and does not require Neo4j or Graphiti.

## Non-goals

The Action edge MUST NOT expose or implement:

- MCP transport or `/mcp`;
- reviewed ingestion or `/ingest`;
- proposal, validation, commit, redaction, or other durable mutation;
- Graphiti or Neo4j query/mutation APIs;
- arbitrary graph traversal outside the canonical lineage/search contracts;
- arbitrary filesystem paths, file reads, file writes, shell execution, or process control;
- credential creation, storage, display, logging, or transport beyond the bearer header supplied by the caller;
- tunnel, DNS, TLS certificate, reverse-proxy, Custom GPT, or account provisioning;
- public deployment from CI.

## Threat model

### Adversaries and failure modes

The boundary assumes an internet-reachable HTTPS origin may receive hostile requests. Relevant threats include:

- unauthenticated callers attempting corpus reads;
- malformed or ambiguous bearer headers;
- oversized bodies intended to consume memory;
- requests to hidden/private FOSSIL routes;
- method confusion such as `GET /actions/search` or `POST /openapi.json`;
- payload fields attempting to smuggle filesystem paths, graph queries, write commands, or MCP instructions;
- forged `X-Forwarded-*` headers intended to alter the OpenAPI origin;
- accidental execution as root or with a writable canonical-data mount;
- error messages leaking secrets, local paths, or internal exception details;
- OpenAPI regressions that make the schema unsuitable for Custom GPT Action import;
- implementation drift that silently widens the route or capability allowlist.

### Out of scope threats

Host compromise, compromise of the reverse proxy/tunnel provider, theft of a real bearer token, or compromise of the ChatGPT account are deployment/operator concerns. The package documents mitigations but does not provision or operate those systems.

## Trust boundaries

1. **Public HTTPS boundary** — an operator-managed reverse proxy or tunnel terminates TLS. It MUST forward only to the Action process.
2. **Action process boundary** — the process accepts only the five scoped capabilities above. It MUST ignore untrusted forwarded headers for schema generation.
3. **Authentication boundary** — every `/actions/*` operation requires one configured bearer token. `/openapi.json` is deliberately public and contains no secret.
4. **Authorization boundary** — authorized requests still pass through FOSSIL pack and skill authorization.
5. **Canonical-data boundary** — the container/process receives the canonical event tree read-only. The Action-specific event-store adapter exposes only `get`, `iter_events`, and redaction-state reads; no commit/redact API exists on that adapter.
6. **Projection boundary** — Neo4j/Graphiti are not dependencies of the Action edge and are never exposed through it.
7. **Operator boundary** — real secrets, public endpoint provisioning, DNS/TLS, and Custom GPT credentials remain outside Git and outside this package.

## Deployment assumptions

- A local integrator may clone the PR from Windows/WSL with the repository and canonical data located on `D:` and bind-mounted into Linux/Podman/Docker paths.
- The Action container runs as a non-root UID.
- Canonical data is mounted read-only.
- TLS is terminated upstream; the Action service itself can listen on a private/loopback or container-network HTTP socket.
- `FOSSIL_ACTION_PUBLIC_BASE_URL` is set to the externally reachable `https://` origin. The service does not trust caller-supplied `X-Forwarded-Proto` or `X-Forwarded-Host` when generating OpenAPI.
- The operator supplies the bearer token at runtime from a host-local secret mechanism; no real value belongs in Git, CI, issue comments, docs, or chat transcripts.

## Read-only boundary

The boundary is normative: only OpenAPI discovery, search, durable-event read, lineage, and capability metadata are permitted. MCP, ingest, proposal, validation, commit, graph mutation, arbitrary filesystem access, and secret exposure are prohibited even for authenticated callers.
