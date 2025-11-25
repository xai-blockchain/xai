#!/bin/bash
# XAI Blockchain Node Monitoring Script
# INTERNAL USE ONLY - DELETE BEFORE PUBLIC RELEASE
# Monitor node health and alert on issues

NODE_URL="http://localhost:5000"
ALERT_EMAIL=""  # Set email for alerts
CHECK_INTERVAL=60  # seconds

echo "XAI Node Monitor Starting..."
echo "Monitoring: $NODE_URL"
echo "Check interval: ${CHECK_INTERVAL}s"
echo ""

send_alert() {
    local message=$1
    echo "[ALERT] $message"
    # Add email notification here if configured
    # echo "$message" | mail -s "XAI Node Alert" "$ALERT_EMAIL"
}

check_node() {
    # Check if node is responding
    if ! curl -s -f "$NODE_URL/stats" > /dev/null 2>&1; then
        send_alert "Node is not responding at $NODE_URL"
        return 1
    fi

    # Get stats
    stats=$(curl -s "$NODE_URL/stats")

    # Parse stats
    blocks=$(echo "$stats" | python3 -c "import sys, json; print(json.load(sys.stdin).get('blocks', 0))")
    peers=$(echo "$stats" | python3 -c "import sys, json; print(json.load(sys.stdin).get('peers', 0))")
    pending=$(echo "$stats" | python3 -c "import sys, json; print(json.load(sys.stdin).get('pending_transactions', 0))")

    # Check for issues
    if [ "$peers" -lt 1 ]; then
        send_alert "Node has no peers connected"
    fi

    if [ "$pending" -gt 1000 ]; then
        send_alert "High pending transaction count: $pending"
    fi

    # Log status
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] OK - Blocks: $blocks, Peers: $peers, Pending: $pending"
    return 0
}

# Monitor loop
while true; do
    check_node
    sleep "$CHECK_INTERVAL"
done
