# XAI Blockchain - Installation Guide

Complete guide for installing XAI blockchain on all platforms.

## Quick Start

Choose your preferred installation method:

| Method | Best For | Installation Time |
|--------|----------|-------------------|
| [One-Click Script](#one-click-installer-linuxmacos) | Linux/macOS users | 2-5 minutes |
| [Docker](#docker-installation) | Quick testing, isolation | 1-2 minutes |
| [Homebrew](#homebrew-macos) | macOS users | 3-5 minutes |
| [APT/DEB](#debian-package-ubuntudebian) | Ubuntu/Debian servers | 2-3 minutes |
| [YUM/RPM](#rpm-package-centosfedorarhel) | CentOS/RHEL/Fedora | 2-3 minutes |
| [pip](#pip-installation) | Python developers | 1-2 minutes |
| [Source](#build-from-source) | Contributors, custom builds | 5-10 minutes |

## System Requirements

### Minimum Requirements
- **OS**: Ubuntu 20.04+, Debian 11+, CentOS 8+, Fedora 35+, macOS 11+, Windows 10+
- **CPU**: 2 cores
- **RAM**: 2 GB
- **Disk**: 10 GB free space
- **Python**: 3.10 or higher

### Recommended Requirements
- **CPU**: 4+ cores
- **RAM**: 8 GB
- **Disk**: 100 GB SSD
- **Network**: Stable internet connection

## Installation Methods

### One-Click Installer (Linux/macOS)

Universal installation script for all Linux distributions and macOS.

**Standard Installation:**
```bash
curl -fsSL https://install.xai-blockchain.io/install.sh | bash
# or
./installers/install-xai.sh
```

**Virtual Environment (Isolated):**
```bash
./installers/install-xai.sh --venv
```

**With Development Tools:**
```bash
./installers/install-xai.sh --dev
```

**Features:**
- ✓ Automatic OS detection
- ✓ Python version verification
- ✓ System dependency installation
- ✓ Data directory setup
- ✓ Genesis file download
- ✓ Shell integration
- ✓ Idempotent (safe to run multiple times)

**Supported Distributions:**
- Ubuntu 20.04, 22.04, 24.04
- Debian 11, 12
- CentOS Stream 8, 9
- Fedora 38, 39, 40
- RHEL 8, 9
- Arch Linux
- macOS 11+

---

### Docker Installation

Fastest way to get started. Runs XAI in isolated container with persistent storage.

**Quick Start:**
```bash
curl -fsSL https://install.xai-blockchain.io/docker.sh | bash
# or
./installers/docker-install.sh
```

**Options:**
```bash
# Mainnet
./installers/docker-install.sh --mainnet

# Enable mining
./installers/docker-install.sh --mine YOUR_XAI_ADDRESS

# Custom data directory
./installers/docker-install.sh --data-dir /path/to/data

# Run in foreground (interactive)
./installers/docker-install.sh --foreground
```

**Manual Docker Setup:**
```bash
# Pull image
docker pull xai-blockchain/node:latest

# Run node
docker run -d \
  --name xai-node \
  -v ~/.xai:/data \
  -p 18545:18545 \
  -p 18546:18546 \
  --restart unless-stopped \
  xai-blockchain/node:latest

# View logs
docker logs -f xai-node
```

**Docker Compose:**
```yaml
version: '3.8'
services:
  xai-node:
    image: xai-blockchain/node:latest
    container_name: xai-node
    ports:
      - "18545:18545"  # P2P
      - "18546:18546"  # RPC
      - "19090:9090"   # Metrics
    volumes:
      - xai-data:/data
      - xai-logs:/logs
    environment:
      - XAI_NETWORK=testnet
    restart: unless-stopped

volumes:
  xai-data:
  xai-logs:
```

**Useful Commands:**
```bash
# Execute wallet commands inside container
docker exec -it xai-node xai-wallet generate-address
docker exec -it xai-node xai-wallet balance --address ADDR

# Interactive shell
docker exec -it xai-node bash

# Stop/Start
docker stop xai-node
docker start xai-node

# Remove (data persists in volumes)
docker rm -f xai-node
```

---

### Homebrew (macOS)

**Installation:**
```bash
# Add XAI tap
brew tap xai-blockchain/tap

# Install XAI
brew install xai

# Or install directly
brew install xai-blockchain/tap/xai
```

**With Development Tools:**
```bash
brew install xai --with-dev
```

**Start as Service:**
```bash
# Start node (runs in background)
brew services start xai

# Stop service
brew services stop xai

# Restart service
brew services restart xai

# View status
brew services info xai
```

**Manual Start:**
```bash
xai-node --network testnet
```

**Configuration:**
- Formula: `installers/xai.rb`
- Config: `/usr/local/etc/xai/node.yaml`
- Data: `/usr/local/var/xai/`
- Logs: `/usr/local/var/log/xai/`

**Update:**
```bash
brew update
brew upgrade xai
```

**Uninstall:**
```bash
brew uninstall xai
brew untap xai-blockchain/tap
```

---

### Debian Package (Ubuntu/Debian)

**Prerequisites:**
```bash
sudo apt update
sudo apt install -y software-properties-common
```

**Installation:**
```bash
# Add XAI repository
curl -fsSL https://packages.xai-blockchain.io/gpg | sudo apt-key add -
sudo add-apt-repository "deb https://packages.xai-blockchain.io/deb $(lsb_release -cs) main"

# Install XAI
sudo apt update
sudo apt install -y xai-blockchain

# Or install from local .deb
sudo dpkg -i xai-blockchain_0.2.0_all.deb
sudo apt-get install -f  # Fix dependencies
```

**With Development Tools:**
```bash
sudo apt install -y xai-blockchain-dev
```

**Service Management:**
```bash
# Start node
sudo systemctl start xai-node

# Enable on boot
sudo systemctl enable xai-node

# Check status
sudo systemctl status xai-node

# View logs
sudo journalctl -u xai-node -f

# Stop node
sudo systemctl stop xai-node

# Restart
sudo systemctl restart xai-node
```

**Configuration:**
- Service: `/lib/systemd/system/xai-node.service`
- Config: `/etc/xai/node.yaml`
- Data: `/var/lib/xai/`
- Logs: `/var/log/xai/`

**Uninstall:**
```bash
sudo systemctl stop xai-node
sudo systemctl disable xai-node
sudo apt remove --purge xai-blockchain
```

---

### RPM Package (CentOS/Fedora/RHEL)

**Prerequisites:**
```bash
sudo dnf install -y epel-release  # RHEL/CentOS only
```

**Installation:**
```bash
# Add XAI repository
sudo curl -fsSL https://packages.xai-blockchain.io/rpm/xai.repo \
  -o /etc/yum.repos.d/xai.repo

# Install XAI
sudo dnf install -y xai-blockchain

# Or install from local .rpm
sudo rpm -ivh xai-blockchain-0.2.0-1.el9.noarch.rpm
```

**With Development Tools:**
```bash
sudo dnf install -y xai-blockchain-devel
```

**Service Management:**
```bash
# Start node
sudo systemctl start xai-node

# Enable on boot
sudo systemctl enable xai-node

# Check status
sudo systemctl status xai-node

# View logs
sudo journalctl -u xai-node -f
```

**Configuration:**
- Service: `/usr/lib/systemd/system/xai-node.service`
- Config: `/etc/xai/node.yaml`
- Data: `/var/lib/xai/`
- Logs: `/var/log/xai/`

**Uninstall:**
```bash
sudo systemctl stop xai-node
sudo dnf remove xai-blockchain
```

---

### Windows PowerShell

**Standard Installation:**
```powershell
# Download and run installer
Invoke-WebRequest -Uri https://install.xai-blockchain.io/install.ps1 -OutFile install-xai.ps1
.\install-xai.ps1

# Or run directly
irm https://install.xai-blockchain.io/install.ps1 | iex
```

**Virtual Environment:**
```powershell
.\installers\install-xai.ps1 -Venv
```

**With Development Tools:**
```powershell
.\installers\install-xai.ps1 -Dev
```

**Without Desktop Shortcuts:**
```powershell
.\installers\install-xai.ps1 -NoShortcuts
```

**Features:**
- ✓ Automatic Python detection
- ✓ PATH configuration
- ✓ Desktop shortcuts creation
- ✓ Virtual environment support

**Post-Installation:**
```powershell
# Restart PowerShell to refresh PATH

# Generate wallet
xai-wallet generate-address

# Start node
xai-node --network testnet
```

**Data Locations:**
- Config: `%USERPROFILE%\.xai\config\`
- Data: `%USERPROFILE%\.xai\blockchain\`
- Logs: `%USERPROFILE%\.xai\logs\`

---

### pip Installation

For Python developers and custom environments.

**From PyPI:**
```bash
# Standard installation
pip install xai-blockchain

# With development dependencies
pip install xai-blockchain[dev]

# With network (QUIC) support
pip install xai-blockchain[network]

# With blockchain utilities
pip install xai-blockchain[blockchain]

# With AI features
pip install xai-blockchain[ai]

# All extras
pip install xai-blockchain[dev,network,blockchain,ai]
```

**User Installation (No sudo):**
```bash
pip install --user xai-blockchain
```

**Virtual Environment (Recommended):**
```bash
# Create venv
python3 -m venv xai-venv
source xai-venv/bin/activate  # Linux/macOS
# or
xai-venv\Scripts\activate     # Windows

# Install XAI
pip install xai-blockchain
```

**Upgrade:**
```bash
pip install --upgrade xai-blockchain
```

**Uninstall:**
```bash
pip uninstall xai-blockchain
```

---

### Build from Source

For contributors and advanced users.

**Prerequisites:**
```bash
# Ubuntu/Debian
sudo apt install -y build-essential python3-dev libssl-dev libffi-dev \
  libsecp256k1-dev libgmp-dev pkg-config git

# CentOS/Fedora
sudo dnf install -y gcc gcc-c++ python3-devel openssl-devel libffi-devel \
  libsecp256k1-devel gmp-devel pkgconfig git

# macOS
brew install openssl libffi libsecp256k1 gmp git
```

**Clone and Build:**
```bash
# Clone repository
git clone https://github.com/xai-blockchain/xai.git
cd xai

# Install in development mode (editable)
pip install -e .

# With all development dependencies
pip install -e ".[dev]"

# Or build wheel
python -m build
pip install dist/xai_blockchain-0.2.0-py3-none-any.whl
```

**Run Tests:**
```bash
pytest tests/ -v
pytest --cov=src
```

**Build Debian Package:**
```bash
cd xai
dpkg-buildpackage -us -uc
sudo dpkg -i ../xai-blockchain_0.2.0_all.deb
```

**Build RPM Package:**
```bash
rpmbuild -ba installers/xai.spec
sudo rpm -ivh ~/rpmbuild/RPMS/noarch/xai-blockchain-0.2.0-1.noarch.rpm
```

---

## Post-Installation

### Verify Installation

```bash
# Check version
xai --version

# Test wallet
xai-wallet generate-address

# Test node
xai-node --help
```

### Initial Setup

**1. Generate Wallet:**
```bash
xai-wallet generate-address
# Save your address and private key securely!
```

**2. Configure Node:**

Edit `~/.xai/config/node.yaml` (or `/etc/xai/node.yaml` for system install):

```yaml
network:
  name: testnet
  port: 18545
  rpc_port: 18546

data:
  dir: ~/.xai/blockchain

logging:
  level: INFO

node:
  enable_mining: false
  max_peers: 50
```

**3. Start Node:**
```bash
# Foreground
xai-node --network testnet

# Background (systemd)
sudo systemctl start xai-node

# Docker
docker start xai-node
```

**4. Get Test Coins:**
```bash
xai-wallet request-faucet --address YOUR_ADDRESS
```

### Configuration

**Environment Variables:**
```bash
export XAI_NETWORK=testnet           # or mainnet
export XAI_DATA_DIR=~/.xai
export XAI_LOG_LEVEL=INFO
export XAI_RPC_PORT=18546
export MINER_ADDRESS=YOUR_ADDRESS    # for mining
```

**Node Configuration (`node.yaml`):**

See [Configuration Guide](../docs/configuration.md) for all options.

---

## Troubleshooting

### Python Version Issues

```bash
# Check Python version
python3 --version

# Install Python 3.12 (Ubuntu/Debian)
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.12 python3.12-venv

# Use specific version
python3.12 -m pip install xai-blockchain
```

### Permission Errors

```bash
# Use --user flag
pip install --user xai-blockchain

# Or use virtual environment
python3 -m venv venv
source venv/bin/activate
pip install xai-blockchain
```

### libsecp256k1 Not Found

```bash
# Ubuntu/Debian
sudo apt install libsecp256k1-dev

# CentOS/Fedora
sudo dnf install libsecp256k1-devel

# macOS
brew install libsecp256k1
```

### Port Already in Use

```bash
# Check what's using the port
sudo lsof -i :18545
sudo netstat -tulpn | grep 18545

# Change port in configuration
export XAI_RPC_PORT=18547
```

### Docker Issues

```bash
# Check Docker is running
docker info

# Pull latest image
docker pull xai-blockchain/node:latest

# Remove old containers
docker rm -f xai-node

# View logs
docker logs xai-node
```

---

## Upgrading

### pip
```bash
pip install --upgrade xai-blockchain
```

### Homebrew
```bash
brew update
brew upgrade xai
```

### APT (Debian/Ubuntu)
```bash
sudo apt update
sudo apt upgrade xai-blockchain
```

### DNF (Fedora/CentOS/RHEL)
```bash
sudo dnf upgrade xai-blockchain
```

### Docker
```bash
docker pull xai-blockchain/node:latest
docker stop xai-node
docker rm xai-node
./installers/docker-install.sh
```

---

## Uninstallation

### One-Click Installer
```bash
# pip uninstall
pip uninstall xai-blockchain

# Remove data (optional)
rm -rf ~/.xai
```

### Homebrew
```bash
brew services stop xai
brew uninstall xai
rm -rf /usr/local/var/xai
```

### APT
```bash
sudo systemctl stop xai-node
sudo apt remove --purge xai-blockchain
sudo rm -rf /var/lib/xai /var/log/xai /etc/xai
```

### DNF
```bash
sudo systemctl stop xai-node
sudo dnf remove xai-blockchain
sudo rm -rf /var/lib/xai /var/log/xai /etc/xai
```

### Docker
```bash
docker stop xai-node
docker rm xai-node
docker rmi xai-blockchain/node:latest
docker volume prune  # Remove volumes
```

---

## Support

- **Documentation**: https://docs.xai-blockchain.io
- **GitHub Issues**: https://github.com/xai-blockchain/xai/issues
- **Community**: https://discord.gg/xai-blockchain

---

## Security Notice

- **Testnet**: Safe for experimentation
- **Mainnet**: Use with caution, secure your private keys
- **Never share**: Private keys, seed phrases, or wallet files
- **Backup**: Always backup wallet and keys securely

See [SECURITY.md](../SECURITY.md) for security best practices.
