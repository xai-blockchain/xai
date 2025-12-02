#!/usr/bin/env bash
# Spin up a Kind cluster, apply monitoring overlays, and run the verifier with a mock SIEM endpoint.
# Useful when staging/prod clusters are unavailable but we still need to validate manifests and SIEM probes.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
KIND_CONFIG="${ROOT_DIR}/k8s/kind/dev-cluster.yaml"
OVERLAY_APPLY="${ROOT_DIR}/k8s/apply-monitoring-overlays.sh"
OVERLAY_VERIFY="${ROOT_DIR}/k8s/verify-monitoring-overlays.sh"

CLUSTER_NAME="${CLUSTER_NAME:-xai-monitoring-dev}"
NAMESPACE="${NAMESPACE:-xai-blockchain}"
APP_NAMESPACE="${APP_NAMESPACE:-$NAMESPACE}"
KEEP_CLUSTER="${KEEP_CLUSTER:-0}"
PORT_FORWARD_PID=""

log() { echo "[$1] $2"; }
info() { log "INFO" "$1"; }
warn() { log "WARN" "$1"; }
error() { log "ERROR" "$1"; }

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    error "Missing required command: $cmd"
    exit 1
  fi
}

require_cmd kind
require_cmd kubectl
require_cmd docker

if [[ ! -f "$KIND_CONFIG" ]]; then
  error "Kind config not found at $KIND_CONFIG"
  exit 1
fi
if [[ ! -x "$OVERLAY_APPLY" || ! -x "$OVERLAY_VERIFY" ]]; then
  error "Overlay scripts not executable: $OVERLAY_APPLY or $OVERLAY_VERIFY"
  exit 1
fi

CREATED_CLUSTER=0
cleanup() {
  if [[ -n "$PORT_FORWARD_PID" ]]; then
    info "Stopping SIEM port-forward (pid ${PORT_FORWARD_PID})..."
    kill "$PORT_FORWARD_PID" >/dev/null 2>&1 || true
  fi
  if [[ "$KEEP_CLUSTER" == "1" ]]; then
    info "KEEP_CLUSTER=1 set; leaving cluster ${CLUSTER_NAME} running."
    return
  fi
  if [[ $CREATED_CLUSTER -eq 1 ]]; then
    info "Deleting Kind cluster ${CLUSTER_NAME}..."
    kind delete cluster --name "$CLUSTER_NAME" || warn "Kind cluster ${CLUSTER_NAME} delete failed (manual cleanup may be needed)."
  fi
}
trap cleanup EXIT

info "Ensuring Kind cluster ${CLUSTER_NAME} is available..."
if ! kind get clusters | grep -Fxq "$CLUSTER_NAME"; then
  info "Creating Kind cluster ${CLUSTER_NAME}..."
  kind create cluster --name "$CLUSTER_NAME" --config "$KIND_CONFIG"
  CREATED_CLUSTER=1
else
  info "Reusing existing Kind cluster ${CLUSTER_NAME}."
fi

kubectl config use-context "kind-${CLUSTER_NAME}"

info "Creating namespaces ${NAMESPACE} (monitoring) and ${APP_NAMESPACE} (app config)..."
kubectl get namespace "$NAMESPACE" >/dev/null 2>&1 || kubectl create namespace "$NAMESPACE"
kubectl get namespace "$APP_NAMESPACE" >/dev/null 2>&1 || kubectl create namespace "$APP_NAMESPACE"

info "Applying monitoring overlays into ${NAMESPACE}..."
"$OVERLAY_APPLY" "$NAMESPACE"

info "Deploying mock SIEM webhook in ${APP_NAMESPACE}..."
kubectl -n "$APP_NAMESPACE" apply -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: siem-mock
  labels:
    app: siem-mock
spec:
  replicas: 1
  selector:
    matchLabels:
      app: siem-mock
  template:
    metadata:
      labels:
        app: siem-mock
    spec:
      containers:
        - name: echo
          image: hashicorp/http-echo:1.0.0
          args:
            - "-text={\"status\":\"ok\"}"
            - "-listen=:5678"
          ports:
            - containerPort: 5678
EOF

kubectl -n "$APP_NAMESPACE" apply -f - <<'EOF'
apiVersion: v1
kind: Service
metadata:
  name: siem-mock
  labels:
    app: siem-mock
spec:
  selector:
    app: siem-mock
  ports:
    - name: http
      port: 5678
      targetPort: 5678
EOF

info "Waiting for mock SIEM deployment rollout..."
kubectl -n "$APP_NAMESPACE" rollout status deploy/siem-mock --timeout=60s

info "Starting port-forward to mock SIEM service..."
kubectl -n "$APP_NAMESPACE" port-forward svc/siem-mock 5678:5678 >/tmp/xai-kind-siem-port-forward.log 2>&1 &
PORT_FORWARD_PID=$!
for i in {1..10}; do
  if curl -sf -m 1 http://127.0.0.1:5678/ >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
if ! curl -sf -m 1 http://127.0.0.1:5678/ >/dev/null 2>&1; then
  warn "Port-forward to mock SIEM not reachable on 127.0.0.1:5678; SIEM probe may fail."
fi

MOCK_URL="http://127.0.0.1:5678/"
info "Publishing SIEM webhook URL into ${APP_NAMESPACE}/xai-blockchain-config..."
kubectl -n "$APP_NAMESPACE" apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: xai-blockchain-config
data:
  XAI_SECURITY_WEBHOOK_URL: "${MOCK_URL}"
  XAI_SECURITY_WEBHOOK_TOKEN: ""
EOF

info "Running monitoring overlay verifier with SIEM probe..."
"$OVERLAY_VERIFY" --namespace="$NAMESPACE" --app-namespace="$APP_NAMESPACE" --probe-siem

info "Monitoring overlay Kind smoke test completed."
