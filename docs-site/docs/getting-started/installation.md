---
sidebar_position: 1
---

# Installation

This guide will walk you through installing XAI blockchain on your system.

## Prerequisites

Before installing XAI, ensure you have:

- **Python 3.10 or higher**
- **2GB RAM minimum** (4GB recommended)
- **10GB+ disk space** for blockchain data
- **Internet connection** for testnet access

## Installation Methods

### Method 1: Install from Source (Recommended for Developers)

```bash
# Clone the repository
git clone https://github.com/xai-blockchain/xai.git
cd xai

# Install dependencies
pip install -e .

# Optional: Install development dependencies
pip install -e ".[dev]"

# Optional: Install network support (QUIC)
pip install -e ".[network]"

# Verify installation
python -m pytest --co -q
```

### Method 2: Install from PyPI

```bash
# Install XAI package
pip install xai-blockchain

# Verify installation
xai --version
```

### Method 3: Docker Installation

```bash
# Pull the XAI image
docker pull xaiblockchain/xai:latest

# Run a node
docker run -d \
  -p 12001:12001 \
  -p 12002:12002 \
  -v xai-data:/data \
  xaiblockchain/xai:latest
```

## Verify Installation

After installation, verify everything is working:

```bash
# Check XAI CLI
xai --help

# Check wallet CLI
xai-wallet --help

# Check node CLI
xai-node --help
```

## Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# Network configuration
export XAI_NETWORK=testnet
export XAI_RPC_PORT=12001
export XAI_P2P_PORT=12002

# Data directory
export XAI_DATA_DIR=~/.xai

# Logging
export XAI_LOG_LEVEL=INFO
```

### Configuration File

Create a configuration file at `~/.xai/config.json`:

```json
{
  "network": "testnet",
  "rpc_port": 12001,
  "p2p_port": 12002,
  "data_dir": "~/.xai",
  "log_level": "INFO"
}
```

## Platform-Specific Notes

### Linux

No additional steps required. Use the standard installation method.

### macOS

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.10+
brew install python@3.10

# Continue with standard installation
pip3 install -e .
```

### Windows

```powershell
# Install Python 3.10+ from python.org
# Then install XAI
pip install -e .

# Or use WSL2 for a Linux environment
wsl --install
```

## Troubleshooting

### Python Version Issues

If you have multiple Python versions:

```bash
# Use python3 explicitly
python3 -m pip install -e .

# Or create a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

### Permission Errors

If you encounter permission errors:

```bash
# Use --user flag
pip install --user -e .

# Or use a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### Dependency Conflicts

If you have dependency conflicts:

```bash
# Use constraints file for reproducible builds
pip install -c constraints.txt -e .
```

## Next Steps

- [Quick Start Guide](quick-start) - Create your first wallet and transaction
- [Developer Guide](../developers/overview) - Start building on XAI
- [API Reference](../api/rest-api) - Explore the API

## Getting Help

If you encounter issues:

- Check the [GitHub Issues](https://github.com/xai-blockchain/xai/issues)
- Join our [Discord community](https://discord.gg/xai-blockchain)
- Read the [FAQ](https://github.com/xai-blockchain/xai/wiki/FAQ)
