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

The generated prompt forbids credential discovery, `.env` access, deploy/promotion, push/PR creation, and external mutation. The Codex child's exit code is not final acceptance: the parent broker runs the configured independent check command afterwards.

## Credential split

There are three separate contexts.

### 1. Broker parent

The parent may use a GitHub coordination/publication credential (prefer an authenticated local `gh`/Git credential setup or a narrowly scoped local token). It reads/posts #94, pushes the mechanically checked branch, and opens the draft PR.

**The GitHub token is never passed to the Codex child.**

The parent publication step uses a reviewed repo allowlist, forces the expected GitHub origin, disables Git hooks for its commit/push path, and runs only after the independent test command succeeds.

### 2. Secretless Codex worker

Use a dedicated local OS account/profile where practical. At minimum configure separate `worker_home` and `codex_home` paths that contain only the Codex authentication/config needed to run the CLI.

The child environment is reconstructed from a small OS allowlist. It does not inherit the interactive user's `HOME`, `GITHUB_TOKEN`, Railway/provider keys, `OPENAI_API_KEY`, or other credential-like environment variables.

Treat Codex's local auth file as a password. Do not copy it into Git, #94, logs, chat, or the repository worktree.

### 3. Privileged verifier

Railway/provider/telemetry/object-store credentials remain a **separate deterministic verifier lane**. A model/Codex process does not receive those credentials.

The existing `dispatch_privileged_verifier` path may load the minimum local credential environment only after exact-reviewed-SHA authorization. Production promotion remains separately forbidden unless explicitly authorized.

## One-time local setup

1. Install/update Codex CLI on the PC.
2. Create a dedicated broker/worker local account or isolated worker home.
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
