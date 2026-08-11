# GitHub-hosted Tailscale control plane

This is the implementation contract for `Pukujan/fossil-core#79`. GitHub-hosted
Actions is the normal orchestrator. Each integration job joins the tailnet as a
short-lived `tag:ci` node, performs a bounded operation, uploads sanitized
evidence, and exits. Fossil remains the durable semantic store; Gravebuster is
only the remote persistent host for services that genuinely need to survive a
workflow run.

## Observed local inventory

The local Codex host can reach the remote Gravebuster machine over Tailscale
SSH. The remote machine is an Ubuntu Linux host and is online on the tailnet.
The Fossil source checkout exists on that machine under its V4 lab workspace.

The inventory also found persistent Langfuse and OpenTelemetry services on
Gravebuster. The database listeners observed during discovery were loopback
bound. No running Fossil health/API service or durable Fossil database endpoint
was found, so the Fossil endpoint variables below remain an explicit bootstrap
blocker. No separate Gravebuster GitHub repository was identified; the source
visibility step is therefore unresolved until the actual Gravebuster project
source is named.

This document intentionally does not record Tailscale IPs, SSH credentials,
tokens, raw traces, or private service URLs.

## GitHub configuration

Create these GitHub Actions variables after the corresponding private service
exists:

| Variable | Meaning |
| --- | --- |
| `FOSSIL_TAILSCALE_HOST` | Fossil MagicDNS name or tailnet address used by the Tailscale action ping |
| `FOSSIL_HEALTH_URL` | Non-mutating Fossil HTTP health endpoint, reachable only over Tailscale |
| `FOSSIL_HEALTH_JSON_KEY` | Required JSON key, normally `status` |
| `GRAVEBUSTER_TAILSCALE_HOST` | Gravebuster MagicDNS name or tailnet address used by the action ping |
| `GRAVEBUSTER_HEALTH_URL` | Health endpoint for the one required Gravebuster service |
| `GRAVEBUSTER_OTEL_HEALTH_URL` | Optional OTel health endpoint, only if the collector is retained |
| `GRAVEBUSTER_LANGFUSE_HEALTH_URL` | Optional Langfuse health endpoint, only if self-hosted Langfuse is retained |
| `LITELLM_BASE_URL` | Private LiteLLM base URL for the manual live probe |
| `LITELLM_MODEL` | Explicit requested model identifier; never inferred from a default |
| `OPENCODE_BASE_URL` | Optional private OpenCode gateway base URL |
| `OPENCODE_MODEL` | Explicit requested OpenCode model identifier |

Configure these encrypted secrets. They are consumed by actions/scripts but are
never written to probe reports:

- `TS_OAUTH_CLIENT_ID`
- `TS_AUDIENCE`
- optional endpoint bearer/API keys as referenced by the workflow

The preferred Tailscale authentication is workload identity federation with
`tailscale/github-action@v4`. The workflow grants only `contents: read` and
`id-token: write`; the latter permits fetching the GitHub OIDC token and does
not grant repository write access. The Tailscale trust policy must restrict
`tag:ci` to the exact Fossil/Gravebuster destinations and ports required by the
probes.

## Workflow behavior

- `fossil-private-health.yml` joins the tailnet and performs a GET-only Fossil
  health check. It rejects HTTP success with an empty body, malformed JSON, or
  a missing required key.
- `gravebuster-private-health.yml` checks the required persistent Gravebuster
  service and optionally checks retained OTel/Langfuse endpoints.
- `cross-repo-contracts.yml` runs the normal FOSSIL suite plus the control-plane
  contract tests on a GitHub-hosted runner.
- `langfuse-synthetic-trace.yml` sends one non-sensitive OTel span over the
  private path and queries it back by trace ID. The observations path is
  configurable so the current self-hosted Langfuse major can be used while the
  deployment remains on its supported API version.
- `live-inference-probe.yml` sends an explicit bounded request to LiteLLM and,
  when configured, OpenCode. It fails on empty bodies, malformed JSON, zero
  usable output, or an unknown transport status. It records requested/actual
  model identity without recording the response body.

Routine Fossil health probes never write the knowledge graph. Temporary
databases and service containers belong in test workflows only; they are not
production truth.

## Local service boundary

Do not expose a Fossil database to the public network. When the durable Fossil
service is selected, bind its database to loopback or the tailnet interface as
appropriate, bind its API only to the intended tailnet path, and add the
smallest firewall rule for that named service. Re-check with a tailnet probe
and a non-tailnet probe before claiming the acceptance gate.

No firewall mutation was made during discovery because no Fossil service/API
target was running and several broadly bound services on Gravebuster are
unrelated to this contract. Rebinding those services would exceed #79.

For every service retained on Gravebuster, record `start`, `stop`, `restart`,
`status`, `health`, and `logs` commands in the service's own runbook. Use one
service manager per process. Do not add Kubernetes, a cluster, a second
semantic database, or a mandatory self-hosted runner.

## Acceptance evidence

The issue is complete only after a manual GitHub-hosted run produces artifacts
showing:

1. the ephemeral Tailscale node joined and was removed after the job;
2. Fossil was reached privately and returned valid non-empty JSON;
3. the required Gravebuster service was reached privately;
4. durable Fossil state remained outside GitHub Actions;
5. the chosen minimal OTel/Langfuse path received one synthetic non-sensitive
   trace and the trace was queried back by ID;
6. live inference probes rejected deliberately empty/malformed responses;
7. cross-repository contract tests passed;
8. no public database/API/admin path was needed;
9. no secret appeared in Git history, workflow logs, or artifacts; and
10. a draft PR links the sanitized run IDs and remaining blockers to #79.

Current blockers are the missing running Fossil endpoint, the unresolved
Gravebuster source repository identity, and the unexecuted GitHub-hosted run
because the Tailscale trust variables/secrets are not yet configured in the
repository.
