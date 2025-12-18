#!/bin/bash
# XAI Explorer Backend Startup Script

set -e

echo "🚀 Starting XAI Blockchain Explorer Backend..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Set environment variables
export DATABASE_URL=${DATABASE_URL:-"postgresql://xai:xai@localhost:5432/xai_explorer"}
export XAI_NODE_URL=${XAI_NODE_URL:-"http://localhost:12001"}
export CORS_ORIGINS=${CORS_ORIGINS:-"http://localhost:12080,http://localhost:5173"}
export HOST=${HOST:-"0.0.0.0"}
export PORT=${PORT:-"8000"}

echo "✅ Configuration:"
echo "   - Node URL: $XAI_NODE_URL"
echo "   - Port: $PORT"
echo "   - CORS: $CORS_ORIGINS"

# Start the server
echo "🌐 Starting FastAPI server..."
echo "   - API: http://localhost:$PORT"
echo "   - Docs: http://localhost:$PORT/docs"
echo ""

uvicorn main:app --host "$HOST" --port "$PORT" --reload
