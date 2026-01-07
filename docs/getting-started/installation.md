# Installation Guide

Multiple installation methods for XAI nodes.

## Prerequisites

- Ubuntu 22.04 LTS (recommended) or macOS
- Python 3.10 or higher
- Git

```bash
# Ubuntu
sudo apt update
sudo apt install -y python3 python3-venv python3-dev git build-essential

# macOS
brew install python@3.11 git
```

## Method 1: Virtual Environment (Recommended)

Best for most users. Isolates XAI dependencies.

```bash
# Clone repository
git clone https://github.com/xai-blockchain/xai.git
cd xai

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .

# Verify installation
xai-node --help
```

## Method 2: System-Wide Installation

For dedicated servers running only XAI.

```bash
# Clone repository
git clone https://github.com/xai-blockchain/xai.git
cd xai

# Install system-wide
sudo pip3 install -r requirements.txt
sudo pip3 install -e .

# Verify
xai-node --help
```

## Method 3: Docker

For containerized deployments.

```bash
# Clone repository
git clone https://github.com/xai-blockchain/xai.git
cd xai

# Build image
docker build -t xai-node -f docker/Dockerfile .

# Run container
docker run -d \
  --name xai-node \
  -p 8333:8333 \
  -p 8545:8545 \
  -p 8766:8766 \
  -v xai-data:/app/data \
  xai-node
```

Or use docker-compose:

```bash
cd docker
docker-compose up -d
```

## Method 4: From Source (Developers)

For contributors who need to modify the code.

```bash
# Clone with submodules
git clone --recursive https://github.com/xai-blockchain/xai.git
cd xai

# Create development environment
python3 -m venv venv
source venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

## Post-Installation

After installation, proceed to [Join Testnet](../node-operators/join-testnet.md) to connect your node to the network.

## Troubleshooting

### Python version too old

```bash
# Install Python 3.11 on Ubuntu
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
python3.11 -m venv venv
```

### Permission denied

```bash
# Use virtual environment instead of system-wide install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Build errors

```bash
# Install build dependencies
sudo apt install -y build-essential python3-dev libssl-dev libffi-dev
```
