#!/usr/bin/env bash
#
# XAI Network Chaos Testing Script
#
# Simulates various network conditions using Toxiproxy to test
# blockchain consensus under adverse network conditions.
#
# Usage:
#   ./scripts/network-chaos.sh <command> [options]
#
# Commands:
#   add-latency <proxy> <latency>     Add latency (e.g., 200ms)
#   add-jitter <proxy> <jitter>       Add jitter/variable latency (e.g., 50ms)
#   add-packet-loss <proxy> <percent> Add packet loss (e.g., 5 for 5%)
#   add-bandwidth <proxy> <rate>      Limit bandwidth (bytes/sec)
#   add-timeout <proxy> <timeout>     Add connection timeout
#   add-slow-close <proxy> <delay>    Slow close connections
#   reset <proxy>                     Remove all toxics from proxy
#   reset-all                         Remove all toxics from all proxies
#   list                              List all proxies and their toxics
#   status                            Show testnet consensus status
#   scenario <name>                   Run a predefined scenario
#
# Scenarios:
#   wan           - Simulate WAN link (150ms latency, 20ms jitter)
#   satellite     - Satellite link (600ms latency, 100ms jitter)
#   mobile-3g     - Mobile 3G (300ms, 10% loss)
#   partition     - Network partition (100% loss on one node)
#   degraded      - Degraded network (all nodes: 100ms, 2% loss)
#   flash-crowd   - Simulate flash crowd (bandwidth limit)
#
# Prerequisites:
#   - Toxiproxy running (docker-compose -f docker-compose.chaos.yml up -d)
#   - curl, jq installed
#

set -euo pipefail

TOXIPROXY_API="${TOXIPROXY_API:-http://localhost:12800}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Check if toxiproxy is running
check_toxiproxy() {
    if ! curl -s "${TOXIPROXY_API}/version" > /dev/null 2>&1; then
        log_error "Toxiproxy not running at ${TOXIPROXY_API}"
        log_error "Start it with: docker-compose -f docker/testnet/docker-compose.chaos.yml up -d"
        exit 1
    fi
}

# List all proxies
list_proxies() {
    check_toxiproxy
    echo "=== Proxies ==="
    curl -s "${TOXIPROXY_API}/proxies" | jq -r 'to_entries[] | "\(.key): \(.value.listen) -> \(.value.upstream) [enabled: \(.value.enabled)]"'
    echo
    echo "=== Toxics ==="
    for proxy in $(curl -s "${TOXIPROXY_API}/proxies" | jq -r 'keys[]'); do
        toxics=$(curl -s "${TOXIPROXY_API}/proxies/${proxy}/toxics")
        if [ "$(echo "$toxics" | jq 'length')" -gt 0 ]; then
            echo "${proxy}:"
            echo "$toxics" | jq -r '.[] | "  - \(.name) (\(.type)): \(.attributes)"'
        fi
    done
}

# Add latency toxic
add_latency() {
    local proxy=$1
    local latency=$2
    check_toxiproxy

    # Parse latency (remove 'ms' suffix if present)
    latency_ms=$(echo "$latency" | sed 's/ms$//')

    log_info "Adding ${latency_ms}ms latency to ${proxy}"
    curl -s -X POST "${TOXIPROXY_API}/proxies/${proxy}/toxics" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"latency_downstream\", \"type\": \"latency\", \"stream\": \"downstream\", \"attributes\": {\"latency\": ${latency_ms}}}" | jq
}

# Add jitter toxic (variable latency)
add_jitter() {
    local proxy=$1
    local jitter=$2
    check_toxiproxy

    jitter_ms=$(echo "$jitter" | sed 's/ms$//')

    log_info "Adding ${jitter_ms}ms jitter to ${proxy}"
    curl -s -X POST "${TOXIPROXY_API}/proxies/${proxy}/toxics" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"jitter\", \"type\": \"latency\", \"stream\": \"downstream\", \"attributes\": {\"latency\": 0, \"jitter\": ${jitter_ms}}}" | jq
}

# Add packet loss
add_packet_loss() {
    local proxy=$1
    local percent=$2
    check_toxiproxy

    # Toxicity is 0.0-1.0, convert from percentage (ensure leading zero)
    toxicity=$(printf "%.2f" "$(echo "scale=2; $percent / 100" | bc)")

    log_info "Adding ${percent}% packet loss to ${proxy}"
    curl -s -X POST "${TOXIPROXY_API}/proxies/${proxy}/toxics" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"packet_loss\", \"type\": \"limit_data\", \"stream\": \"downstream\", \"toxicity\": ${toxicity}, \"attributes\": {\"bytes\": 0}}" | jq
}

# Add bandwidth limit
add_bandwidth() {
    local proxy=$1
    local rate=$2
    check_toxiproxy

    log_info "Adding ${rate} bytes/sec bandwidth limit to ${proxy}"
    curl -s -X POST "${TOXIPROXY_API}/proxies/${proxy}/toxics" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"bandwidth\", \"type\": \"bandwidth\", \"stream\": \"downstream\", \"attributes\": {\"rate\": ${rate}}}" | jq
}

# Add timeout
add_timeout() {
    local proxy=$1
    local timeout=$2
    check_toxiproxy

    timeout_ms=$(echo "$timeout" | sed 's/ms$//')

    log_info "Adding ${timeout_ms}ms timeout to ${proxy}"
    curl -s -X POST "${TOXIPROXY_API}/proxies/${proxy}/toxics" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"timeout\", \"type\": \"timeout\", \"stream\": \"downstream\", \"attributes\": {\"timeout\": ${timeout_ms}}}" | jq
}

# Add slow close
add_slow_close() {
    local proxy=$1
    local delay=$2
    check_toxiproxy

    delay_ms=$(echo "$delay" | sed 's/ms$//')

    log_info "Adding ${delay_ms}ms slow close to ${proxy}"
    curl -s -X POST "${TOXIPROXY_API}/proxies/${proxy}/toxics" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"slow_close\", \"type\": \"slow_close\", \"stream\": \"downstream\", \"attributes\": {\"delay\": ${delay_ms}}}" | jq
}

# Reset all toxics from a proxy
reset_proxy() {
    local proxy=$1
    check_toxiproxy

    log_info "Removing all toxics from ${proxy}"
    toxics=$(curl -s "${TOXIPROXY_API}/proxies/${proxy}/toxics" | jq -r '.[].name')
    for toxic in $toxics; do
        curl -s -X DELETE "${TOXIPROXY_API}/proxies/${proxy}/toxics/${toxic}" > /dev/null
        log_info "  Removed ${toxic}"
    done
}

# Reset all toxics from all proxies
reset_all() {
    check_toxiproxy
    log_info "Removing all toxics from all proxies"

    for proxy in $(curl -s "${TOXIPROXY_API}/proxies" | jq -r 'keys[]'); do
        reset_proxy "$proxy"
    done
}

# Get consensus status from nodes
status() {
    echo "=== XAI Testnet Consensus Status ==="

    for port in 12001 12011 12021 12031; do
        node_name="node-${port}"
        if response=$(curl -s --max-time 5 "http://localhost:${port}/health" 2>/dev/null); then
            height=$(echo "$response" | jq -r '.blockchain.height // "unknown"')
            status=$(echo "$response" | jq -r '.status // "unknown"')
            echo "${node_name} (port ${port}): height=${height}, status=${status}"
        else
            echo "${node_name} (port ${port}): UNREACHABLE"
        fi
    done
}

# Run predefined scenarios
run_scenario() {
    local scenario=$1
    check_toxiproxy

    case $scenario in
        wan)
            log_info "Running WAN scenario (150ms latency, 20ms jitter)"
            for proxy in xai-node1-p2p xai-node2-p2p xai-node3-p2p; do
                add_latency "$proxy" 150
                add_jitter "$proxy" 20
            done
            ;;
        satellite)
            log_info "Running satellite scenario (600ms latency, 100ms jitter)"
            for proxy in xai-node1-p2p xai-node2-p2p xai-node3-p2p; do
                add_latency "$proxy" 600
                add_jitter "$proxy" 100
            done
            ;;
        mobile-3g)
            log_info "Running mobile 3G scenario (300ms latency, 10% packet loss)"
            for proxy in xai-node1-p2p xai-node2-p2p xai-node3-p2p; do
                add_latency "$proxy" 300
                add_packet_loss "$proxy" 10
            done
            ;;
        partition)
            log_info "Running partition scenario (isolating node1)"
            add_packet_loss "xai-node1-p2p" 100
            add_packet_loss "xai-node1-rpc" 100
            ;;
        degraded)
            log_info "Running degraded network scenario (100ms latency, 2% loss on all nodes)"
            for proxy in xai-bootstrap-p2p xai-node1-p2p xai-node2-p2p xai-node3-p2p; do
                add_latency "$proxy" 100
                add_packet_loss "$proxy" 2
            done
            ;;
        flash-crowd)
            log_info "Running flash crowd scenario (bandwidth limit: 10KB/s)"
            for proxy in xai-bootstrap-rpc xai-node1-rpc xai-node2-rpc xai-node3-rpc; do
                add_bandwidth "$proxy" 10240
            done
            ;;
        *)
            log_error "Unknown scenario: $scenario"
            echo "Available scenarios: wan, satellite, mobile-3g, partition, degraded, flash-crowd"
            exit 1
            ;;
    esac

    log_info "Scenario applied. Run './scripts/network-chaos.sh status' to check impact."
    log_info "Run './scripts/network-chaos.sh reset-all' to remove all toxics."
}

# Main
case "${1:-help}" in
    add-latency)
        add_latency "$2" "$3"
        ;;
    add-jitter)
        add_jitter "$2" "$3"
        ;;
    add-packet-loss)
        add_packet_loss "$2" "$3"
        ;;
    add-bandwidth)
        add_bandwidth "$2" "$3"
        ;;
    add-timeout)
        add_timeout "$2" "$3"
        ;;
    add-slow-close)
        add_slow_close "$2" "$3"
        ;;
    reset)
        reset_proxy "$2"
        ;;
    reset-all)
        reset_all
        ;;
    list)
        list_proxies
        ;;
    status)
        status
        ;;
    scenario)
        run_scenario "$2"
        ;;
    help|--help|-h)
        echo "XAI Network Chaos Testing Script"
        echo ""
        echo "Usage: $0 <command> [options]"
        echo ""
        echo "Commands:"
        echo "  add-latency <proxy> <latency>     Add latency (e.g., 200ms)"
        echo "  add-jitter <proxy> <jitter>       Add jitter (e.g., 50ms)"
        echo "  add-packet-loss <proxy> <percent> Add packet loss (e.g., 5)"
        echo "  add-bandwidth <proxy> <rate>      Limit bandwidth (bytes/sec)"
        echo "  add-timeout <proxy> <timeout>     Add connection timeout"
        echo "  add-slow-close <proxy> <delay>    Slow close connections"
        echo "  reset <proxy>                     Remove all toxics from proxy"
        echo "  reset-all                         Remove all toxics"
        echo "  list                              List proxies and toxics"
        echo "  status                            Show testnet consensus status"
        echo "  scenario <name>                   Run predefined scenario"
        echo ""
        echo "Scenarios: wan, satellite, mobile-3g, partition, degraded, flash-crowd"
        echo ""
        echo "Example:"
        echo "  $0 scenario wan          # Apply WAN-like conditions"
        echo "  $0 status                # Check consensus"
        echo "  $0 reset-all             # Clean up"
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Run '$0 help' for usage"
        exit 1
        ;;
esac
