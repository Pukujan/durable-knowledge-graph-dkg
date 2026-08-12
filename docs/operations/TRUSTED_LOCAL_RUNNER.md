# Trusted-local runner enrollment and operations

**Authority:** D022; `docs/architecture/2026-08-12-trusted-local-runner-boundary.md`; issue #96 / #94 `INFRA-03`.

This runbook enrolls one narrow credential-boundary runner. It does not authorize a deployment, production promotion, a public inbound endpoint, or ordinary pull-request execution.

## Enroll the runner (LOCAL_INFRA)

1. In the repository Actions settings, create a short-lived self-hosted runner registration token. Never paste the token into Git, issue comments, chat, logs, receipts, or shell history.
2. Install the GitHub Actions runner under a dedicated local OS account/service boundary where practical. Use a runner name that identifies the host/trust class but exposes no credential or personal data.
3. Register it only for `Pukujan/fossil-core` with labels `self-hosted,trusted-local,windows` (replace `windows` only if the actual host OS differs). Do not use `trusted-local` on a general-purpose or untrusted runner.
4. Start the service with no Railway/provider/telemetry/object-store environment variables. The service account must not inherit an interactive user's `.env`.
5. Confirm that only `.github/workflows/trusted-local-workorder.yml` targets `trusted-local`, and that it has no `pull_request` or `pull_request_target` trigger.
6. Dispatch a `CLOUD_SECRETLESS`, `luna` WorkOrder with an exact 40-character reviewed SHA and the `pytest` check profile. Confirm receipt redaction, worktree cleanup, and that no protected variable is visible to the child process.

The runner uses GitHub's outbound connection; do not open a webhook listener or inbound public port on the PC.

## Privileged verifier installation

The repository workflow never starts the privileged lane. Install a separate local-only wrapper outside this repository that calls `dkg.trusted_local_runner.dispatch_privileged_verifier`.

Before that wrapper loads its minimum local credential environment, it must verify all of the following:

- the WorkOrder access class is one of `LOCAL_INFRA`, `TRUSTED_SECRET_WORKFLOW`, `LIVE_STAGING`, or `OBJECT_STORE_LIVE`;
- `starting_ref` is a 40-character SHA and equals `reviewed_sha`;
- `trusted_dispatch_ref` is a reviewed/default-branch dispatcher SHA pinned in its local policy;
- #94 reports the running dispatcher as the active winning claim owner;
- the task/repository/mutation scope are locally allowlisted;
- production promotion is explicitly absent from mutation scope.

The wrapper must pass only the minimum required credential names to the isolated verifier process, collect a sanitized compact receipt, and observe remote effect identity before retrying. It must never execute PR-controlled workflow definitions or echo environment values.

## Disable, revoke, and recover

- Disable the runner in GitHub Actions settings first, then stop its local service.
- Revoke the registration token if it remains valid; rotate any credential that may have reached an unintended process.
- Remove the runner registration using the GitHub-provided remove token; do not commit either token.
- Delete only the dedicated disposable worktree directory after terminal receipt preservation; an interrupted attempt remains recoverable from its exact SHA and receipt/correlation IDs.
- A ledger/API read failure, expired claim, malformed WorkOrder, duplicate attempt, stale generation, cancellation, or late result is a `BLOCKED` closeout, not a reason to bypass validation.
