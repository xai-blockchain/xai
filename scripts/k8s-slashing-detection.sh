#!/bin/bash
# Slashing Behavior Detection for XAI Validators

NAMESPACE="xai"
KUBECONFIG="/etc/rancher/k3s/k3s.yaml"
KUBECTL="sudo kubectl --kubeconfig=$KUBECONFIG"

echo "=== XAI Slashing Detection ==="

# Check for double-signing indicators
echo "[1] Checking for double-signing patterns..."
$KUBECTL logs -n $NAMESPACE -l app=xai-validator --tail=1000 | grep -i "double.*sign\|duplicate.*vote\|conflicting.*block" || echo "No double-signing detected"

# Check for downtime/missed blocks
echo ""
echo "[2] Checking validator uptime..."
for pod in $($KUBECTL get pods -n $NAMESPACE -l app=xai-validator -o name); do
    echo "Pod: $pod"
    RESTARTS=$($KUBECTL get $pod -n $NAMESPACE -o jsonpath='{.status.containerStatuses[0].restartCount}')
    READY=$($KUBECTL get $pod -n $NAMESPACE -o jsonpath='{.status.containerStatuses[0].ready}')
    echo "  Restarts: $RESTARTS"
    echo "  Ready: $READY"

    # Check recent logs for missed blocks
    $KUBECTL logs -n $NAMESPACE $pod --tail=100 | grep -i "missed.*block\|timeout.*proposal\|validator.*offline" || echo "  No missed blocks detected"
done

# Check for byzantine behavior
echo ""
echo "[3] Checking for byzantine behavior..."
$KUBECTL logs -n $NAMESPACE -l app=xai-validator --tail=1000 | grep -i "byzantine\|malicious\|invalid.*signature\|equivocation" || echo "No byzantine behavior detected"

# Network partition detection
echo ""
echo "[4] Checking for network partitions..."
$KUBECTL logs -n $NAMESPACE -l app=xai-validator --tail=500 | grep -i "partition\|split.*brain\|isolated\|peer.*disconnect" || echo "No partition detected"

echo ""
echo "=== Slashable Conditions ==="
echo "Monitor for these patterns that trigger slashing:"
echo "  - Double signing: Signing two different blocks at same height"
echo "  - Downtime: Missing >500 consecutive blocks (configurable)"
echo "  - Byzantine behavior: Invalid signatures, malformed proposals"
echo ""
echo "To simulate (DANGEROUS - testnet only):"
echo "  - Double-sign: Run same validator with same key on 2 pods"
echo "  - Downtime: kubectl scale statefulset xai-validator --replicas=0"
