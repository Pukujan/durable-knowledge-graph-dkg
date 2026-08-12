# Trusted Local Broker Supervisor Boundary

**Date:** 2026-08-12  
**Status:** implementation contract for Issue #94 `INFRA-09`

The broker container and its Codex worker have no Docker socket or host-control capability. A small deterministic host supervisor is the one exceptional root of trust that may invoke Docker Desktop to refresh the continuously running broker after review.

The supervisor accepts only a trusted-author queue line in this literal form:

```text
BROKER_RELEASE repo=Pukujan/fossil-core reviewed_sha=<40-lowercase-hex-SHA>
```

It ignores every other field on that line. The SHA must equal live `origin/main`, have readable successful GitHub check evidence, and be built only from a detached exact-SHA worktree whose `origin` is `https://github.com/Pukujan/fossil-core(.git)`. The candidate image tag is derived from that SHA; mutable tags are never promotion authority.

The candidate is built with the fixed broker Dockerfile and smoke-tested with no network and no mounts before the old broker stops. Runtime Docker argv is fixed code plus an owner-local config containing only named allowlisted volumes, a read-only local broker config bind, the `bridge` network, and `restart=unless-stopped`. It exposes no ports and cannot express Docker-socket, owner-profile, broad-drive, or provider-secret mounts.

On a start/identity/health failure, the supervisor removes the candidate container and starts the previously captured image with the same fixed policy. It never removes the prior image until a replacement is proven healthy. Repeating an already-running SHA is a no-op.

The optional supervisor GitHub credential is separate from the broker-parent and Codex-worker credentials. It is used only by the host supervisor for release/check reads (and a future sanitized receipt writer), is never passed to Docker build/smoke/runtime or Codex, and is not logged. Receipts/logs contain only task/SHA/image-ID class/status, never secrets or owner paths.

## Residual risk

Docker Desktop does not offer a per-container Docker-control capability. The host supervisor therefore necessarily has broad Docker capability. Its command surface, owner-local config, and credential must remain tiny, non-model, local-only, reviewed, and independently auditable. The supervisor is not self-modifying: after one separately authorized `LOCAL_INFRA` bootstrap installation, normal reviewed broker releases can be hands-off.

## One-time bootstrap (not performed by this change)

1. Copy `config/trusted-local-broker-supervisor.example.json` to an owner-local path and replace the placeholder paths with the checked-out repository and broker config paths.
2. Provide a distinct supervisor-only GitHub credential in the host service environment as `FOSSIL_SUPERVISOR_GITHUB_TOKEN`; do not place it in the broker config, image, or worker environment.
3. Install a host service that invokes `scripts/run_trusted_local_broker_supervisor.py --config <owner-local-config>` under the dedicated local supervisor account.
4. Test only a reviewed benign SHA, then enable polling. The supervisor itself is not installed or started by repository code.
