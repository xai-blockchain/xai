#!/usr/bin/env bash
set -euo pipefail

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

need_cmd k6
need_cmd jq

RUN_ID=${RUN_ID:-$(date -u +%Y%m%d-%H%M%S)}
OUT_DIR=${OUT_DIR:-./out}/${RUN_ID}
mkdir -p "$OUT_DIR"

LOG_DIR="$OUT_DIR/k6"
mkdir -p "$LOG_DIR"

if [ -f "scripts/testnet/runbook/.env" ]; then
  set -a
  . scripts/testnet/runbook/.env
  set +a
fi

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

run_one() {
  local profile="$1"
  local script="$2"
  local name
  name=$(basename "$script" .js)
  local out="$LOG_DIR/${name}_${profile}.log"
  local summary="$LOG_DIR/${name}_${profile}.summary.json"
  log "Running $script ($profile)"
  if PROFILE="$profile" k6 run --summary-export "$summary" "$script" | tee "$out" >/dev/null; then
    log "$script ($profile) OK"
    echo "$name,$profile,ok,$summary" >> "$LOG_DIR/summary.csv"
    return 0
  fi
  log "$script ($profile) FAILED"
  echo "$name,$profile,failed,$summary" >> "$LOG_DIR/summary.csv"
  return 1
}

scripts=(
  "scripts/testnet/runbook/k6_api_read.js"
)

fail=0
echo "script,profile,status,summary_json" > "$LOG_DIR/summary.csv"
for profile in baseline peak; do
  log "Starting profile: $profile"
  for script in "${scripts[@]}"; do
    run_one "$profile" "$script" || fail=1
  done
  log "Completed profile: $profile"
  echo >> "$LOG_DIR/summary.txt"
  echo "Profile $profile logs in $LOG_DIR" >> "$LOG_DIR/summary.txt"
  echo >> "$LOG_DIR/summary.txt"
 done

SUMMARY_MD="$LOG_DIR/summary.md"
{
  echo "# K6 Summary"
  echo
  echo "| script | profile | status | p95_ms | p99_ms | error_rate | checks_rate |"
  echo "| --- | --- | --- | --- | --- | --- | --- |"
  while IFS=, read -r script profile status summary; do
    if [ "$script" = "script" ]; then
      continue
    fi
    p95=$(jq -r '.metrics.http_req_duration["p(95)"]? // empty' "$summary" 2>/dev/null || true)
    p99=$(jq -r '.metrics.http_req_duration["p(99)"]? // empty' "$summary" 2>/dev/null || true)
    err=$(jq -r '.metrics.http_req_failed.rate? // empty' "$summary" 2>/dev/null || true)
    checks=$(jq -r '.metrics.checks.rate? // empty' "$summary" 2>/dev/null || true)
    printf "| %s | %s | %s | %s | %s | %s | %s |\n" "$script" "$profile" "$status" "${p95:-n/a}" "${p99:-n/a}" "${err:-n/a}" "${checks:-n/a}"
  done < "$LOG_DIR/summary.csv"
} > "$SUMMARY_MD"

log "Summary written to $SUMMARY_MD"

if [ "$fail" -ne 0 ]; then
  echo "One or more k6 tests failed. See logs in $LOG_DIR" >&2
  exit 1
fi

log "All k6 baseline/peak runs completed"
