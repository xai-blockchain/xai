# XAI Blockchain Testnet

**Status:** 🟢 **LIVE** - Multi-region deployment across AWS
**Launch Date:** November 2025
**Network ID:** `0xABCD` (43981)
**Consensus:** Proof-of-Work (SHA-256)
**Block Time:** ~120 seconds target

---

## Quick Connect

### Network Endpoints

| Service | URL | Description |
|---------|-----|-------------|
| **RPC API** | `http://xai-api-lb-835033547.us-east-1.elb.amazonaws.com` | Primary RPC endpoint |
| **Block Explorer** | `http://xai-api-lb-835033547.us-east-1.elb.amazonaws.com/explorer` | View blocks and transactions |
| **Faucet** | `http://xai-api-lb-835033547.us-east-1.elb.amazonaws.com/faucet` | Request test XAI tokens |
| **Metrics** | `http://xai-api-lb-835033547.us-east-1.elb.amazonaws.com/metrics` | Network statistics |

### Network Parameters

```json
{
  "chainId": "0xABCD",
  "networkId": 43981,
  "consensus": "proof-of-work",
  "hashAlgorithm": "SHA-256",
  "blockTime": 120,
  "difficulty": "dynamic",
  "totalSupply": "84000000 XAI",
  "blockReward": "50 XAI",
  "halvingInterval": 210000
}
```

---

## Getting Started

### 1. Get Test Tokens

Request 100 test XAI from the faucet:

```bash
# Via API
curl -X POST http://xai-api-lb-835033547.us-east-1.elb.amazonaws.com/faucet \
  -H "Content-Type: application/json" \
  -d '{"address": "YOUR_XAI_ADDRESS", "amount": 100}'

# Or visit the web faucet
open http://xai-api-lb-835033547.us-east-1.elb.amazonaws.com/faucet
```

CLI alternative:

```bash
xai-wallet request-faucet --address YOUR_XAI_ADDRESS
```

**Faucet Limits:**
- 100 XAI per address per 24 hours
- Maximum 1000 XAI per IP per day
- No authentication required

### 2. Connect Your Node

```bash
# Clone the repository
git clone https://github.com/YOUR_ORG/xai-blockchain.git
cd xai-blockchain

# Set testnet configuration
export XAI_NETWORK=testnet
export XAI_BOOTSTRAP_NODES="xai-api-lb-835033547.us-east-1.elb.amazonaws.com:8333"

# Start your node
xai node run --miner $MINER_ADDRESS --peer http://xai-api-lb-835033547.us-east-1.elb.amazonaws.com:18545
```

Check health or trigger resync with:

```bash
xai node status --base-url http://localhost:18545
xai node sync --base-url http://localhost:18545
```

### 3. Create a Wallet

```python
from xai.core.wallet import Wallet

# Generate new wallet
wallet = Wallet()
address = wallet.get_address()
print(f"Your testnet address: {address}")

# Or use CLI

xai-wallet generate-address
```

### 4. Send Transactions

```bash
# Using the API
curl -X POST http://xai-api-lb-835033547.us-east-1.elb.amazonaws.com/api/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "sender": "YOUR_ADDRESS",
    "recipient": "RECIPIENT_ADDRESS",
    "amount": 10.0,
    "private_key": "YOUR_PRIVATE_KEY"
  }'
```

---

## Network Infrastructure

### Deployed Nodes

The testnet currently runs on:
- **2 validator nodes** in US East (N. Virginia)
- **1 validator node** in EU West (Ireland)
- **1 validator node** in Asia Pacific (Singapore)

All nodes are:
- Running on **AWS t3.small** instances (2 vCPU, 2GB RAM)
- Using **50GB encrypted EBS volumes**
- Load-balanced via AWS Application Load Balancer
- Monitored with CloudWatch and Prometheus

### Network Topology

```
        ┌─────────────────────────────────┐
        │   Application Load Balancer     │
        │  (Primary API Endpoint)         │
        └────────────┬────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
   ┌────▼────┐             ┌────▼────┐
   │  Node 1 │◄───P2P───► │  Node 2 │
   │us-east-1│             │us-east-1│
   └────┬────┘             └────┬────┘
        │                       │
        │         P2P           │
        │      Network          │
        │                       │
   ┌────▼────┐             ┌───▼─────┐
   │  Node 3 │◄───────────►│ Node 4  │
   │eu-west-1│             │ap-se-1  │
   └─────────┘             └─────────┘
```

---

## What's Being Tested

### Phase 1: Core Functionality (Current)
- ✅ Block production and propagation
- ✅ Transaction processing
- ✅ Wallet creation and management
- ✅ Mining and difficulty adjustment
- ✅ P2P network synchronization
- ✅ API endpoint stability

### Phase 2: Advanced Features (Next)
- 🔄 AI governance proposals
- 🔄 Multi-signature transactions
- 🔄 Cross-chain atomic swaps
- 🔄 Smart contract execution
- 🔄 Time-locked transactions

### Phase 3: Performance & Security
- ⏳ Load testing (target: 100 TPS)
- ⏳ Security audit
- ⏳ Network partition recovery
- ⏳ Chain reorganization handling

---

## Known Issues & Limitations

### Current Known Issues

1. **Bootstrap Time**: Initial node sync may take 10-15 minutes
2. **User Data Script**: GitHub clone URL needs to be updated with actual repository
3. **Health Endpoint**: Nodes may not have `/health` endpoint implemented yet
4. **Block Explorer**: May not be fully functional until nodes complete bootstrap

### Limitations

- **This is a testnet**: Expect resets, downtime, and data loss
- **No SLA**: Network uptime not guaranteed
- **Rate limits**: API has rate limiting enabled
- **Test tokens only**: XAI tokens have no monetary value
- **Subject to change**: Network parameters may be adjusted

---

## API Reference

### Get Network Status

```bash
GET /api/blockchain/status
```

**Response:**
```json
{
  "network": "testnet",
  "chain_height": 12345,
  "total_nodes": 4,
  "difficulty": "0x1234567890abcdef",
  "hash_rate": "1.2 TH/s",
  "avg_block_time": 118.5
}
```

### Get Block by Height

```bash
GET /api/blocks/{height}
```

### Get Latest Block

```bash
GET /api/blocks/latest
```

### Get Transaction

```bash
GET /api/transactions/{tx_hash}
```

### Submit Transaction

```bash
POST /api/transactions
Content-Type: application/json

{
  "sender": "XAI_ADDRESS",
  "recipient": "XAI_ADDRESS",
  "amount": 10.0,
  "private_key": "PRIVATE_KEY"
}
```

### Get Address Balance

```bash
GET /api/wallet/balance/{address}
```

**Full API Documentation:** See [API_REFERENCE.md](docs/API_REFERENCE.md)

---

## Mining on Testnet

### Solo Mining

```bash
# Start mining with your address
python -m xai.core.node \
  --network testnet \
  --miner-address YOUR_XAI_ADDRESS \
  --mining-intensity medium
```

**Mining Rewards:**
- **Block Reward:** 50 XAI
- **Uncle Reward:** 43.75 XAI (87.5% of block reward)
- **Difficulty:** Adjusts every 2016 blocks (~4 weeks)
- **Target Block Time:** 120 seconds

### Mining Pools

Currently no public mining pools available for testnet. Solo mining only.

---

## Network Statistics

### Real-Time Metrics

Visit the metrics endpoint for live network statistics:
```
http://xai-api-lb-835033547.us-east-1.elb.amazonaws.com/metrics
```

**Available Metrics:**
- Total blocks mined
- Average block time (24h)
- Network difficulty
- Total transactions
- Active addresses
- Mempool size
- Peer count

### Block Explorer

View all blocks and transactions:
```
http://xai-api-lb-835033547.us-east-1.elb.amazonaws.com/explorer
```

**Features:**
- Search by block height, hash, or transaction ID
- View transaction history for any address
- Real-time mempool monitoring
- Network health indicators
- Rich list and token distribution

---

## Support & Community

### Report Issues

- **GitHub Issues:** [github.com/YOUR_ORG/xai-blockchain/issues](https://github.com/YOUR_ORG/xai-blockchain/issues)
- **Security Issues:** security@xai.io (GPG key available)

### Get Help

- **Discord:** [discord.gg/xai-blockchain](https://discord.gg/xai-blockchain)
- **Telegram:** [@xai_testnet](https://t.me/xai_testnet)
- **Forum:** [forum.xai.io](https://forum.xai.io)

### Stay Updated

- **Twitter:** [@xai_blockchain](https://twitter.com/xai_blockchain)
- **Blog:** [blog.xai.io](https://blog.xai.io)
- **Newsletter:** [Subscribe here](https://xai.io/newsletter)

---

## Testnet Phases & Roadmap

### Testnet 1.0 (Current)
- **Duration:** November 2025 - January 2026
- **Focus:** Core functionality, stability testing
- **Expected Resets:** Up to 3 major resets
- **Participants:** Developers, early testers

### Testnet 2.0 (Planned)
- **Duration:** February 2026 - May 2026
- **Focus:** Advanced features, AI governance
- **Expected Resets:** 1-2 resets
- **Participants:** Public, validators, developers

### Testnet 3.0 (Planned)
- **Duration:** June 2026 - August 2026
- **Focus:** Mainnet rehearsal, security hardening
- **Expected Resets:** No resets (unless critical issues)
- **Participants:** Public, mainnet validators

### Mainnet Launch
- **Target:** Q4 2026
- **Prerequisites:**
  - Security audit completion
  - 90+ days of testnet stability
  - Community governance established

---

## FAQ

### What is the testnet for?

The XAI testnet allows developers and users to test blockchain functionality, build applications, and experiment with features without risking real value.

### Do testnet tokens have value?

No. Testnet XAI tokens have zero monetary value and cannot be exchanged for mainnet tokens.

### Will testnet data persist?

No. Testnet may be reset at any time. Do not rely on testnet data for production use.

### How do I get more test tokens?

Use the faucet (100 XAI per 24 hours) or mine blocks (50 XAI per block).

### Can I run a validator?

Yes! Anyone can run a testnet node. See [Node Setup Guide](docs/NODE_SETUP.md) for instructions.

### What happens to my testnet XAI after mainnet launch?

Testnet tokens will not transfer to mainnet. Testnet will continue running alongside mainnet.

### How is this different from mainnet?

Testnet uses:
- Different network ID (0xABCD vs 0x5841)
- Faster block times (may be adjusted)
- Lower difficulty for easier mining
- Regular resets and upgrades
- No real value

---

## Important Disclaimers

⚠️ **TESTNET ONLY**: This network is for testing purposes only.

⚠️ **NO REAL VALUE**: Testnet tokens have zero monetary value.

⚠️ **EXPECT RESETS**: The testnet blockchain may be reset at any time without notice.

⚠️ **NO SLA**: No uptime guarantees or service level agreements.

⚠️ **EXPERIMENTAL**: Features may be unstable, incomplete, or subject to change.

⚠️ **USE AT YOUR OWN RISK**: Not suitable for production applications.

---

## Version Information

- **Testnet Version:** 1.0.0
- **Protocol Version:** 1
- **Last Updated:** November 21, 2025
- **Genesis Block:** `0x742d35cc6634c0532925a3b844bc9e7eaac3e8c48e0f2f6f4a5e8d5c6b3a2f1e`
- **Genesis Timestamp:** 2025-11-21 01:42:00 UTC

---

**Ready to start testing? Get your test tokens from the [faucet](http://xai-api-lb-835033547.us-east-1.elb.amazonaws.com/faucet)!**
