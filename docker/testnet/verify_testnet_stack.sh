#!/bin/bash
# XAI Testnet Stack Verification
# Verifies that all services (nodes, explorer, monitoring) are running and healthy

set -e

echo "============================================"
echo "XAI Testnet Stack Verification"
echo "============================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0

# Function to check HTTP endpoint
check_endpoint() {
    local name=$1
    local url=$2
    local timeout=${3:-10}

    if curl -sf -m "$timeout" "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $name: $url"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $name: $url (unreachable)"
        ((FAILED++))
        return 1
    fi
}

# Function to check container health
check_container() {
    local container=$1

    if docker ps --filter "name=$container" --filter "health=healthy" | grep -q "$container"; then
        echo -e "${GREEN}✓${NC} Container: $container (healthy)"
        ((PASSED++))
        return 0
    elif docker ps --filter "name=$container" | grep -q "$container"; then
        echo -e "${YELLOW}⚠${NC} Container: $container (running but not healthy yet)"
        return 1
    else
        echo -e "${RED}✗${NC} Container: $container (not running)"
        ((FAILED++))
        return 1
    fi
}

echo "Checking Container Health..."
echo "----------------------------"
check_container "xai-testnet-bootstrap"
check_container "xai-testnet-node1"
check_container "xai-testnet-node2"
check_container "xai-testnet-node3"
check_container "xai-testnet-postgres"
check_container "xai-testnet-redis"
check_container "xai-testnet-explorer"
check_container "xai-testnet-prometheus"
check_container "xai-testnet-grafana"
echo ""

echo "Checking Node Endpoints..."
echo "----------------------------"
check_endpoint "Bootstrap Node API" "http://localhost:12001/health"
check_endpoint "Node 1 API" "http://localhost:12011/health"
check_endpoint "Node 2 API" "http://localhost:12021/health"
check_endpoint "Node 3 API" "http://localhost:12031/health"
echo ""

echo "Checking Explorer..."
echo "----------------------------"
check_endpoint "Block Explorer" "http://localhost:12080/health"
echo ""

echo "Checking Monitoring..."
echo "----------------------------"
check_endpoint "Prometheus" "http://localhost:12090/-/healthy"
check_endpoint "Grafana" "http://localhost:12091/api/health"
echo ""

echo "Checking Node Metrics..."
echo "----------------------------"
check_endpoint "Bootstrap Metrics" "http://localhost:12070/metrics"
check_endpoint "Node 1 Metrics" "http://localhost:12071/metrics"
check_endpoint "Node 2 Metrics" "http://localhost:12072/metrics"
check_endpoint "Node 3 Metrics" "http://localhost:12073/metrics"
echo ""

echo "Checking Consensus..."
echo "----------------------------"
HEIGHTS=""
HASHES=""
for port in 12001 12011 12021 12031; do
    if DATA=$(curl -sf -m 5 "http://localhost:$port/block/latest?summary=1" 2>/dev/null); then
        HEIGHT=$(echo "$DATA" | jq -r '.block_number // "N/A"')
        HASH=$(echo "$DATA" | jq -r '.hash[0:16] // "N/A"')
        echo "  Node :$port - Height: $HEIGHT, Hash: $HASH"
        HEIGHTS="$HEIGHTS $HEIGHT"
        HASHES="$HASHES $HASH"
    else
        echo -e "${RED}  Node :$port - UNREACHABLE${NC}"
    fi
done

# Check consensus
UNIQUE_HEIGHTS=$(echo "$HEIGHTS" | tr ' ' '\n' | grep -v '^$' | sort -u | wc -l)
UNIQUE_HASHES=$(echo "$HASHES" | tr ' ' '\n' | grep -v '^$' | sort -u | wc -l)

echo ""
if [ "$UNIQUE_HEIGHTS" -eq 1 ] && [ "$UNIQUE_HASHES" -eq 1 ]; then
    echo -e "${GREEN}✓${NC} CONSENSUS: All nodes agree"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} DIVERGED: $UNIQUE_HEIGHTS unique heights, $UNIQUE_HASHES unique hashes"
    ((FAILED++))
fi
echo ""

echo "============================================"
echo "Summary"
echo "============================================"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All checks passed!${NC}"
    echo ""
    echo "Access Points:"
    echo "  Block Explorer: http://localhost:12080"
    echo "  Grafana:        http://localhost:12091 (admin/admin)"
    echo "  Prometheus:     http://localhost:12090"
    echo "  Node API:       http://localhost:12001"
    echo ""
    exit 0
else
    echo -e "${RED}Some checks failed. Review the output above.${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  docker logs xai-testnet-explorer"
    echo "  docker logs xai-testnet-bootstrap"
    echo "  docker compose -f docker-compose.full.yml ps"
    echo ""
    exit 1
fi
