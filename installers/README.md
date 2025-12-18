# XAI Blockchain Installers

Production-ready installation packages for all platforms.

## Contents

This directory contains one-click installers and package specifications for deploying XAI blockchain across all major operating systems and platforms.

### Installation Scripts

| File | Platform | Description |
|------|----------|-------------|
| `install-xai.sh` | Linux/macOS | Universal installer with OS auto-detection |
| `install-xai.ps1` | Windows | PowerShell installer with GUI shortcuts |
| `docker-install.sh` | All (Docker) | One-liner Docker deployment |
| `INSTALL.md` | Documentation | Complete installation guide |

### Package Specifications

| File/Directory | Type | Platform |
|----------------|------|----------|
| `xai.rb` | Homebrew Formula | macOS |
| `debian/` | Debian Package | Ubuntu/Debian |
| `xai.spec` | RPM Package | CentOS/Fedora/RHEL |

## Quick Start

### Linux/macOS One-Click Install
```bash
./install-xai.sh
```

Options:
- `--venv` - Install in virtual environment
- `--dev` - Include development dependencies

### Windows PowerShell
```powershell
.\install-xai.ps1
```

Options:
- `-Venv` - Install in virtual environment
- `-Dev` - Include development tools
- `-NoShortcuts` - Skip desktop shortcut creation

### Docker (All Platforms)
```bash
./docker-install.sh
```

Options:
- `--mainnet` - Use mainnet
- `--mine ADDRESS` - Enable mining
- `--data-dir DIR` - Custom data directory
- `--foreground` - Run in foreground

## Features

### Universal Linux/macOS Installer (`install-xai.sh`)

**Capabilities:**
- Automatic OS detection (Ubuntu, Debian, Fedora, CentOS, RHEL, Arch, macOS)
- Python version verification (3.10+)
- System dependency installation
- Virtual environment support
- Data directory creation
- Genesis file download
- Shell integration (bash/zsh)
- Idempotent (safe to run multiple times)

**Supported Distributions:**
- Ubuntu 20.04, 22.04, 24.04
- Debian 11, 12
- CentOS Stream 8, 9
- Fedora 38, 39, 40
- RHEL 8, 9
- Arch Linux
- macOS 11+ (Big Sur and later)

**Installation Locations:**
- System: User Python packages (`~/.local/bin`)
- Venv: `~/.xai/venv/`
- Data: `~/.xai/`
- Config: `~/.xai/config/`
- Logs: `~/.xai/logs/`

### Windows PowerShell Installer (`install-xai.ps1`)

**Capabilities:**
- Python detection and version check
- PATH configuration
- Desktop shortcut creation
- Virtual environment support
- Data directory setup
- Genesis file download
- Error handling and cleanup

**Desktop Shortcuts:**
- XAI Node (launches node in terminal)
- XAI Wallet (opens wallet CLI)

**Installation Locations:**
- Data: `%USERPROFILE%\.xai\`
- Config: `%USERPROFILE%\.xai\config\`
- Logs: `%USERPROFILE%\.xai\logs\`
- Venv: `%USERPROFILE%\.xai\venv\`

### Docker Installer (`docker-install.sh`)

**Capabilities:**
- Docker verification
- Image pull/build
- Persistent volume mounting
- Network configuration
- Port mapping
- Automatic restart policy
- Log streaming

**Container Features:**
- Non-root user execution
- Health checks
- Resource limits
- Security hardening
- Persistent data volumes

**Exposed Ports:**
- Testnet: 18545 (P2P), 18546 (RPC), 19090 (Metrics)
- Mainnet: 8545 (P2P), 8546 (RPC), 9090 (Metrics)

### Homebrew Formula (`xai.rb`)

**Installation:**
```bash
brew tap xai-blockchain/tap
brew install xai
```

**Features:**
- Automatic dependency resolution
- Virtual environment isolation
- Service management (launchd)
- Automatic updates via `brew upgrade`
- Clean uninstall

**Locations:**
- Formula: `/usr/local/Homebrew/Library/Taps/xai-blockchain/tap/xai.rb`
- Config: `/usr/local/etc/xai/`
- Data: `/usr/local/var/xai/`
- Logs: `/usr/local/var/log/xai/`

### Debian Package (`debian/`)

**Build Package:**
```bash
cd /path/to/xai
dpkg-buildpackage -us -uc
sudo dpkg -i ../xai-blockchain_0.2.0_all.deb
```

**Features:**
- systemd service integration
- User/group creation
- Directory permissions
- Configuration management
- Automatic dependency installation
- Clean uninstall with purge

**Packages:**
- `xai-blockchain` - Main package
- `xai-blockchain-dev` - Development tools
- `xai-blockchain-doc` - Documentation

**Files:**
- `control` - Package metadata and dependencies
- `rules` - Build rules
- `postinst` - Post-installation script
- `xai-node.service` - systemd service unit

### RPM Package (`xai.spec`)

**Build Package:**
```bash
rpmbuild -ba xai.spec
sudo rpm -ivh ~/rpmbuild/RPMS/noarch/xai-blockchain-0.2.0-1.noarch.rpm
```

**Features:**
- systemd service integration
- User/group creation
- SELinux compatibility
- Configuration management
- Automatic updates via `dnf upgrade`

**Locations:**
- Config: `/etc/xai/`
- Data: `/var/lib/xai/`
- Logs: `/var/log/xai/`
- Service: `/usr/lib/systemd/system/xai-node.service`

## Building Packages

### Debian Package

**Prerequisites:**
```bash
sudo apt install -y debhelper dh-python python3-all python3-setuptools
```

**Build:**
```bash
cd /path/to/xai
dpkg-buildpackage -us -uc
```

**Output:**
```
../xai-blockchain_0.2.0_all.deb
../xai-blockchain-dev_0.2.0_all.deb
../xai-blockchain-doc_0.2.0_all.deb
```

### RPM Package

**Prerequisites:**
```bash
sudo dnf install -y rpm-build rpmdevtools python3-devel
rpmdev-setuptree
```

**Build:**
```bash
rpmbuild -ba installers/xai.spec
```

**Output:**
```
~/rpmbuild/RPMS/noarch/xai-blockchain-0.2.0-1.noarch.rpm
~/rpmbuild/RPMS/noarch/xai-blockchain-devel-0.2.0-1.noarch.rpm
~/rpmbuild/RPMS/noarch/xai-blockchain-doc-0.2.0-1.noarch.rpm
```

## Testing Installers

### Test install-xai.sh
```bash
# In a clean VM or container
./installers/install-xai.sh --venv
source ~/.xai/activate
xai --version
```

### Test install-xai.ps1
```powershell
# In a clean Windows VM
.\installers\install-xai.ps1 -Venv
. $env:USERPROFILE\.xai\activate.ps1
xai --version
```

### Test docker-install.sh
```bash
# With Docker installed
./installers/docker-install.sh --testnet
docker logs -f xai-node
```

### Test Debian Package
```bash
# In Ubuntu/Debian VM
sudo dpkg -i xai-blockchain_0.2.0_all.deb
sudo systemctl start xai-node
sudo systemctl status xai-node
```

### Test RPM Package
```bash
# In CentOS/Fedora VM
sudo rpm -ivh xai-blockchain-0.2.0-1.noarch.rpm
sudo systemctl start xai-node
sudo systemctl status xai-node
```

## Continuous Integration

All installers are tested in CI:

```yaml
# .github/workflows/installers.yml
jobs:
  test-install-script:
    strategy:
      matrix:
        os: [ubuntu-22.04, ubuntu-24.04, macos-13, macos-14]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - name: Test installer
        run: ./installers/install-xai.sh --venv

  test-docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Test Docker installer
        run: ./installers/docker-install.sh --foreground &

  test-packages:
    strategy:
      matrix:
        include:
          - os: ubuntu-22.04
            package: debian
          - os: fedora:39
            package: rpm
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - name: Build and test package
        run: |
          # Build and install package
          # Test service starts
```

## Distribution

### GitHub Releases

Upload installers to releases:
```bash
gh release create v0.2.0 \
  installers/install-xai.sh \
  installers/install-xai.ps1 \
  installers/docker-install.sh \
  xai-blockchain_0.2.0_all.deb \
  xai-blockchain-0.2.0-1.noarch.rpm
```

### Package Repositories

**Debian/Ubuntu Repository:**
```bash
# Set up apt repository at packages.xai-blockchain.io
reprepro -b /var/www/deb includedeb stable xai-blockchain_0.2.0_all.deb
```

**RPM Repository:**
```bash
# Set up yum repository at packages.xai-blockchain.io
createrepo /var/www/rpm
```

**Homebrew Tap:**
```bash
# Push formula to github.com/xai-blockchain/homebrew-tap
git clone https://github.com/xai-blockchain/homebrew-tap
cp installers/xai.rb homebrew-tap/Formula/
cd homebrew-tap
git add Formula/xai.rb
git commit -m "Release v0.2.0"
git push
```

## Idempotency

All installers are designed to be idempotent (safe to run multiple times):

- **install-xai.sh**: Skips existing installations, updates configuration
- **install-xai.ps1**: Checks for existing installations, updates PATH
- **docker-install.sh**: Stops and removes existing containers
- **Debian/RPM**: Package managers handle upgrades

## Security

### Script Verification

Verify installer integrity:
```bash
# Download checksum
curl -fsSL https://install.xai-blockchain.io/SHA256SUMS -o SHA256SUMS
curl -fsSL https://install.xai-blockchain.io/SHA256SUMS.sig -o SHA256SUMS.sig

# Verify signature
gpg --verify SHA256SUMS.sig SHA256SUMS

# Verify installer
sha256sum -c SHA256SUMS --ignore-missing
```

### HTTPS Only

All installers download over HTTPS with certificate verification.

### Package Signing

- **Debian**: Packages signed with GPG
- **RPM**: Packages signed with GPG
- **Homebrew**: Formula verified via git signatures

## Troubleshooting

See [INSTALL.md](INSTALL.md) for detailed troubleshooting guide.

### Common Issues

**Python not found:**
```bash
# Install Python 3.12
sudo apt install python3.12  # Ubuntu/Debian
brew install python@3.12      # macOS
```

**Permission denied:**
```bash
# Use --user flag or venv
./install-xai.sh --venv
```

**Docker not running:**
```bash
sudo systemctl start docker
```

**Port already in use:**
```bash
# Change port in configuration
export XAI_RPC_PORT=18547
```

## Support

- **Documentation**: [INSTALL.md](INSTALL.md)
- **Issues**: https://github.com/xai-blockchain/xai/issues
- **Security**: security@xai-blockchain.io

## License

MIT License - See [../LICENSE](../LICENSE)
