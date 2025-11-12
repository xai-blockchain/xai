#!/bin/bash
# XAI Blockchain - Pre-Release Cleanup Script
# DELETES ALL DOCUMENTATION AND INTERNAL FILES

set -e

echo "============================================================"
echo "XAI BLOCKCHAIN - PRE-RELEASE CLEANUP"
echo "============================================================"
echo ""
echo "This script will DELETE all documentation and internal files."
echo "The blockchain will be ready for public release."
echo ""
echo "⚠️  WARNING: This action CANNOT be undone!"
echo ""
read -p "Are you sure you want to continue? (type YES): " confirm

if [ "$confirm" != "YES" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo "Starting cleanup..."
echo ""

# Delete all markdown documentation
echo "[1/7] Deleting markdown documentation..."
find . -name "*.md" -type f -delete
echo "  ✓ All .md files deleted"

# Delete deployment directory
echo "[2/7] Deleting deployment scripts..."
rm -rf deploy/
echo "  ✓ deploy/ directory deleted"

# Delete test files
echo "[3/7] Deleting test files..."
find . -name "*test*.py" -type f -delete
find . -name "test_*" -type d -exec rm -rf {} + 2>/dev/null || true
echo "  ✓ Test files deleted"

# Delete example/template files
echo "[4/7] Deleting templates and examples..."
find . -name "*.template.*" -type f -delete
find . -name "*example*" -type f -delete
echo "  ✓ Templates deleted"

# Delete internal scripts
echo "[5/7] Deleting internal scripts..."
rm -f START_TESTNET.sh START_TESTNET.bat
rm -f explorer.py
rm -rf templates/  # Web UI for testing
echo "  ✓ Internal scripts deleted"

# Delete technical summary
echo "[6/7] Deleting technical documentation..."
rm -f TECHNICAL_SUMMARY.md
rm -f README.md 2>/dev/null || true
echo "  ✓ Technical docs deleted"

# Clean up comments in core files
echo "[7/7] Removing verbose comments from core files..."
# This would require sed/awk to strip out detailed comments
# For now, just notify
echo "  ⚠️  Manual step: Review core/*.py files and remove verbose comments"

echo ""
echo "============================================================"
echo "CLEANUP COMPLETE"
echo "============================================================"
echo ""
echo "Deleted:"
echo "  - All .md files"
echo "  - deploy/ directory"
echo "  - Test files"
echo "  - Templates"
echo "  - Internal scripts"
echo "  - Web UI"
echo ""
echo "Remaining:"
echo "  - core/ (blockchain implementation)"
echo "  - config.py"
echo "  - generate_premine.py"
echo "  - requirements.txt"
echo "  - Dockerfile (optional: delete if not needed)"
echo "  - docker-compose.yml (optional: delete if not needed)"
echo ""
echo "Manual steps still required:"
echo "  1. Review core/*.py files for verbose comments"
echo "  2. Remove any internal-only features"
echo "  3. Generate mainnet genesis block"
echo "  4. Test thoroughly"
echo ""
echo "⚠️  The blockchain is now in minimal state."
echo "⚠️  Community will need to discover features on their own."
echo ""
echo "============================================================"
