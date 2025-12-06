#!/usr/bin/env bash
#
# Orchestrated local smoke test:
#   - Ensures .env exists
#   - Starts docker/testnet stack with node1 scaled to zero (to avoid 9091 conflict)
#   - Waits for bootstrap/node2 healthy status + Grafana/Prometheus readiness
#   - Runs send_rejection_smoke_test.sh
#   - Tears everything down unless KEEP_STACK=1

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STACK_DIR="${ROOT}/docker/testnet"
LOG_PREFIX="[local_smoke]"

require_bin() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "${LOG_PREFIX} Missing dependency '$1'." >&2
    exit 1
  }
}

require_bin docker
require_bin jq
require_bin curl

if [[ ! -f "${ROOT}/.env" ]]; then
  echo "${LOG_PREFIX} .env not found, copying from .env.example"
  cp "${ROOT}/.env.example" "${ROOT}/.env"
fi

echo "${LOG_PREFIX} starting docker stack..."
pushd "${ROOT}" >/dev/null
docker compose -f docker/testnet/docker-compose.yml up -d --scale xai-testnet-node1=0
popd >/dev/null

cleanup() {
  if [[ "${KEEP_STACK:-0}" != "1" ]]; then
    echo "${LOG_PREFIX} tearing down stack..."
    pushd "${ROOT}" >/dev/null
    docker compose -f docker/testnet/docker-compose.yml down || true
    popd >/dev/null
  else
    echo "${LOG_PREFIX} KEEP_STACK=1 set - leaving containers running."
  fi
}
trap cleanup EXIT

containers=(xai-testnet-bootstrap xai-testnet-node2)

wait_for_container() {
  local name=$1
  echo "${LOG_PREFIX} waiting for container ${name}..."
  local retries=30
  while (( retries > 0 )); do
    health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}n/a{{end}}' "$name" 2>/dev/null || echo "unknown")
    state=$(docker inspect --format '{{.State.Status}}' "$name" 2>/dev/null || echo "unknown")
    if [[ "$health" == "healthy" || "$state" == "running" ]]; then
      echo "${LOG_PREFIX} ${name} ready (state=${state}, health=${health})."
      return
    fi
    sleep 5
    retries=$((retries - 1))
  done
  echo "${LOG_PREFIX} ERROR: container ${name} did not become healthy." >&2
  exit 1
}

wait_for_port() {
  local url=$1
  local retries=30
  echo "${LOG_PREFIX} waiting for ${url}..."
  while (( retries > 0 )); do
    if curl -sf "$url" >/dev/null; then
      echo "${LOG_PREFIX} ${url} ready."
      return
    fi
    sleep 5
    retries=$((retries - 1))
  done
  echo "${LOG_PREFIX} ERROR: ${url} not reachable." >&2
  exit 1
}

for name in "${containers[@]}"; do
  wait_for_container "$name"
done

wait_for_port "http://localhost:8080/health"
wait_for_port "http://localhost:9093/-/ready"
wait_for_port "http://localhost:3001/api/health"

echo "${LOG_PREFIX} running send_rejection_smoke_test.sh..."
API_URL=http://localhost:8080 PROM_URL=http://localhost:9093 \
  "${ROOT}/scripts/tools/send_rejection_smoke_test.sh"

echo "${LOG_PREFIX} local smoke test complete."
