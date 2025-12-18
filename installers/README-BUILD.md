# Building XAI Blockchain Installers

Complete guide for building one-click installers for all platforms.

## Directory Structure

```
installers/
├── windows/              # Windows installer configurations
│   ├── setup.iss        # Inno Setup script
│   ├── xai-nsis.nsi     # NSIS installer script
│   ├── *.bat            # Windows launcher scripts
│   └── README.md        # Windows build instructions
├── macos/               # macOS installer configurations
│   ├── xai.rb           # Homebrew formula
│   ├── create-dmg.sh    # DMG packaging script
│   ├── create-pkg.sh    # PKG installer script
│   └── README.md        # macOS build instructions
├── linux/               # Linux package configurations
│   ├── debian/          # Debian/Ubuntu .deb package
│   ├── xai.spec         # RPM package spec
│   ├── create-appimage.sh # AppImage build script
│   ├── AppImageBuilder.yml # AppImage configuration
│   └── README.md        # Linux build instructions
└── README-BUILD.md      # This file
```

## Quick Start

### Prerequisites

Install platform-specific build tools:

**Windows:**
- [Inno Setup 6.2+](https://jrsoftware.org/isinfo.php) or [NSIS 3.08+](https://nsis.sourceforge.io/)
- Python 3.12.1 embedded distribution
- PowerShell 5.1+

**macOS:**
- Xcode Command Line Tools: `xcode-select --install`
- Homebrew: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
- create-dmg: `brew install create-dmg`

**Linux:**
- Debian/Ubuntu: `sudo apt-get install debhelper dh-python`
- Fedora/RHEL: `sudo dnf install rpm-build`
- AppImage: `sudo pip3 install appimage-builder`

### Build All Platforms

```bash
# From project root
make -f installers/Makefile all
```

### Build Specific Platform

```bash
# Windows (from Windows machine)
cd installers/windows
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup.iss

# macOS
cd installers/macos
./create-dmg.sh
./create-pkg.sh

# Linux
cd installers/linux
dpkg-buildpackage -us -uc -b  # Debian
rpmbuild -ba xai.spec          # RPM
./create-appimage.sh           # AppImage
```

## Platform-Specific Instructions

### Windows Installers

See [windows/README.md](windows/README.md) for complete instructions.

**Summary:**

1. Download Python embedded distribution:
   ```powershell
   Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.12.1/python-3.12.1-embed-amd64.zip" -OutFile "python.zip"
   Expand-Archive python.zip -DestinationPath python-3.12.1-embed-amd64
   ```

2. Build XAI package:
   ```powershell
   cd ..\..
   python -m build
   New-Item -ItemType Directory -Force installers\windows\dist\xai
   Copy-Item -Recurse src\xai\* installers\windows\dist\xai\
   ```

3. Build installer:
   ```powershell
   cd installers\windows
   & "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup.iss
   ```

**Output:** `installers/windows/output/xai-blockchain-0.2.0-setup.exe`

### macOS Installers

See [macos/README.md](macos/README.md) for complete instructions.

**Summary:**

1. **DMG Installer:**
   ```bash
   cd installers/macos
   brew install create-dmg
   ./create-dmg.sh
   ```

2. **PKG Installer:**
   ```bash
   ./create-pkg.sh
   ```

3. **Homebrew Formula:**
   ```bash
   # Update SHA256 in xai.rb
   shasum -a 256 ../../dist/xai-blockchain-0.2.0.tar.gz

   # Test locally
   brew install --build-from-source ./xai.rb

   # Push to tap repository
   git -C homebrew-tap add Formula/xai.rb
   git -C homebrew-tap commit -m "Update to 0.2.0"
   git -C homebrew-tap push
   ```

**Outputs:**
- `installers/macos/xai-blockchain-0.2.0.dmg`
- `installers/macos/xai-blockchain-0.2.0.pkg`

### Linux Packages

See [linux/README.md](linux/README.md) for complete instructions.

**Summary:**

1. **Debian Package:**
   ```bash
   cd ../..  # Project root
   sudo apt-get install debhelper dh-python
   dpkg-buildpackage -us -uc -b
   ```

2. **RPM Package:**
   ```bash
   mkdir -p ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
   cp installers/linux/xai.spec ~/rpmbuild/SPECS/
   python3 -m build --sdist
   cp dist/*.tar.gz ~/rpmbuild/SOURCES/
   rpmbuild -ba ~/rpmbuild/SPECS/xai.spec
   ```

3. **AppImage:**
   ```bash
   cd installers/linux
   sudo pip3 install appimage-builder
   ./create-appimage.sh
   ```

**Outputs:**
- `../xai-blockchain_0.2.0_amd64.deb`
- `~/rpmbuild/RPMS/noarch/xai-blockchain-0.2.0-1.noarch.rpm`
- `installers/linux/XAI_Blockchain-0.2.0-x86_64.AppImage`

## Testing Installers

### Windows

```powershell
# Silent install
.\xai-blockchain-0.2.0-setup.exe /VERYSILENT /NORESTART

# Verify
& "C:\Program Files\XAI\xai-node.bat" --version

# Silent uninstall
& "C:\Program Files\XAI\uninst.exe" /VERYSILENT /NORESTART
```

### macOS

```bash
# Test DMG
hdiutil attach xai-blockchain-0.2.0.dmg
cp -R "/Volumes/XAI Blockchain/XAI.app" /tmp/
/tmp/XAI.app/Contents/MacOS/xai-launcher --version
rm -rf /tmp/XAI.app
hdiutil detach "/Volumes/XAI Blockchain"

# Test PKG
sudo installer -pkg xai-blockchain-0.2.0.pkg -target /
xai --version
sudo rm -rf /usr/local/lib/xai /usr/local/bin/xai*

# Test Homebrew
brew install --build-from-source ./xai.rb
brew test xai
brew uninstall xai
```

### Linux

```bash
# Test Debian (in Docker)
docker run -it --rm ubuntu:22.04 bash
# Inside container:
apt-get update && apt-get install -y ./xai-blockchain_0.2.0_amd64.deb
xai --version
systemctl start xai-node

# Test RPM (in Docker)
docker run -it --rm fedora:39 bash
# Inside container:
dnf install -y ./xai-blockchain-0.2.0-1.noarch.rpm
xai --version
systemctl start xai-node

# Test AppImage
chmod +x XAI_Blockchain-0.2.0-x86_64.AppImage
./XAI_Blockchain-0.2.0-x86_64.AppImage --version
```

## Code Signing

### Windows

```powershell
# Using signtool.exe from Windows SDK
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com output\xai-blockchain-0.2.0-setup.exe
```

### macOS

```bash
# Sign .app bundle
codesign --deep --force --verify --verbose \
  --sign "Developer ID Application: Your Name (TEAM_ID)" \
  --options runtime \
  build/XAI.app

# Notarize DMG
xcrun notarytool submit xai-blockchain-0.2.0.dmg \
  --apple-id "your@email.com" \
  --team-id "TEAM_ID" \
  --password "app-specific-password" \
  --wait

# Staple ticket
xcrun stapler staple xai-blockchain-0.2.0.dmg
```

### Linux

```bash
# Sign Debian package with GPG
dpkg-sig --sign builder xai-blockchain_0.2.0_amd64.deb

# Sign RPM package
rpm --addsign xai-blockchain-0.2.0-1.noarch.rpm

# Sign AppImage
gpg --armor --detach-sign XAI_Blockchain-0.2.0-x86_64.AppImage
```

## Distribution

### Generating Checksums

```bash
# For all platforms
find . -name "*.exe" -o -name "*.dmg" -o -name "*.pkg" \
  -o -name "*.deb" -o -name "*.rpm" -o -name "*.AppImage" | \
  xargs -I {} sh -c 'sha256sum "{}" > "{}".sha256'
```

### Creating Release Archive

```bash
# Create release directory
mkdir -p release/v0.2.0

# Copy all installers
cp windows/output/*.exe release/v0.2.0/
cp macos/*.dmg release/v0.2.0/
cp macos/*.pkg release/v0.2.0/
cp ../*.deb release/v0.2.0/
cp ~/rpmbuild/RPMS/noarch/*.rpm release/v0.2.0/
cp linux/*.AppImage release/v0.2.0/

# Copy checksums
cp windows/output/*.sha256 release/v0.2.0/
cp macos/*.sha256 release/v0.2.0/
cp ../*.sha256 release/v0.2.0/
cp linux/*.sha256 release/v0.2.0/

# Create archive
tar czf xai-blockchain-0.2.0-installers.tar.gz release/v0.2.0/
```

### GitHub Release

```bash
# Using GitHub CLI
gh release create v0.2.0 \
  release/v0.2.0/*.exe \
  release/v0.2.0/*.dmg \
  release/v0.2.0/*.pkg \
  release/v0.2.0/*.deb \
  release/v0.2.0/*.rpm \
  release/v0.2.0/*.AppImage \
  release/v0.2.0/*.sha256 \
  --title "XAI Blockchain v0.2.0" \
  --notes-file CHANGELOG.md
```

## CI/CD Integration

### Complete GitHub Actions Workflow

Create `.github/workflows/build-installers.yml`:

```yaml
name: Build All Installers

on:
  release:
    types: [created]
  workflow_dispatch:

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - name: Download Python
        run: |
          Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.12.1/python-3.12.1-embed-amd64.zip" -OutFile "python.zip"
          Expand-Archive python.zip -DestinationPath installers/windows/python-3.12.1-embed-amd64
      - name: Install Inno Setup
        run: choco install innosetup -y
      - name: Build Package
        run: python -m build
      - name: Prepare Dist
        run: |
          New-Item -ItemType Directory -Force installers/windows/dist/xai
          Copy-Item -Recurse src/xai/* installers/windows/dist/xai/
      - name: Build Installer
        run: |
          & "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installers/windows/setup.iss
      - name: Upload Artifact
        uses: actions/upload-artifact@v3
        with:
          name: windows-installer
          path: installers/windows/output/*.exe

  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install Dependencies
        run: brew install create-dmg
      - name: Build DMG
        run: |
          cd installers/macos
          ./create-dmg.sh
      - name: Build PKG
        run: |
          cd installers/macos
          ./create-pkg.sh
      - name: Upload Artifacts
        uses: actions/upload-artifact@v3
        with:
          name: macos-installers
          path: |
            installers/macos/*.dmg
            installers/macos/*.pkg

  build-linux:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v3
      - name: Build Debian
        run: |
          sudo apt-get update
          sudo apt-get install -y debhelper dh-python
          dpkg-buildpackage -us -uc -b
      - name: Build RPM
        run: |
          sudo dnf install -y rpm-build python3-devel
          mkdir -p ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
          cp installers/linux/xai.spec ~/rpmbuild/SPECS/
          python3 -m build --sdist
          cp dist/*.tar.gz ~/rpmbuild/SOURCES/
          rpmbuild -ba ~/rpmbuild/SPECS/xai.spec
      - name: Build AppImage
        run: |
          sudo pip3 install appimage-builder
          cd installers/linux
          ./create-appimage.sh
      - name: Upload Artifacts
        uses: actions/upload-artifact@v3
        with:
          name: linux-packages
          path: |
            ../*.deb
            ~/rpmbuild/RPMS/noarch/*.rpm
            installers/linux/*.AppImage

  create-release:
    needs: [build-windows, build-macos, build-linux]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v3
      - name: Generate Checksums
        run: |
          find . -type f \( -name "*.exe" -o -name "*.dmg" -o -name "*.pkg" -o -name "*.deb" -o -name "*.rpm" -o -name "*.AppImage" \) -exec sha256sum {} \; > checksums.txt
      - name: Upload to Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            windows-installer/*
            macos-installers/*
            linux-packages/*
            checksums.txt
```

## Troubleshooting

### Common Build Issues

**Windows: "Python not found"**
- Ensure Python embedded distribution is in correct location
- Verify path in setup.iss matches actual directory

**macOS: "create-dmg not found"**
```bash
brew install create-dmg
```

**Linux: "debhelper not found"**
```bash
sudo apt-get install debhelper dh-python
```

### Testing Issues

**Windows: "Installer fails silently"**
- Run with `/LOG="install.log"` parameter
- Check Windows Event Viewer

**macOS: "App can't be opened"**
- Remove quarantine: `xattr -d com.apple.quarantine XAI.app`
- Or right-click → Open (first time only)

**Linux: "systemd service fails"**
```bash
sudo journalctl -u xai-node -n 50
sudo systemctl status xai-node
```

## Support

For installer-specific issues:
- Windows: See [windows/README.md](windows/README.md)
- macOS: See [macos/README.md](macos/README.md)
- Linux: See [linux/README.md](linux/README.md)

For general installation help: See [INSTALL.md](INSTALL.md)

## License

MIT License - See LICENSE file for details
