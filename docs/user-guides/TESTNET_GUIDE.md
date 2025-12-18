# XAI Testnet Guide

Complete guide to joining and using the XAI testnet. Get free testnet tokens, experiment with features, and prepare for mainnet.

---

## Overview

The XAI testnet is a fully functional blockchain network for testing and development. All features available on mainnet are available on testnet, but testnet coins have **no real value**.

### Why Use Testnet?

- **Free Tokens:** Get free testnet XAI from the faucet
- **Safe Testing:** Experiment without risking real funds
- **Development:** Build and test applications before mainnet
- **Learning:** Understand blockchain operations in a forgiving environment
- **Beta Features:** Try new features before they go live on mainnet

---

## Testnet Network Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Network ID | `0xABCD` | Testnet identifier |
| Chain Name | `XAI Testnet` | Display name |
| P2P Port | `18545` | Node communication |
| RPC Port | `18546` | API access |
| Address Prefix | `TXAI` | Testnet addresses start with TXAI |
| Block Time | `2 minutes` | 120 seconds per block |
| Difficulty Adjustment | `Every 720 blocks` | ~1 day |
| Max Supply | `121,000,000 XAI` | Same as mainnet |
| Initial Block Reward | `12.0 XAI` | Per block |
| Halving Interval | `262,800 blocks` | ~1 year |

---

## Connecting to Testnet

### Quick Start

```bash
# Set testnet environment
export XAI_NETWORK=testnet
export XAI_PORT=18545
export XAI_RPC_PORT=18546

# Start testnet node
python -m xai.core.node
```

### Configuration File

Create `~/.xai/testnet.yaml`:

```yaml
# XAI Testnet Configuration
network:
  type: testnet
  network_id: 0xABCD
  port: 18545
  rpc_port: 18546
  address_prefix: "TXAI"

# Bootstrap peers
peers:
  bootstrap:
    - "testnet-seed1.xai.io:18545"
    - "testnet-seed2.xai.io:18545"
    - "testnet-seed3.xai.io:18545"
  max_peers: 32
  min_peers: 4

# API settings
api:
  enabled: true
  host: "0.0.0.0"
  port: 18546
  cors_origins:
    - "http://localhost:5000"
    - "http://localhost:3000"

# Mining settings
mining:
  enabled: false
  address: ""  # Set your TXAI address
  threads: 1

# Data directory
data_dir: "~/.xai/testnet"
```

### Use Configuration

```bash
python -m xai.core.node --config ~/.xai/testnet.yaml
```

---

## Testnet Faucet

Get free testnet XAI tokens for development and testing.

### Faucet Details

- **Amount:** 100 XAI per request
- **Rate Limit:** 1 request per address per hour
- **Rate Limit (IP):** 10 requests per IP per hour
- **Requirements:** Valid TXAI address
- **Delivery Time:** Next block (~2 minutes)

### Using the Faucet (CLI)

```bash
# Request testnet tokens
python src/xai/wallet/cli.py request-faucet --address TXAI_YOUR_ADDRESS

# Output:
# ✅ Testnet faucet claim successful!
# 100 XAI will be added to your address after the next block.
# Note: This is testnet XAI - it has no real value!
```

### Using the Faucet (API)

```bash
# POST request to faucet endpoint
curl -X POST http://localhost:18545/faucet/claim \
  -H "Content-Type: application/json" \
  -d '{
    "address": "TXAI_YOUR_ADDRESS"
  }'

# Response:
# {
#   "success": true,
#   "amount": 100.0,
#   "txid": "abc123...",
#   "message": "Testnet faucet claim successful! 100 XAI will be added to your address after the next block.",
#   "note": "This is testnet XAI - it has no real value!"
# }
```

### Using the Faucet (Web UI)

**Coming Soon:** Web-based faucet interface at `https://testnet-faucet.xai.io`

Features will include:
- Simple address input form
- CAPTCHA verification
- Real-time balance updates
- Transaction status tracking

### Faucet Rate Limiting

If you exceed the rate limit:

```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "code": "rate_limited",
  "retry_after": 3600,
  "message": "You can request testnet tokens once per hour. Please try again in 58 minutes."
}
```

### Faucet Troubleshooting

**"Invalid address for this network"**
- Ensure your address starts with `TXAI` (testnet prefix)
- Check for typos in the address

**"Rate limit exceeded"**
- Wait one hour between requests to the same address
- Use a different address if you need more tokens immediately

**"Faucet is disabled"**
- The faucet may be temporarily disabled for maintenance
- Check testnet status at `/health` endpoint

---

## Explorer Access

View testnet blocks, transactions, and addresses in real-time.

### Local Explorer

```bash
# Start the block explorer
python src/xai/explorer.py

# Access in browser
# http://localhost:5000
```

### Explorer Features

- **Block Browser:** View all blocks with details
- **Transaction Search:** Search by transaction ID
- **Address Lookup:** Check any address balance and history
- **Real-time Updates:** WebSocket for live block/transaction notifications
- **Network Stats:** Current height, difficulty, hash rate
- **Mempool Viewer:** See pending transactions

### Explorer API

```bash
# Get latest block
curl http://localhost:5000/api/block/latest

# Get specific block
curl http://localhost:5000/api/block/12345

# Get transaction
curl http://localhost:5000/api/transaction/TX_HASH

# Get address balance
curl http://localhost:5000/api/address/TXAI_ADDRESS

# Get network stats
curl http://localhost:5000/api/stats
```

### Public Explorer (Coming Soon)

**URL:** `https://testnet-explorer.xai.io`

Features:
- Public testnet explorer
- No installation required
- Mobile-friendly interface
- Advanced search capabilities

---

## Testnet RPC Endpoints

### Node API Endpoints

```bash
# Health check
GET http://localhost:18546/health

# Get blockchain stats
GET http://localhost:18546/stats

# Get latest block
GET http://localhost:18546/block/latest

# Get specific block
GET http://localhost:18546/block/{height}

# Get transaction
GET http://localhost:18546/transaction/{txid}

# Get address balance
GET http://localhost:18546/account/{address}

# Get address nonce
GET http://localhost:18546/address/{address}/nonce

# Submit transaction
POST http://localhost:18546/send
Content-Type: application/json
{
  "from": "TXAI_FROM",
  "to": "TXAI_TO",
  "amount": 10.0,
  "signature": "...",
  "timestamp": 1704067200
}

# Get mempool stats
GET http://localhost:18546/mempool/stats

# Get peer list
GET http://localhost:18546/peers

# Claim faucet
POST http://localhost:18546/faucet/claim
Content-Type: application/json
{
  "address": "TXAI_ADDRESS"
}
```

### WebSocket API

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:18546/ws');

// Subscribe to new blocks
ws.send(JSON.stringify({
  action: 'subscribe',
  channel: 'blocks'
}));

// Subscribe to new transactions
ws.send(JSON.stringify({
  action: 'subscribe',
  channel: 'transactions'
}));

// Receive updates
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('New block:', data);
};
```

---

## Mining on Testnet

Run a testnet miner to help secure the network and earn testnet rewards.

### Start Mining

```bash
# Generate mining address first
python src/xai/wallet/cli.py generate-address

# Set mining address
export MINER_ADDRESS=TXAI_YOUR_ADDRESS

# Start mining
python -m xai.core.node --miner $MINER_ADDRESS

# Output:
# [INFO] Starting XAI node on testnet
# [INFO] Mining enabled for address: TXAI_YOUR_ADDRESS
# [INFO] Mining thread started (1 thread)
# [INFO] Block mined! Height: 12346, Reward: 12.0 XAI
```

### Mining Configuration

```yaml
# In testnet.yaml
mining:
  enabled: true
  address: "TXAI_YOUR_MINING_ADDRESS"
  threads: 2  # Number of CPU threads to use
  min_transaction_fee: 0.0001
```

### Mining Rewards

| Block Range | Reward | Notes |
|-------------|--------|-------|
| 0 - 262,800 | 12.0 XAI | Year 1 |
| 262,801 - 525,600 | 6.0 XAI | Year 2 (first halving) |
| 525,601 - 788,400 | 3.0 XAI | Year 3 (second halving) |
| ... | ... | Halves every 262,800 blocks |

**Note:** Testnet rewards have no real value. Mining is for testing purposes only.

---

## Common Testnet Issues

### Node won't sync

**Symptoms:** Node stuck at low block height, no peers connecting

**Solutions:**
1. Check bootstrap peers in config
2. Ensure ports 18545/18546 are not blocked
3. Verify internet connection
4. Try manual peer addition:
   ```bash
   curl -X POST http://localhost:18546/peers/add \
     -H "Content-Type: application/json" \
     -d '{"peer": "testnet-seed1.xai.io:18545"}'
   ```

### Faucet not working

**Symptoms:** Faucet returns error or tokens not received

**Solutions:**
1. Verify address starts with `TXAI`
2. Check rate limit (1 hour between requests)
3. Wait for next block (~2 minutes) for tokens to arrive
4. Check node is synced: `curl http://localhost:18546/stats`

### Transaction not confirming

**Symptoms:** Transaction stuck in mempool

**Solutions:**
1. Wait for next block (~2 minutes)
2. Check mempool status: `curl http://localhost:18546/mempool/stats`
3. Verify transaction fee is sufficient (minimum 0.0001 XAI)
4. Check nonce is correct: `curl http://localhost:18546/address/TXAI_ADDRESS/nonce`

### Mining no blocks

**Symptoms:** Mining runs but no blocks found

**Solutions:**
1. Testnet mining is competitive - blocks may take time
2. Check node is synced to latest height
3. Verify mining address is set correctly
4. Increase mining threads (if CPU allows)
5. Be patient - testnet difficulty adjusts based on network hash rate

### Explorer shows old data

**Symptoms:** Explorer displays stale information

**Solutions:**
1. Refresh the browser page
2. Check WebSocket connection is active
3. Restart explorer: `python src/xai/explorer.py`
4. Clear browser cache

---

## Testnet Reset Policy

The testnet may be reset periodically for the following reasons:

- **Breaking Changes:** Protocol upgrades requiring clean start
- **Testing Scenarios:** Large-scale network testing
- **Security Issues:** Critical bugs requiring fresh chain
- **Performance Testing:** Benchmark new optimizations

**Notice Period:** 7 days minimum notice before planned resets

**Communication:** Resets announced via:
- GitHub repository announcements
- Developer mailing list
- Community forums

**Faucet:** Faucet will be available immediately after resets

---

## Best Practices

### Development

1. **Test Thoroughly:** Use testnet extensively before mainnet deployment
2. **Reset Awareness:** Design apps to handle testnet resets gracefully
3. **Faucet Consideration:** Don't abuse the faucet - share with other developers
4. **Report Bugs:** Help improve XAI by reporting testnet issues

### Security

1. **Different Keys:** Never use mainnet private keys on testnet
2. **No Real Value:** Remember testnet coins have no value
3. **Public Network:** Testnet is public - don't send sensitive data
4. **Testing Only:** Don't rely on testnet for production workloads

### Network Participation

1. **Run Nodes:** Help secure testnet by running validator nodes
2. **Mine Blocks:** Participate in mining to maintain block production
3. **Test Features:** Try new features and provide feedback
4. **Join Community:** Engage with other testnet users

---

## Testnet Monitoring

### Check Network Health

```bash
# Node status
curl http://localhost:18546/health

# Network stats
curl http://localhost:18546/stats

# Response:
# {
#   "height": 22341,
#   "difficulty": 123456.78,
#   "hash_rate": "45.2 MH/s",
#   "peers": 24,
#   "mempool_size": 42,
#   "sync_status": "synced"
# }
```

### Monitor Your Node

```bash
# View logs
tail -f ~/.xai/testnet/logs/node.log

# Check peer connections
curl http://localhost:18546/peers?verbose=true

# Monitor mining
curl http://localhost:18546/mining/stats
```

---

## Advanced Testnet Features

### Checkpoint Sync

Enable fast sync using checkpoints:

```bash
export XAI_PARTIAL_SYNC_ENABLED=1
export XAI_P2P_PARTIAL_SYNC_ENABLED=1
export XAI_P2P_PARTIAL_SYNC_MIN_DELTA=100
```

See [Partial Sync Documentation](../deployment/partial-sync.md) for details.

### Light Client Mode

Run a light client for minimal resource usage:

```bash
export XAI_NODE_MODE=light_client
python -m xai.core.light_client
```

See [Light Client Guide](LIGHT_CLIENT_GUIDE.md) for details.

---

## Getting Help

### Documentation

- **[Quick Start Guide](../QUICK_START.md)** - 5-minute setup
- **[CLI Guide](../CLI_GUIDE.md)** - Complete CLI reference
- **[API Documentation](../api/)** - Full API reference
- **[Troubleshooting](troubleshooting.md)** - Common issues

### Support Channels

- **GitHub Issues:** Report bugs and request features
- **Developer Forum:** Ask questions and share knowledge
- **Discord:** Real-time community chat (coming soon)

---

## Next Steps

Ready to go deeper?

- **[Light Client Guide](LIGHT_CLIENT_GUIDE.md)** - Run a lightweight node
- **[Mining Guide](mining.md)** - Detailed mining instructions
- **[Wallet Setup](wallet-setup.md)** - Advanced wallet features
- **[Developer Onboarding](developer_onboarding.md)** - Build on XAI
- **[API Reference](../api/)** - Integrate XAI into your apps

---

**Welcome to XAI Testnet!** Start building and testing today.

---

*Last Updated: January 2025 | XAI Version: 0.2.0 | Testnet Active*
