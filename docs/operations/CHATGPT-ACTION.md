# ChatGPT Custom GPT Action boundary

This document describes the **read-only compatibility edge** for using a ChatGPT Custom GPT Action with FOSSIL.

The Action edge is a protocol adapter only. It does not change FOSSIL truth authority, pack authorization, provenance, or the existing MCP contract.

## Security boundary

Use `create_chatgpt_action_app(...)` as a **distinct public HTTPS edge**. Do not publish the normal FOSSIL node network app merely to make ChatGPT reachable.

The dedicated Action app exposes only:

- `GET /openapi.json` — public schema used to configure the GPT Action;
- `POST /actions/search` — `fossil.search` through `ThinMCPAdapter`;
- `POST /actions/read` — `fossil.read` through `ThinMCPAdapter`;
- `POST /actions/lineage` — `fossil.lineage` through `ThinMCPAdapter`;
- `GET /actions/capabilities` — static metadata describing this bounded Action surface.

It deliberately does **not** expose:

- `/mcp`;
- `/ingest`;
- `fossil.propose`;
- `fossil.validate`;
- `fossil.commit`;
- Neo4j/Graphiti APIs or arbitrary graph mutation.

All `/actions/*` operations require a bearer token. `/openapi.json` is intentionally unauthenticated so ChatGPT can import the schema.

## Runtime composition

Construct the Action app from the same `FilesystemFossilNode` used by the private runtime, but give it a read-only corpus-search agent context:

```python
from fossil_core.agent import AgentContext
from fossil_core.runtime.chatgpt_action import create_chatgpt_action_app

context = AgentContext(
    actor_id="chatgpt-action",
    model_id="chatgpt",
    harness_version="custom-gpt-action-v1",
    skill_id="skill_corpus-search",
    skill_version="1.0.0",
)

app = create_chatgpt_action_app(
    node,
    context=context,
    bearer_token=action_token,
)
```

`action_token` must come from the deployment secret store/environment at runtime. Never commit it, put it in an issue, or print it in logs.

The public edge still uses the node's existing `CorpusService`, `PackAccess`, durable event store, and `ThinMCPAdapter`, so read authorization and pack boundaries remain canonical.

## ChatGPT Custom GPT setup

In the ChatGPT web GPT editor:

1. Create or edit the private GPT used for FOSSIL.
2. Open **Configure → Actions**.
3. Import or paste the schema from `https://<ACTION_HOST>/openapi.json`.
4. Configure Action authentication as an API key/bearer token and enter the same deployment token used by the Action edge.
5. Keep the GPT private while validating the integration.
6. Test `fossilSearch`, then `fossilRead`, then `fossilLineage` from the Action test UI.

Do not paste the token into GPT instructions, the OpenAPI document, source control, GitHub issues, or chat messages.

## Deployment rule

The existing private FOSSIL Node can remain reachable over its intended private/Tailscale boundary. The ChatGPT Action edge needs externally reachable HTTPS for ChatGPT, but only the dedicated Action app should be exposed on that public route.

A reverse proxy, tunnel, or later deployment unit may terminate TLS and route the public hostname to the dedicated Action ASGI app. That deployment choice is separate from this adapter and does not authorize public exposure of the MCP, ingestion, database, or admin surfaces.

## Acceptance checks

Before using a real secret or public hostname, verify mechanically that:

- `/openapi.json` contains only the four Action paths;
- `/actions/*` rejects missing/wrong bearer tokens;
- `/mcp`, `/ingest`, and write-like Action paths return `404` on the dedicated app;
- search/read/lineage results stay pack-authorized;
- the existing MCP test suite remains unchanged and green;
- no secret value appears in Git history, CI output, issues, or documentation.
