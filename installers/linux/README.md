# Linux Installers for XAI Blockchain

This directory contains configuration files for building Linux packages for XAI Blockchain.

## Overview

Multiple package formats are provided:

1. **Debian Package (.deb)** - Ubuntu, Debian, and derivatives
2. **RPM Package (.rpm)** - Fedora, RHEL, CentOS, and derivatives
3. **AppImage** - Universal, portable format for all distributions
4. **systemd Service** - System-wide daemon integration

## Package Formats

### 1. Debian Package (.deb)

For Ubuntu, Debian, Linux Mint, Pop!_OS, elementary OS, etc.

#### Building

```bash
# Install build dependencies
sudo apt-get install debhelper dh-python python3-all python3-setuptools \
    libssl-dev libffi-dev libsecp256k1-dev libgmp-dev pkg-config

# Build package
cd ../..  # Go to project root
dpkg-buildpackage -us -uc -b

# Output: ../xai-blockchain_0.2.0_amd64.deb
```

#### Installing

```bash
# Install package
sudo dpkg -i xai-blockchain_0.2.0_amd64.deb

# Install dependencies (if needed)
sudo apt-get install -f

# Start service
sudo systemctl start xai-node
sudo systemctl enable xai-node

# Check status
systemctl status xai-node
```

#### Package Contents

The .deb package includes:

- **Main Package** (`xai-blockchain`): Core node, wallet, and CLI
- **Dev Package** (`xai-blockchain-dev`): Development tools and headers
- **Doc Package** (`xai-blockchain-doc`): Documentation

#### Files Installed

- Binaries: `/usr/bin/xai`, `/usr/bin/xai-node`, `/usr/bin/xai-wallet`
- Libraries: `/usr/lib/python3/dist-packages/xai/`
- Configuration: `/etc/xai/`
- Data: `/var/lib/xai/`
- Logs: `/var/log/xai/`
- Service: `/lib/systemd/system/xai-node.service`

### 2. RPM Package (.rpm)

For Fedora, RHEL, CentOS, Rocky Linux, AlmaLinux, etc.

#### Building

```bash
# Install build dependencies
sudo dnf install rpm-build python3-devel python3-setuptools \
    openssl-devel libffi-devel libsecp256k1-devel gmp-devel pkgconfig

# Create RPM build structure
mkdir -p ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# Copy spec file
cp linux/xai.spec ~/rpmbuild/SPECS/

# Create source tarball
cd ../..
python3 -m build --sdist
cp dist/xai-blockchain-0.2.0.tar.gz ~/rpmbuild/SOURCES/

# Build RPM
rpmbuild -ba ~/rpmbuild/SPECS/xai.spec

# Output: ~/rpmbuild/RPMS/noarch/xai-blockchain-0.2.0-1.noarch.rpm
```

#### Installing

```bash
# Install package
sudo rpm -ivh xai-blockchain-0.2.0-1.noarch.rpm

# Or with dnf
sudo dnf install xai-blockchain-0.2.0-1.noarch.rpm

# Start service
sudo systemctl start xai-node
sudo systemctl enable xai-node

# Check status
systemctl status xai-node
```

#### Package Contents

The .rpm creates three packages:

- **xai-blockchain**: Main package with node and tools
- **xai-blockchain-devel**: Development files and testing tools
- **xai-blockchain-doc**: Documentation and guides

### 3. AppImage

Universal portable format that runs on most Linux distributions without installation.

#### Building

```bash
# Install appimage-builder
sudo pip3 install appimage-builder

# Build AppImage
./create-appimage.sh

# Output: XAI_Blockchain-0.2.0-x86_64.AppImage
```

#### Using

```bash
# Make executable
chmod +x XAI_Blockchain-0.2.0-x86_64.AppImage

# Run directly
./XAI_Blockchain-0.2.0-x86_64.AppImage

# Run node
./XAI_Blockchain-0.2.0-x86_64.AppImage --network testnet

# Install to user bin (optional)
mkdir -p ~/.local/bin
cp XAI_Blockchain-0.2.0-x86_64.AppImage ~/.local/bin/xai-blockchain
chmod +x ~/.local/bin/xai-blockchain
```

#### AppImage Features

- No installation required
- Includes all dependencies
- Runs on most distributions
- Self-contained Python environment
- Portable - runs from any location
- User-space execution - no root needed

#### Data Locations

When running AppImage:

- **Data**: `~/.xai/`
- **Blockchain**: `~/.xai/blockchain/`
- **Wallets**: `~/.xai/wallets/`
- **Config**: `~/.xai/config/`
- **Logs**: `~/.xai/logs/`

### 4. systemd Service

All package formats include systemd integration.

#### Service File

Located at `/lib/systemd/system/xai-node.service` (Debian) or `/usr/lib/systemd/system/xai-node.service` (RPM).

#### Service Management

```bash
# Start service
sudo systemctl start xai-node

# Stop service
sudo systemctl stop xai-node

# Restart service
sudo systemctl restart xai-node

# Enable on boot
sudo systemctl enable xai-node

# Disable on boot
sudo systemctl disable xai-node

# Check status
systemctl status xai-node

# View logs
sudo journalctl -u xai-node -f

# View logs since boot
sudo journalctl -u xai-node -b
```

#### Service Configuration

Edit `/etc/xai/node.yaml` to configure the service:

```yaml
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
```

After editing, restart the service:

```bash
sudo systemctl restart xai-node
```

## Testing Packages

### Testing Debian Package

```bash
# Install in container
docker run -it --rm ubuntu:22.04 bash

# Inside container
apt-get update
apt-get install -y ./xai-blockchain_0.2.0_amd64.deb

# Test commands
xai --version
xai-node --help
xai-wallet --help

# Test service
systemctl start xai-node
sleep 5
systemctl status xai-node
```

### Testing RPM Package

```bash
# Install in container
docker run -it --rm fedora:39 bash

# Inside container
dnf install -y ./xai-blockchain-0.2.0-1.noarch.rpm

# Test commands
xai --version
xai-node --help

# Test service
systemctl start xai-node
systemctl status xai-node
```

### Testing AppImage

```bash
# Test in minimal environment
docker run -it --rm ubuntu:22.04 bash

# Inside container
apt-get update
apt-get install -y libfuse2

# Run AppImage
./XAI_Blockchain-0.2.0-x86_64.AppImage --version
./XAI_Blockchain-0.2.0-x86_64.AppImage --help
```

## Distribution

### Debian Repository

Set up a Debian repository for easy updates:

```bash
# On repository server
mkdir -p /var/www/apt/pool/main
mkdir -p /var/www/apt/dists/stable/main/binary-amd64

# Copy packages
cp *.deb /var/www/apt/pool/main/

# Generate Packages file
cd /var/www/apt
dpkg-scanpackages pool/main /dev/null | gzip -9c > dists/stable/main/binary-amd64/Packages.gz

# Generate Release file
cd dists/stable
cat > Release << EOF
Origin: XAI Blockchain
Label: XAI Blockchain
Suite: stable
Codename: stable
Architectures: amd64
Components: main
Description: XAI Blockchain APT Repository
EOF

apt-ftparchive release . >> Release

# Sign Release file (optional)
gpg --armor --detach-sign -o Release.gpg Release
gpg --clearsign -o InRelease Release
```

Users can then add the repository:

```bash
# Add repository
echo "deb [trusted=yes] https://apt.xai-blockchain.io stable main" | sudo tee /etc/apt/sources.list.d/xai.list

# Update and install
sudo apt-get update
sudo apt-get install xai-blockchain
```

### RPM Repository

Set up a YUM/DNF repository:

```bash
# On repository server
mkdir -p /var/www/yum/xai/el8/x86_64

# Copy packages
cp *.rpm /var/www/yum/xai/el8/x86_64/

# Create repository metadata
createrepo /var/www/yum/xai/el8/x86_64/

# Sign repository (optional)
gpg --detach-sign --armor /var/www/yum/xai/el8/x86_64/repodata/repomd.xml
```

Users can add the repository:

```bash
# Add repository
cat > /etc/yum.repos.d/xai.repo << EOF
[xai]
name=XAI Blockchain Repository
baseurl=https://yum.xai-blockchain.io/xai/el8/x86_64/
enabled=1
gpgcheck=0
EOF

# Install
sudo dnf install xai-blockchain
```

### AppImage Distribution

Distribute via GitHub Releases:

```bash
# Upload to GitHub Release
gh release create v0.2.0 \
  XAI_Blockchain-0.2.0-x86_64.AppImage \
  XAI_Blockchain-0.2.0-x86_64.AppImage.sha256 \
  --title "XAI Blockchain v0.2.0" \
  --notes "AppImage for Linux"
```

## Building All Packages

Use the provided Makefile to build all formats:

```bash
# Build all packages
make -C ../.. -f installers/Makefile all

# Build specific format
make -C ../.. -f installers/Makefile debian
make -C ../.. -f installers/Makefile rpm
make -C ../.. -f installers/Makefile appimage

# Test all packages
make -C ../.. -f installers/Makefile test
```

## CI/CD Integration

### GitHub Actions Workflow

```yaml
name: Build Linux Packages

on:
  release:
    types: [created]

jobs:
  build-deb:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v3

      - name: Install build dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y debhelper dh-python python3-all \
            python3-setuptools libssl-dev libffi-dev libsecp256k1-dev

      - name: Build Debian package
        run: dpkg-buildpackage -us -uc -b

      - name: Upload artifact
        uses: actions/upload-release-asset@v1
        with:
          upload_url: ${{ github.event.release.upload_url }}
          asset_path: ../xai-blockchain_0.2.0_amd64.deb
          asset_name: xai-blockchain_0.2.0_amd64.deb
          asset_content_type: application/vnd.debian.binary-package

  build-rpm:
    runs-on: ubuntu-22.04
    container: fedora:39
    steps:
      - uses: actions/checkout@v3

      - name: Install build dependencies
        run: |
          dnf install -y rpm-build python3-devel python3-setuptools \
            openssl-devel libffi-devel libsecp256k1-devel

      - name: Build RPM package
        run: |
          mkdir -p ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
          cp installers/linux/xai.spec ~/rpmbuild/SPECS/
          python3 -m build --sdist
          cp dist/*.tar.gz ~/rpmbuild/SOURCES/
          rpmbuild -ba ~/rpmbuild/SPECS/xai.spec

      - name: Upload artifact
        uses: actions/upload-release-asset@v1
        with:
          upload_url: ${{ github.event.release.upload_url }}
          asset_path: ~/rpmbuild/RPMS/noarch/xai-blockchain-0.2.0-1.noarch.rpm
          asset_name: xai-blockchain-0.2.0-1.noarch.rpm
          asset_content_type: application/x-rpm

  build-appimage:
    runs-on: ubuntu-20.04
    steps:
      - uses: actions/checkout@v3

      - name: Install appimage-builder
        run: sudo pip3 install appimage-builder

      - name: Build AppImage
        run: |
          cd installers/linux
          ./create-appimage.sh

      - name: Upload artifact
        uses: actions/upload-release-asset@v1
        with:
          upload_url: ${{ github.event.release.upload_url }}
          asset_path: installers/linux/XAI_Blockchain-0.2.0-x86_64.AppImage
          asset_name: XAI_Blockchain-0.2.0-x86_64.AppImage
          asset_content_type: application/x-executable
```

## Troubleshooting

### Debian Package Issues

**Dependencies not satisfied:**
```bash
sudo apt-get install -f
```

**Package conflicts:**
```bash
sudo dpkg --remove --force-remove-reinstreq xai-blockchain
sudo apt-get install xai-blockchain
```

### RPM Package Issues

**Dependency problems:**
```bash
sudo dnf install --skip-broken xai-blockchain
```

**Clean cache:**
```bash
sudo dnf clean all
sudo dnf install xai-blockchain
```

### AppImage Issues

**FUSE not available:**
```bash
# Extract and run without FUSE
./XAI_Blockchain-0.2.0-x86_64.AppImage --appimage-extract
./squashfs-root/AppRun
```

**Permission denied:**
```bash
chmod +x XAI_Blockchain-0.2.0-x86_64.AppImage
```

### Service Issues

**Service won't start:**
```bash
# Check logs
sudo journalctl -u xai-node -n 50

# Check configuration
sudo xai-node --test-config

# Check permissions
sudo chown -R xai:xai /var/lib/xai
sudo chown -R xai:xai /var/log/xai
```

**Port already in use:**
```bash
# Find process using port
sudo lsof -i :18545

# Kill process or change port in /etc/xai/node.yaml
```

## Uninstallation

### Debian

```bash
# Stop service
sudo systemctl stop xai-node
sudo systemctl disable xai-node

# Remove package
sudo apt-get remove xai-blockchain

# Remove configuration and data (optional)
sudo apt-get purge xai-blockchain
sudo rm -rf /var/lib/xai
```

### RPM

```bash
# Stop service
sudo systemctl stop xai-node
sudo systemctl disable xai-node

# Remove package
sudo dnf remove xai-blockchain

# Remove data (optional)
sudo rm -rf /var/lib/xai /var/log/xai /etc/xai
```

### AppImage

```bash
# Simply delete the file
rm XAI_Blockchain-0.2.0-x86_64.AppImage

# Remove user data (optional)
rm -rf ~/.xai
```

## Support

- **Installation Issues**: See main [INSTALL.md](../INSTALL.md)
- **Service Issues**: Check `/var/log/xai/` or `journalctl -u xai-node`
- **AppImage Issues**: Check `~/.xai/logs/`

## License

MIT License - See LICENSE file for details
