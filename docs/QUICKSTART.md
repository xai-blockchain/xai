# XAI Blockchain - Quick Start Guide

**Get started with XAI in 5 minutes!** This guide covers installation, wallet creation, getting testnet tokens, and sending your first transaction.

---

## What is XAI?

XAI is a proof-of-work blockchain with AI governance, atomic swaps, and comprehensive wallet support. This guide gets you running quickly on testnet.

**Choose your path:**
- **Desktop/Server User** → Follow Steps 1-6 below
- **Mobile Developer** → See [Mobile Quick Start](user-guides/mobile_quickstart.md)
- **IoT/Raspberry Pi** → See [Lightweight Node Guide](user-guides/lightweight_node_guide.md)
- **Light Client** → See [Light Client Mode](user-guides/light_client_mode.md)

---

## Installation Options

Pick the method that works best for you:

### Option A: One-Line Install (Recommended)

**Linux/macOS:**
```bash
curl -sSL https://install.xai.network | bash
```

**Windows PowerShell:**
```powershell
iwr -useb https://install.xai.network/install.ps1 | iex
```

### Option B: From Source (Developers)

```bash
git clone https://github.com/your-org/xai.git
cd xai
pip install -c constraints.txt -e ".[dev]"
```

### Option C: Docker (Isolated)

```bash
docker pull xai/node:latest
docker run -d -p 18545:18545 -p 18546:18546 xai/node:testnet
```

### Option D: Package Managers

**Debian/Ubuntu:**
```bash
wget https://releases.xai.network/xai_latest_amd64.deb
sudo dpkg -i xai_latest_amd64.deb
```

**Homebrew (macOS):**
```bash
brew tap xai-blockchain/xai
brew install xai
```

**See [installers/README.md](../installers/README.md) for all installation methods.**

---

## Step 1: Create Your First Wallet (30 seconds)

```bash
# Generate a new wallet address
python src/xai/wallet/cli.py generate-address

# Output:
# ✅ Wallet created successfully!
# Address: TXAI1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
# Private Key: 5KYZdUEo39z3FPrtuX2QbbwGnNP5zTd7yyr2SC1j299sBCnWjss
# ⚠️  CRITICAL: Save your private key securely! It cannot be recovered if lost.
```

**Security Alert:**
- Your private key controls your funds
- Never share it with anyone
- Store it in a password manager or encrypted file
- Write it down and keep it somewhere safe

---

## Step 2: Get Free Testnet Tokens (1 minute)

**Official Testnet Faucet:** https://faucet.xai.network

### Method A: Web UI (Easiest)
1. Visit https://faucet.xai.network
2. Enter your TXAI address
3. Complete CAPTCHA
4. Receive 100 XAI in ~2 minutes

### Method B: Command Line
```bash
python src/xai/wallet/cli.py request-faucet --address TXAI_YOUR_ADDRESS

# Output:
# ✅ Faucet request successful!
# 100 XAI will be delivered in the next block (~2 minutes)
# Note: This is testnet XAI with no real value
```

### Method C: Direct API Call
```bash
curl -X POST https://faucet.xai.network/claim \
  -H "Content-Type: application/json" \
  -d '{"address": "TXAI_YOUR_ADDRESS"}'
```

**Faucet Details:**
- **Amount:** 100 XAI per request
- **Rate Limit:** 1 request per address per hour
- **Delivery Time:** Next block (~2 minutes)
- **Testnet Only:** These tokens have no real value

**Need more tokens?** Check the faucet URL in the testnet output or wait 24 hours for automatic refill

---

## Step 3: Check Your Balance (30 seconds)

Wait ~2 minutes for the next block, then check:

```bash
python src/xai/wallet/cli.py balance --address TXAI_YOUR_ADDRESS

# Output:
# Balance: 100.00000000 XAI
# Pending: 0.00000000 XAI
```

**Via API:**
```bash
curl http://localhost:12001/account/TXAI_YOUR_ADDRESS
```

---

## Step 4: Send Your First Transaction (1 minute)

```bash
python src/xai/wallet/cli.py send \
  --from TXAI_YOUR_ADDRESS \
  --to TXAI_RECIPIENT_ADDRESS \
  --amount 10.0

# The CLI will:
# 1. Display transaction hash for review
# 2. Ask you to confirm by typing hash prefix (security feature)
# 3. Prompt for your private key (never sent to network)
# 4. Sign transaction locally
# 5. Broadcast to network
#
# Output:
# Transaction Hash: 0xabc123...
# ✅ Transaction broadcast successfully!
# Confirmations: Pending (~2 minutes)
```

**Transaction Confirmations:**
- **Small Amounts (<100 XAI):** 1 confirmation (2 minutes)
- **Medium Amounts (100-1000 XAI):** 3 confirmations (6 minutes)
- **Large Amounts (>1000 XAI):** 6 confirmations (12 minutes)

---

## Step 5: View in Block Explorer (30 seconds)

### Web Explorer (Recommended)
**Testnet Explorer:** https://explorer.xai.network/testnet

Search for:
- Your address
- Transaction hash
- Block number

### Local Explorer (Optional)
```bash
# Start local explorer
python src/xai/explorer.py

# Open in browser
# http://localhost:12080
```

**Explorer Features:**
- Real-time block updates
- Transaction details
- Address balance lookup
- Network statistics
- Mempool viewer

---

## Step 6: Run Your Own Node (Optional, 2 minutes)

Join the network as a full participant:

```bash
# Set environment
export XAI_NETWORK=testnet

# Start node
python -m xai.core.node

# Node starts on:
# - P2P Port: 18545
# - RPC Port: 18546
#
# Output:
# [INFO] XAI Node starting...
# [INFO] Network: testnet
# [INFO] Syncing blockchain (0 / 22341 blocks)...
```

**Start Mining (Optional):**
```bash
export MINER_ADDRESS=TXAI_YOUR_ADDRESS
python -m xai.core.node --miner $MINER_ADDRESS

# Mining rewards: 50 XAI per block
# Block time: ~2 minutes
# Difficulty: Adjusts every 2016 blocks
```

---

## Configuration

### Environment Variables

```bash
# Network selection
export XAI_NETWORK=testnet           # or 'mainnet'

# Ports
export XAI_PORT=18545                # P2P port (8545 for mainnet)
export XAI_RPC_PORT=18546            # RPC port (8546 for mainnet)

# Node behavior
export XAI_LOG_LEVEL=INFO            # DEBUG, INFO, WARNING, ERROR
export XAI_DATA_DIR=~/.xai           # Blockchain data directory
export MINER_ADDRESS=TXAI_...        # Mining rewards address

# Performance
export XAI_CACHE_TTL=60              # Response cache TTL (seconds)
export XAI_PARTIAL_SYNC_ENABLED=1    # Enable checkpoint sync
```

### Network Endpoints

**Testnet:**
- RPC: `http://localhost:12001` or `https://testnet-rpc.xai.network`
- WebSocket: `ws://localhost:12003`
- Faucet: `https://faucet.xai.network`
- Explorer: `https://explorer.xai.network/testnet`

**Mainnet:**
- RPC: `http://localhost:12001` or `https://rpc.xai.network`
- WebSocket: `ws://localhost:12003`
- Explorer: `https://explorer.xai.network`

---

## Common Commands Cheat Sheet

### Wallet Operations
```bash
# Generate new wallet
python src/xai/wallet/cli.py generate-address

# Check balance
python src/xai/wallet/cli.py balance --address TXAI_ADDRESS

# Send transaction
python src/xai/wallet/cli.py send --from TXAI_FROM --to TXAI_TO --amount 10.0

# Export private key (SECURE THIS!)
python src/xai/wallet/cli.py export-key --address TXAI_ADDRESS

# Import wallet
python src/xai/wallet/cli.py import-key --private-key YOUR_PRIVATE_KEY

# Request testnet tokens
python src/xai/wallet/cli.py request-faucet --address TXAI_ADDRESS
```

### Node Operations
```bash
# Start full node
python -m xai.core.node

# Start with mining
python -m xai.core.node --miner TXAI_ADDRESS

# Check node health
curl http://localhost:12001/health

# View connected peers
curl http://localhost:12001/peers

# Get blockchain info
curl http://localhost:12001/blockchain/stats
```

### Query Blockchain
```bash
# Get block by number
curl http://localhost:12001/block/12345

# Get transaction
curl http://localhost:12001/transaction/TX_HASH

# Get address balance
curl http://localhost:12001/account/TXAI_ADDRESS
```

---

## Troubleshooting

### Installation Issues

**"Command not found"**
- Make sure you're in the xai directory
- Activate virtual environment if using one: `source venv/bin/activate`
- Check Python version: `python --version` (need 3.10+)

**"Permission denied"**
- Use `sudo` for system-wide installation: `sudo pip install -e .`
- Or install in user directory: `pip install --user -e .`

### Wallet Issues

**"Faucet rate limit exceeded"**
- Faucet allows 1 claim per address per hour
- Wait 60 minutes and try again
- Or create a new address for testing

**"Insufficient funds"**
- Check balance: `python src/xai/wallet/cli.py balance --address TXAI_ADDRESS`
- Ensure you have enough for amount + fee (typically 0.001 XAI)
- Request more from faucet if needed

### Node Issues

**"Cannot connect to node"**
- Make sure node is running: `python -m xai.core.node`
- Check correct port (18546 testnet, 8546 mainnet)
- Verify firewall allows connections

**"Transaction not confirming"**
- XAI has a 2-minute block time - be patient
- Check mempool: `curl http://localhost:12001/mempool`
- Verify transaction was broadcast: `curl http://localhost:12001/transaction/TX_HASH`

**"Sync taking too long"**
- Enable checkpoint sync: `export XAI_PARTIAL_SYNC_ENABLED=1`
- Use a light client for faster startup
- Check your internet connection

---

## Next Steps

Now that you're set up, explore XAI's advanced features:

### For Users
- **[Testnet Guide](user-guides/TESTNET_GUIDE.md)** - Complete testnet walkthrough
- **[Wallet Setup](user-guides/wallet-setup.md)** - Multi-sig, HD wallets, advanced features
- **[Mining Guide](user-guides/mining.md)** - Detailed mining instructions
- **[Light Client Guide](user-guides/LIGHT_CLIENT_GUIDE.md)** - Run lightweight node

### For Developers
- **[API Documentation](api/rest-api.md)** - Build dApps on XAI
- **[TypeScript SDK](api/sdk.md)** - JavaScript/TypeScript integration
- **[Python SDK](../src/xai/sdk/python/README.md)** - Python development
- **[Mobile Quick Start](user-guides/mobile_quickstart.md)** - React Native/Flutter SDKs

### For Mobile Users
- **[Mobile Quick Start](user-guides/mobile_quickstart.md)** - React Native and Flutter SDKs
- **[Biometric Auth](../src/xai/sdk/biometric/QUICKSTART.md)** - Secure mobile wallets
- **[Push Notifications](PUSH_NOTIFICATIONS.md)** - Real-time transaction alerts

### For IoT/Edge Devices
- **[Lightweight Node Guide](user-guides/lightweight_node_guide.md)** - Raspberry Pi, IoT
- **[Light Client Mode](user-guides/light_client_mode.md)** - SPV verification

### Advanced Topics
- **[Atomic Swaps](advanced/atomic-swaps.md)** - Cross-chain trading
- **[Smart Contracts](architecture/evm_interpreter.md)** - Deploy contracts
- **[Governance](user-guides/staking.md)** - Participate in governance

---

## Getting Help

### Documentation
- **Quick Reference:** [CLI Guide](CLI_GUIDE.md)
- **FAQ:** [user-guides/faq.md](user-guides/faq.md)
- **Troubleshooting:** [user-guides/troubleshooting.md](user-guides/troubleshooting.md)
- **Technical Specs:** [../WHITEPAPER.md](../WHITEPAPER.md)

### Community & Support (Coming Soon)
Official community channels are being established. For now:
- **GitHub Issues:** File technical issues and bug reports
- **Documentation:** Browse the docs/ directory
- **Security Issues:** See [SECURITY.md](../SECURITY.md)

### Video Tutorials (Coming Soon)
Video tutorials are planned for:
- Getting Started walkthrough
- Mining setup guide
- Mobile wallet usage

---

## Network Information

### Testnet Parameters

| Parameter | Value |
|-----------|-------|
| Network ID | 0xABCD |
| Address Prefix | TXAI |
| P2P Port | 18545 |
| RPC Port | 18546 |
| Block Time | 2 minutes |
| Block Reward | 50 XAI |
| Difficulty Adjustment | Every 2016 blocks |
| Max Supply | 121,000,000 XAI |
| Halving Interval | Every 210,000 blocks |

### Mainnet Parameters (Future)

| Parameter | Value |
|-----------|-------|
| Network ID | 0x5841 |
| Address Prefix | XAI |
| P2P Port | 8545 |
| RPC Port | 8546 |
| Block Time | 2 minutes |
| Block Reward | 50 XAI (halves) |
| Max Supply | 121,000,000 XAI |

---

## What's Next?

**You now have:**
- ✅ XAI blockchain installed
- ✅ A wallet with testnet tokens
- ✅ Sent your first transaction
- ✅ Knowledge of basic operations

**Continue your journey:**
1. Try [mining](user-guides/mining.md) to earn rewards
2. Build a [dApp](api/rest-api.md) on XAI
3. Run a [light client](user-guides/light_client_mode.md) on Raspberry Pi
4. Explore advanced features in the documentation
5. Contribute to the project on GitHub

**Welcome to XAI blockchain development!**

---

*Last Updated: January 2025 | XAI Version: 0.2.0*
