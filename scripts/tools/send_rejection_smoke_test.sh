#!/usr/bin/env bash
#
# Smoke test for /send rejection telemetry.
# Requires:
#   - Local docker testnet (or any node) reachable via $API_URL (default http://localhost:8080)
#   - Prometheus scraping node metrics at $PROM_URL (default http://localhost:9093)
#   - curl, jq available in PATH
#
# The script:
#   1. Captures current counter values for each /send rejection reason.
#   2. Issues three intentionally invalid /send requests (stale timestamp, future timestamp, txid mismatch).
#   3. Verifies that the counters increment accordingly.

set -euo pipefail

API_URL="${API_URL:-http://localhost:8080}"
PROM_URL="${PROM_URL:-http://localhost:9093}"
SENDER="${SENDER:-XAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA}"
RECIPIENT="${RECIPIENT:-XAIBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB}"
PUBLIC_KEY="${PUBLIC_KEY:-04$(printf 'C%.0s' {1..128})}"
SIGNATURE="${SIGNATURE:-$(printf 'AB%.0s' {1..64})}"
COOKIE_JAR="$(mktemp)"
trap 'rm -f "$COOKIE_JAR"' EXIT

METRICS=(
  xai_send_rejections_stale_timestamp_total
  xai_send_rejections_future_timestamp_total
  xai_send_rejections_txid_mismatch_total
)

require_bin() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: Missing dependency '$1'." >&2
    exit 1
  }
}

require_bin curl
require_bin jq

fetch_csrf_token() {
  curl -s -c "$COOKIE_JAR" "${API_URL}/csrf-token" \
    | jq -r '.csrf_token' \
    || {
      echo "ERROR: unable to fetch CSRF token from ${API_URL}/csrf-token" >&2
      exit 1
    }
}

fetch_metric() {
  local metric=$1
  curl -sG "${PROM_URL}/api/v1/query" \
    --data-urlencode "query=${metric}" \
    | jq -r '.data.result[0].value[1] // "0"' \
    || echo "0"
}

declare -A BEFORE
declare -A AFTER

echo "Capturing baseline metric values from ${PROM_URL}..."
for metric in "${METRICS[@]}"; do
  BEFORE["$metric"]="$(fetch_metric "$metric")"
  echo "  ${metric}: ${BEFORE[$metric]}"
done

CSRF_TOKEN="$(fetch_csrf_token)"

post_send() {
  local payload=$1
  curl -s -X POST "${API_URL}/send" \
    -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
    -H "Content-Type: application/json" \
    -H "X-CSRF-Token: ${CSRF_TOKEN}" \
    -d "$payload" >/dev/null
}

echo "Triggering stale timestamp rejection..."
post_send "$(jq -nc --arg sender "$SENDER" \
  --arg recipient "$RECIPIENT" \
  --arg pk "$PUBLIC_KEY" \
  --arg sig "$SIGNATURE" \
  '{sender:$sender,recipient:$recipient,amount:1.0,fee:0.001,public_key:$pk,nonce:1,signature:$sig,timestamp:1000}')"

echo "Triggering future timestamp rejection..."
FUTURE_TS=$(( $(date +%s) + 7200 + 600 ))
post_send "$(jq -nc --arg sender "$SENDER" \
  --arg recipient "$RECIPIENT" \
  --arg pk "$PUBLIC_KEY" \
  --arg sig "$SIGNATURE" \
  --argjson ts "$FUTURE_TS" \
  '{sender:$sender,recipient:$recipient,amount:1.0,fee:0.001,public_key:$pk,nonce:2,signature:$sig,timestamp:$ts}')"

echo "Triggering txid mismatch rejection..."
CURRENT_TS=$(date +%s)
post_send "$(jq -nc --arg sender "$SENDER" \
  --arg recipient "$RECIPIENT" \
  --arg pk "$PUBLIC_KEY" \
  --arg sig "$SIGNATURE" \
  --argjson ts "$CURRENT_TS" \
  '{sender:$sender,recipient:$recipient,amount:1.0,fee:0.001,public_key:$pk,nonce:3,signature:$sig,timestamp:$ts,txid:"deadbeef"}')"

sleep 2

echo "Fetching post-test metric values..."
for metric in "${METRICS[@]}"; do
  AFTER["$metric"]="$(fetch_metric "$metric")"
  echo "  ${metric}: ${AFTER[$metric]}"
done

failures=0
check_increment() {
  local metric=$1
  local before=${BEFORE[$metric]:-0}
  local after=${AFTER[$metric]:-0}
  if (( $(printf "%0.f" "$after") <= $(printf "%0.f" "$before") )); then
    echo "ERROR: ${metric} did not increase (before=${before}, after=${after})." >&2
    failures=$((failures + 1))
  fi
}

check_increment xai_send_rejections_stale_timestamp_total
check_increment xai_send_rejections_future_timestamp_total
check_increment xai_send_rejections_txid_mismatch_total

if (( failures > 0 )); then
  echo "Smoke test failed: ${failures} metric(s) did not increment." >&2
  exit 1
fi

echo "Smoke test succeeded: all /send rejection metrics incremented."
