# Verification package — FOSSIL read-only ChatGPT Action

## Verification layers

### Focused unit / integration / architecture

```bash
pytest -q \
  tests/test_chatgpt_action.py \
  tests/test_chatgpt_action_server.py \
  tests/test_chatgpt_action_architecture.py
```

These tests cover:

- exact route/method allowlist;
- bearer authentication, duplicate-header/scheme/token handling, and constant-time comparison contract;
- request-size, JSON, type/range, extra-field, and opaque-identifier validation;
- canonical search/read/lineage delegation through the existing authorization boundary;
- empty canonical data returning `200 []`;
- sanitized errors and credential/path non-reflection;
- OpenAPI 3.1 validation using `openapi-spec-validator`;
- non-empty `components.schemas`, stable operation IDs, explicit successful-response object properties, and bearer security;
- fixed HTTPS origin and explicit trusted-proxy CIDR behavior;
- no Graphiti/Neo4j composition and no mutable event-store API;
- Docker artifact rules for non-root execution, loopback publication, and read-only canonical mount.

### Separately maintainable holdout

```bash
pytest -q tests/holdout/test_chatgpt_action_holdout.py
```

The holdout suite is black-box separated from focused implementation tests. Its normative plan is `CHATGPT-ACTION-HOLDOUT.md`. It covers absent/malformed/wrong/duplicated credentials, authorization-scheme confusion, forged/missing proxy headers, accidental HTTP schema origin, oversized/malformed payloads, unsupported methods, prohibited/unknown paths, filesystem/capability smuggling, schema regressions, empty-data behavior, and token/configuration leakage.

Committed tests cannot literally be hidden from the implementation author; downstream integrators may keep additional tests private using the same behavioral plan.

### Container / deployment smoke

GitHub workflow:

```text
.github/workflows/chatgpt-action-container.yml
```

The workflow builds the same Linux image used by Docker Desktop and mechanically verifies:

- image runtime user is non-root;
- synthetic runtime token is absent from image history/config;
- effective UID/GID are `10001`;
- Docker host publication is exactly `127.0.0.1:8787`;
- `/var/lib/fossil` reports `RW=false`;
- an in-container canonical-data write probe fails and creates no host file;
- an existing empty `canonical/events` directory boots successfully;
- unauthenticated search returns `401`;
- authenticated empty-corpus search returns exactly `[]`;
- all prohibited routes remain `404`;
- fixed HTTPS origin resists forged forwarded headers;
- a second private Docker-network smoke proves trusted-proxy origin generation works only from the configured proxy peer IP;
- application logs do not contain the synthetic runtime token.

The CI token is an obvious non-secret fixture and is never a deployment credential.

### Mutation assurance

Command:

```bash
python scripts/run_chatgpt_action_mutations.py
```

GitHub workflow:

```text
.github/workflows/chatgpt-action-mutation.yml
```

The deterministic harness changes one security property at a time, runs the holdout + architecture suites in a fresh Python subprocess, restores the source file, and fails if a mutant survives or an anchor cannot be applied.

Current required mutants:

| Mutant | Regression that must be killed |
| --- | --- |
| `bypass_bearer_check` | authentication bypass |
| `widen_route_allowlist` | prohibited/unknown route reaches dispatcher |
| `enable_commit_route` | durable write route becomes addressable |
| `remove_body_size_guards` | oversized bodies accepted |
| `weaken_search_limit_validation` | boolean/ambiguous limit accepted as an integer |
| `allow_extra_capability_fields` | extra JSON fields smuggle new capability |
| `trust_forwarded_headers_from_any_peer` | forged proxy origin accepted from untrusted peer |
| `remove_trusted_proxy_origin_support` | correctly configured proxy cannot produce HTTPS schema origin |
| `publish_http_schema_origin` | OpenAPI server regresses to HTTP |
| `remove_components_schemas` | GPT/OpenAPI schema loses `components.schemas` |
| `erase_search_response_properties` | successful response object becomes opaque |
| `enable_uvicorn_global_proxy_headers` | Uvicorn globally trusts forwarded headers |
| `add_write_method_to_read_store` | read-only event store gains mutation API |
| `run_container_as_root` | image executes as root |
| `make_canonical_mount_writable` | canonical Docker mounts become writable |
| `remove_loopback_host_binding` | container port becomes publicly/all-interface bound |

The final PR description records the exact killed/surviving/harness-error result from the final workflow. A build-ready result requires no unjustified survivor and no harness error.

## OpenAPI / private Custom GPT compatibility checks

`/openapi.json` must pass an independent OpenAPI 3.1 validator and preserve:

- OpenAPI 3.1.x;
- a non-empty `components.schemas` object;
- named request schemas;
- explicit successful-response object properties;
- explicit `ErrorEnvelope` responses;
- HTTP bearer security;
- four unique/stable operation IDs;
- exactly four authenticated Action paths;
- an HTTPS `servers[0].url` only;
- no MCP, ingest, proposal, validation, commit, redaction, graph/filesystem/admin operation;
- no runtime token/configuration value.

No automated test logs into ChatGPT, creates a GPT, provisions a tunnel/DNS/TLS endpoint, or handles a real credential.

## Windows / Docker Desktop / WSL 2 acceptance recipe

Required checkout and persistent layout:

```text
D:\FossilBrokerWorker\chatgpt-action\
  fossil-core\
  data\canonical\events\
  secrets\chatgpt-action.env
```

Optional Python verification from WSL:

```bash
cd /mnt/d/FossilBrokerWorker/chatgpt-action/fossil-core
git fetch origin pull/235/head:pr-235
git checkout pr-235
python3 -m venv .venv-linux
. .venv-linux/bin/activate
pip install -e '.[test,node]'
pytest -q tests/test_chatgpt_action.py tests/test_chatgpt_action_server.py tests/test_chatgpt_action_architecture.py tests/holdout/test_chatgpt_action_holdout.py
python scripts/run_chatgpt_action_mutations.py
```

Docker Desktop verification/build from Windows PowerShell:

```powershell
Set-Location 'D:\FossilBrokerWorker\chatgpt-action\fossil-core'
docker build --file docker/chatgpt-action/Dockerfile --tag fossil-chatgpt-action:pr235 .
```

Docker commands do not require Docker integration inside the Ubuntu WSL distribution. The local integrator later creates the real `D:\...\secrets\chatgpt-action.env`, bind-mounts `D:\...\data` read-only, publishes only `127.0.0.1:8787`, establishes the HTTPS edge, and configures the private Custom GPT. Those steps are deliberately not executed by this PR.

## Known limitations

- The Action is deliberately read-only and cannot ingest or persist new knowledge.
- The target canonical event directory is currently empty; smoke validation proves correct empty behavior but not semantic retrieval quality.
- Standalone lineage availability depends on lineage data being present in the existing `CorpusService` composition; this PR does not add a new graph/projection query path.
- TLS/tunnel/DNS uptime and edge rate limiting remain operator responsibilities.
- Trusted-proxy mode requires the local integrator to identify the actual proxy peer CIDR observed by the container; Docker Desktop network addressing may differ by installation.
- One static bearer credential is the v1 auth model; OAuth/multi-user identity is out of scope.
- CI cannot prove a real private Custom GPT account configuration without handling credentials, which is explicitly prohibited.

## Rollback

There are no data migrations and no Action-side writes. Rollback is:

1. disable/remove the external HTTPS route if one was configured locally;
2. stop/remove the Action container;
3. restore the previous image/tag or repository SHA;
4. leave `D:\FossilBrokerWorker\chatgpt-action\data` untouched;
5. locally remove/rotate a runtime token if desired.

No durable event, projection, or Neo4j state requires reversal.

## Delivery evidence

The exact final PR head SHA, workflow run IDs/results, mutation killed/survived count, and remaining limitations are recorded in PR #235 after the final CI pass. Keeping that evidence in the PR avoids a self-referential commit-SHA change inside this tracked document.
