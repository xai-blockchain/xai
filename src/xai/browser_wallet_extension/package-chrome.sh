#!/bin/bash
# Package XAI Browser Wallet for Chrome Web Store
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Packaging for Chrome Web Store ==="

# Check if build exists
if [ ! -d "build" ]; then
    echo "Build directory not found. Running build.sh first..."
    bash build.sh
fi

# Get version from manifest
VERSION=$(grep '"version"' build/manifest.json | cut -d'"' -f4)
OUTPUT_FILE="xai-wallet-chrome-v${VERSION}.zip"

# Remove old package if exists
rm -f "$OUTPUT_FILE"

echo "Creating Chrome package: $OUTPUT_FILE"

# Create ZIP for Chrome Web Store
cd build
zip -r "../$OUTPUT_FILE" . -x "*.DS_Store" -x "__MACOSX/*"
cd ..

# Display package info
echo ""
echo "Chrome package created successfully!"
echo "File: $OUTPUT_FILE"
echo "Size: $(du -h "$OUTPUT_FILE" | cut -f1)"
echo ""
echo "Next steps:"
echo "1. Go to https://chrome.google.com/webstore/devconsole"
echo "2. Upload $OUTPUT_FILE"
echo "3. See store/CHROME_STORE_LISTING.md for store listing details"
echo ""
echo "Review checklist:"
echo "  [ ] Manifest version correct"
echo "  [ ] Permissions minimal and justified"
echo "  [ ] CSP properly configured"
echo "  [ ] No remote code loading"
echo "  [ ] Privacy policy included"
