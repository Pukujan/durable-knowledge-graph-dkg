# Public FOSSIL MCP edge

The FOSSIL network app exposes the existing `ThinMCPAdapter` tool boundary at
`/mcp`. It requires a host-local bearer token before any MCP request reaches
the MCP server or canonical `CorpusService`.

Configure the token in one of two ways:

- pass `bearer_token=` to `create_node_network_app()`; or
- set `FOSSIL_MCP_BEARER_TOKEN` in the local process environment.

The app fails to construct when no token is configured. Requests must send:

```text
Authorization: Bearer <API_TOKEN>
```

Missing, malformed, duplicate, and incorrect authorization headers receive a
generic `401` response with `WWW-Authenticate: Bearer`. The token is compared
without logging or reflecting its value. Pack, Skill, and capability
authorization remains enforced by the existing FOSSIL boundary after
authentication.

The node application also has `/healthz`, `/readyz`, and `/ingest` for local
operations. They are **not part of the public internet contract**. Configure the
public tunnel/reverse proxy so `fossil.design-bakery.com` forwards only `/mcp`;
non-MCP paths must remain blocked externally. `/healthz` and `/readyz` may stay
unauthenticated on the local listener for local operational probing, while
`/ingest` remains bearer-protected locally.

For the public hostname, keep the MCP SDK listener host as loopback and supply
an explicit `TransportSecuritySettings` allowlist for
`fossil.design-bakery.com`; see `PUBLIC-MCP-INVARIANTS.md`. Do not work around a
421 Host rejection by changing the SDK `host` value to the public hostname
without an explicit Host/Origin policy.

Use [`config/fossil-mcp.env.example`](../../config/fossil-mcp.env.example) only
as a placeholder template. Keep the populated environment file outside Git.
