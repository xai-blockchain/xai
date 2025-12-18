#!/usr/bin/env bash
#
# Verify CLI entry points are properly installed and functional.
#
# Usage:
#   ./scripts/verify_cli_entry_points.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "========================================="
echo "XAI CLI Entry Points Verification"
echo "========================================="
echo

# Check if we're in a venv
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "WARNING: Not in a virtual environment"
    echo "It's recommended to run this in a virtualenv"
    echo
fi

# Check if package is installed
echo "1. Checking package installation..."
if python -c "import xai" 2>/dev/null; then
    echo "✓ xai package is importable"
else
    echo "✗ xai package not found"
    echo "  Run: pip install -e $PROJECT_ROOT"
    exit 1
fi
echo

# Check entry points exist
echo "2. Checking entry point scripts..."
for cmd in xai xai-wallet xai-node; do
    if command -v "$cmd" &>/dev/null; then
        echo "✓ $cmd command found at: $(command -v $cmd)"
    else
        echo "✗ $cmd command not found"
        echo "  Run: pip install -e $PROJECT_ROOT"
        exit 1
    fi
done
echo

# Test each command's help
echo "3. Testing command help outputs..."
echo

echo "--- xai --help ---"
if xai --help &>/dev/null; then
    echo "✓ xai --help works"
    xai --help | head -5
else
    echo "✗ xai --help failed"
    exit 1
fi
echo

echo "--- xai-wallet --help ---"
if xai-wallet --help &>/dev/null; then
    echo "✓ xai-wallet --help works"
    xai-wallet --help | head -5
else
    echo "✗ xai-wallet --help failed"
    exit 1
fi
echo

echo "--- xai-node --help ---"
if xai-node --help 2>&1 | grep -q "XAI Blockchain Node"; then
    echo "✓ xai-node --help works"
    xai-node --help 2>&1 | grep -A 3 "XAI Blockchain Node"
else
    echo "✗ xai-node --help failed"
    exit 1
fi
echo

# Check pyproject.toml has correct entry points
echo "4. Verifying pyproject.toml configuration..."
if grep -q 'xai = "xai.cli.main:main"' "$PROJECT_ROOT/pyproject.toml"; then
    echo "✓ xai entry point configured"
else
    echo "✗ xai entry point not found in pyproject.toml"
    exit 1
fi

if grep -q 'xai-wallet = "xai.wallet.cli:main"' "$PROJECT_ROOT/pyproject.toml"; then
    echo "✓ xai-wallet entry point configured"
else
    echo "✗ xai-wallet entry point not found in pyproject.toml"
    exit 1
fi

if grep -q 'xai-node = "xai.core.node:main"' "$PROJECT_ROOT/pyproject.toml"; then
    echo "✓ xai-node entry point configured"
else
    echo "✗ xai-node entry point not found in pyproject.toml"
    exit 1
fi
echo

# Test Python module execution as fallback
echo "5. Testing Python module execution (fallback mode)..."
if python -m xai.cli.main --help &>/dev/null; then
    echo "✓ python -m xai.cli.main works"
else
    echo "✗ python -m xai.cli.main failed"
fi

if python -m xai.wallet.cli --help &>/dev/null; then
    echo "✓ python -m xai.wallet.cli works"
else
    echo "✗ python -m xai.wallet.cli failed"
fi

if python -m xai.core.node --help &>/dev/null; then
    echo "✓ python -m xai.core.node works"
else
    echo "✗ python -m xai.core.node failed"
fi
echo

echo "========================================="
echo "All checks passed!"
echo "========================================="
echo
echo "Available commands:"
echo "  xai         - Main CLI with blockchain, wallet, AI, mining"
echo "  xai-wallet  - Legacy wallet CLI"
echo "  xai-node    - Node management"
echo
echo "For detailed usage, see: docs/CLI_USAGE.md"
