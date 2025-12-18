#!/bin/bash

echo "============================================================"
echo "XAI BLOCKCHAIN - LOCAL TESTNET LAUNCHER (Development Mode)"
echo "============================================================"
echo ""
echo "This script is for local development testing only."
echo "For production testnet deployment, use Docker Compose:"
echo "  cd docker/testnet"
echo "  docker compose -f docker-compose.three-node.yml up -d"
echo ""
echo "This will start:"
echo "  1. Testnet Node (localhost:12001)"
echo "  2. Block Explorer (localhost:12080)"
echo "  3. Testing Dashboard (localhost:12080/dashboard)"
echo ""
echo "Note: For production deployment, use Docker Compose which"
echo "provides a complete multi-node testnet with monitoring:"
echo "  - Node API: http://localhost:12001"
echo "  - Explorer: http://localhost:12080"
echo "  - Grafana (monitoring): http://localhost:12030"
echo "  - Prometheus (metrics): http://localhost:12090"
echo ""
echo "To verify Docker testnet after startup:"
echo "  curl http://localhost:12001/health         # Node health"
echo "  curl http://localhost:12080/health         # Explorer health"
echo ""
echo "Press Ctrl+C to stop services"
echo "============================================================"
echo ""

# Check if genesis block exists
if [ ! -f "genesis_testnet.json" ]; then
    echo "[STEP 1/3] Generating testnet genesis block..."
    echo ""
    python3 generate_premine.py
    echo ""
    echo "Genesis block created!"
    echo ""
    read -p "Press Enter to continue..."
else
    echo "[INFO] Genesis block already exists"
    echo ""
fi

# Start node in background
echo "[STEP 2/3] Starting blockchain node on port 12001..."
echo ""
export XAI_RPC_PORT=12001
export XAI_P2P_PORT=12002
export XAI_WS_PORT=12003
python3 core/node.py &
NODE_PID=$!
sleep 3

# Start explorer in background
echo "[STEP 3/3] Starting block explorer on port 12080..."
echo ""
export XAI_EXPLORER_PORT=12080
python3 explorer.py &
EXPLORER_PID=$!
sleep 2

echo ""
echo "============================================================"
echo "XAI BLOCKCHAIN TESTNET RUNNING"
echo "============================================================"
echo ""
echo "Node API:        http://localhost:12001"
echo "Block Explorer:  http://localhost:12080"
echo "Test Dashboard:  http://localhost:12080/dashboard"
echo ""
echo "Node PID:        $NODE_PID"
echo "Explorer PID:    $EXPLORER_PID"
echo ""
echo "============================================================"
echo ""
echo "Opening dashboard in browser..."
sleep 2

# Try to open browser
if command -v xdg-open > /dev/null; then
    xdg-open http://localhost:12080/dashboard
elif command -v open > /dev/null; then
    open http://localhost:12080/dashboard
fi

echo ""
echo "Press Ctrl+C to stop all services..."
echo ""

# Wait for Ctrl+C
trap "echo 'Stopping services...'; kill $NODE_PID $EXPLORER_PID; exit" INT
wait
