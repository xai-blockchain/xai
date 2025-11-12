#!/bin/bash

echo "============================================"
echo "AIXN P2P Exchange - Frontend Quick Start"
echo "============================================"
echo ""
echo "Starting local web server on port 8080..."
echo ""
echo "Open your browser and navigate to:"
echo "http://localhost:8080"
echo ""
echo "To test the connection first, go to:"
echo "http://localhost:8080/test.html"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
echo "============================================"
echo ""

# Try Python 3 first, then Python 2
if command -v python3 &> /dev/null; then
    python3 -m http.server 8080
elif command -v python &> /dev/null; then
    python -m http.server 8080
else
    echo "ERROR: Python not found!"
    echo ""
    echo "Please install Python or open index.html directly in your browser."
    echo ""
    exit 1
fi
