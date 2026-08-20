# Verification package — FOSSIL read-only ChatGPT Action

## Verification layers

### Focused unit / integration / architecture

```bash
pip install -e '.[test,node]'
pytest -q \
  tests/test_chatgpt_action.py \
  tests/test_chatgpt_action_server.py \
  tests/test_chatgpt_action_architecture.py \
  tests/holdout/test_chatgpt_action_holdout.py
```

These tests cover the exact search/read/capabilities route boundary, bearer authentication, input validation, OpenAPI 3.1 compatibility, the real standalone environment composition, redaction suppression, empty-corpus behavior, bounded streaming request reads, trusted-proxy origin handling, forged direct-HTTPS Host rejection, and non-leakage behavior.

OpenAPI validation is performed in both focused and holdout tests with `openapi-spec-validator`. The schema must contain a non-empty `components.schemas` object, explicit successful-response properties, unique operation IDs, and no `/actions/lineage` or mutation routes.

### Targeted mutation assurance

```bash
python scripts/run_chatgpt_action_mutations.py
```

The command runs the independent holdout plus architecture checks against each deliberate mutant. It returns non-zero if any mutant survives or any mutation anchor cannot be applied.

Current mutant families include:

- bearer bypass;
- route-allowlist widening;
- lineage-route reintroduction without a provider;
- accidental durable commit route;
- removal of declared body-size guard;
- removal of streaming body-size guard;
- weakened search-limit validation;
- extra-field capability smuggling;
- forwarded-header trust from untrusted peers;
- loss of trusted-proxy HTTPS support;
- caller-controlled direct HTTPS `Host` trusted as origin;
- HTTP schema origin;
- missing `components.schemas`;
- erased response properties;
- redacted event bytes made searchable;
- `_redactions` paths reintroduced into event iteration;
- global Uvicorn proxy-header trust;
- write method added to the read-only event store;
- root container execution;
- writable canonical mount;
- non-loopback Docker publication.

No surviving mutant is an acceptable release result.

### Container smoke

Reference workflow:

```text
.github/workflows/chatgpt-action-container.yml
```

It builds the actual Docker image and proves:

- image/config contains no synthetic runtime credential;
- effective UID/GID is 10001;
- host publication is `127.0.0.1` only;
- `/var/lib/fossil` is `RW=false` and rejects a write probe;
- OpenAPI contains only search/read/capabilities and an HTTPS public origin;
- forged host/forwarded values cannot override fixed origin;
- unauthenticated Action access returns 401;
- search remains empty for an unrelated query;
- redacted event bytes and tombstone markers are not searchable;
- redacted read returns generic 404 without redaction metadata;
- `/actions/lineage`, MCP, ingest and mutation-like routes return 404;
- explicitly trusted proxy peer can generate the forwarded HTTPS origin;
- runtime token does not appear in application logs.

### Repository regression gates

The exact candidate head must also pass:

- `DKG contract tests`;
- `Dependency integrity` including architecture-boundary and metadata/reproducible-install jobs;
- `ChatGPT Action container`;
- `ChatGPT Action mutation assurance`.

Other repository workflows may run as normal; delivery evidence must distinguish required Action gates from unrelated optional/live integrations.

## Windows / D: local integrator verification

Target layout:

```text
D:\FossilBrokerWorker\chatgpt-action\
  fossil-core\
  data\
    canonical\
      events\
  secrets\
    chatgpt-action.env
```

The integrator should clone/checkout the exact reviewed PR head under `D:\FossilBrokerWorker\chatgpt-action\fossil-core`, run the Python/mutation suite, build the image with Docker Desktop, and inspect the same UID, bind address, and read-only mount properties as CI.

The target canonical data directory may be empty. The expected authenticated search result in that state is exactly `200 []`.

Do not create a real bearer token until local deployment/configuration work begins. Real tunnel/provider and Custom GPT credentials are outside this repository package.

## Required delivery evidence

The PR conversation must record, for the final code/documentation head:

- exact commit SHA;
- DKG contract-test run ID/result;
- ChatGPT Action container run ID/result;
- Dependency integrity run ID/results;
- ChatGPT Action mutation run ID/result and killed/surviving/harness-error counts;
- any known limitations;
- rollback procedure;
- confirmation that no real bearer secret, tunnel/provider credential, or Custom GPT credential was created, handled, or committed.

Do not reuse green evidence from an earlier SHA after changing production code, tests, workflows, or normative documentation.

## Known limitations

- The Action is deliberately read-only and cannot ingest or persist new knowledge.
- `/actions/lineage` is intentionally absent because the standalone composition has no durable lineage provider. FOSSIL domain/MCP lineage support is unchanged.
- The target canonical event directory is currently empty; smoke validation proves correct empty behavior, not semantic retrieval quality.
- TLS/tunnel/DNS uptime, public-edge rate limiting, and real Custom GPT configuration remain local-operator responsibilities.
- Trusted-proxy mode requires the operator to identify the actual immediate proxy peer CIDR seen by the container.
- One static bearer credential is the v1 Action authentication model; OAuth/multi-user identity is out of scope.
- CI cannot prove the operator's real Windows `D:` filesystem permissions, tunnel configuration, or private Custom GPT account without handling local credentials, which this package explicitly does not do.

## Rollback

If a locally deployed candidate fails integration:

1. remove/disable the public route if it was configured;
2. stop/remove the Action container;
3. return to the previously reviewed image/SHA;
4. leave canonical data untouched.

The Action cannot mutate canonical data, so rollback requires no knowledge-store migration.
