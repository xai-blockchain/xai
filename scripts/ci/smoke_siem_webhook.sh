#!/usr/bin/env bash
# Optional SIEM webhook smoke-test. Exits 0 if URL not provided.
set -euo pipefail

WEBHOOK_URL="${XAI_SECURITY_WEBHOOK_URL:-}"
WEBHOOK_TOKEN="${XAI_SECURITY_WEBHOOK_TOKEN:-}"

if [[ -z "$WEBHOOK_URL" ]]; then
  echo "[WARN] XAI_SECURITY_WEBHOOK_URL not set; skipping SIEM webhook smoke-test."
  exit 0
fi

echo "[INFO] Probing SIEM webhook..."
payload='{"event_type":"p2p.siem_probe","severity":"WARNING","details":{"probe":"ci-smoke"}}'
headers=(-H "Content-Type: application/json")
if [[ -n "$WEBHOOK_TOKEN" ]]; then
  headers+=(-H "Authorization: Bearer ${WEBHOOK_TOKEN}")
fi

if curl -sf -m 5 -X POST "${headers[@]}" -d "$payload" "$WEBHOOK_URL" >/dev/null; then
  echo "[INFO] SIEM webhook responded successfully."
else
  echo "[ERROR] SIEM webhook probe failed."
  exit 1
fi
