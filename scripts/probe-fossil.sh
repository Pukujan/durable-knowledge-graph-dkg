#!/usr/bin/env bash
set -euo pipefail

: "${FOSSIL_HEALTH_URL:?Set FOSSIL_HEALTH_URL to the private, non-mutating Fossil health endpoint}"

output_path="${FOSSIL_PROBE_OUTPUT:-${RUNNER_TEMP:-.}/fossil-private-health.json}"
mkdir -p "$(dirname "$output_path")"

python scripts/private_probe.py \
  --name fossil \
  --url "$FOSSIL_HEALTH_URL" \
  --require-json-key "${FOSSIL_HEALTH_JSON_KEY:-status}" \
  --bearer-env FOSSIL_HEALTH_TOKEN \
  --output "$output_path"
