#!/bin/bash
# Package XAI Browser Wallet for Firefox Add-ons (AMO)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Packaging for Firefox Add-ons (AMO) ==="

# Check if build exists
if [ ! -d "build" ]; then
    echo "Build directory not found. Running build.sh first..."
    bash build.sh
fi

# Create Firefox-specific build
FIREFOX_BUILD="build-firefox"
rm -rf "$FIREFOX_BUILD"
cp -r build "$FIREFOX_BUILD"

# Get version from manifest
VERSION=$(grep '"version"' "$FIREFOX_BUILD/manifest.json" | cut -d'"' -f4)
OUTPUT_FILE="xai-wallet-firefox-v${VERSION}.zip"

# Firefox-specific manifest adjustments
echo "Applying Firefox-specific adjustments..."

# Add Firefox-specific manifest keys if needed
# Note: Firefox supports Manifest V3, but may need browser_specific_settings
cat > "$FIREFOX_BUILD/manifest_additions.json" << 'EOF'
{
  "browser_specific_settings": {
    "gecko": {
      "id": "{xai-wallet@example.com}",
      "strict_min_version": "109.0"
    }
  }
}
EOF

# Merge manifest additions using Python
python3 << 'PYEOF'
import json

with open('build-firefox/manifest.json', 'r') as f:
    manifest = json.load(f)

with open('build-firefox/manifest_additions.json', 'r') as f:
    additions = json.load(f)

manifest.update(additions)

with open('build-firefox/manifest.json', 'w') as f:
    json.dump(manifest, f, indent=2)
PYEOF

rm "$FIREFOX_BUILD/manifest_additions.json"

# Remove old package if exists
rm -f "$OUTPUT_FILE"

echo "Creating Firefox package: $OUTPUT_FILE"

# Create ZIP for Firefox Add-ons
cd "$FIREFOX_BUILD"
zip -r "../$OUTPUT_FILE" . -x "*.DS_Store" -x "__MACOSX/*"
cd ..

# Cleanup Firefox build directory
rm -rf "$FIREFOX_BUILD"

# Display package info
echo ""
echo "Firefox package created successfully!"
echo "File: $OUTPUT_FILE"
echo "Size: $(du -h "$OUTPUT_FILE" | cut -f1)"
echo ""
echo "Next steps:"
echo "1. Go to https://addons.mozilla.org/developers/"
echo "2. Upload $OUTPUT_FILE"
echo "3. See store/FIREFOX_LISTING.md for AMO listing details"
echo ""
echo "Review checklist:"
echo "  [ ] Manifest version correct"
echo "  [ ] browser_specific_settings configured"
echo "  [ ] Permissions minimal and justified"
echo "  [ ] CSP properly configured"
echo "  [ ] No remote code loading"
echo "  [ ] Privacy policy included"
echo ""
echo "Note: You may need to submit source code if using build tools"
