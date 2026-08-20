# FOSSIL read-only ChatGPT Action — operator entrypoint

This PR packages a private, bearer-authenticated, read-only GPT Action edge. It does **not** deploy, create secrets, create tunnels, or configure a Custom GPT.

Design/verification documents:

- `CHATGPT-ACTION-PDD.md` — problem, scope, threat model, trust boundaries, exact Windows target;
- `CHATGPT-ACTION-INVARIANTS.md` — normative machine-testable invariants;
- `CHATGPT-ACTION-SDD.md` — architecture, API/OpenAPI contract, proxy rules, Docker Desktop runbook;
- `CHATGPT-ACTION-HOLDOUT.md` — separately maintainable black-box holdout plan;
- `CHATGPT-ACTION-VERIFICATION.md` — focused/container/mutation verification and delivery evidence.

## Exact read-only boundary

Public, unauthenticated:

- `GET /openapi.json`

Bearer-protected:

- `POST /actions/search`
- `POST /actions/read`
- `POST /actions/lineage`
- `GET /actions/capabilities`

Prohibited even when authenticated:

- MCP and `/mcp`;
- ingest and `/ingest`;
- proposal, validation, commit, redaction, write, admin, or management routes;
- Neo4j/Graphiti query or mutation surfaces;
- arbitrary graph mutation/query language;
- arbitrary filesystem access, shell/process control, or runtime-configuration disclosure;
- secret/token/credential disclosure.

## Target environment

The build-ready target is:

- Windows host;
- Docker Desktop Linux engine with WSL 2 backend;
- Ubuntu/Ubuntu-22.04 may be used for Python verification, but Docker integration inside those distros is not required;
- no Podman/systemd/Quadlet/cloud-VM assumption;
- all persistent material under:

```text
D:\FossilBrokerWorker\chatgpt-action\
  fossil-core\
  data\canonical\events\
  secrets\chatgpt-action.env
```

The current target `data\canonical\events` is empty. Authenticated search must therefore return `200 []`, never fabricated content.

## Build and verification

From WSL, Python-only verification can run against the checkout on `D:`:

```bash
cd /mnt/d/FossilBrokerWorker/chatgpt-action/fossil-core
python3 -m venv .venv-linux
. .venv-linux/bin/activate
pip install -e '.[test,node]'
pytest -q \
  tests/test_chatgpt_action.py \
  tests/test_chatgpt_action_server.py \
  tests/test_chatgpt_action_architecture.py \
  tests/holdout/test_chatgpt_action_holdout.py
python scripts/run_chatgpt_action_mutations.py
```

Docker commands run from Windows PowerShell against Docker Desktop:

```powershell
Set-Location 'D:\FossilBrokerWorker\chatgpt-action\fossil-core'
docker build --file docker/chatgpt-action/Dockerfile --tag fossil-chatgpt-action:pr235 .
```

The image runs as UID/GID 10001. Canonical data is mounted read-only at `/var/lib/fossil`. The Windows host port is published only as `127.0.0.1:8787`.

## HTTPS schema origin

`/openapi.json` never advertises a plain-HTTP public server URL.

Preferred fixed mode:

```text
FOSSIL_ACTION_PUBLIC_BASE_URL=https://<public-origin>
```

The fixed origin is authoritative and forged forwarded headers cannot override it.

Trusted-proxy mode is also supported when a fixed origin is not used:

```text
FOSSIL_ACTION_TRUSTED_PROXY_CIDRS=<explicit proxy peer CIDR(s)>
```

Only requests from those networks may use one `X-Forwarded-Proto: https` and one valid `X-Forwarded-Host` to define the OpenAPI origin. Uvicorn runs with `proxy_headers=False`; wildcard proxy trust is not part of the design. If no trusted HTTPS origin exists, `/openapi.json` returns `503` instead of publishing internal HTTP.

## Runtime variables

```text
FOSSIL_ACTION_BEARER_TOKEN      required, runtime-only, >=32 characters
FOSSIL_ACTION_HOST              image uses 0.0.0.0; Windows publish remains loopback-only
FOSSIL_ACTION_PORT              default 8787
FOSSIL_ACTION_MAX_REQUEST_BYTES default 65536
FOSSIL_ACTION_PUBLIC_BASE_URL   optional fixed HTTPS origin
FOSSIL_ACTION_TRUSTED_PROXY_CIDRS optional explicit proxy source networks
FOSSIL_REPOSITORY_ROOT          image /opt/fossil-core
FOSSIL_DATA_ROOT                image /var/lib/fossil
FOSSIL_PACK_MANIFEST            read-pack manifest
```

`config/chatgpt-action.env.example` contains placeholders only. The local integrator creates the populated file under `D:\...\secrets` after review; it is never committed.

## Docker Desktop launch shape

Documentation only — the PR does not execute this and contains no real credential:

```powershell
docker run --detach `
  --name fossil-chatgpt-action `
  --restart unless-stopped `
  --env-file 'D:\FossilBrokerWorker\chatgpt-action\secrets\chatgpt-action.env' `
  --publish 127.0.0.1:8787:8787 `
  --mount 'type=bind,source=D:\FossilBrokerWorker\chatgpt-action\data,target=/var/lib/fossil,readonly' `
  fossil-chatgpt-action:pr235
```

The external HTTPS reverse proxy/tunnel forwards only to Windows `127.0.0.1:8787`; it is the sole public exposure point.

## Acceptance before private GPT connection

Verify all focused, holdout, mutation, and container checks are green; effective UID is 10001; Docker `HostIp` is `127.0.0.1`; the canonical mount reports `RW=false` and rejects writes; empty search is `[]`; all prohibited routes are `404`; OpenAPI validates as 3.1 with non-empty `components.schemas`, explicit response properties, unique operation IDs, bearer security, exactly four Action paths, and an HTTPS server URL.

Only then does the local integrator create/manage the real token, establish the HTTPS endpoint, and import the schema into a private Custom GPT. Those operations are outside this PR.

## Rollback

Stop/remove the Action container and external route, then restore the previous image/checkout. No canonical-data migration or rollback exists because the Action cannot write.
