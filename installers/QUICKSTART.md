# XAI Blockchain - Quick Start Guide

Get XAI blockchain running in under 5 minutes.

## Choose Your Path

### 1. Docker (Fastest - 1 minute)

**One command to rule them all:**
```bash
curl -fsSL https://install.xai-blockchain.io/docker.sh | bash
```

**Or locally:**
```bash
./installers/docker-install.sh
```

That's it! XAI node is running.

**What just happened:**
- ✓ Pulled XAI Docker image
- ✓ Created persistent data volumes
- ✓ Started node in background
- ✓ Exposed RPC on port 18546

**Next steps:**
```bash
# Generate wallet
docker exec -it xai-node xai-wallet generate-address

# Check status
docker logs xai-node
```

---

### 2. Linux/macOS Script (2 minutes)

**One-liner:**
```bash
curl -fsSL https://install.xai-blockchain.io/install.sh | bash
```

**Or locally:**
```bash
./installers/install-xai.sh
```

**Restart your shell, then:**
```bash
# Generate wallet
xai-wallet generate-address

# Start node
xai-node --network testnet
```

---

### 3. Windows (3 minutes)

**PowerShell (as Administrator):**
```powershell
irm https://install.xai-blockchain.io/install.ps1 | iex
```

**Or locally:**
```powershell
.\installers\install-xai.ps1
```

**After installation:**
```powershell
# Restart PowerShell

# Generate wallet
xai-wallet generate-address

# Start node (use desktop shortcut or command line)
xai-node --network testnet
```

---

### 4. macOS Homebrew (3 minutes)

```bash
brew tap xai-blockchain/tap
brew install xai
brew services start xai
```

**Check status:**
```bash
brew services info xai
```

---

### 5. Ubuntu/Debian (2 minutes)

```bash
# Add repository
curl -fsSL https://packages.xai-blockchain.io/gpg | sudo apt-key add -
sudo add-apt-repository "deb https://packages.xai-blockchain.io/deb $(lsb_release -cs) main"

# Install
sudo apt update
sudo apt install xai-blockchain

# Start service
sudo systemctl start xai-node
```

---

### 6. CentOS/Fedora/RHEL (2 minutes)

```bash
# Add repository
sudo curl -fsSL https://packages.xai-blockchain.io/rpm/xai.repo \
  -o /etc/yum.repos.d/xai.repo

# Install
sudo dnf install xai-blockchain

# Start service
sudo systemctl start xai-node
```

---

## First Steps After Installation

### 1. Generate Your Wallet

```bash
xai-wallet generate-address
```

**Output:**
```
Address: XAI1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0
Private Key: ************************************************
```

**⚠️ IMPORTANT:** Save your private key securely! Never share it.

### 2. Get Test Coins (Testnet Faucet)

Request free testnet XAI tokens:

```bash
xai-wallet request-faucet --address YOUR_XAI_ADDRESS
```

**Faucet Details:**
- 100 XAI per request
- 1 hour cooldown
- Tokens arrive in ~2 minutes

**[→ Complete Faucet Guide](../docs/user-guides/TESTNET_FAUCET.md)**

### 3. Check Your Balance

```bash
xai-wallet balance --address YOUR_XAI_ADDRESS
```

### 4. Send a Transaction

```bash
xai-wallet send \
  --from YOUR_ADDRESS \
  --to RECIPIENT_ADDRESS \
  --amount 10.5
```

### 5. Start Mining (Optional)

```bash
xai-node --network testnet --mine YOUR_XAI_ADDRESS
```

---

## Verification Checklist

After installation, verify everything works:

- [ ] `xai --version` shows version number
- [ ] `xai-wallet generate-address` creates a wallet
- [ ] `xai-node --help` shows node options
- [ ] Node starts without errors
- [ ] RPC responds: `curl http://localhost:12001/health`

---

## Common Commands

### Node Management

```bash
# Start node (foreground)
xai-node --network testnet

# Start node (background - systemd)
sudo systemctl start xai-node
sudo systemctl status xai-node
sudo journalctl -u xai-node -f

# Start node (background - Docker)
docker start xai-node
docker logs -f xai-node
```

### Wallet Operations

```bash
# Generate address
xai-wallet generate-address

# Check balance
xai-wallet balance --address ADDR

# Send transaction
xai-wallet send --from ADDR --to ADDR --amount 10

# Export private key
xai-wallet export-key --address ADDR
```

### Network Status

```bash
# Get blockchain info
curl http://localhost:12001/info

# Get latest block
curl http://localhost:12001/block/latest

# Get transaction
curl http://localhost:12001/transaction/TX_HASH
```

---

## Configuration

### Environment Variables

```bash
export XAI_NETWORK=testnet        # or mainnet
export XAI_DATA_DIR=~/.xai        # data directory
export XAI_LOG_LEVEL=INFO         # log level
export XAI_RPC_PORT=18546         # RPC port
export MINER_ADDRESS=YOUR_ADDR    # mining address
```

### Configuration File

Edit `~/.xai/config/node.yaml`:

```yaml
network:
  name: testnet
  port: 18545
  rpc_port: 18546

logging:
  level: INFO

node:
  enable_mining: false
  max_peers: 50
```

---

## Troubleshooting

### Node won't start

```bash
# Check logs
tail -f ~/.xai/logs/node.log

# Or for systemd
sudo journalctl -u xai-node -f

# Or for Docker
docker logs xai-node
```

### Port already in use

```bash
# Find what's using the port
sudo lsof -i :18545

# Use different port
export XAI_RPC_PORT=18547
```

### Python version error

```bash
# Check Python version
python3 --version

# Must be 3.10 or higher
sudo apt install python3.12  # Ubuntu/Debian
brew install python@3.12      # macOS
```

---

## Network Ports

| Port | Purpose | Protocol |
|------|---------|----------|
| 18545 | P2P Network (testnet) | TCP |
| 18546 | RPC API (testnet) | HTTP |
| 19090 | Prometheus Metrics | HTTP |
| 8545 | P2P Network (mainnet) | TCP |
| 8546 | RPC API (mainnet) | HTTP |

**Firewall:**
```bash
# Ubuntu/Debian
sudo ufw allow 18545/tcp
sudo ufw allow 18546/tcp

# CentOS/Fedora
sudo firewall-cmd --permanent --add-port=18545/tcp
sudo firewall-cmd --permanent --add-port=18546/tcp
sudo firewall-cmd --reload
```

---

## Upgrading

### Docker
```bash
docker pull xai-blockchain/node:latest
docker stop xai-node
docker rm xai-node
./installers/docker-install.sh
```

### Homebrew
```bash
brew update
brew upgrade xai
brew services restart xai
```

### APT
```bash
sudo apt update
sudo apt upgrade xai-blockchain
sudo systemctl restart xai-node
```

### DNF
```bash
sudo dnf upgrade xai-blockchain
sudo systemctl restart xai-node
```

### pip
```bash
pip install --upgrade xai-blockchain
```

---

## Uninstalling

### Docker
```bash
docker stop xai-node
docker rm xai-node
docker rmi xai-blockchain/node:latest
rm -rf ~/.xai  # Remove data (optional)
```

### Homebrew
```bash
brew services stop xai
brew uninstall xai
rm -rf /usr/local/var/xai  # Remove data (optional)
```

### APT
```bash
sudo systemctl stop xai-node
sudo apt remove --purge xai-blockchain
sudo rm -rf /var/lib/xai  # Remove data (optional)
```

### DNF
```bash
sudo systemctl stop xai-node
sudo dnf remove xai-blockchain
sudo rm -rf /var/lib/xai  # Remove data (optional)
```

### pip
```bash
pip uninstall xai-blockchain
rm -rf ~/.xai  # Remove data (optional)
```

---

## Support

- **Documentation**: https://docs.xai-blockchain.io
- **Full Install Guide**: [INSTALL.md](INSTALL.md)
- **Issues**: https://github.com/xai-blockchain/xai/issues
- **Discord**: https://discord.gg/xai-blockchain

---

## Security Reminders

- ✓ Never share your private key
- ✓ Never share your seed phrase
- ✓ Always backup your wallet
- ✓ Use testnet for experimentation
- ✓ Secure your RPC endpoint
- ✓ Keep your node updated

---

**Ready to build on XAI?**

Check out the [Developer Guide](../docs/developer-guide.md) for APIs, smart contracts, and advanced features.
