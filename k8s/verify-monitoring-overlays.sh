#!/usr/bin/env bash
# Verify monitoring overlays (Alertmanager/Prometheus rules/Grafana) after applying to a namespace.
set -euo pipefail

NAMESPACE="xai-blockchain"
APP_NAMESPACE=""
ALERTMANAGER_SERVICE=""
PROBE_SIEM=0
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATUS=0

usage() {
  cat <<'EOF'
Usage: ./k8s/verify-monitoring-overlays.sh [--namespace=<ns>] [--app-namespace=<ns>] [--alertmanager-service=<svc>] [--probe-siem]

Checks:
  - ConfigMaps: alertmanager-xai-blockchain, xai-prometheus-alerts, xai-grafana-security-ops
  - Alertmanager config includes p2p.* / fast_mining routes to SIEM
  - Prometheus rules contain fast-mining and QUIC error/timeout alerts
  - Grafana dashboard references Prometheus datasource and QUIC panels
  - Optional: probe SIEM webhook using XAI_SECURITY_WEBHOOK_URL from the app ConfigMap
  - Optional: hit Alertmanager /api/v2/alerts via <alertmanager-service>
EOF
}

log_info() { echo "[INFO] $1"; }
log_warn() { echo "[WARN] $1"; }
log_error() { echo "[ERROR] $1"; STATUS=1; }
log_ok() { echo "[OK] $1"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --namespace=*) NAMESPACE="${1#*=}"; shift ;;
    --app-namespace=*) APP_NAMESPACE="${1#*=}"; shift ;;
    --alertmanager-service=*) ALERTMANAGER_SERVICE="${1#*=}"; shift ;;
    --probe-siem) PROBE_SIEM=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) log_error "Unknown argument: $1"; usage; exit 1 ;;
  esac
done

if [[ -z "$APP_NAMESPACE" ]]; then
  APP_NAMESPACE="$NAMESPACE"
fi

log_info "Namespace for monitoring assets: $NAMESPACE"
log_info "Namespace for app ConfigMap/SIEM probe: $APP_NAMESPACE"

if ! command -v kubectl >/dev/null 2>&1; then
  log_error "kubectl not found"
  exit 1
fi
if ! kubectl cluster-info >/dev/null 2>&1; then
  log_error "Cannot reach Kubernetes cluster via kubectl"
  exit 1
fi

check_configmap_exists() {
  local cm="$1"
  if kubectl -n "$NAMESPACE" get configmap "$cm" >/dev/null 2>&1; then
    log_ok "ConfigMap $cm present in $NAMESPACE"
    return 0
  fi
  log_error "ConfigMap $cm missing in $NAMESPACE"
  return 1
}

check_alertmanager_config() {
  local cm="alertmanager-xai-blockchain"
  check_configmap_exists "$cm" || return
  local config
  config=$(kubectl -n "$NAMESPACE" get configmap "$cm" -o jsonpath='{.data.alertmanager\.yml}' 2>/dev/null || echo "")
  if echo "$config" | grep -Fq 'p2p\\.'; then
    log_ok "Alertmanager config includes p2p.* routing"
  else
    log_warn "Alertmanager config missing p2p.* routing"
  fi
  if echo "$config" | grep -Fq 'config\\.fast_mining_'; then
    log_ok "Alertmanager config includes fast_mining routes"
  else
    log_warn "Alertmanager config missing fast_mining routes"
  fi
  if echo "$config" | grep -qi "siem"; then
    log_ok "Alertmanager config references SIEM receiver"
  else
    log_warn "Alertmanager config does not reference SIEM receiver"
  fi
}

check_prometheus_rules() {
  local cm="xai-prometheus-alerts"
  check_configmap_exists "$cm" || return
  local rules
  rules=$(kubectl -n "$NAMESPACE" get configmap "$cm" -o jsonpath='{.data.prometheus_alerts\.yml}' 2>/dev/null || echo "")
  if echo "$rules" | grep -q "FastMiningConfigEnabled"; then
    log_ok "Prometheus rules include fast-mining alert"
  else
    log_warn "Fast-mining alert missing from Prometheus rules"
  fi
  if echo "$rules" | grep -q "P2PQuicErrors"; then
    log_ok "Prometheus rules include P2PQuicErrors"
  else
    log_warn "P2PQuicErrors missing from Prometheus rules"
  fi
  if echo "$rules" | grep -q "P2PQuicDialTimeouts"; then
    log_ok "Prometheus rules include P2PQuicDialTimeouts"
  else
    log_warn "P2PQuicDialTimeouts missing from Prometheus rules"
  fi
}

check_grafana_dashboard() {
  local cm="xai-grafana-security-ops"
  check_configmap_exists "$cm" || return
  local dashboard
  dashboard=$(kubectl -n "$NAMESPACE" get configmap "$cm" -o jsonpath='{.data.aixn_security_operations\.json}' 2>/dev/null || echo "")
  if echo "$dashboard" | grep -Eq '"uid"[[:space:]]*:[[:space:]]*"prometheus"'; then
    log_ok "Grafana dashboard references datasource uid=prometheus"
  else
    log_warn "Grafana dashboard missing datasource uid=prometheus"
  fi
  if echo "$dashboard" | grep -q "xai_p2p_quic_errors_total"; then
    log_ok "Grafana dashboard includes QUIC error panel"
  else
    log_warn "Grafana dashboard missing QUIC error panel"
  fi
  if echo "$dashboard" | grep -q "xai_p2p_quic_timeouts_total"; then
    log_ok "Grafana dashboard includes QUIC timeout series"
  else
    log_warn "Grafana dashboard missing QUIC timeout series"
  fi
  if echo "$dashboard" | grep -q "Fast Mining Config Events"; then
    log_ok "Grafana dashboard includes fast-mining panel"
  else
    log_warn "Grafana dashboard missing fast-mining panel"
  fi
}

probe_siem_webhook() {
  local cm="xai-blockchain-config"
  local url token
  url=$(kubectl -n "$APP_NAMESPACE" get configmap "$cm" -o jsonpath='{.data.XAI_SECURITY_WEBHOOK_URL}' 2>/dev/null || echo "")
  token=$(kubectl -n "$APP_NAMESPACE" get configmap "$cm" -o jsonpath='{.data.XAI_SECURITY_WEBHOOK_TOKEN}' 2>/dev/null || echo "")
  if [[ -z "$url" ]]; then
    log_warn "XAI_SECURITY_WEBHOOK_URL not set in $APP_NAMESPACE/$cm; skipping SIEM probe"
    return
  fi
  log_info "Probing SIEM webhook defined in $APP_NAMESPACE/$cm..."
  XAI_SECURITY_WEBHOOK_URL="$url" XAI_SECURITY_WEBHOOK_TOKEN="$token" "${ROOT_DIR}/scripts/ci/smoke_siem_webhook.sh" && \
    log_ok "SIEM webhook probe succeeded" || {
      log_warn "SIEM webhook probe failed"
      STATUS=1
    }
}

check_alertmanager_api() {
  if [[ -z "$ALERTMANAGER_SERVICE" ]]; then
    return
  fi
  if ! kubectl -n "$NAMESPACE" get svc "$ALERTMANAGER_SERVICE" >/dev/null 2>&1; then
    log_warn "Alertmanager service $ALERTMANAGER_SERVICE not found in $NAMESPACE"
    return
  fi
  local pod="am-api-check-$(date +%s)"
  log_info "Querying Alertmanager /api/v2/alerts via service $ALERTMANAGER_SERVICE..."
  if kubectl -n "$NAMESPACE" run "$pod" --image=curlimages/curl:8.5.0 --rm -i --restart=Never --command -- \
    curl -sSf "http://${ALERTMANAGER_SERVICE}:9093/api/v2/alerts" >/dev/null; then
    log_ok "Alertmanager /api/v2/alerts reachable"
  else
    log_warn "Unable to reach Alertmanager /api/v2/alerts via $ALERTMANAGER_SERVICE"
    STATUS=1
  fi
}

check_alertmanager_config
check_prometheus_rules
check_grafana_dashboard
check_alertmanager_api
if [[ "$PROBE_SIEM" -eq 1 ]]; then
  probe_siem_webhook
fi

if [[ $STATUS -eq 0 ]]; then
  log_ok "Monitoring overlay verification completed without critical failures."
else
  log_warn "Monitoring overlay verification finished with warnings/errors."
fi

exit $STATUS
