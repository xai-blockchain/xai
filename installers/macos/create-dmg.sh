#!/bin/bash
# Create DMG installer for XAI Blockchain on macOS
# Uses create-dmg tool: https://github.com/create-dmg/create-dmg

set -e

VERSION="0.2.0"
APP_NAME="XAI Blockchain"
DMG_NAME="xai-blockchain-${VERSION}.dmg"
BUILD_DIR="build"
APP_BUNDLE="XAI.app"

echo "=================================="
echo "Building XAI Blockchain DMG"
echo "Version: ${VERSION}"
echo "=================================="

# Check dependencies
if ! command -v create-dmg &> /dev/null; then
    echo "Installing create-dmg..."
    brew install create-dmg
fi

if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required"
    exit 1
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf "${BUILD_DIR}"
rm -f "${DMG_NAME}"
mkdir -p "${BUILD_DIR}"

# Create .app bundle structure
echo "Creating .app bundle..."
APP_PATH="${BUILD_DIR}/${APP_BUNDLE}"
mkdir -p "${APP_PATH}/Contents/MacOS"
mkdir -p "${APP_PATH}/Contents/Resources"
mkdir -p "${APP_PATH}/Contents/Frameworks"

# Create Info.plist
echo "Generating Info.plist..."
cat > "${APP_PATH}/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleExecutable</key>
    <string>xai-launcher</string>
    <key>CFBundleIconFile</key>
    <string>xai.icns</string>
    <key>CFBundleIdentifier</key>
    <string>io.xai-blockchain.xai</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>${VERSION}</string>
    <key>CFBundleVersion</key>
    <string>${VERSION}</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
    <key>CFBundleDocumentTypes</key>
    <array>
        <dict>
            <key>CFBundleTypeName</key>
            <string>XAI Wallet</string>
            <key>CFBundleTypeExtensions</key>
            <array>
                <string>xai</string>
            </array>
            <key>CFBundleTypeRole</key>
            <string>Editor</string>
        </dict>
    </array>
</dict>
</plist>
EOF

# Create launcher script
echo "Creating launcher script..."
cat > "${APP_PATH}/Contents/MacOS/xai-launcher" << 'LAUNCHER'
#!/bin/bash

# XAI Blockchain Launcher for macOS
# This script launches the XAI node from within the .app bundle

# Determine bundle path
BUNDLE_PATH="$(cd "$(dirname "$0")/../.." && pwd)"
CONTENTS_PATH="${BUNDLE_PATH}/Contents"
RESOURCES_PATH="${CONTENTS_PATH}/Resources"
PYTHON_PATH="${RESOURCES_PATH}/python/bin/python3"

# Set environment variables
export XAI_HOME="${RESOURCES_PATH}"
export XAI_DATA_DIR="${HOME}/Library/Application Support/XAI"
export XAI_CONFIG_DIR="${XAI_DATA_DIR}/config"
export XAI_LOG_DIR="${HOME}/Library/Logs/XAI"
export PYTHONPATH="${RESOURCES_PATH}/xai:${PYTHONPATH}"
export PYTHONUNBUFFERED=1

# Create directories
mkdir -p "${XAI_DATA_DIR}/blockchain"
mkdir -p "${XAI_DATA_DIR}/wallets"
mkdir -p "${XAI_DATA_DIR}/state"
mkdir -p "${XAI_LOG_DIR}"
mkdir -p "${XAI_CONFIG_DIR}"

# Check for Python
if [ ! -f "${PYTHON_PATH}" ]; then
    osascript -e 'display dialog "Python runtime not found. Please reinstall XAI Blockchain." buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi

# Launch node in Terminal or background
if [ "$1" == "--terminal" ]; then
    # Open in Terminal
    osascript -e "tell application \"Terminal\" to do script \"${PYTHON_PATH} -m xai.core.node\""
else
    # Run in background and show dialog
    "${PYTHON_PATH}" -m xai.core.node > "${XAI_LOG_DIR}/node.log" 2>&1 &
    NODE_PID=$!
    osascript -e "display notification \"XAI Node started (PID: ${NODE_PID})\" with title \"XAI Blockchain\""
fi
LAUNCHER

chmod +x "${APP_PATH}/Contents/MacOS/xai-launcher"

# Copy Python framework (using system Python or create virtual environment)
echo "Setting up Python environment..."
if [ -d "/Library/Frameworks/Python.framework/Versions/3.12" ]; then
    # Use system Python framework
    cp -R /Library/Frameworks/Python.framework/Versions/3.12 "${APP_PATH}/Contents/Frameworks/Python.framework"
else
    # Create minimal Python environment
    python3 -m venv "${APP_PATH}/Contents/Resources/python"
    source "${APP_PATH}/Contents/Resources/python/bin/activate"
    pip install --upgrade pip
    pip install -e ../../
    deactivate
fi

# Copy XAI package
echo "Copying XAI package..."
cp -R ../../src/xai "${APP_PATH}/Contents/Resources/"

# Copy resources
echo "Copying resources..."
cp xai.icns "${APP_PATH}/Contents/Resources/" 2>/dev/null || echo "Warning: xai.icns not found"
cp ../../LICENSE "${APP_PATH}/Contents/Resources/"
cp ../../README.md "${APP_PATH}/Contents/Resources/"

# Copy configuration
if [ -f "../../src/xai/genesis_testnet.json" ]; then
    mkdir -p "${APP_PATH}/Contents/Resources/config"
    cp ../../src/xai/genesis_testnet.json "${APP_PATH}/Contents/Resources/config/genesis.json"
fi

# Create DMG
echo "Creating DMG..."
create-dmg \
    --volname "${APP_NAME}" \
    --volicon "xai.icns" \
    --window-pos 200 120 \
    --window-size 800 400 \
    --icon-size 100 \
    --icon "${APP_BUNDLE}" 200 190 \
    --hide-extension "${APP_BUNDLE}" \
    --app-drop-link 600 185 \
    --background "dmg-background.png" \
    --hdiutil-quiet \
    "${DMG_NAME}" \
    "${BUILD_DIR}"

# Calculate checksum
echo "Calculating checksum..."
shasum -a 256 "${DMG_NAME}" > "${DMG_NAME}.sha256"

echo ""
echo "=================================="
echo "DMG created successfully!"
echo "File: ${DMG_NAME}"
echo "SHA256: $(cat ${DMG_NAME}.sha256)"
echo "=================================="
echo ""
echo "To install:"
echo "  1. Open ${DMG_NAME}"
echo "  2. Drag XAI.app to Applications"
echo "  3. Launch from Applications or Launchpad"
echo ""
