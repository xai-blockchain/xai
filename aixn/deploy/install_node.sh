#!/bin/bash
# XAI Blockchain Node Installation Script
# INTERNAL USE ONLY - DELETE BEFORE PUBLIC RELEASE
# For Linux/Mac

set -e

echo "============================================================"
echo "XAI BLOCKCHAIN NODE INSTALLER"
echo "============================================================"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "Error: Do not run as root"
    exit 1
fi

# Check Python version
echo "[1/7] Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Python version: $PYTHON_VERSION"

if [[ $(echo "$PYTHON_VERSION < 3.8" | bc) -eq 1 ]]; then
    echo "Error: Python 3.8 or higher required"
    exit 1
fi

# Create installation directory
echo ""
echo "[2/7] Creating installation directory..."
INSTALL_DIR="$HOME/xai-blockchain"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Download/copy blockchain files
echo ""
echo "[3/7] Installing XAI blockchain..."
# In production, this would download from release
# For now, assume files are in current directory
if [ -f "../core/node.py" ]; then
    cp -r ../* .
    echo "Files copied from source"
else
    echo "Error: Blockchain files not found"
    exit 1
fi

# Create virtual environment
echo ""
echo "[4/7] Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo ""
echo "[5/7] Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create data directories
echo ""
echo "[6/7] Creating data directories..."
mkdir -p data logs gamification_data mining_data recovery_data exchange_data governance_data crypto_deposits burning_data

# Generate configuration
echo ""
echo "[7/7] Generating configuration..."
cat > config.env << EOF
# XAI Node Configuration
XAI_HOST=0.0.0.0
XAI_PORT=5000
XAI_NETWORK=mainnet
EOF

echo ""
echo "============================================================"
echo "INSTALLATION COMPLETE"
echo "============================================================"
echo ""
echo "Installation directory: $INSTALL_DIR"
echo ""
echo "To start the node:"
echo "  cd $INSTALL_DIR"
echo "  source venv/bin/activate"
echo "  python core/node.py"
echo ""
echo "To install as system service:"
echo "  sudo ./deploy/install_service.sh"
echo ""
echo "============================================================"
