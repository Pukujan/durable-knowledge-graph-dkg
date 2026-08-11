#!/usr/bin/env bash
set -euo pipefail

: "${GRAVEBUSTER_HEALTH_URL:?Set GRAVEBUSTER_HEALTH_URL to a required private Gravebuster service health endpoint}"

output_dir="${GRAVEBUSTER_PROBE_OUTPUT_DIR:-${RUNNER_TEMP:-.}}"
mkdir -p "$output_dir"

python scripts/private_probe.py \
  --name gravebuster \
  --url "$GRAVEBUSTER_HEALTH_URL" \
  --require-json-key "${GRAVEBUSTER_HEALTH_JSON_KEY:-status}" \
  --bearer-env GRAVEBUSTER_HEALTH_TOKEN \
  --output "$output_dir/gravebuster-private-health.json"

probe_optional() {
  local name="$1"
  local url="$2"
  local key="$3"
  local token_env="$4"
  [[ -n "$url" ]] || return 0
  python scripts/private_probe.py \
    --name "$name" \
    --url "$url" \
    --require-json-key "$key" \
    --bearer-env "$token_env" \
    --output "$output_dir/${name}-private-health.json"
}

probe_optional "gravebuster-otel" "${GRAVEBUSTER_OTEL_HEALTH_URL:-}" \
  "${GRAVEBUSTER_OTEL_HEALTH_JSON_KEY:-status}" GRAVEBUSTER_OTEL_HEALTH_TOKEN
probe_optional "gravebuster-langfuse" "${GRAVEBUSTER_LANGFUSE_HEALTH_URL:-}" \
  "${GRAVEBUSTER_LANGFUSE_HEALTH_JSON_KEY:-status}" GRAVEBUSTER_LANGFUSE_HEALTH_TOKEN
