#!/bin/bash

echo "============================================================"
echo "XAI BLOCKCHAIN - LOCAL TESTNET LAUNCHER"
echo "============================================================"
echo ""
echo "This will start:"
echo "  1. Testnet Node (localhost:5000)"
echo "  2. Block Explorer (localhost:3000)"
echo "  3. Testing Dashboard (localhost:3000/dashboard)"
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
echo "[STEP 2/3] Starting blockchain node on port 5000..."
echo ""
python3 core/node.py &
NODE_PID=$!
sleep 3

# Start explorer in background
echo "[STEP 3/3] Starting block explorer on port 3000..."
echo ""
python3 explorer.py &
EXPLORER_PID=$!
sleep 2

echo ""
echo "============================================================"
echo "XAI BLOCKCHAIN TESTNET RUNNING"
echo "============================================================"
echo ""
echo "Node API:        http://localhost:5000"
echo "Block Explorer:  http://localhost:3000"
echo "Test Dashboard:  http://localhost:3000/dashboard"
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
    xdg-open http://localhost:3000/dashboard
elif command -v open > /dev/null; then
    open http://localhost:3000/dashboard
fi

echo ""
echo "Press Ctrl+C to stop all services..."
echo ""

# Wait for Ctrl+C
trap "echo 'Stopping services...'; kill $NODE_PID $EXPLORER_PID; exit" INT
wait
