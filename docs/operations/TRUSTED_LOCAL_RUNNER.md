# Trusted-local autonomous broker and verifier

**Authority:** D022; issue #96; #94 `INFRA-03` / `INFRA-04`.

The preferred local execution path is now an **outbound polling broker**, not a self-hosted GitHub Actions runner attached to this public repository.

Why: the owner's PC is persistent credential-adjacent infrastructure. Public repository workflow code must not be able to schedule it directly. The broker connects outbound to GitHub, reads the append-only queue, and only executes tasks that are explicitly machine-ready under the rules below.

## Security invariant

> A PR, fork, arbitrary issue comment, or repository workflow cannot directly invoke the owner's PC.

The broker accepts a local Codex task only when all of these are true:

1. the #94 `TASK` comment is authored by trusted GitHub login `Pukujan`;
2. `state=READY`;
3. `repo` is in the reviewed local allowlist;
4. `starting_ref` is an exact 40-character SHA;
5. `local_role=terra` or `local_role=luna` is explicit;
6. access is exactly `CLOUD_SECRETLESS` for Codex work;
7. there is no earlier active unexpired claim;
8. the broker posts a claim, re-reads #94, and confirms it won;
9. generation/cancel/terminal attempt state is re-derived from live `WORKORDER*` records before launch.

Old task prose that lacks the exact SHA or `local_role` is inert to the broker.

## What actually invokes Codex

`scripts/run_trusted_local_broker.py` launches a **fresh non-interactive** Codex process for each accepted WorkOrder using `codex exec` with:

- `--ephemeral` — no session rollout reuse;
- `--sandbox workspace-write` — write access for the isolated repository worktree;
- `--json` — machine-readable run events;
- `--ignore-user-config` — do not inherit interactive user MCP/config policy;
- `gpt-5.6-terra` for role `terra`;
- `gpt-5.6-luna` for role `luna`.

The generated prompt forbids credential discovery, `.env` access, deploy/promotion, push/PR creation, and external mutation. The Codex child's exit code is not final acceptance: the parent broker runs the configured independent check command afterwards, inside the same dedicated worker boundary.

## Credential split

There are three separate contexts.

### 1. Broker parent

The parent may use a GitHub coordination/publication credential (prefer an authenticated local `gh`/Git credential setup or a narrowly scoped local token). It reads/posts #94, pushes the mechanically checked branch, and opens the draft PR.

**The GitHub token is never passed to the Codex child.**

The parent publication step uses a reviewed repo allowlist, forces the expected GitHub origin, disables Git hooks for its commit/push path, and runs only after the independent test command succeeds.

### 2. Secretless Codex worker

Use a dedicated local OS account/profile or container boundary. Separate `worker_home` and `codex_home` paths contain only the Codex authentication/config needed to run the CLI. The broker parent and its independent checks must execute in that same boundary: do not run changed-code checks under the owner's normal host identity.

The child environment is reconstructed from a small OS allowlist. It does not inherit the interactive user's `HOME`, `GITHUB_TOKEN`, Railway/provider keys, `OPENAI_API_KEY`, or other credential-like environment variables.

Treat Codex's local auth file as a password. Do not copy it into Git, #94, logs, chat, or the repository worktree.

### 3. Privileged verifier

Railway/provider/telemetry/object-store credentials remain a **separate deterministic verifier lane**. A model/Codex process does not receive those credentials.

`scripts/run_privileged_local_verifier.py` is the executable implementation. It has no Codex installation, no model authentication/profile, and never accepts a command or credential variable name from #94. A queue task can select only a locally configured `verifier_action`; that action fixes the literal argv, access class, root-only secret file, and exact environment-variable allowlist. The verifier coordinator loads only that allowlist after exact-reviewed-SHA authorization, demotes the reviewed-code process to its dedicated `verifier` identity, discards its stdout/stderr, and posts only a fixed sanitized receipt.

Production is intentionally unsupported by this service. A `production: true` action is rejected. A future promotion path requires a separately reviewed authorization design.

## One-time local setup

1. Install/update Codex CLI on the PC, or build the checked-in `docker/trusted-local-broker/Dockerfile` image.
2. Create a dedicated broker/worker local account or isolated container boundary.
3. Sign Codex in inside that dedicated worker profile only.
4. Keep the normal interactive user's `.env`, GitHub credential files, Railway/provider keys, browser profiles, and other secrets outside that worker profile.
5. Authenticate the **broker parent** to GitHub separately. Do not make the GitHub token part of the worker environment.
6. Ensure each allowed repo already exists as a local clone with the expected GitHub `origin` and that the parent Git credential helper can push.
7. Create a local-only broker config JSON outside Git. Example:

```json
{
  "agent": "trusted-local-broker-my-pc",
  "worker_home": "<dedicated-worker-home>",
  "codex_home": "<dedicated-worker-home>/.codex",
  "codex_executable": "codex",
  "repos": {
    "Pukujan/fossil-core": {"path": "<local-fossil-core>", "check_command": ["python", "-m", "pytest", "-q"]},
    "Pukujan/cortex-v4": {"path": "<local-cortex-v4>", "check_command": ["python", "-m", "pytest", "-q"]},
    "Pukujan/litellm-ckff-ops": {"path": "<local-litellm-ckff-ops>", "check_command": ["python", "-m", "pytest", "-q"]}
  }
}
```

Do not commit this config if it contains personal paths or local policy details.

### Container boundary (recommended when the PC owner is the normal login)

The checked-in Dockerfile runs the broker parent, its Git publication, and its independent checks inside one narrow container. It demotes only `codex exec` to an unprivileged `codexworker` user. This keeps both model execution and changed-code tests away from the Windows owner profile.

Build it from the repository root:

```text
docker build --tag fossil-trusted-local-broker:local --file docker/trusted-local-broker/Dockerfile .
```

Keep broker credentials, clones, and worktrees in named Docker volumes. Docker Desktop stores those volumes in its managed WSL data location; on this PC that location is `D:\DockerDesktopWSL`. Use a separate volume for the unprivileged Codex authentication, a root-only volume for the parent GitHub CLI authentication, and volumes for allowlisted clones and disposable worktrees. A single read-only local config-file mount may provide non-secret paths/policy. Do not mount `C:\Users\<owner>`, a broad `D:` directory, the Docker socket, provider credentials, browser data, or an inbound port. Configure `codex_executable` as `/usr/local/bin/worker-codex`, and use container paths in the config.

The GitHub CLI parent login is performed as container root and stored only in its dedicated GitHub volume. The Codex device login is performed as `codexworker` and stored only in the dedicated Codex volume. Never copy either auth material between the two volumes. The worker wrapper gives `codexworker` ownership of the new disposable worktree while deliberately leaving its `.git` pointer and the parent clone metadata root-owned.

Docker Desktop may prohibit Codex's nested Linux `workspace-write` namespace. Only in the checked-in Docker topology, set `codex_sandbox` to `danger-full-access`: Docker's named-volume mount set and `codexworker` identity are then the enforcement boundary. The worker has no owner profile, parent GitHub volume, provider credentials, Docker socket, or inbound port. Keep the default `workspace-write` sandbox for non-container deployments.

### Privileged verifier setup (separate container)

The secret file belongs in a **third**, root-only named volume. On this PC the volume data is held by Docker Desktop's WSL store on `D:\DockerDesktopWSL`; it is not in GitHub, the repository, the Codex volume, or the broker container. The original source file remains yours to rotate/delete after verifying the copy. The unprivileged Codex worker must be unable to read this volume.

Build the separate image:

```text
docker build --tag fossil-privileged-local-verifier:local --file docker/privileged-local-verifier/Dockerfile .
```

Keep this local-only JSON at `D:\FossilBrokerWorker\config\privileged-verifier.json` (do not commit it). Start with an empty action map; that is safe and means the service cannot inject any application credential until you deliberately add one narrow action.

```json
{
  "agent": "trusted-local-verifier-my-pc",
  "repos": {"Pukujan/fossil-core": "/data/repos/fossil-core"},
  "trusted_dispatch_refs": ["<exact verifier-image source commit SHA>"],
  "actions": {}
}
```

An approved staging-only action is an owner-administered mapping such as:

```json
"railway-staging-smoke": {
  "access_class": "LIVE_STAGING",
  "secret_file": "/secrets/ssc.env",
  "required_env": ["ONE_EXACT_KEY_THE_CHECK_NEEDS"],
  "command": ["/opt/fossil-venv/bin/python", "scripts/staging_smoke.py", "--worktree", "{worktree}"]
}
```

Use literal argv, never a shell. The queue cannot override any field in that mapping. The task must include the exact reviewed SHA, an allowlisted verifier image source SHA, a matching privileged access class, and the action name:

```text
TASK task=INFRA-EXAMPLE
state=READY
repo=Pukujan/fossil-core
access=LIVE_STAGING
starting_ref=<exact-40-char-reviewed-sha>
reviewed_sha=<same-exact-sha>
trusted_dispatch_ref=<allowlisted-verifier-image-source-sha>
local_role=luna
verifier_action=railway-staging-smoke
```

`local_role=luna` is retained only because the frozen WorkOrder v1 schema requires a role; it never invokes Luna/Codex in this lane and conveys no authority.


## Start and stop

One cycle:

```text
python scripts/run_trusted_local_broker.py --config <local-config.json> --once
```

Continuous outbound polling:

```text
python scripts/run_trusted_local_broker.py --config <local-config.json> --poll-seconds 60
```

The broker opens no inbound port and requires no webhook or self-hosted Actions runner registration.

The privileged verifier is a separate process/container and uses the same polling cadence:

```text
python scripts/run_privileged_local_verifier.py --config <local-verifier-config.json> --poll-seconds 60
```

Stop the process/service to stop local automation immediately.

## Task format required for autonomous local execution

A queue writer must deliberately opt a task in:

```text
TASK task=CORTEX-05
state=READY
repo=Pukujan/cortex-v4
access=CLOUD_SECRETLESS
starting_ref=<exact-40-char-sha>
local_role=terra
purpose=...
acceptance=...
```

`local_role` is an execution/model choice, not an authority grant. Neither Terra nor Luna receives infrastructure credentials.

## Execution lifecycle

For one eligible task the broker:

1. reads trusted #94 state;
2. posts `CLAIM`;
3. re-reads and confirms earliest winning claim;
4. posts versioned `WORKORDER` with generation/attempt identity;
5. creates an isolated exact-SHA worktree;
6. launches fresh ephemeral Codex with the dedicated secretless profile;
7. runs independent configured checks;
8. if checks pass and there is a diff, the **parent broker** commits with hooks disabled, pushes a task branch, and opens a draft PR;
9. posts sanitized `WORKORDER_DONE` + `DONE`/`BLOCKED` + `RELEASE` records;
10. removes the disposable worktree.

GitHub publication happens outside the Codex child so repository credentials do not have to be exposed to the model-driven process.

## Fault and recovery rules

- unreadable GitHub queue -> do nothing / BLOCKED;
- malformed or non-trusted-author task -> ignore;
- lost claim race -> do not launch;
- duplicate/terminal attempt -> reject;
- stale generation -> reject;
- cancel record -> reject;
- deadline/process timeout -> FAILED/BLOCKED mechanically;
- Codex exits 0 but independent checks fail -> not PASS;
- Codex produces no diff for a coding WorkOrder -> BLOCKED `NO_CHANGES`;
- broker/PC dies -> exact SHA + #94 WorkOrder generation make a fresh attempt safe; late attempts remain rejectable.

## Public-repository runner decision

`.github/workflows/trusted-local-workorder.yml` is intentionally removed. If a future GitHub plan/account provides a runner group that can be restricted at the control-plane level to selected trusted workflows, that topology may be re-evaluated. It is not needed for the current outbound-broker design.

## Remaining LOCAL_INFRA proof

Repository code/tests can prove policy and deterministic behavior, but a cloud ChatGPT session cannot start a process on the owner's physical PC. Final acceptance still requires one local proof using the dedicated worker profile:

1. broker starts successfully;
2. one benign `CLOUD_SECRETLESS` local-auto task is claimed and runs through real `codex exec`;
3. independent checks pass;
4. draft PR + sanitized #94 closeout appear;
5. no infrastructure credential is visible to the Codex child;
6. privileged verifier remains separate and no production mutation occurs.
