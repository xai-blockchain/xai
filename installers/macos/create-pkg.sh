#!/bin/bash
# Create PKG installer for XAI Blockchain on macOS
# System-wide installation using macOS native package format

set -e

VERSION="0.2.0"
IDENTIFIER="io.xai-blockchain.xai"
PKG_NAME="xai-blockchain-${VERSION}.pkg"
BUILD_DIR="build-pkg"
INSTALL_ROOT="${BUILD_DIR}/root"
SCRIPTS_DIR="${BUILD_DIR}/scripts"

echo "=================================="
echo "Building XAI Blockchain PKG"
echo "Version: ${VERSION}"
echo "=================================="

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf "${BUILD_DIR}"
rm -f "${PKG_NAME}"
mkdir -p "${INSTALL_ROOT}"
mkdir -p "${SCRIPTS_DIR}"

# Create directory structure
echo "Creating directory structure..."
mkdir -p "${INSTALL_ROOT}/usr/local/bin"
mkdir -p "${INSTALL_ROOT}/usr/local/lib/xai"
mkdir -p "${INSTALL_ROOT}/Library/LaunchDaemons"
mkdir -p "${INSTALL_ROOT}/var/lib/xai"
mkdir -p "${INSTALL_ROOT}/var/log/xai"
mkdir -p "${INSTALL_ROOT}/etc/xai"

# Build XAI package
echo "Building XAI package..."
cd ../..
python3 -m build
cd installers/macos

# Install to staging area
echo "Installing to staging area..."
python3 -m venv "${INSTALL_ROOT}/usr/local/lib/xai/venv"
source "${INSTALL_ROOT}/usr/local/lib/xai/venv/bin/activate"
pip install --upgrade pip
pip install ../../dist/xai_blockchain-${VERSION}.tar.gz
deactivate

# Create wrapper scripts
echo "Creating wrapper scripts..."

cat > "${INSTALL_ROOT}/usr/local/bin/xai" << 'EOF'
#!/bin/bash
export XAI_DATA_DIR="/var/lib/xai"
export XAI_CONFIG_DIR="/etc/xai"
export XAI_LOG_DIR="/var/log/xai"
exec /usr/local/lib/xai/venv/bin/xai "$@"
EOF

cat > "${INSTALL_ROOT}/usr/local/bin/xai-node" << 'EOF'
#!/bin/bash
export XAI_DATA_DIR="/var/lib/xai"
export XAI_CONFIG_DIR="/etc/xai"
export XAI_LOG_DIR="/var/log/xai"
exec /usr/local/lib/xai/venv/bin/xai-node "$@"
EOF

cat > "${INSTALL_ROOT}/usr/local/bin/xai-wallet" << 'EOF'
#!/bin/bash
export XAI_DATA_DIR="/var/lib/xai"
export XAI_CONFIG_DIR="/etc/xai"
export XAI_WALLETS_DIR="/var/lib/xai/wallets"
exec /usr/local/lib/xai/venv/bin/xai-wallet "$@"
EOF

chmod +x "${INSTALL_ROOT}/usr/local/bin/xai"
chmod +x "${INSTALL_ROOT}/usr/local/bin/xai-node"
chmod +x "${INSTALL_ROOT}/usr/local/bin/xai-wallet"

# Create LaunchDaemon
echo "Creating LaunchDaemon..."
cat > "${INSTALL_ROOT}/Library/LaunchDaemons/${IDENTIFIER}.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${IDENTIFIER}</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/xai-node</string>
        <string>--network</string>
        <string>testnet</string>
    </array>

    <key>RunAtLoad</key>
    <false/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>

    <key>StandardOutPath</key>
    <string>/var/log/xai/node.log</string>

    <key>StandardErrorPath</key>
    <string>/var/log/xai/error.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>XAI_DATA_DIR</key>
        <string>/var/lib/xai</string>
        <key>XAI_CONFIG_DIR</key>
        <string>/etc/xai</string>
        <key>XAI_LOG_DIR</key>
        <string>/var/log/xai</string>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
    </dict>

    <key>WorkingDirectory</key>
    <string>/var/lib/xai</string>

    <key>ThrottleInterval</key>
    <integer>60</integer>
</dict>
</plist>
EOF

chmod 644 "${INSTALL_ROOT}/Library/LaunchDaemons/${IDENTIFIER}.plist"

# Copy configuration
echo "Copying configuration..."
if [ -f "../../src/xai/genesis_testnet.json" ]; then
    cp "../../src/xai/genesis_testnet.json" "${INSTALL_ROOT}/etc/xai/genesis.json"
fi

# Create default configuration
cat > "${INSTALL_ROOT}/etc/xai/node.yaml" << EOF
# XAI Node Configuration

network:
  name: testnet
  port: 18545
  rpc_port: 18546

data:
  dir: /var/lib/xai/blockchain
  wallets_dir: /var/lib/xai/wallets
  state_dir: /var/lib/xai/state

logging:
  level: INFO
  dir: /var/log/xai

node:
  enable_mining: false
  max_peers: 50
  checkpoint_sync: true
EOF

# Create postinstall script
echo "Creating installation scripts..."
cat > "${SCRIPTS_DIR}/postinstall" << 'POSTINSTALL'
#!/bin/bash

# Create data directories
mkdir -p /var/lib/xai/blockchain
mkdir -p /var/lib/xai/wallets
mkdir -p /var/lib/xai/state
mkdir -p /var/log/xai

# Set permissions
chmod 755 /var/lib/xai
chmod 755 /var/log/xai
chmod 644 /etc/xai/*.json 2>/dev/null || true
chmod 644 /etc/xai/*.yaml 2>/dev/null || true

# Load LaunchDaemon (but don't start)
echo "XAI Blockchain installed successfully!"
echo ""
echo "To start the node service:"
echo "  sudo launchctl load /Library/LaunchDaemons/io.xai-blockchain.xai.plist"
echo ""
echo "To start manually:"
echo "  xai-node --network testnet"
echo ""
echo "Configuration: /etc/xai/node.yaml"
echo "Data directory: /var/lib/xai"
echo "Logs: /var/log/xai"
echo ""

exit 0
POSTINSTALL

chmod +x "${SCRIPTS_DIR}/postinstall"

# Create preinstall script
cat > "${SCRIPTS_DIR}/preinstall" << 'PREINSTALL'
#!/bin/bash

# Stop service if running
if launchctl list | grep -q "io.xai-blockchain.xai"; then
    launchctl unload /Library/LaunchDaemons/io.xai-blockchain.xai.plist 2>/dev/null || true
fi

exit 0
PREINSTALL

chmod +x "${SCRIPTS_DIR}/preinstall"

# Build component package
echo "Building component package..."
pkgbuild \
    --root "${INSTALL_ROOT}" \
    --scripts "${SCRIPTS_DIR}" \
    --identifier "${IDENTIFIER}" \
    --version "${VERSION}" \
    --install-location "/" \
    "${BUILD_DIR}/xai-component.pkg"

# Create distribution XML
echo "Creating distribution configuration..."
cat > "${BUILD_DIR}/distribution.xml" << EOF
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="1">
    <title>XAI Blockchain ${VERSION}</title>
    <organization>io.xai-blockchain</organization>
    <domains enable_localSystem="true"/>
    <options customize="never" require-scripts="false" hostArchitectures="x86_64,arm64"/>

    <welcome file="welcome.html" mime-type="text/html"/>
    <license file="../../LICENSE"/>
    <readme file="readme.html" mime-type="text/html"/>

    <pkg-ref id="${IDENTIFIER}"/>

    <options customize="never" require-scripts="true"/>

    <choices-outline>
        <line choice="default">
            <line choice="${IDENTIFIER}"/>
        </line>
    </choices-outline>

    <choice id="default"/>

    <choice id="${IDENTIFIER}" visible="false">
        <pkg-ref id="${IDENTIFIER}"/>
    </choice>

    <pkg-ref id="${IDENTIFIER}" version="${VERSION}" onConclusion="none">
        xai-component.pkg
    </pkg-ref>
</installer-gui-script>
EOF

# Create welcome HTML
cat > "${BUILD_DIR}/welcome.html" << 'HTML'
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: -apple-system, sans-serif; padding: 20px; }
        h1 { color: #007AFF; }
    </style>
</head>
<body>
    <h1>Welcome to XAI Blockchain</h1>
    <p>This installer will install XAI Blockchain on your system.</p>
    <p><strong>Features:</strong></p>
    <ul>
        <li>Proof-of-Work blockchain with SHA-256</li>
        <li>Smart contract support</li>
        <li>Atomic swap capabilities</li>
        <li>AI-powered governance</li>
        <li>Comprehensive wallet management</li>
    </ul>
    <p>Installation will place files in:</p>
    <ul>
        <li><code>/usr/local/bin/</code> - Executables</li>
        <li><code>/usr/local/lib/xai/</code> - Application files</li>
        <li><code>/var/lib/xai/</code> - Blockchain data</li>
        <li><code>/etc/xai/</code> - Configuration</li>
    </ul>
</body>
</html>
HTML

# Create readme HTML
cat > "${BUILD_DIR}/readme.html" << 'HTML'
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: -apple-system, sans-serif; padding: 20px; }
        h2 { color: #007AFF; }
        code { background: #f0f0f0; padding: 2px 6px; border-radius: 3px; }
    </style>
</head>
<body>
    <h2>Getting Started</h2>
    <p>After installation, you can start using XAI Blockchain:</p>

    <h3>Start the Node</h3>
    <pre><code>sudo launchctl load /Library/LaunchDaemons/io.xai-blockchain.xai.plist</code></pre>

    <h3>Or run manually:</h3>
    <pre><code>xai-node --network testnet</code></pre>

    <h3>Use the Wallet</h3>
    <pre><code>xai-wallet create my-wallet</code></pre>

    <h3>Check Status</h3>
    <pre><code>xai --version</code></pre>

    <h3>View Logs</h3>
    <pre><code>tail -f /var/log/xai/node.log</code></pre>

    <h2>Configuration</h2>
    <p>Edit <code>/etc/xai/node.yaml</code> to customize settings.</p>

    <h2>Uninstallation</h2>
    <p>To uninstall:</p>
    <pre><code>sudo launchctl unload /Library/LaunchDaemons/io.xai-blockchain.xai.plist
sudo rm -rf /usr/local/lib/xai /var/lib/xai /etc/xai
sudo rm /usr/local/bin/xai*
sudo rm /Library/LaunchDaemons/io.xai-blockchain.xai.plist</code></pre>

    <h2>Support</h2>
    <p>For help, visit <a href="https://xai-blockchain.io">xai-blockchain.io</a></p>
</body>
</html>
HTML

# Build product archive
echo "Building product archive..."
productbuild \
    --distribution "${BUILD_DIR}/distribution.xml" \
    --package-path "${BUILD_DIR}" \
    --resources "${BUILD_DIR}" \
    "${PKG_NAME}"

# Calculate checksum
echo "Calculating checksum..."
shasum -a 256 "${PKG_NAME}" > "${PKG_NAME}.sha256"

# Get package info
echo "Getting package info..."
pkgutil --pkg-info-plist "${IDENTIFIER}" 2>/dev/null || echo "Package not yet installed"

echo ""
echo "=================================="
echo "PKG created successfully!"
echo "File: ${PKG_NAME}"
echo "SHA256: $(cat ${PKG_NAME}.sha256)"
echo "=================================="
echo ""
echo "To install:"
echo "  sudo installer -pkg ${PKG_NAME} -target /"
echo ""
echo "Or double-click ${PKG_NAME} to use GUI installer"
echo ""
