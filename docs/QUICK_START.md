# XAI Blockchain - Quick Start Guide

Get started with XAI blockchain in just 5 minutes! This guide will walk you through installation, wallet creation, and your first transaction.

---

## Prerequisites

- **Python 3.10 or higher**
- **2GB RAM minimum**
- **10GB+ disk space** for blockchain data
- **Internet connection** for testnet access

---

## Step 1: Installation (1 minute)

Clone the repository and install:

```bash
# Clone the repository
git clone https://github.com/your-org/xai.git
cd xai

# Install XAI blockchain
pip install -c constraints.txt -e ".[dev]"

# Optional: Enable QUIC network support
pip install -e ".[network]"

# Verify installation
python -m pytest --co -q
```

---

## Step 2: Create Your First Wallet (30 seconds)

```bash
# Generate a new wallet address
python src/xai/wallet/cli.py generate-address

# Output example:
# Address: TXAI1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
# Private Key: 5KYZdUEo39z3FPrtuX2QbbwGnNP5zTd7yyr2SC1j299sBCnWjss
# ⚠️  IMPORTANT: Save your private key securely!
```

**Security Warning:** Never share your private key with anyone. Store it in a secure location like a password manager.

---

## Step 3: Get Testnet Tokens (1 minute)

Get free testnet XAI tokens from the faucet - choose your preferred method:

### Method 1: CLI (Recommended)

```bash
# Request testnet tokens (replace with your address)
python src/xai/wallet/cli.py request-faucet --address TXAI_YOUR_ADDRESS

# Output:
# ✅ Testnet faucet claim successful! 100 XAI will be added to your address after the next block.
# Note: This is testnet XAI - it has no real value!
```

### Method 2: API Direct

```bash
curl -X POST http://localhost:12001/faucet/claim \
  -H "Content-Type: application/json" \
  -d '{"address": "TXAI_YOUR_ADDRESS"}'

# Response:
# {
#   "success": true,
#   "amount": 100.0,
#   "txid": "abc123...",
#   "message": "Testnet faucet claim successful! 100 XAI will be added to your address after the next block."
# }
```

### Method 3: Web UI

```bash
# Start the faucet web interface (Docker required)
cd docker/faucet
docker-compose up -d

# Open in browser: http://localhost:8086
# Enter your TXAI address and click "Request Tokens"
```

**Faucet Details:**
- **Amount:** 100 XAI per request
- **Rate Limit:** 1 request per hour per address
- **Delivery:** Next block (~2 minutes)
- **API Endpoint:** `POST http://localhost:12001/faucet/claim`
- **Web UI:** http://localhost:8086 (when Docker faucet is running)

**[→ Complete Faucet Documentation](user-guides/TESTNET_FAUCET.md)**

---

## Step 4: Check Your Balance (30 seconds)

Wait for the next block (~2 minutes), then check your balance:

```bash
# Check wallet balance
python src/xai/wallet/cli.py balance --address TXAI_YOUR_ADDRESS

# Output:
# Balance: 100.00000000 XAI
```

---

## Step 5: Send Your First Transaction (1 minute)

Send XAI to another address:

```bash
# Send 10 XAI to a recipient
python src/xai/wallet/cli.py send \
  --from TXAI_YOUR_ADDRESS \
  --to TXAI_RECIPIENT_ADDRESS \
  --amount 10.0

# The CLI will:
# 1. Display the transaction hash for confirmation
# 2. Prompt for your private key (never sent to network)
# 3. Sign and broadcast the transaction
```

**Transaction Details:**
- **Block Time:** ~2 minutes
- **Confirmation Time:** 1 block (2 minutes) for small amounts, 6 blocks (12 minutes) for large amounts

---

## Step 6: View in Explorer (30 seconds)

View your transaction in the blockchain explorer:

```bash
# Start the block explorer (separate terminal)
python src/xai/explorer.py

# Open in browser
# http://localhost:12080
```

**Explorer Features:**
- View blocks and transactions
- Check address balances
- Search by address, transaction ID, or block number
- Real-time updates via WebSocket

---

## Step 7: Start a Node (Optional)

Run your own XAI node to participate in the network:

```bash
# Set testnet environment
export XAI_NETWORK=testnet

# Start the node
python -m xai.core.node

# Node will start on:
# - RPC Port: 12001
# - P2P Port: 12002
# - WebSocket: 12003
```

**Start Mining:**

```bash
# Start mining with your wallet address
export MINER_ADDRESS=TXAI_YOUR_ADDRESS
python -m xai.core.node --miner $MINER_ADDRESS
```

---

## Network Information

### Testnet Configuration

| Parameter | Value |
|-----------|-------|
| Network ID | 0xABCD |
| RPC Port | 12001 |
| P2P Port | 12002 |
| WebSocket Port | 12003 |
| Explorer Port | 12080 |
| Address Prefix | TXAI |
| Block Time | 2 minutes |
| Faucet Amount | 100 XAI |
| Max Supply | 121,000,000 XAI |

### Testnet Endpoints

- **RPC:** `http://localhost:12001`
- **Faucet:** `http://localhost:12001/faucet/claim`
- **Explorer:** `http://localhost:12080`
- **WebSocket:** `ws://localhost:12003`
- **Grafana:** `http://localhost:12030` (Docker setup only)
- **Prometheus:** `http://localhost:12090` (Docker setup only)

---

## Common Commands

### Wallet Operations

```bash
# Generate address
python src/xai/wallet/cli.py generate-address

# Check balance
python src/xai/wallet/cli.py balance --address TXAI_ADDRESS

# Send transaction
python src/xai/wallet/cli.py send --from TXAI_FROM --to TXAI_TO --amount 10.0

# Export private key
python src/xai/wallet/cli.py export-key --address TXAI_ADDRESS

# Request faucet
python src/xai/wallet/cli.py request-faucet --address TXAI_ADDRESS
```

### Node Operations

```bash
# Start node
python -m xai.core.node

# Start mining
python -m xai.core.node --miner TXAI_ADDRESS

# Check node status
curl http://localhost:12001/health

# View peers
curl http://localhost:12001/peers
```

---

## Troubleshooting

### "Command not found" error

Make sure you're in the xai directory and have activated your Python environment.

### "Faucet rate limit exceeded"

The faucet allows one claim per address per hour. Wait and try again.

### "Insufficient funds" error

Check your balance with `balance --address`. Ensure you have enough for both the amount and transaction fee.

### "Cannot connect to node"

Start the node first with `python -m xai.core.node`, then run your command in a separate terminal.

### Transaction not confirming

Wait for the next block (~2 minutes). XAI has a 2-minute block time.

---

## Next Steps

Now that you're set up, explore advanced features:

- **[Testnet Guide](user-guides/TESTNET_GUIDE.md)** - Comprehensive testnet information
- **[Light Client Guide](user-guides/LIGHT_CLIENT_GUIDE.md)** - Run a lightweight node
- **[Wallet Setup](user-guides/wallet-setup.md)** - Advanced wallet features (multi-sig, HD wallets)
- **[Mining Guide](user-guides/mining.md)** - Detailed mining instructions
- **[API Documentation](api/)** - Build applications on XAI
- **[CLI Guide](CLI_GUIDE.md)** - Complete CLI reference

---

## Getting Help

### Documentation

- **[FAQ](user-guides/faq.md)** - Frequently asked questions
- **[Troubleshooting](user-guides/troubleshooting.md)** - Common issues and solutions
- **[Whitepaper](../WHITEPAPER.md)** - Technical specification

### Support

- **Issues:** Report bugs on GitHub
- **Documentation:** See `docs/` directory
- **Security:** See [SECURITY.md](../SECURITY.md) for vulnerability reporting

---

**Congratulations!** You're now ready to use XAI blockchain. Welcome to the network!

---

*Last Updated: January 2025 | XAI Version: 0.2.0*
