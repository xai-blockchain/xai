#!/bin/bash
# XAI Blockchain Project Setup Script
# Run after completing: bash ~/blockchain-projects/setup-dependencies.sh

set -e

echo "=== XAI Blockchain Project Setup ==="
echo ""

PROJECT_DIR="$HOME/blockchain-projects/crypto"
cd "$PROJECT_DIR"

# Remove old Windows venvs (they won't work in WSL)
echo "[1/6] Cleaning old virtual environments..."
rm -rf .venv .venv313 .venv_wsl 2>/dev/null || true

# Create fresh Python virtual environment
echo "[2/6] Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "[3/6] Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "[4/6] Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install project dependencies
echo "[5/6] Installing project dependencies..."
pip install -r src/xai/requirements.txt

# Install project in editable mode
echo "[6/6] Installing project in development mode..."
pip install -e ".[dev]" 2>/dev/null || pip install -e .

echo ""
echo "=== XAI Blockchain Setup Complete! ==="
echo ""
echo "Project: XAI - AI-Enhanced Blockchain Platform"
echo "Location: ~/blockchain-projects/crypto"
echo ""
echo "To activate the environment:"
echo "  cd ~/blockchain-projects/crypto"
echo "  source venv/bin/activate"
echo ""
echo "Key Features:"
echo "  ✓ AI Integration (Anthropic & OpenAI)"
echo "  ✓ Flask REST API"
echo "  ✓ PostgreSQL Database"
echo "  ✓ Cryptocurrency & Blockchain Core"
echo "  ✓ Prometheus Monitoring"
echo ""
echo "Environment variables needed:"
echo "  - Check .env.example file"
echo "  - Configure database connection"
echo "  - Add API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY)"
echo ""
