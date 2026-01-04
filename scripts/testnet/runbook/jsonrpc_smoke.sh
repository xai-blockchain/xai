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

require JSONRPC_URL

RUN_ID=${RUN_ID:-$(date -u +%Y%m%d-%H%M%S)}
OUT_DIR=${OUT_DIR:-./out}/${RUN_ID}
mkdir -p "$OUT_DIR"

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

call() {
  local method="$1"
  local params="$2"
  local id="$3"
  curl -fsS -X POST "$JSONRPC_URL" \
    -H 'Content-Type: application/json' \
    -d "{\"jsonrpc\":\"2.0\",\"id\":$id,\"method\":\"$method\",\"params\":$params}" \
    -o "$OUT_DIR/${method}.json"
  jq -e '.result // empty' "$OUT_DIR/${method}.json" >/dev/null
}

log "JSON-RPC clientVersion"
call "web3_clientVersion" "[]" 1

log "JSON-RPC chainId"
call "eth_chainId" "[]" 2

log "JSON-RPC blockNumber"
call "eth_blockNumber" "[]" 3

log "JSON-RPC smoke checks complete"
