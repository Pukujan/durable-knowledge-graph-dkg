# D027 — Broker refresh is controlled by a tiny host-side supervisor

**State:** accepted / provisional trusted-local topology refinement  
**Date:** 2026-08-12  
**Refines:** D024, D025; Issue #94 `INFRA-09`

## Decision

Use deterministic host-side supervisor code to rebuild and atomically refresh the trusted-local broker only for an explicit trusted-author `BROKER_RELEASE` directive naming `Pukujan/fossil-core` and an exact reviewed SHA. The directive cannot select a repository, branch, image, Dockerfile, command, mount, port, environment variable, or credential path.

The supervisor validates live `origin/main`, successful GitHub checks, exact origin, detached build revision, image revision label, candidate smoke, and post-start container identity. It rolls back to the captured prior image on failed replacement. The broker/Codex containers remain without Docker socket, owner profile, provider credentials, or inbound ports.

## Residual risk and reconsideration

The supervisor necessarily retains broad Docker Desktop authority; it is therefore a deliberately tiny non-model local root of trust, not an extensible deployment agent. Reconsider if Docker Desktop gains a sufficiently constrained control plane or a narrower independently auditable host mechanism proves equivalent safety.
