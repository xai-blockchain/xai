#!/bin/bash
# Blockchain Finality Verification for XAI

NAMESPACE="xai"
KUBECONFIG="/etc/rancher/k3s/k3s.yaml"
KUBECTL="sudo kubectl --kubeconfig=$KUBECONFIG"

echo "=== XAI Finality Verification ==="

# Check block production rate
echo "[1] Checking block production..."
for pod in $($KUBECTL get pods -n $NAMESPACE -l app=xai-validator -o name | head -1); do
    echo "Querying $pod for latest block..."

    # Simulate RPC query (adjust for actual XAI node RPC)
    $KUBECTL exec -n $NAMESPACE $pod -- sh -c 'echo "Block height check - use: curl localhost:26657/status"' || true
done

# Check for finality delays
echo ""
echo "[2] Checking for finality delays..."
$KUBECTL logs -n $NAMESPACE -l app=xai-validator --tail=500 | grep -i "finality.*delay\|slow.*commit\|timeout.*commit" || echo "No finality delays detected"

# Check consensus participation
echo ""
echo "[3] Checking consensus participation..."
for pod in $($KUBECTL get pods -n $NAMESPACE -l app=xai-validator -o name); do
    echo "$pod consensus activity:"
    $KUBECTL logs -n $NAMESPACE $pod --tail=100 | grep -i "commit\|prevote\|precommit\|round" | tail -5 || echo "  No consensus messages found"
done

# Monitor block confirmations
echo ""
echo "[4] Block confirmation monitoring..."
echo "For production finality verification:"
echo "  - Query RPC: curl http://validator:26657/status | jq '.result.sync_info'"
echo "  - Check: latest_block_height vs latest_block_time"
echo "  - Finality threshold: Typically 2/3+ validators commit"
echo ""
echo "Prometheus metrics (if enabled):"
echo "  - tendermint_consensus_height"
echo "  - tendermint_consensus_validators"
echo "  - tendermint_consensus_missing_validators"

echo ""
echo "=== Finality Health Indicators ==="
echo "Good: Blocks produced every 1-3s, no timeout_commits"
echo "Warning: Blocks >5s apart, occasional timeouts"
echo "Critical: No new blocks >30s, persistent timeouts"
