#!/usr/bin/env bash
# Apply monitoring overlays (Alertmanager/Prometheus rules/Grafana dashboard) for staging/prod.
set -euo pipefail

NAMESPACE="${1:-xai-blockchain}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MONITORING_DIR="${ROOT_DIR}/monitoring"

ALERTMANAGER_CFG="${MONITORING_DIR}/alertmanager.yml"
ALERT_RULES="${MONITORING_DIR}/prometheus_alerts.yml"
DASHBOARD="${MONITORING_DIR}/dashboards/grafana/production/aixn_security_operations.json"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "[ERROR] kubectl is required to apply monitoring overlays"
  exit 1
fi
if ! kubectl cluster-info >/dev/null 2>&1; then
  echo "[ERROR] kubectl cannot reach a cluster; check your KUBECONFIG/context"
  exit 1
fi

if [[ ! -f "$ALERTMANAGER_CFG" || ! -f "$ALERT_RULES" || ! -f "$DASHBOARD" ]]; then
  echo "[ERROR] Monitoring assets not found; expected in ${MONITORING_DIR}"
  exit 1
fi

echo "[INFO] Applying Alertmanager config (SIEM + security routes) to namespace ${NAMESPACE}..."
kubectl -n "$NAMESPACE" create configmap alertmanager-xai-blockchain \
  --from-file=alertmanager.yml="$ALERTMANAGER_CFG" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "[INFO] Applying Prometheus alert rules (fast-mining/P2P/security)..."
kubectl -n "$NAMESPACE" create configmap xai-prometheus-alerts \
  --from-file=prometheus_alerts.yml="$ALERT_RULES" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "[INFO] Applying Grafana security operations dashboard (prometheus datasource uid=prometheus)..."
kubectl -n "$NAMESPACE" create configmap xai-grafana-security-ops \
  --from-file=aixn_security_operations.json="$DASHBOARD" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "$NAMESPACE" label configmap xai-grafana-security-ops grafana_dashboard=1 --overwrite

cat <<'EOF'
[NEXT] Restart your monitoring stack to pick up the new configs:
- Alertmanager: kubectl -n <namespace> rollout restart statefulset/alertmanager or helm upgrade values
- Prometheus rules: ensure rule ConfigMap is mounted or referenced by the operator, then restart if needed
- Grafana: restart deployment/statefulset and verify dashboard is provisioned
- Verify via:
  - ./k8s/verify-monitoring-overlays.sh --namespace=<namespace> --alertmanager-service=<alertmanager-svc> [--probe-siem]
  - ./k8s/verify-deployment.sh --namespace=<app-namespace> to confirm P2P metrics (nonce/QUIC) export
EOF
