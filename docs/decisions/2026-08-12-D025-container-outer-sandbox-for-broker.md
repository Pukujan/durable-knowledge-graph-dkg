# D025 — Docker outer sandbox for trusted local broker

**State:** accepted / implementation refinement  
**Date:** 2026-08-12  
**Refines:** D024; INFRA-05 physical proof.

## Decision

When Docker Desktop prevents nested unprivileged Linux namespaces, run Codex with `danger-full-access` **only inside** the dedicated broker Docker container. The container remains the OS-enforced boundary: the child is `codexworker`; it receives only its Codex-auth volume and the disposable repository/worktree volumes; the root-only GitHub-parent volume, owner profile, provider credentials, Docker socket, and inbound ports are absent.

Non-container broker deployments retain Codex `workspace-write` as their default. This is not permission to run Codex with unrestricted host access.

## Evidence

The physical proof showed `workspace-write` failing before file operations because Docker Desktop denied nested user namespaces, including with the distribution `bubblewrap` package. Under the restricted container mount set, a Luna `danger-full-access` diagnostic successfully created a requested disposable-worktree file while still running as `codexworker`.

## Reconsider when

Docker Desktop enables nested unprivileged namespaces reliably, or a stronger nested sandbox works under the same corpus-specific isolation proof.
