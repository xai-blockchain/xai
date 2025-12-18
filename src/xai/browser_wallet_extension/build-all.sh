#!/bin/bash
# Build and package XAI Browser Wallet for all platforms
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "═══════════════════════════════════════════════════════════════"
echo "   XAI BROWSER WALLET - BUILD ALL PLATFORMS"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Step 1: Build
echo "Step 1/4: Building extension..."
echo "───────────────────────────────────────────────────────────────"
bash build.sh
echo ""

# Step 2: Package for Chrome
echo "Step 2/4: Packaging for Chrome Web Store..."
echo "───────────────────────────────────────────────────────────────"
bash package-chrome.sh
echo ""

# Step 3: Package for Firefox
echo "Step 3/4: Packaging for Firefox Add-ons..."
echo "───────────────────────────────────────────────────────────────"
bash package-firefox.sh
echo ""

# Step 4: Verify
echo "Step 4/4: Running verification..."
echo "───────────────────────────────────────────────────────────────"
bash verify-packaging.sh
VERIFY_RESULT=$?
echo ""

# Summary
echo "═══════════════════════════════════════════════════════════════"
echo "   BUILD SUMMARY"
echo "═══════════════════════════════════════════════════════════════"
echo ""

if [ $VERIFY_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ BUILD SUCCESSFUL${NC}"
    echo ""
    echo "Packages created:"
    ls -lh xai-wallet-*.zip 2>/dev/null || echo "  No packages found!"
    echo ""
    echo "Next steps:"
    echo "  1. Read store/CHROME_SUBMISSION_GUIDE.md"
    echo "  2. Read store/FIREFOX_SUBMISSION_GUIDE.md"
    echo "  3. Capture screenshots (see store/SCREENSHOT_GUIDE.md)"
    echo "  4. Host privacy policy publicly"
    echo "  5. Submit to stores!"
else
    echo -e "${YELLOW}⚠ BUILD COMPLETED WITH WARNINGS${NC}"
    echo ""
    echo "Review warnings above and fix if necessary."
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
