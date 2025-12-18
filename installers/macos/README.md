# macOS Installer for XAI Blockchain

This directory contains configuration files for distributing XAI Blockchain on macOS.

## Overview

Three distribution methods are provided:

1. **Homebrew Formula** (`xai.rb`) - Recommended for most users
2. **DMG Installer** (`create-dmg.sh`) - Standalone .app bundle
3. **PKG Installer** (`create-pkg.sh`) - System-wide installation

## Prerequisites

- macOS 11.0 (Big Sur) or later
- Python 3.10+
- Homebrew (for Homebrew installation)
- Xcode Command Line Tools: `xcode-select --install`

## Method 1: Homebrew Installation (Recommended)

### Setting Up a Homebrew Tap

```bash
# Create a tap repository
mkdir -p homebrew-tap/Formula
cp xai.rb homebrew-tap/Formula/

# Create tap repository on GitHub
cd homebrew-tap
git init
git add .
git commit -m "Initial commit: XAI Blockchain formula"
git remote add origin https://github.com/xai-blockchain/homebrew-tap.git
git push -u origin main
```

### Installing via Homebrew

```bash
# Add tap
brew tap xai-blockchain/tap

# Install XAI
brew install xai

# Start service
brew services start xai

# Check status
brew services list | grep xai
```

### Updating the Formula

```bash
# Update SHA256 checksums
# 1. Build and upload package to PyPI or GitHub
# 2. Calculate SHA256
shasum -a 256 xai-blockchain-0.2.0.tar.gz

# 3. Update xai.rb with correct SHA256
# 4. Test locally
brew install --build-from-source ./xai.rb

# 5. Audit formula
brew audit --strict --online xai

# 6. Test formula
brew test xai

# 7. Push to tap repository
git add Formula/xai.rb
git commit -m "Update to version 0.2.0"
git push
```

## Method 2: DMG Installer

### Building the DMG

```bash
# Install create-dmg
brew install create-dmg

# Create icon file (requires iconutil)
# If you have a PNG logo:
mkdir xai.iconset
sips -z 16 16     logo.png --out xai.iconset/icon_16x16.png
sips -z 32 32     logo.png --out xai.iconset/icon_16x16@2x.png
sips -z 32 32     logo.png --out xai.iconset/icon_32x32.png
sips -z 64 64     logo.png --out xai.iconset/icon_32x32@2x.png
sips -z 128 128   logo.png --out xai.iconset/icon_128x128.png
sips -z 256 256   logo.png --out xai.iconset/icon_128x128@2x.png
sips -z 256 256   logo.png --out xai.iconset/icon_256x256.png
sips -z 512 512   logo.png --out xai.iconset/icon_256x256@2x.png
sips -z 512 512   logo.png --out xai.iconset/icon_512x512.png
sips -z 1024 1024 logo.png --out xai.iconset/icon_512x512@2x.png
iconutil -c icns xai.iconset -o xai.icns

# Build DMG
./create-dmg.sh

# Output: xai-blockchain-0.2.0.dmg
```

### DMG Contents

The DMG installer creates a complete .app bundle with:

- **XAI.app** - Drag-and-drop application
- Embedded Python runtime
- All dependencies bundled
- Launch scripts for node and wallet
- Default configuration files

### Installation

1. Open `xai-blockchain-0.2.0.dmg`
2. Drag **XAI.app** to Applications folder
3. Launch from Applications or Launchpad
4. First launch may require right-click -> Open (Gatekeeper)

### Data Locations

- **Application**: `/Applications/XAI.app`
- **Data**: `~/Library/Application Support/XAI/`
- **Logs**: `~/Library/Logs/XAI/`
- **Config**: `~/Library/Application Support/XAI/config/`
- **Wallets**: `~/Library/Application Support/XAI/wallets/`

## Method 3: PKG Installer

### Building a PKG

```bash
# Run the PKG creation script
./create-pkg.sh

# Output: xai-blockchain-0.2.0.pkg
```

### PKG Features

- System-wide installation to `/usr/local/`
- LaunchDaemon for automatic startup
- Proper uninstallation support
- macOS Installer.app integration

### Installation

```bash
# GUI Installation
open xai-blockchain-0.2.0.pkg

# Command Line Installation
sudo installer -pkg xai-blockchain-0.2.0.pkg -target /
```

### Uninstallation

```bash
# Stop service
sudo launchctl unload /Library/LaunchDaemons/io.xai-blockchain.plist

# Remove files
sudo rm -rf /usr/local/xai
sudo rm /Library/LaunchDaemons/io.xai-blockchain.plist
sudo rm -rf /var/lib/xai
sudo rm -rf /var/log/xai

# Remove user data (optional)
rm -rf ~/Library/Application\ Support/XAI
```

## Code Signing and Notarization

For distribution outside the Mac App Store, you must sign and notarize.

### Prerequisites

- Apple Developer account ($99/year)
- Developer ID Application certificate
- Developer ID Installer certificate (for PKG)
- App-specific password for notarization

### Signing the .app Bundle

```bash
# Sign the app
codesign --deep --force --verify --verbose \
  --sign "Developer ID Application: Your Name (TEAM_ID)" \
  --options runtime \
  --entitlements entitlements.plist \
  build/XAI.app

# Verify signature
codesign --verify --deep --strict --verbose=2 build/XAI.app
spctl --assess --verbose build/XAI.app
```

### Notarizing the DMG

```bash
# Create app-specific password at appleid.apple.com

# Store credentials
xcrun notarytool store-credentials "xai-notary" \
  --apple-id "your@email.com" \
  --team-id "TEAM_ID" \
  --password "app-specific-password"

# Notarize DMG
xcrun notarytool submit xai-blockchain-0.2.0.dmg \
  --keychain-profile "xai-notary" \
  --wait

# Staple notarization ticket
xcrun stapler staple xai-blockchain-0.2.0.dmg

# Verify
spctl --assess --type install --verbose xai-blockchain-0.2.0.dmg
```

### Entitlements

Create `entitlements.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.allow-dyld-environment-variables</key>
    <true/>
    <key>com.apple.security.network.client</key>
    <true/>
    <key>com.apple.security.network.server</key>
    <true/>
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
</dict>
</plist>
```

## Testing

### Homebrew Formula Testing

```bash
# Local install test
brew install --build-from-source ./xai.rb

# Verify installation
xai --version
xai-node --version
xai-wallet --help

# Test service
brew services start xai
sleep 5
brew services list | grep xai
brew services stop xai

# Uninstall
brew uninstall xai
```

### DMG Testing

```bash
# Mount DMG
hdiutil attach xai-blockchain-0.2.0.dmg

# Install app
cp -R /Volumes/XAI\ Blockchain/XAI.app /Applications/

# Launch
open /Applications/XAI.app

# Verify
/Applications/XAI.app/Contents/MacOS/xai-launcher --version

# Uninstall
rm -rf /Applications/XAI.app
hdiutil detach /Volumes/XAI\ Blockchain
```

### Automated Testing Script

```bash
#!/bin/bash
# test-installers.sh

set -e

echo "Testing Homebrew installation..."
brew install --build-from-source ./xai.rb
xai --version
brew services start xai
sleep 5
brew services stop xai
brew uninstall xai

echo "Testing DMG installation..."
hdiutil attach xai-blockchain-0.2.0.dmg -nobrowse
cp -R /Volumes/XAI\ Blockchain/XAI.app /tmp/
/tmp/XAI.app/Contents/MacOS/xai-launcher --version
rm -rf /tmp/XAI.app
hdiutil detach /Volumes/XAI\ Blockchain

echo "All tests passed!"
```

## Distribution Checklist

- [ ] Update version in `xai.rb`
- [ ] Calculate and update SHA256 checksums
- [ ] Test Homebrew formula locally
- [ ] Audit formula: `brew audit --strict --online`
- [ ] Build DMG installer
- [ ] Sign .app bundle with Developer ID
- [ ] Notarize DMG with Apple
- [ ] Staple notarization ticket
- [ ] Test on clean macOS installation
- [ ] Generate checksums for all artifacts
- [ ] Upload to GitHub Releases
- [ ] Update Homebrew tap repository
- [ ] Update documentation

## CI/CD Integration

### GitHub Actions Workflow

```yaml
name: Build macOS Installers

on:
  release:
    types: [created]

jobs:
  build-dmg:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          brew install create-dmg
          pip install build

      - name: Build package
        run: python -m build

      - name: Create DMG
        run: |
          cd installers/macos
          ./create-dmg.sh

      - name: Sign and Notarize
        env:
          SIGNING_IDENTITY: ${{ secrets.SIGNING_IDENTITY }}
          APPLE_ID: ${{ secrets.APPLE_ID }}
          APPLE_PASSWORD: ${{ secrets.APPLE_PASSWORD }}
          TEAM_ID: ${{ secrets.TEAM_ID }}
        run: |
          # Sign app
          codesign --deep --force --verify --verbose \
            --sign "$SIGNING_IDENTITY" \
            --options runtime \
            build/XAI.app

          # Notarize
          xcrun notarytool submit xai-blockchain-0.2.0.dmg \
            --apple-id "$APPLE_ID" \
            --password "$APPLE_PASSWORD" \
            --team-id "$TEAM_ID" \
            --wait

          # Staple
          xcrun stapler staple xai-blockchain-0.2.0.dmg

      - name: Upload Release Asset
        uses: actions/upload-release-asset@v1
        with:
          upload_url: ${{ github.event.release.upload_url }}
          asset_path: ./installers/macos/xai-blockchain-0.2.0.dmg
          asset_name: xai-blockchain-0.2.0.dmg
          asset_content_type: application/x-apple-diskimage

  update-homebrew:
    runs-on: ubuntu-latest
    needs: build-dmg
    steps:
      - name: Update Homebrew Tap
        run: |
          # Calculate SHA256
          SHA256=$(curl -sL ${{ github.event.release.tarball_url }} | shasum -a 256 | cut -d ' ' -f 1)

          # Update formula
          git clone https://github.com/xai-blockchain/homebrew-tap
          cd homebrew-tap
          sed -i "s/sha256 \".*\"/sha256 \"$SHA256\"/" Formula/xai.rb
          sed -i "s/version \".*\"/version \"${{ github.event.release.tag_name }}\"/" Formula/xai.rb

          # Commit and push
          git add Formula/xai.rb
          git commit -m "Update to ${{ github.event.release.tag_name }}"
          git push
```

## Troubleshooting

### Homebrew Issues

**Formula fails to install:**
```bash
# Check dependencies
brew deps xai

# View detailed logs
brew install xai --verbose --debug

# Clean cache
brew cleanup
rm -rf $(brew --cache)
```

**Service won't start:**
```bash
# Check logs
tail -f /usr/local/var/log/xai/error.log

# Manual start
/usr/local/bin/xai-daemon --network testnet
```

### DMG Issues

**App won't open (Gatekeeper):**
```bash
# Remove quarantine attribute
xattr -d com.apple.quarantine /Applications/XAI.app

# Or right-click -> Open (first launch only)
```

**Python not found:**
```bash
# Verify Python in bundle
ls -la /Applications/XAI.app/Contents/Resources/python/bin/
```

### Code Signing Issues

**"Developer cannot be verified":**
- App must be signed with Developer ID
- App must be notarized by Apple
- Ticket must be stapled to DMG

**Verify signature:**
```bash
codesign --verify --deep --strict /Applications/XAI.app
spctl --assess --verbose /Applications/XAI.app
```

## Resources

- [Homebrew Formula Cookbook](https://docs.brew.sh/Formula-Cookbook)
- [create-dmg Documentation](https://github.com/create-dmg/create-dmg)
- [Apple Code Signing Guide](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
- [Notarization Documentation](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)

## Support

For installation issues:
- Homebrew: Check `/usr/local/var/log/xai/`
- DMG: Check `~/Library/Logs/XAI/`
- General: See main [INSTALL.md](../INSTALL.md)

## License

MIT License - See LICENSE file for details
