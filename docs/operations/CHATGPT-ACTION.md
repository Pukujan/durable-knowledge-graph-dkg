# ChatGPT Custom GPT Action boundary

This is the operator entrypoint for the **read-only compatibility edge** used by a private ChatGPT Custom GPT. Detailed design and verification live in:

- `CHATGPT-ACTION-PDD.md` — user problem, threat model, trust boundaries, non-goals;
- `CHATGPT-ACTION-INVARIANTS.md` — normative machine-testable invariants;
- `CHATGPT-ACTION-SDD.md` — architecture, API, environment, container, proxy, WSL handoff;
- `CHATGPT-ACTION-VERIFICATION.md` — focused/holdout/mutation verification and delivery evidence.

The Action edge does not change FOSSIL truth authority, pack authorization, provenance, or the MCP contract.

## Security boundary

The dedicated Action service exposes only:

- `GET /openapi.json` — public OpenAPI discovery;
- `POST /actions/search` — authenticated FOSSIL search;
- `POST /actions/read` — authenticated durable-event read;
- `POST /actions/lineage` — authenticated lineage read;
- `GET /actions/capabilities` — authenticated read-only capability metadata.

It deliberately exposes **no** MCP, ingest, proposal, validation, commit, redaction, Graphiti/Neo4j API, graph mutation, arbitrary filesystem access, shell/admin operation, or credential surface.

All `/actions/*` operations require bearer authentication. `/openapi.json` is intentionally unauthenticated and contains no secret.

## Standalone runtime

The entrypoint is:

```text
fossil-chatgpt-action
```

It boots directly from canonical FOSSIL events plus pack and skill contracts. It does not initialize Graphiti or Neo4j. The Action-specific event-store view has read methods only and is designed to boot against a physically read-only canonical mount.

Runtime variables:

```text
FOSSIL_ACTION_BEARER_TOKEN      required; runtime-only; at least 32 characters
FOSSIL_ACTION_HOST              default 127.0.0.1
FOSSIL_ACTION_PORT              default 8787
FOSSIL_ACTION_MAX_REQUEST_BYTES default 65536
FOSSIL_ACTION_PUBLIC_BASE_URL   production HTTPS origin advertised in OpenAPI
FOSSIL_REPOSITORY_ROOT          default current working directory
FOSSIL_DATA_ROOT                default <repository>/data
FOSSIL_PACK_MANIFEST            default examples/packs/common/manifest.json
```

This package does not create, receive, print, or deploy any real token or endpoint credential. The operator supplies those locally after code review.

## Container build

From the repository root:

```bash
podman build \
  -f docker/chatgpt-action/Dockerfile \
  -t localhost/fossil-chatgpt-action:local \
  .
```

The container runs as UID/GID 10001. Production launch must mount canonical data read-only at `/var/lib/fossil`; the expected event path is `/var/lib/fossil/canonical/events`.

No real launch command with a credential is included here. Use `config/chatgpt-action.env.example` only as a field-name template and keep the populated file outside source control.

## Public HTTPS edge

ChatGPT reaches the Action through operator-managed HTTPS. Tailscale is not required for this Action path. The reverse proxy/tunnel, DNS, TLS certificate, and provider credentials are all out of scope for this PR.

The Action process **does not trust `Forwarded` or `X-Forwarded-*` headers** to determine its public origin. Uvicorn proxy-header processing is disabled. Instead the local operator sets an explicit origin:

```text
FOSSIL_ACTION_PUBLIC_BASE_URL=https://<public-action-origin>
```

That value must be an origin-only `https://` URL. `/openapi.json` then emits it exactly in `servers[0].url`, so the schema remains correct even when the internal hop is plain HTTP and even if a caller forges forwarded headers.

The external HTTPS edge must forward only the Action service. It must not publish the private FOSSIL Node, MCP, ingestion, Neo4j, or admin surfaces.

## Windows / WSL `D:` integrator handoff

A supported local layout is:

```text
D:\fossil\fossil-core   -> /mnt/d/fossil/fossil-core
D:\fossil\data          -> /mnt/d/fossil/data
```

From WSL:

```bash
cd /mnt/d/fossil/fossil-core
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test,node]'
pytest -q \
  tests/test_chatgpt_action.py \
  tests/test_chatgpt_action_server.py \
  tests/test_chatgpt_action_architecture.py \
  tests/holdout/test_chatgpt_action_holdout.py
python scripts/run_chatgpt_action_mutations.py
docker build -f docker/chatgpt-action/Dockerfile -t fossil-chatgpt-action:local .
```

The local integrator can then perform machine-specific configuration with locally generated secrets and an HTTPS endpoint. Those actions are intentionally not performed by this PR or its CI.

## Private Custom GPT setup boundary

After the local endpoint passes verification, the operator may import `https://<public-action-origin>/openapi.json` into a private Custom GPT and configure the same locally managed bearer credential in the GPT Action authentication UI.

This repository never stores or handles the real Custom GPT credential. The GPT must remain read-only because the imported OpenAPI document contains only search, read, lineage, and capabilities.

## Acceptance checks

Before use, verify:

- OpenAPI validates as 3.1 and has a real `components.schemas` object;
- `servers[0].url` is the configured HTTPS origin despite forged forwarded headers;
- only the four Action operations appear in `paths`;
- `/actions/*` rejects malformed/missing/wrong bearer credentials;
- request-size/type/range validation fails closed;
- `/mcp`, `/ingest`, proposal, validation, commit, redaction, graph, filesystem, and admin paths return `404`;
- path-like `event_id` values are rejected before filesystem access;
- the container runs non-root and canonical data is physically read-only;
- Action startup requires no Neo4j/Graphiti credential or connectivity;
- focused, holdout, container, architecture, and mutation checks are green;
- no real secret value exists in Git, CI, docs, issue comments, or test fixtures.
