#!/bin/bash
# Build XAI Browser Wallet Extension for Production
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Building XAI Browser Wallet Extension ==="

# Create build directory
BUILD_DIR="$SCRIPT_DIR/build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

echo "Copying extension files..."

# Core files
cp manifest.json "$BUILD_DIR/"
cp background.js "$BUILD_DIR/"
cp *.html "$BUILD_DIR/" 2>/dev/null || true
cp *.js "$BUILD_DIR/" 2>/dev/null || true
cp *.css "$BUILD_DIR/" 2>/dev/null || true

# Icons
mkdir -p "$BUILD_DIR/icons"
cp icons/*.png "$BUILD_DIR/icons/"

# Remove development/documentation files from build
cd "$BUILD_DIR"
rm -f *_SUMMARY.md *_IMPLEMENTATION*.md *_NOTES.md *_README.md *_INTEGRATION.md *_QUICK_START.md
rm -f __init__.py

# Remove example/demo files not needed in production
rm -f hw-demo.html ledger-hw-example.html trezor-hw-example.js

echo ""
echo "Build complete!"
echo "Output: $BUILD_DIR"
echo ""
echo "Files included:"
ls -lh "$BUILD_DIR"
echo ""
echo "Icons:"
ls -lh "$BUILD_DIR/icons"
echo ""
echo "Ready for packaging with package-chrome.sh or package-firefox.sh"
