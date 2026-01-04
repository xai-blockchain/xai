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
require ADDRESS

RUN_ID=${RUN_ID:-$(date -u +%Y%m%d-%H%M%S)}
OUT_DIR=${OUT_DIR:-./out}/${RUN_ID}
mkdir -p "$OUT_DIR"

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

if [ -n "${FAUCET_URL:-}" ]; then
  log "Requesting faucet funds"
  curl -fsS -X POST "$FAUCET_URL" \
    -H 'Content-Type: application/json' \
    -d "{\"address\":\"$ADDRESS\"}" \
    -o "$OUT_DIR/faucet.json"
fi

log "Checking balance"
RESP=$(curl -fsS "$API_BASE_URL/balance/$ADDRESS")
echo "$RESP" > "$OUT_DIR/balance.json"

BAL=$(echo "$RESP" | jq -r '.balance // .amount // .result // empty' 2>/dev/null || true)
if [[ "$BAL" =~ ^[0-9]+$ ]]; then
  log "Balance: $BAL"
else
  log "Balance response saved (non-standard shape)"
fi

log "Faucet/balance check complete"
