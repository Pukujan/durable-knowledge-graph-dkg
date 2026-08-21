# Public MCP requirements and invariants

This document is the assurance contract for the generic public FOSSIL MCP edge in issue #231.

## Required external shape

```text
Any MCP-capable client
        |
        | HTTPS + Authorization: Bearer <API_TOKEN>
        v
https://fossil.design-bakery.com/mcp
        |
        v
local FOSSIL MCP server -> ThinMCPAdapter -> CorpusService
```

The edge is client-agnostic. It is not a ChatGPT Action, OpenAPI service, or OpenAI-specific integration.

## Invariants

1. **HTTPS only.** The external acceptance URL is `https://fossil.design-bakery.com/mcp`.
2. **Authentication precedes MCP parsing and tool dispatch.** Missing, malformed, duplicate, or incorrect bearer credentials fail with a generic `401` and must not reach a tool.
3. **The bearer token is authentication, not semantic authorization.** Pack scope, Skill capabilities, actor provenance, proposal validation, and durable commit rules remain enforced by FOSSIL after authentication.
4. **Real MCP transport only.** `/mcp` speaks the pinned MCP Streamable HTTP protocol; no REST/OpenAPI compatibility layer is required.
5. **Bounded requests.** The MCP request-body limit remains active for authenticated callers. Authentication also runs before parsing an unauthenticated oversized or malformed request.
6. **Explicit public-host transport security.** Keep the MCP SDK `host` value loopback (`127.0.0.1`) and explicitly configure `TransportSecuritySettings` for the public hostname. Do not work around HTTP 421 by setting the SDK `host` argument to the public hostname without an explicit Host/Origin policy.
7. **Public routing is MCP-only.** The internet-facing tunnel/reverse proxy routes `/mcp`; `/healthz`, `/readyz`, and `/ingest` remain local/private operational routes even though they exist on the node application.
8. **No graph/admin escape.** No arbitrary Neo4j/Cypher, graph mutation, filesystem, shell, admin, OpenAPI, or `/actions/*` route is part of the public MCP contract.
9. **Secrets stay local.** The real token is never committed, logged, returned in errors, written into CI artifacts, or supplied on a command line.
10. **Canonical FOSSIL semantics survive the network edge.** Existing redaction, pack isolation, lifecycle, lineage, proposal/validation/commit, and projection-outage invariants remain authoritative.

## Public-host configuration

For a reverse proxy that preserves the public `Host` header, configure the MCP SDK explicitly:

```python
from mcp.server.transport_security import TransportSecuritySettings

security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=[
        "fossil.design-bakery.com",
        "fossil.design-bakery.com:*",
    ],
    allowed_origins=[],
)

app = create_node_network_app(
    node,
    context=context,
    bearer_token=token,
    host="127.0.0.1",
    transport_security=security,
)
```

The public MCP clients in the current target are non-browser clients, so they do not need an `Origin` header. If browser-origin access is deliberately added later, its origins must be explicitly reviewed and allowlisted rather than using a wildcard.

## Cloud/CI assurance

`tests/holdout/test_public_mcp_holdout.py` exercises:

- absent/malformed/wrong/duplicate bearer credentials;
- token non-reflection;
- public hostname allowlisting and forged Host/Origin rejection;
- auth-before-parse behavior;
- MCP body-size enforcement;
- bearer token not widening a read-only Skill into write authority;
- pack-scope rejection on the reviewed ingestion route;
- absence of graph/filesystem/shell/admin/vendor-specific HTTP routes.

`scripts/run_public_mcp_mutations.py` deliberately weakens those controls and requires every targeted mutant to be killed by the holdout suite.

## What still requires the real local PC

Cloud tests cannot prove Windows/WSL networking, the real DNS/tunnel mapping, host-local secret injection, PC sleep/reboot behavior, or reachability from the public internet. Local acceptance should therefore be mechanical rather than exploratory:

1. run the exact reviewed FOSSIL SHA locally;
2. inject the real bearer token through the host-local environment;
3. configure explicit MCP transport security for `fossil.design-bakery.com`;
4. expose only `/mcp` through the HTTPS tunnel/reverse proxy;
5. from a machine outside the local process, run `scripts/verify_public_mcp_edge.py`;
6. restart the local FOSSIL process/tunnel once and rerun the same verifier;
7. record only the exact SHA and sanitized PASS/FAIL receipt.

A local failure is evidence about the WSL/tunnel/deployment boundary; it is not permission to weaken the MCP, FOSSIL authorization, or redaction invariants.
