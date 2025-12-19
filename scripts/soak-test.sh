#!/bin/bash
# XAI 24-Hour Soak Test
# Logs metrics every 5 minutes for 24 hours

DURATION_HOURS=24
INTERVAL_SECONDS=300
LOG_DIR="/home/hudson/blockchain-projects/xai/soak-test-results"
LOG_FILE="$LOG_DIR/soak-$(date +%Y%m%d-%H%M%S).log"
SUMMARY_FILE="$LOG_DIR/summary.txt"

export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

mkdir -p "$LOG_DIR"

echo "=== XAI Soak Test Started ===" | tee "$LOG_FILE"
echo "Duration: ${DURATION_HOURS}h" | tee -a "$LOG_FILE"
echo "Start: $(date)" | tee -a "$LOG_FILE"
echo "Log: $LOG_FILE" | tee -a "$LOG_FILE"
echo "==============================" | tee -a "$LOG_FILE"

START_TIME=$(date +%s)
END_TIME=$((START_TIME + DURATION_HOURS * 3600))
ITERATION=0

while [ $(date +%s) -lt $END_TIME ]; do
    ITERATION=$((ITERATION + 1))
    ELAPSED_HOURS=$(( ($(date +%s) - START_TIME) / 3600 ))

    echo "" >> "$LOG_FILE"
    echo "=== Iteration $ITERATION (Hour $ELAPSED_HOURS) - $(date) ===" >> "$LOG_FILE"

    # Get metrics from each node
    for pod in xai-node-0 xai-node-1; do
        echo "--- $pod ---" >> "$LOG_FILE"

        # Health check with timeout
        HEALTH=$(kubectl exec $pod -n xai -- curl -s --max-time 10 http://localhost:8080/health 2>/dev/null)

        if [ -n "$HEALTH" ]; then
            HEIGHT=$(echo "$HEALTH" | jq -r '.blockchain.height // "N/A"')
            STATUS=$(echo "$HEALTH" | jq -r '.status // "N/A"')
            PEERS=$(echo "$HEALTH" | jq -r '.network.peers // "N/A"')
            PENDING=$(echo "$HEALTH" | jq -r '.backlog.pending_transactions // "N/A"')

            echo "  Height: $HEIGHT | Status: $STATUS | Peers: $PEERS | Pending: $PENDING" >> "$LOG_FILE"
        else
            echo "  ERROR: Health check failed" >> "$LOG_FILE"
        fi

        # Pod resource usage
        RESOURCES=$(kubectl top pod $pod -n xai --no-headers 2>/dev/null)
        if [ -n "$RESOURCES" ]; then
            echo "  Resources: $RESOURCES" >> "$LOG_FILE"
        fi
    done

    # Node-level metrics
    echo "--- Cluster ---" >> "$LOG_FILE"
    kubectl top nodes --no-headers 2>/dev/null >> "$LOG_FILE"

    # Check for restarts
    RESTARTS=$(kubectl get pods -n xai -l app=xai-node -o jsonpath='{range .items[*]}{.metadata.name}: {.status.containerStatuses[0].restartCount}{"\n"}{end}' 2>/dev/null)
    echo "Restarts: $RESTARTS" >> "$LOG_FILE"

    # Sleep until next iteration
    sleep $INTERVAL_SECONDS
done

echo "" >> "$LOG_FILE"
echo "=== Soak Test Complete ===" >> "$LOG_FILE"
echo "End: $(date)" >> "$LOG_FILE"
echo "Total iterations: $ITERATION" >> "$LOG_FILE"

# Generate summary
echo "=== SOAK TEST SUMMARY ===" > "$SUMMARY_FILE"
echo "Duration: ${DURATION_HOURS}h" >> "$SUMMARY_FILE"
echo "Start: $(head -4 "$LOG_FILE" | grep Start)" >> "$SUMMARY_FILE"
echo "End: $(date)" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"
echo "Final Status:" >> "$SUMMARY_FILE"
kubectl get pods -n xai -l app=xai-node -o wide >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"
echo "Restart Count:" >> "$SUMMARY_FILE"
kubectl get pods -n xai -l app=xai-node -o jsonpath='{range .items[*]}{.metadata.name}: {.status.containerStatuses[0].restartCount} restarts{"\n"}{end}' >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"
echo "Check full log: $LOG_FILE" >> "$SUMMARY_FILE"

echo "Summary written to: $SUMMARY_FILE"
