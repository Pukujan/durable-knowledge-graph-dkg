# FOSSIL TLA+ models

These models are protocol-assurance artifacts for #176. They do not prove the Python implementation and do not replace deterministic, mutation, live-provider, rebuild, security, or semantic acceptance gates.

## DurableStore

`DurableStore.tla` abstracts the provider-neutral laws shared by the filesystem and S3-compatible durable stores:

- an identity is created with one immutable first value;
- byte-identical replay is accepted without changing durable state;
- a different value under the same live identity conflicts;
- a redaction tombstone becomes durable before payload deletion;
- once an identity is redacted, create attempts are rejected and a deleted payload cannot reappear;
- unavailable durable storage produces no successful durable mutation;
- restart preserves durable live/tombstone/history state.

Property traceability:

- `FOSSIL-PROP-IDEMPOTENCY-001`
- `FOSSIL-PROP-REDACTION-NONRESURRECTION-001`

The model intentionally does **not** specify provider APIs, filesystem paths, S3 keys, payload schemas, multi-writer concurrency, or promotion semantics.

### Bounded configuration

`DurableStore.cfg` checks two abstract identities and two abstract values. The bounded state space is intended to expose protocol/interleaving mistakes, not to establish unbounded correctness.

Checked invariants:

- `TypeOK`
- `ImmutableFirstValue`
- `TombstoneRequiresHistory`
- `DeleteRequiresTombstone`
- `DeletedRedactedIdentityAbsent`
- `SuccessfulAttemptWasAvailable`

### Local checking

CI pins the TLA+ tools jar and verifies its published checksum before parsing and running TLC. Equivalent local invocation from this directory is:

```sh
java -cp /path/to/tla2tools.jar tla2sany.SANY DurableStore.tla
java -jar /path/to/tla2tools.jar -config DurableStore.cfg DurableStore.tla
```

Implementation conformance remains established by the existing Python storage/redaction tests and live durability evidence, not by this model alone.
