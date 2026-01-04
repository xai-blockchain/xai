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

RUN_ID=${RUN_ID:-$(date -u +%Y%m%d-%H%M%S)}
OUT_DIR=${OUT_DIR:-./out}/${RUN_ID}
mkdir -p "$OUT_DIR"

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

log "Health"
curl -fsS "$API_BASE_URL/health" -o "$OUT_DIR/health.json"

log "Stats"
curl -fsS "$API_BASE_URL/stats" -o "$OUT_DIR/stats.json"

log "Blocks list"
curl -fsS "$API_BASE_URL/blocks" -o "$OUT_DIR/blocks.json"

log "Peers"
curl -fsS "$API_BASE_URL/peers" -o "$OUT_DIR/peers.json"

jq -e '.' "$OUT_DIR/stats.json" >/dev/null
jq -e '.' "$OUT_DIR/blocks.json" >/dev/null
jq -e '.' "$OUT_DIR/peers.json" >/dev/null

log "Smoke checks complete"
