# ChatGPT Custom GPT Action boundary

This document describes the **read-only compatibility edge** for using a ChatGPT Custom GPT Action with FOSSIL.

The Action edge is a protocol adapter only. It does not change FOSSIL truth authority, pack authorization, provenance, or the existing MCP contract.

## Security boundary

Deploy the dedicated Action service as the only public ChatGPT-facing surface. It exposes only:

- `GET /openapi.json` — public schema used to configure the GPT Action;
- `POST /actions/search` — `fossil.search` through `ThinMCPAdapter`;
- `POST /actions/read` — `fossil.read` through `ThinMCPAdapter`;
- `POST /actions/lineage` — `fossil.lineage` through `ThinMCPAdapter`;
- `GET /actions/capabilities` — metadata describing this bounded Action surface.

It deliberately does **not** expose `/mcp`, `/ingest`, `fossil.propose`, `fossil.validate`, `fossil.commit`, Neo4j/Graphiti APIs, or arbitrary graph mutation.

All `/actions/*` operations require a bearer token. `/openapi.json` is intentionally unauthenticated so ChatGPT can import the schema.

## Standalone runtime

The production entrypoint is:

```text
fossil-chatgpt-action
```

It boots directly from the canonical FOSSIL event store plus the pack and skill contracts. It does **not** construct Graphiti or connect to Neo4j. This keeps the public edge independent of the private MCP/projector/database runtime.

Runtime variables:

```text
FOSSIL_ACTION_BEARER_TOKEN   required; at least 32 characters
FOSSIL_ACTION_HOST           default 127.0.0.1
FOSSIL_ACTION_PORT           default 8787
FOSSIL_REPOSITORY_ROOT       default current working directory
FOSSIL_DATA_ROOT             default <repository>/data
FOSSIL_PACK_MANIFEST         default examples/packs/common/manifest.json
```

The bearer secret must exist only in the host/deployment secret store or a host-local environment file. Never commit it, put it in an issue, or print it in logs.

## Container build

From the repository root:

```bash
podman build \
  -f docker/chatgpt-action/Dockerfile \
  -t localhost/fossil-chatgpt-action:local \
  .
```

Create a host-local env file outside the repository from `config/chatgpt-action.env.example`, replace the placeholder token with a random secret, and restrict its permissions.

Example local-only container launch:

```bash
podman run --rm \
  --name fossil-chatgpt-action \
  --env-file "$HOME/.config/fossil/chatgpt-action.env" \
  -p 127.0.0.1:8787:8787 \
  -v /ABSOLUTE/PATH/TO/FOSSIL-DATA:/var/lib/fossil:ro,Z \
  localhost/fossil-chatgpt-action:local
```

The canonical data bind should be read-only for this service. The expected event-store path inside that mount is `/var/lib/fossil/canonical/events`.

## Public HTTPS edge

ChatGPT must be able to reach the Action API over HTTPS. Tailscale is **not required** for this public Action path.

Keep the container bound to host loopback as shown above and terminate public HTTPS in a separately configured reverse proxy or outbound tunnel on the PC. Forward only the Action service; do not forward the private FOSSIL Node, MCP, ingestion, Neo4j, or admin surfaces.

The HTTPS layer must preserve the public host/protocol headers so `/openapi.json` advertises the public HTTPS base URL. Before configuring ChatGPT, verify from outside the PC/network:

```text
https://<PUBLIC-ACTION-HOST>/openapi.json
```

and verify that `/mcp` and `/ingest` return `404` on that same host.

## ChatGPT Custom GPT setup

In the ChatGPT web GPT editor:

1. Create or edit the private GPT used for FOSSIL.
2. Open **Configure → Actions**.
3. Import or paste the schema from `https://<PUBLIC-ACTION-HOST>/openapi.json`.
4. Configure Action authentication as an API key/bearer token and enter the same runtime token used by the Action service.
5. Keep the GPT private while validating the integration.
6. Test `fossilSearch`, then `fossilRead`, then `fossilLineage` from the Action test UI.

Do not paste the token into GPT instructions, the OpenAPI document, source control, GitHub issues, or chat messages.

## LOCAL_INFRA handoff

A PC-local agent/Codex session should perform only the machine-specific steps below after this PR is reviewed/merged:

1. build the exact reviewed commit with `docker/chatgpt-action/Dockerfile`;
2. identify the authoritative FOSSIL data root and mount it read-only at `/var/lib/fossil`;
3. generate/store `FOSSIL_ACTION_BEARER_TOKEN` locally without printing it;
4. start the container bound to `127.0.0.1:8787`;
5. configure a public HTTPS reverse proxy or outbound tunnel to that loopback port;
6. verify `/openapi.json`, bearer rejection, authorized search, and `404` for `/mcp`, `/ingest`, and write-like paths;
7. configure the same bearer token in the private Custom GPT Action authentication UI;
8. record only sanitized PASS/FAIL evidence, exact git SHA/image ID, and public hostname — never the secret.

## Acceptance checks

Before using the integration for real work, verify mechanically that:

- `/openapi.json` contains only the four Action paths;
- `/actions/*` rejects missing/wrong bearer tokens;
- `/mcp`, `/ingest`, and write-like Action paths return `404`;
- search/read results stay pack-authorized;
- the Action service starts without Neo4j credentials or Graphiti connectivity;
- the canonical data mount is read-only;
- the existing MCP contract remains unchanged;
- no secret value appears in Git history, CI output, issues, or documentation.
