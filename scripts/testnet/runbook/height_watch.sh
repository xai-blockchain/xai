#!/usr/bin/env bash
set -euo pipefail

require() {
  local name="$1"
  if [ -z "${!name:-}" ]; then
    echo "Missing required env: $name" >&2
    exit 1
  fi
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

need_cmd curl
need_cmd jq

require API_BASE_URL

ITERATIONS=${ITERATIONS:-6}
SLEEP_SECONDS=${SLEEP_SECONDS:-20}

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

prev_height=0

log "Watching heights for $ITERATIONS iterations"
for i in $(seq 1 "$ITERATIONS"); do
  height=$(curl -fsS "$API_BASE_URL/stats" | jq -r '.chain_height // empty')
  if ! [[ "$height" =~ ^[0-9]+$ ]]; then
    echo "Invalid chain_height: ${height:-<empty>}" >&2
    exit 1
  fi
  if [ "$height" -lt "$prev_height" ]; then
    echo "Chain height decreased: $prev_height -> $height" >&2
    exit 1
  fi
  log "Iteration $i: height=$height"
  prev_height=$height
  sleep "$SLEEP_SECONDS"
done

log "Height watch complete"
