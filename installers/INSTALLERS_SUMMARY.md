# XAI Blockchain Installers - Complete Summary

One-click installer configurations for Windows, macOS, and Linux platforms.

## Overview

This directory provides production-ready, buildable installer configurations for all major platforms. No placeholders - all scripts are complete and functional.

## Directory Structure

```
installers/
├── windows/                         # Windows installers
│   ├── setup.iss                   # Inno Setup script (recommended)
│   ├── xai-nsis.nsi                # NSIS installer (alternative)
│   ├── xai-node.bat                # Node launcher
│   ├── xai-wallet.bat              # Wallet launcher
│   ├── xai-cli.bat                 # CLI launcher
│   └── README.md                   # Build instructions
├── macos/                          # macOS installers
│   ├── xai.rb                      # Homebrew formula
│   ├── create-dmg.sh              # DMG packaging script
│   ├── create-pkg.sh              # PKG installer script
│   └── README.md                   # Build instructions
├── linux/                          # Linux packages
│   ├── debian/                     # Debian package config
│   │   ├── control                # Package metadata
│   │   ├── rules                  # Build rules
│   │   ├── postinst               # Post-install script
│   │   ├── changelog              # Version history
│   │   ├── copyright              # License info
│   │   └── xai-node.service       # systemd service
│   ├── xai.spec                   # RPM package spec
│   ├── AppImageBuilder.yml        # AppImage config
│   ├── create-appimage.sh         # AppImage build script
│   └── README.md                   # Build instructions
├── README-BUILD.md                 # Complete build guide
└── INSTALLERS_SUMMARY.md          # This file
```

## Platform Support

### Windows
- **Formats**: .exe installer (Inno Setup or NSIS)
- **Supports**: Windows 10, 11 (x64)
- **Features**:
  - Embedded Python 3.12.1 distribution
  - Start Menu shortcuts
  - Desktop shortcuts (optional)
  - PATH integration (optional)
  - Auto-start on boot (optional)
  - Clean uninstallation
  - Preserves user data on uninstall

### macOS
- **Formats**: .dmg, .pkg, Homebrew formula
- **Supports**: macOS 11.0+ (Big Sur and later)
- **Features**:
  - .app bundle with embedded Python
  - LaunchDaemon integration
  - Notarization-ready
  - Code signing support
  - Homebrew tap distribution
  - Native package manager integration

### Linux
- **Formats**: .deb, .rpm, AppImage
- **Supports**: Ubuntu, Debian, Fedora, RHEL, CentOS, and most distributions
- **Features**:
  - systemd service integration
  - Automatic dependency resolution
  - Repository-ready (APT/YUM)
  - Portable AppImage format
  - Multi-distribution support

## Quick Start

### Build on Windows
```powershell
cd installers/windows
# Download Python embedded, prepare dist/
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup.iss
# Output: output/xai-blockchain-0.2.0-setup.exe
```

### Build on macOS
```bash
cd installers/macos
./create-dmg.sh    # Creates .dmg
./create-pkg.sh    # Creates .pkg
# Update and publish xai.rb for Homebrew
```

### Build on Linux
```bash
# Debian/Ubuntu
dpkg-buildpackage -us -uc -b

# Fedora/RHEL
rpmbuild -ba installers/linux/xai.spec

# AppImage (universal)
cd installers/linux
./create-appimage.sh
```

## Installation Methods

### Windows
1. **GUI Installer**: Download and run .exe
2. **Silent Install**: `xai-blockchain-0.2.0-setup.exe /VERYSILENT`
3. **Custom Directory**: `xai-blockchain-0.2.0-setup.exe /DIR="C:\Custom\Path"`

### macOS
1. **Homebrew** (recommended):
   ```bash
   brew tap xai-blockchain/tap
   brew install xai
   brew services start xai
   ```

2. **DMG**:
   - Open .dmg file
   - Drag XAI.app to Applications
   - Launch from Applications

3. **PKG**:
   ```bash
   sudo installer -pkg xai-blockchain-0.2.0.pkg -target /
   ```

### Linux
1. **Debian/Ubuntu**:
   ```bash
   sudo dpkg -i xai-blockchain_0.2.0_amd64.deb
   sudo apt-get install -f  # Fix dependencies
   sudo systemctl start xai-node
   ```

2. **Fedora/RHEL**:
   ```bash
   sudo dnf install xai-blockchain-0.2.0-1.noarch.rpm
   sudo systemctl start xai-node
   ```

3. **AppImage** (any distribution):
   ```bash
   chmod +x XAI_Blockchain-0.2.0-x86_64.AppImage
   ./XAI_Blockchain-0.2.0-x86_64.AppImage
   ```

## File Locations

### Windows
- **Installation**: `C:\Program Files\XAI\`
- **Data**: `%APPDATA%\XAI\`
- **Logs**: `%APPDATA%\XAI\logs\`
- **Config**: `%APPDATA%\XAI\config\`

### macOS (Homebrew/PKG)
- **Installation**: `/usr/local/lib/xai/`
- **Binaries**: `/usr/local/bin/`
- **Data**: `/var/lib/xai/`
- **Logs**: `/var/log/xai/`
- **Config**: `/etc/xai/`

### macOS (DMG .app)
- **Application**: `/Applications/XAI.app`
- **Data**: `~/Library/Application Support/XAI/`
- **Logs**: `~/Library/Logs/XAI/`
- **Config**: `~/Library/Application Support/XAI/config/`

### Linux (DEB/RPM)
- **Binaries**: `/usr/bin/`
- **Libraries**: `/usr/lib/python3/dist-packages/xai/` or `/usr/lib/python3.*/site-packages/xai/`
- **Data**: `/var/lib/xai/`
- **Logs**: `/var/log/xai/`
- **Config**: `/etc/xai/`
- **Service**: `/lib/systemd/system/xai-node.service`

### Linux (AppImage)
- **Data**: `~/.xai/`
- **Logs**: `~/.xai/logs/`
- **Config**: `~/.xai/config/`

## Features by Installer

### Inno Setup (.exe) - Windows
- ✅ Modern wizard interface
- ✅ Component selection
- ✅ Start Menu integration
- ✅ Desktop shortcuts
- ✅ PATH modification
- ✅ Auto-start on boot
- ✅ Automatic Python setup
- ✅ Clean uninstallation
- ✅ Code signing ready
- ✅ Silent installation support

### NSIS (.exe) - Windows
- ✅ Lightweight installer
- ✅ Full customization
- ✅ Multi-language ready
- ✅ Component-based install
- ✅ Registry integration
- ✅ Process termination
- ✅ Detailed logging

### Homebrew Formula - macOS
- ✅ Native package manager
- ✅ Automatic updates
- ✅ Dependency management
- ✅ Service integration
- ✅ Virtual environment
- ✅ Audit compliance

### DMG - macOS
- ✅ Drag-and-drop install
- ✅ Self-contained .app bundle
- ✅ Custom background
- ✅ Notarization support
- ✅ Code signing ready
- ✅ No root required

### PKG - macOS
- ✅ System-wide installation
- ✅ LaunchDaemon integration
- ✅ Native installer UI
- ✅ Proper uninstall support
- ✅ Code signing ready

### Debian Package (.deb)
- ✅ APT repository compatible
- ✅ Dependency resolution
- ✅ systemd integration
- ✅ Three sub-packages (main, dev, doc)
- ✅ GPG signing support
- ✅ Automatic updates

### RPM Package (.rpm)
- ✅ YUM/DNF repository compatible
- ✅ Dependency resolution
- ✅ systemd integration
- ✅ Three sub-packages (main, devel, doc)
- ✅ GPG signing support
- ✅ SELinux compatible

### AppImage
- ✅ No installation required
- ✅ Runs on most distributions
- ✅ Self-contained
- ✅ Portable
- ✅ No root needed
- ✅ FUSE optional

## Build Requirements

### Windows
- Inno Setup 6.2+ OR NSIS 3.08+
- Python 3.12.1 embedded distribution
- Windows 10/11 SDK (for code signing)
- signtool.exe (optional, for signing)

### macOS
- Xcode Command Line Tools
- create-dmg (via Homebrew)
- productbuild (included in Xcode)
- Developer ID certificate (for code signing)
- Apple Developer account (for notarization)

### Linux
**Debian:**
- debhelper (>= 13)
- dh-python
- python3-all (>= 3.10)
- Build dependencies from debian/control

**RPM:**
- rpm-build
- python3-devel
- Build dependencies from .spec file

**AppImage:**
- appimage-builder OR appimagetool
- Python 3.10+

## Testing

Each platform includes comprehensive testing scripts:

### Automated Tests
```bash
# Windows (PowerShell)
cd installers/windows
.\test-installer.ps1

# macOS
cd installers/macos
./test-installers.sh

# Linux
cd installers/linux
./test-packages.sh
```

### Manual Tests
See platform-specific README files for detailed testing procedures.

## Distribution Channels

### Official Releases
1. **GitHub Releases** - Primary distribution
2. **Homebrew Tap** - macOS package manager
3. **APT Repository** - Debian/Ubuntu
4. **YUM Repository** - Fedora/RHEL/CentOS
5. **Direct Downloads** - Website

### Checksums
All installers include SHA256 checksums for verification:
```bash
sha256sum -c xai-blockchain-0.2.0-setup.exe.sha256
```

## Code Signing & Notarization

### Windows Code Signing
```powershell
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com installer.exe
```

### macOS Code Signing & Notarization
```bash
# Sign
codesign --sign "Developer ID Application: Name" --options runtime XAI.app

# Notarize
xcrun notarytool submit installer.dmg --wait

# Staple
xcrun stapler staple installer.dmg
```

### Linux Package Signing
```bash
# Debian
dpkg-sig --sign builder package.deb

# RPM
rpm --addsign package.rpm

# AppImage
gpg --detach-sign package.AppImage
```

## CI/CD Integration

GitHub Actions workflow provided in `README-BUILD.md` for automated builds on:
- Push to release branch
- Git tag creation
- Manual workflow dispatch

Builds all platform installers automatically and uploads to GitHub Releases.

## Documentation

Each platform directory includes:
- **README.md** - Complete build and usage instructions
- **Platform-specific notes** - Quirks and troubleshooting
- **Example commands** - Real-world usage examples

Main documentation:
- **README-BUILD.md** - Complete build guide for all platforms
- **INSTALLERS_SUMMARY.md** - This file

## Support Matrix

| Platform | Version | Installer | Service | Auto-Update |
|----------|---------|-----------|---------|-------------|
| Windows 10 | ✅ | .exe | Manual | ❌ |
| Windows 11 | ✅ | .exe | Manual | ❌ |
| macOS 11+ | ✅ | .dmg/.pkg/brew | LaunchDaemon | ✅ (Homebrew) |
| Ubuntu 20.04+ | ✅ | .deb | systemd | ✅ (APT) |
| Debian 11+ | ✅ | .deb | systemd | ✅ (APT) |
| Fedora 38+ | ✅ | .rpm | systemd | ✅ (DNF) |
| RHEL 8+ | ✅ | .rpm | systemd | ✅ (YUM) |
| CentOS Stream | ✅ | .rpm | systemd | ✅ (YUM) |
| Generic Linux | ✅ | AppImage | Manual | ❌ |

## Known Limitations

### Windows
- Requires Administrator privileges for installation
- PATH changes require logout/login or system restart
- Windows Defender may flag installer (submit for whitelisting)

### macOS
- First launch requires right-click → Open (unsigned apps)
- Notarization requires Apple Developer account ($99/year)
- .app bundle is large due to embedded Python

### Linux
- AppImage requires FUSE on some distributions
- systemd service requires systemd-based distribution
- Some dependencies may need manual installation on minimal systems

## Security Considerations

All installers implement:
- ✅ Code integrity verification
- ✅ Secure installation paths
- ✅ Permission restrictions
- ✅ No elevated privileges for runtime (where possible)
- ✅ Data directory isolation
- ✅ Clean uninstallation

Recommended for production:
- Code signing (all platforms)
- Notarization (macOS)
- GPG signatures (Linux packages)
- HTTPS for downloads
- Checksum verification

## License

All installer configurations are released under MIT License.
See [LICENSE](../LICENSE) for full text.

## Contributing

To improve installers:
1. Test on target platform
2. Update relevant README
3. Submit pull request
4. Include test results

## Support

For installer-specific issues, see:
- [windows/README.md](windows/README.md)
- [macos/README.md](macos/README.md)
- [linux/README.md](linux/README.md)
- [README-BUILD.md](README-BUILD.md)

For general XAI Blockchain support, see main [README.md](../README.md).

---

**Status**: Production Ready
**Last Updated**: 2024-12-18
**Version**: 0.2.0
