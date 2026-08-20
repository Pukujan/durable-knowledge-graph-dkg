# Verification package — Read-only ChatGPT Action edge

## Verification layers

### Focused unit/integration

```bash
pytest -q \
  tests/test_chatgpt_action.py \
  tests/test_chatgpt_action_server.py \
  tests/test_chatgpt_action_architecture.py
```

Covers authentication, request validation, route isolation, canonical delegation, identifier/path safety, environment parsing, explicit HTTPS-origin behavior, non-Neo4j bootstrap, no mutation methods, container/source architecture contracts, and secretless examples.

### Independent holdout

```bash
pytest -q tests/holdout/test_chatgpt_action_holdout.py
```

The holdout suite uses only the public settings/app boundary and observable HTTP behavior where practical. It deliberately does not assert private helper implementations. It covers:

- malformed/missing/wrong/duplicated authorization;
- forged `Forwarded` and `X-Forwarded-*` headers;
- OpenAPI 3.1 validation using `openapi-spec-validator`;
- valid `components.schemas` and explicit response-object properties;
- oversized declared and actual request bodies;
- unknown paths and all prohibited routes;
- unsupported HTTP methods;
- filesystem path traversal through `event_id`;
- read-only event-store surface and boot against a non-writable event directory;
- invalid search-limit types/ranges;
- secret non-reflection in schema/capability/error responses.

This suite is separated from the focused tests so an external integrator can copy the behavioral cases into a private holdout runner without depending on implementation internals. Because tests committed in a PR cannot literally be secret from the implementation author, the security property is **black-box separation**, not obscurity. A downstream organization may keep an additional copy private using the same behavioral plan.

### Container/deployment smoke

GitHub workflow: `.github/workflows/chatgpt-action-container.yml`.

It mechanically verifies:

- image builds;
- process starts with a read-only `/var/lib/fossil` mount;
- runtime UID/GID are `10001`;
- canonical event directory is not writable and a write attempt fails;
- forged forwarded headers do not change the configured HTTPS OpenAPI server URL;
- unauthenticated search is `401`;
- authenticated search succeeds;
- MCP, ingest, write-like, graph, and filesystem routes are `404`;
- unsupported methods are `405`.

No real secret is used. The workflow token string is a clearly labeled non-secret CI fixture and is not suitable for deployment.

### Mutation assurance

```bash
python scripts/run_chatgpt_action_mutations.py
```

GitHub workflow: `.github/workflows/chatgpt-action-mutation.yml`.

The harness mutates the checked-out files one mutant at a time, runs the independent holdout plus architecture tests in a fresh Python subprocess, and restores the original file after each run. A mutant is **killed** when verification fails as expected; any surviving mutant fails the mutation workflow.

Defined mutants:

| Mutant | Security regression expected to be killed |
| --- | --- |
| `bypass_bearer_check` | unauthenticated reads enabled |
| `widen_route_allowlist` | unknown/prohibited routes enter Action dispatcher |
| `enable_commit_route` | durable write route becomes addressable |
| `remove_body_size_guards` | oversized requests accepted |
| `weaken_search_limit_validation` | ambiguous/out-of-range limits accepted |
| `trust_request_origin_for_openapi` | public schema origin becomes caller/proxy-header dependent |
| `remove_components_schemas` | GPT-import schema loses required schema object |
| `erase_response_properties` | response contract becomes opaque |
| `enable_proxy_headers` | uvicorn begins trusting forwarded headers |
| `add_write_method_to_read_store` | Action event-store gains a mutation method |
| `run_container_as_root` | image executes as root |
| `make_canonical_mount_writable` | deployment contract permits canonical writes |

The PR delivery evidence records killed/surviving counts from the final mutation workflow run. Surviving mutants must be either fixed or explicitly justified before this package is considered build-ready.

## OpenAPI / private Custom GPT compatibility

`/openapi.json` must pass `openapi-spec-validator` and preserve:

- OpenAPI 3.1.x;
- `components.schemas` as an object;
- HTTP bearer security scheme;
- unique operation IDs;
- explicit response schemas/properties;
- exactly four Action operation paths;
- HTTPS `servers[0].url` when `FOSSIL_ACTION_PUBLIC_BASE_URL` is configured;
- no MCP/ingest/write/mutation operations.

No CI test logs into ChatGPT, creates a GPT, uploads a credential, provisions a tunnel, or uses a real token. Final UI import/auth is a local integrator step after repository verification.

## Windows / WSL `D:` acceptance recipe

```bash
cd /mnt/d/fossil/fossil-core
git fetch origin pull/235/head:pr-235
git checkout pr-235
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test,node]'
pytest -q tests/test_chatgpt_action.py tests/test_chatgpt_action_server.py tests/test_chatgpt_action_architecture.py tests/holdout/test_chatgpt_action_holdout.py
python scripts/run_chatgpt_action_mutations.py
docker build -f docker/chatgpt-action/Dockerfile -t fossil-chatgpt-action:pr235 .
```

The local integrator then uses `/mnt/d/...` (or an equivalent WSL path) for the canonical data bind and keeps all populated environment/secret material outside the repository. Deployment itself is not part of this package.

## Known limitations

- The Action is deliberately read-only; it cannot ingest or persist new knowledge.
- Standalone lineage availability depends on lineage data being available through the existing `CorpusService` composition; this PR does not add a projection/database query path.
- TLS/proxy/tunnel uptime, DNS, certificates, and rate limiting at the public edge are operator responsibilities.
- One static bearer credential is the v1 auth model. OAuth/multi-user identity is out of scope.
- CI validates the API/schema and container behavior but cannot prove an actual private Custom GPT account configuration without handling credentials, which this package explicitly forbids.
- The committed holdout is behaviorally independent but not literally hidden; downstream integrators can run the documented cases privately.

## Rollback plan

There are no migrations and no Action-side writes. Rollback is:

1. do not import/use the Action schema, or remove the Action from the private GPT if already configured locally;
2. stop/remove the Action process/container;
3. remove the external HTTPS route locally;
4. checkout/revert to the pre-PR repository SHA;
5. leave canonical FOSSIL data untouched.

No durable event, projection, Neo4j state, or pack contract requires rollback because this feature has no write capability.

## Delivery evidence

The exact final PR head SHA, workflow run IDs/results, mutation killed/survived count, and any remaining limitations are recorded in the PR description/conversation after the final CI pass. This avoids a self-referential commit-SHA problem inside a file whose own update would change that SHA.
