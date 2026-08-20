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
without logging or reflecting its value. `/healthz` and `/readyz` remain public
operational probes; MCP, ingestion, and all other HTTP routes require the
token. Pack, Skill, and capability authorization remains enforced by the
existing FOSSIL boundary after authentication.

Use [`config/fossil-mcp.env.example`](../../config/fossil-mcp.env.example) only
as a placeholder template. Keep the populated environment file outside Git.
