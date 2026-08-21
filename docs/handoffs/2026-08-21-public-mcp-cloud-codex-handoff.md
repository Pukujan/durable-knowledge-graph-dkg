# Public FOSSIL Action/MCP handoff for Cloud Codex

**Date:** 2026-08-21  
**Repository:** `Pukujan/fossil-core`  
**Reviewed PR head:** `ff1524c67e968019da13b957456ebb8e21b5357a` (PR #236)

## Current verified state

### ChatGPT Action edge

- Public schema: `https://fossil.design-bakery.com/openapi.json`
- Authenticated capability probe: HTTP 200
- The running Action container is healthy and uses the existing host-local bearer secret.
- The OpenAPI document now advertises `https://fossil.design-bakery.com` rather than the stale temporary Cloudflare URL.
- The Action surface is read-only: search, read, and capabilities only. It does not expose MCP, ingest, commit, or arbitrary graph mutation.

### MCP edge

- The PR #236 network app was exercised from the exact reviewed head.
- Missing bearer auth returns HTTP 401.
- Wrong bearer auth returns HTTP 401.
- Valid bearer auth returns HTTP 200.
- Tool discovery returned the frozen seven-tool surface:
  `fossil.search`, `fossil.read`, `fossil.lineage`, `fossil.propose`,
  `fossil.validate`, `fossil.commit`, `fossil.manage`.
- Public non-MCP routes were blocked.
- The sanitized external verifier passed.

The temporary MCP URL used for this edge-only proof was:

`https://scanner-finishing-beast-adipex.trycloudflare.com/mcp`

It is an accountless quick tunnel and must not be treated as a production URL.

## Important implementation boundary

The local MCP proof used an isolated PR worktree, an empty writable development canonical store, and a local projection seam so the authentication, MCP transport, tool discovery, and route-isolation contract could be checked without Neo4j/Graphiti. This is edge assurance only, not production semantic proof.

Do **not** treat the temporary local launcher, quick tunnel, empty data root, or projection seam as an approved production deployment. Do not commit the bearer secret, Desktop `.env`, tunnel token, or generated runtime data.

## Why the first online Action check failed

The Action container was healthy, but its OpenAPI `servers` value pointed at a dead temporary `trycloudflare.com` URL. The container was restarted with the stable public base URL, and the public schema/capability probes now pass. A ChatGPT GPT that imported the old schema must re-import the stable schema and configure API-key/Bearer authentication with the same host-local secret.

## Cloud Codex plugin work

The plugin builder should choose and document one of these separate integrations:

1. **ChatGPT Action adapter:** import the stable OpenAPI document and expose only read/search capabilities.
2. **Generic MCP adapter:** use a dedicated production MCP hostname and `/mcp` route after a real node, canonical data root, Graphiti/Neo4j projection policy, named tunnel/reverse-proxy route, and host-local secret management are ready.

Do not merge the two public surfaces into one unrestricted route set. Preserve the PR #236 requirements: explicit Host/Origin transport policy, authentication before parsing/dispatch, no public non-MCP routes, bounded requests, pack/skill authority after authentication, and no secret reflection.

## Remaining production work

- Replace the temporary MCP quick tunnel with a named, stable HTTPS route.
- Run the MCP app against the authoritative canonical data root and approved projection configuration.
- Add a real service launcher/container definition rather than the local development seam.
- Run the verifier from outside the host after restart/reboot testing.
- Keep PR #236 unmerged until the exact-head Graphiti-live job and all required review gates finish.
