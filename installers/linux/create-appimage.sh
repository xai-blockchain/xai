#!/bin/bash
# Create AppImage for XAI Blockchain
# Portable Linux application format that runs on most distributions

set -e

VERSION="0.2.0"
APPIMAGE_NAME="XAI_Blockchain-${VERSION}-x86_64.AppImage"
BUILD_DIR="AppDir"

echo "=================================="
echo "Building XAI Blockchain AppImage"
echo "Version: ${VERSION}"
echo "=================================="

# Check dependencies
if ! command -v appimage-builder &> /dev/null; then
    echo "Installing appimage-builder..."
    sudo pip3 install appimage-builder
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf "${BUILD_DIR}"
rm -f *.AppImage

# Create AppDir structure
echo "Creating AppDir structure..."
mkdir -p "${BUILD_DIR}/usr/bin"
mkdir -p "${BUILD_DIR}/usr/lib"
mkdir -p "${BUILD_DIR}/usr/share/applications"
mkdir -p "${BUILD_DIR}/usr/share/icons/hicolor/256x256/apps"
mkdir -p "${BUILD_DIR}/usr/share/metainfo"

# Build XAI package
echo "Building XAI package..."
cd ../..
python3 -m build
cd installers/linux

# Install to AppDir
echo "Installing XAI to AppDir..."
python3 -m venv "${BUILD_DIR}/usr/venv"
source "${BUILD_DIR}/usr/venv/bin/activate"
pip install --upgrade pip
pip install ../../dist/xai_blockchain-${VERSION}.tar.gz
deactivate

# Create wrapper script
echo "Creating wrapper script..."
cat > "${BUILD_DIR}/AppRun" << 'EOF'
#!/bin/bash

# XAI Blockchain AppRun launcher
# This script is executed when the AppImage is run

APPDIR="$(dirname "$(readlink -f "$0")")"

export PYTHONHOME="${APPDIR}/usr/venv"
export PYTHONPATH="${APPDIR}/usr/venv/lib/python3.10/site-packages"
export PATH="${APPDIR}/usr/venv/bin:${PATH}"
export LD_LIBRARY_PATH="${APPDIR}/usr/lib:${LD_LIBRARY_PATH}"

# Set XAI environment
export XAI_DATA_DIR="${HOME}/.xai"
export XAI_CONFIG_DIR="${XAI_DATA_DIR}/config"
export XAI_LOG_DIR="${XAI_DATA_DIR}/logs"
export PYTHONUNBUFFERED=1

# Create directories
mkdir -p "${XAI_DATA_DIR}/blockchain"
mkdir -p "${XAI_DATA_DIR}/wallets"
mkdir -p "${XAI_DATA_DIR}/state"
mkdir -p "${XAI_LOG_DIR}"
mkdir -p "${XAI_CONFIG_DIR}"

# Determine which command to run
BASENAME="$(basename "$0")"

case "$BASENAME" in
    xai-node*)
        exec "${APPDIR}/usr/venv/bin/python3" -m xai.core.node "$@"
        ;;
    xai-wallet*)
        exec "${APPDIR}/usr/venv/bin/python3" -m xai.wallet.cli "$@"
        ;;
    xai-cli*|xai*)
        exec "${APPDIR}/usr/venv/bin/python3" -m xai.cli.main "$@"
        ;;
    *)
        # Default: run node
        exec "${APPDIR}/usr/venv/bin/python3" -m xai.core.node "$@"
        ;;
esac
EOF

chmod +x "${BUILD_DIR}/AppRun"

# Create desktop entry
echo "Creating desktop entry..."
cat > "${BUILD_DIR}/usr/share/applications/xai-blockchain.desktop" << EOF
[Desktop Entry]
Type=Application
Name=XAI Blockchain
GenericName=Blockchain Node
Comment=AI-Enhanced Blockchain Platform
Exec=xai-node
Icon=xai
Categories=Network;P2P;Utility;
Terminal=false
StartupNotify=true
Keywords=blockchain;cryptocurrency;node;wallet;
EOF

# Create AppStream metadata
cat > "${BUILD_DIR}/usr/share/metainfo/io.xai-blockchain.xai.appdata.xml" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
    <id>io.xai-blockchain.xai</id>
    <metadata_license>Apache-2.0</metadata_license>
    <project_license>Apache-2.0</project_license>
    <name>XAI Blockchain</name>
    <summary>Proof-of-work blockchain implementation</summary>
    <description>
        <p>
            XAI is a Python-based proof-of-work blockchain implementation with a UTXO
            transaction model, REST API, and wallet CLI.
        </p>
    </description>
    <launchable type="desktop-id">xai-blockchain.desktop</launchable>
    <provides>
        <binary>xai-node</binary>
        <binary>xai-wallet</binary>
        <binary>xai</binary>
    </provides>
    <releases>
        <release version="${VERSION}" date="2024-12-18">
            <description>
                <p>Initial AppImage release</p>
            </description>
        </release>
    </releases>
</component>
EOF

# Copy icon (or create placeholder)
if [ -f "xai.png" ]; then
    cp xai.png "${BUILD_DIR}/usr/share/icons/hicolor/256x256/apps/xai.png"
    ln -sf usr/share/icons/hicolor/256x256/apps/xai.png "${BUILD_DIR}/xai.png"
else
    echo "Warning: xai.png not found, creating placeholder"
    # Create a simple placeholder icon
    convert -size 256x256 xc:blue -pointsize 72 -fill white -gravity center \
        -annotate +0+0 'XAI' "${BUILD_DIR}/xai.png" 2>/dev/null || \
        touch "${BUILD_DIR}/xai.png"
fi

# Build AppImage using appimage-builder
if [ -f "AppImageBuilder.yml" ]; then
    echo "Building with appimage-builder..."
    appimage-builder --recipe AppImageBuilder.yml --skip-test
else
    # Alternative: Use appimagetool
    echo "Building with appimagetool..."

    # Download appimagetool if not present
    if [ ! -f "appimagetool-x86_64.AppImage" ]; then
        wget -q https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
        chmod +x appimagetool-x86_64.AppImage
    fi

    # Build AppImage
    ARCH=x86_64 ./appimagetool-x86_64.AppImage "${BUILD_DIR}" "${APPIMAGE_NAME}"
fi

# Verify AppImage was created
if [ ! -f "${APPIMAGE_NAME}" ]; then
    echo "ERROR: AppImage was not created"
    exit 1
fi

# Make executable
chmod +x "${APPIMAGE_NAME}"

# Calculate checksum
echo "Calculating checksum..."
sha256sum "${APPIMAGE_NAME}" > "${APPIMAGE_NAME}.sha256"

# Test AppImage
echo "Testing AppImage..."
./"${APPIMAGE_NAME}" --version || echo "Warning: Version test failed"

echo ""
echo "=================================="
echo "AppImage created successfully!"
echo "File: ${APPIMAGE_NAME}"
echo "Size: $(du -h ${APPIMAGE_NAME} | cut -f1)"
echo "SHA256: $(cat ${APPIMAGE_NAME}.sha256)"
echo "=================================="
echo ""
echo "To run:"
echo "  ./${APPIMAGE_NAME}"
echo ""
echo "To install (optional):"
echo "  mkdir -p ~/.local/bin"
echo "  cp ${APPIMAGE_NAME} ~/.local/bin/xai-blockchain"
echo "  chmod +x ~/.local/bin/xai-blockchain"
echo ""
