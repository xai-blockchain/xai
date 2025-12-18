#!/bin/bash
# Validator Key Rotation Script for K8s

set -e

NAMESPACE="xai"
KUBECONFIG="/etc/rancher/k3s/k3s.yaml"
KUBECTL="sudo kubectl --kubeconfig=$KUBECONFIG"

echo "=== XAI Validator Key Rotation ==="

# Step 1: Create rotated keys secret
echo "[1/5] Creating rotated keys secret..."
$KUBECTL apply -f /home/hudson/blockchain-projects/xai/k8s/validator-keys-rotated.yaml

# Step 2: Get current StatefulSet
echo "[2/5] Backing up current StatefulSet..."
$KUBECTL get statefulset xai-validator -n $NAMESPACE -o yaml > /tmp/xai-validator-backup.yaml

# Step 3: Patch StatefulSet to use new secret
echo "[3/5] Updating StatefulSet to use rotated keys..."
$KUBECTL patch statefulset xai-validator -n $NAMESPACE --type json -p '[
  {
    "op": "add",
    "path": "/spec/template/spec/volumes/-",
    "value": {
      "name": "validator-keys",
      "secret": {
        "secretName": "validator-keys-rotated"
      }
    }
  },
  {
    "op": "add",
    "path": "/spec/template/spec/containers/0/volumeMounts/-",
    "value": {
      "name": "validator-keys",
      "mountPath": "/keys",
      "readOnly": true
    }
  }
]' || echo "Note: May already be configured for secret volumes"

# Step 4: Rolling restart
echo "[4/5] Performing rolling restart..."
$KUBECTL rollout restart statefulset/xai-validator -n $NAMESPACE

# Step 5: Wait for rollout
echo "[5/5] Waiting for rollout to complete..."
$KUBECTL rollout status statefulset/xai-validator -n $NAMESPACE --timeout=5m

echo ""
echo "=== Verification ==="
$KUBECTL get pods -n $NAMESPACE -l app=xai-validator
echo ""
echo "Key rotation complete. Verify keys in use:"
echo "  $KUBECTL exec -n $NAMESPACE xai-validator-0 -- ls -la /keys"
