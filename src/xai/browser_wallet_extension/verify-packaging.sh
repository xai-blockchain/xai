#!/bin/bash
# Verification script for XAI Browser Wallet packaging
# Run this before submitting to stores

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "═══════════════════════════════════════════════════════════════"
echo "   XAI BROWSER WALLET - PRE-SUBMISSION VERIFICATION"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS=0
WARN=0
FAIL=0

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    PASS=$((PASS + 1))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    WARN=$((WARN + 1))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    FAIL=$((FAIL + 1))
}

echo "Checking build system..."
echo "─────────────────────────────────────────────────────────────"

if [ -f "build.sh" ] && [ -x "build.sh" ]; then
    check_pass "build.sh exists and is executable"
else
    check_fail "build.sh missing or not executable"
fi

if [ -f "package-chrome.sh" ] && [ -x "package-chrome.sh" ]; then
    check_pass "package-chrome.sh exists and is executable"
else
    check_fail "package-chrome.sh missing or not executable"
fi

if [ -f "package-firefox.sh" ] && [ -x "package-firefox.sh" ]; then
    check_pass "package-firefox.sh exists and is executable"
else
    check_fail "package-firefox.sh missing or not executable"
fi

echo ""
echo "Checking extension files..."
echo "─────────────────────────────────────────────────────────────"

if [ -f "manifest.json" ]; then
    check_pass "manifest.json exists"

    # Validate JSON
    if python3 -c "import json; json.load(open('manifest.json'))" 2>/dev/null; then
        check_pass "manifest.json is valid JSON"
    else
        check_fail "manifest.json has invalid JSON syntax"
    fi

    # Check manifest version
    VERSION=$(grep '"manifest_version"' manifest.json | grep -o '[0-9]')
    if [ "$VERSION" = "3" ]; then
        check_pass "Manifest V3 (latest standard)"
    else
        check_fail "Not using Manifest V3"
    fi
else
    check_fail "manifest.json missing"
fi

for file in background.js popup.html popup.js icons/icon16.png icons/icon48.png icons/icon128.png; do
    if [ -f "$file" ]; then
        check_pass "$file exists"
    else
        check_fail "$file missing"
    fi
done

echo ""
echo "Checking packages..."
echo "─────────────────────────────────────────────────────────────"

if [ -f "xai-wallet-chrome-v0.2.0.zip" ]; then
    check_pass "Chrome package exists"
    SIZE=$(du -h "xai-wallet-chrome-v0.2.0.zip" | cut -f1)
    echo "   Size: $SIZE"
else
    check_warn "Chrome package not generated (run ./package-chrome.sh)"
fi

if [ -f "xai-wallet-firefox-v0.2.0.zip" ]; then
    check_pass "Firefox package exists"
    SIZE=$(du -h "xai-wallet-firefox-v0.2.0.zip" | cut -f1)
    echo "   Size: $SIZE"
else
    check_warn "Firefox package not generated (run ./package-firefox.sh)"
fi

echo ""
echo "Checking documentation..."
echo "─────────────────────────────────────────────────────────────"

for doc in README_PACKAGING.md PUBLISHING.md PACKAGING_QUICKSTART.md SECURITY_REVIEW.md; do
    if [ -f "$doc" ]; then
        check_pass "$doc exists"
    else
        check_fail "$doc missing"
    fi
done

echo ""
echo "Checking store assets..."
echo "─────────────────────────────────────────────────────────────"

for asset in store/CHROME_STORE_LISTING.md store/FIREFOX_LISTING.md store/privacy-policy.md store/ICON_REQUIREMENTS.md; do
    if [ -f "$asset" ]; then
        check_pass "$asset exists"
    else
        check_fail "$asset missing"
    fi
done

echo ""
echo "Security checks..."
echo "─────────────────────────────────────────────────────────────"

# Check for dangerous patterns
if grep -r "eval(" *.js 2>/dev/null | grep -v "evaluation" > /dev/null; then
    check_fail "Found eval() usage in JavaScript files"
else
    check_pass "No eval() usage detected"
fi

if grep -r "Function(" *.js 2>/dev/null > /dev/null; then
    check_fail "Found Function() constructor usage"
else
    check_pass "No Function() constructor usage"
fi

if grep -q "content_security_policy" manifest.json; then
    check_pass "Content Security Policy defined"
else
    check_warn "No Content Security Policy found"
fi

echo ""
echo "Permissions audit..."
echo "─────────────────────────────────────────────────────────────"

if grep -q '"storage"' manifest.json; then
    check_pass "storage permission declared"
fi

if grep -q '"alarms"' manifest.json; then
    check_pass "alarms permission declared"
fi

if grep -q '"usb"' manifest.json; then
    check_pass "usb permission declared (hardware wallet)"
fi

if grep -q '"hid"' manifest.json && grep -q "optional_permissions" manifest.json; then
    check_pass "hid is optional permission (good practice)"
fi

# Check for overly broad permissions
if grep -q '"<all_urls>"' manifest.json; then
    check_fail "Uses <all_urls> permission (too broad)"
fi

if grep -q '"tabs"' manifest.json; then
    check_warn "Uses 'tabs' permission (review if needed)"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "   VERIFICATION SUMMARY"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo -e "${GREEN}Passed: $PASS${NC}"
echo -e "${YELLOW}Warnings: $WARN${NC}"
echo -e "${RED}Failed: $FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    if [ $WARN -eq 0 ]; then
        echo -e "${GREEN}✓ READY FOR SUBMISSION${NC}"
        echo ""
        echo "Next steps:"
        echo "  1. Host privacy policy publicly"
        echo "  2. Capture screenshots (1280x800)"
        echo "  3. Create developer accounts"
        echo "  4. Upload packages to stores"
        echo ""
        echo "See PUBLISHING.md for detailed instructions"
    else
        echo -e "${YELLOW}⚠ READY WITH WARNINGS${NC}"
        echo ""
        echo "Review warnings above before submission"
    fi
else
    echo -e "${RED}✗ NOT READY - FIX FAILURES${NC}"
    echo ""
    echo "Fix the failures above before proceeding"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"

exit $FAIL
