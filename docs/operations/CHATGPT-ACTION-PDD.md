# PDD — FOSSIL read-only ChatGPT Action

## Problem statement and intended users

A private ChatGPT Custom GPT needs a narrow, auditable retrieval interface to FOSSIL without receiving any durable-write, ingestion, MCP, graph-mutation, shell, or arbitrary-filesystem capability. The intended operator is a local integrator running `Pukujan/fossil-core` on one Windows PC and exposing only this bounded Action service through an independently managed HTTPS reverse proxy or tunnel.

The visible user experience is limited to asking the private GPT to search readable FOSSIL knowledge, read a known durable event, inspect conversation lineage, or describe the Action's read-only capabilities.

## Target environment

The supported target for PR #235 is specific:

- host OS: Windows;
- Linux container runtime: Docker Desktop with the WSL 2 backend;
- installed WSL distributions include Ubuntu and Ubuntu-22.04 on `D:`;
- Docker Desktop WSL storage is on `D:\DockerDesktopWSL`;
- Docker integration inside the Ubuntu distribution is **not required** and must not be assumed;
- Podman is not installed and is not a dependency;
- Linux-native systemd/Quadlet and cloud-VM deployment are non-goals;
- Docker lifecycle commands are expected to run from Windows/PowerShell against Docker Desktop's Linux engine;
- source, canonical data, and local runtime secret material remain under `D:\FossilBrokerWorker\chatgpt-action\`.

Required host layout:

```text
D:\FossilBrokerWorker\chatgpt-action\
  fossil-core\
  data\
    canonical\
      events\
  secrets\
    chatgpt-action.env
```

The populated `secrets\chatgpt-action.env` is local-only and must never be committed.

## Scope: normative read-only boundary

The Action edge provides exactly five externally visible paths:

1. unauthenticated OpenAPI discovery at `GET /openapi.json`;
2. bearer-authenticated search at `POST /actions/search`;
3. bearer-authenticated durable-event read at `POST /actions/read`;
4. bearer-authenticated lineage read at `POST /actions/lineage`;
5. bearer-authenticated capability metadata at `GET /actions/capabilities`.

The OpenAPI document contains only the four authenticated Action operations. `/openapi.json` is discovery, not an Action operation.

The service reuses FOSSIL pack and skill authorization and reads canonical event files through an Action-specific read-only event-store view. It does not require Neo4j or Graphiti.

## Non-goals and explicit prohibitions

The Action edge MUST NOT expose or implement:

- MCP transport, `/mcp`, MCP discovery, or MCP tool execution;
- reviewed ingestion or `/ingest`;
- proposal, validation, commit, redaction, deletion, or any durable mutation;
- write, admin, management, shell, process-control, or arbitrary command endpoints;
- Graphiti or Neo4j query/mutation/admin APIs;
- arbitrary graph mutation or unrestricted graph-query strings;
- caller-selected filesystem paths, arbitrary file reads/writes, directory listing, or path traversal;
- runtime configuration, environment-variable, bearer-token, tunnel credential, account credential, or Custom GPT credential disclosure;
- creation or operation of a public tunnel, DNS name, TLS certificate, reverse proxy, or Custom GPT;
- public deployment from CI;
- Podman, systemd, Quadlet, Kubernetes, or a cloud VM.

These prohibitions remain in force for authenticated callers.

## Threat model

The public HTTPS origin is assumed to receive hostile traffic. Relevant threats include:

- missing, malformed, duplicated, smuggled, or incorrect bearer authorization;
- unsupported HTTP methods and unknown/prohibited route probing;
- oversized bodies, invalid UTF-8, malformed JSON, type/range confusion, and extra-field capability smuggling;
- path traversal through event/conversation/node identifiers;
- attempts to smuggle graph queries or write instructions through otherwise valid JSON;
- forged `Forwarded`/`X-Forwarded-*` headers intended to make `/openapi.json` advertise an attacker-controlled or plain-HTTP origin;
- accidental root execution;
- accidental writable canonical-data mounts;
- accidental public binding of the container port to all host interfaces;
- exception/error leakage of local Windows/Linux paths, environment data, secrets, or stack traces;
- OpenAPI regressions that make GPT Action import ambiguous or silently widen capabilities;
- image-layer, CI-log, documentation, or fixture leakage of a real secret;
- implementation drift that enables MCP, ingest, proposal, validation, commit, redaction, graph mutation, or filesystem access.

Host compromise, reverse-proxy/tunnel-provider compromise, theft of a real bearer token, and compromise of the ChatGPT account remain operator/security-operations concerns. This PR reduces blast radius but cannot solve a compromised trusted host or credential.

## Trust boundaries

1. **Public HTTPS boundary.** An operator-managed tunnel/reverse proxy terminates TLS and forwards only to the Windows loopback listener for this Action service.
2. **Windows loopback boundary.** Docker publishes container port 8787 only as `127.0.0.1:8787`; it must not be bound to `0.0.0.0`, `::`, or a LAN address on the Windows host.
3. **Proxy-origin boundary.** The OpenAPI origin is either a fixed operator-configured `https://` origin or is derived from `X-Forwarded-Proto` + `X-Forwarded-Host` only when the request peer is inside an explicit trusted proxy CIDR. Uvicorn's global proxy-header trust remains disabled.
4. **Authentication boundary.** Every `/actions/*` request requires exactly one valid bearer header. `/openapi.json` is public and contains no secret.
5. **Authorization boundary.** Authenticated requests still pass through FOSSIL skill and pack-read authorization.
6. **Canonical-data boundary.** `D:\...\data` is bind-mounted at `/var/lib/fossil` read-only. The Action event-store view provides read operations only and has no commit/redact API.
7. **Projection boundary.** Neo4j/Graphiti are not initialized and are not reachable through this service.
8. **Operator-secret boundary.** Real bearer/tunnel/Custom-GPT credentials exist only in operator-controlled local systems and are outside Git, CI, docs, tests, issues, and this implementation package.

## Secret handling

The repository contains only variable names and clearly non-secret example placeholders. The real bearer token is generated and stored by the local integrator after code review in:

```text
D:\FossilBrokerWorker\chatgpt-action\secrets\chatgpt-action.env
```

The application does not return the token, log request authorization headers, add token examples to OpenAPI, or embed a token in the image. CI may use a clearly synthetic test-only string that is not a credential.

## HTTPS/reverse-proxy assumptions

The Action process itself listens on HTTP inside the Docker/host-local boundary. The public endpoint MUST be HTTPS.

Schema-origin precedence is fail-closed:

1. a configured `FOSSIL_ACTION_PUBLIC_BASE_URL` (must be origin-only HTTPS) is authoritative and forwarded headers cannot override it;
2. otherwise a direct HTTPS request may define the origin;
3. otherwise `X-Forwarded-Proto: https` plus one `X-Forwarded-Host` may define the origin only when the request peer matches `FOSSIL_ACTION_TRUSTED_PROXY_CIDRS`;
4. otherwise `GET /openapi.json` returns `503` rather than advertising an internal HTTP URL.

Never configure a wildcard trusted proxy CIDR merely to make schema generation work.

## Data availability and empty-corpus behavior

The current target canonical event directory is empty. That is valid. If `data\canonical\events` exists and is readable but contains no events, authenticated `POST /actions/search` returns HTTP `200` with `[]`. The service must not fabricate corpus content, seed fake events, query Neo4j as a fallback, or convert an empty corpus into an error.

If the canonical event directory itself is missing or inaccessible, startup/reads fail rather than silently creating or mutating canonical state.

## Deployment assumptions

The local integrator will:

- clone/check out PR #235 under the required `D:` layout;
- run the verification suite;
- build the Linux image using Docker Desktop from Windows;
- create the real local env file and secret outside source control;
- mount `D:\...\data` read-only;
- publish the container port only to Windows `127.0.0.1:8787`;
- establish the public HTTPS reverse-proxy/tunnel separately;
- import `/openapi.json` into a private Custom GPT and configure authentication there.

This PR performs none of those deployment/account/credential actions.
