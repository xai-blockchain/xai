# XAI Light Client Mode Guide

Comprehensive guide to running XAI in light client mode using Simplified Payment Verification (SPV). Perfect for mobile devices, IoT, and resource-constrained environments.

---

## What is a Light Client?

A light client verifies transactions without downloading the entire blockchain. Instead, it:
1. Downloads only **block headers** (~80 bytes each)
2. Requests **merkle proofs** for relevant transactions
3. Verifies transactions are in blocks using cryptographic proofs

**Benefits:**
- **Minimal Storage:** ~2-5 MB vs. several GB for full node
- **Fast Sync:** Minutes instead of hours
- **Low Bandwidth:** ~1-5 MB per day
- **Mobile-Friendly:** Works on phones and tablets
- **Battery Efficient:** Minimal CPU usage

**Trade-offs:**
- **Privacy:** May reveal addresses to connected peers
- **Trust:** Relies on full nodes for transaction data
- **Limited Validation:** Doesn't verify all consensus rules

---

## When to Use Light Client Mode

**Best For:**
- Mobile wallet applications
- Browser extensions
- IoT devices with limited storage
- Quick wallet setup (no waiting for sync)
- Checking balances and sending transactions
- Development and testing

**Not Recommended For:**
- Mining operations (requires full validation)
- Running a public API node
- Block explorer backends
- Consensus-critical applications
- Privacy-sensitive use cases

**Alternative:** Use [Lightweight Node](lightweight_node_guide.md) for full validation with optimizations.

---

## How SPV Works

### Step 1: Download Headers

```
Full Block (~1 MB):          Header Only (~80 bytes):
┌─────────────────────┐     ┌──────────────────┐
│ Header              │  →  │ Version: 2       │
│   Version           │     │ Prev Hash: 0x... │
│   Previous Hash     │     │ Merkle Root: 0x..│
│   Merkle Root       │     │ Timestamp: ...   │
│   Timestamp         │     │ Difficulty: ...  │
│   Difficulty        │     │ Nonce: ...       │
│   Nonce             │     └──────────────────┘
├─────────────────────┤
│ Transactions        │
│   TX 1 (~250 bytes) │
│   TX 2 (~250 bytes) │
│   ...               │
│   TX 4000 (~1 MB)   │
└─────────────────────┘
```

### Step 2: Verify Merkle Proof

When you need to verify a transaction:

```
1. Request merkle proof from full node
2. Receive proof path (300-500 bytes)
3. Verify transaction is in block:

    Merkle Root (in header)
         ├── Hash AB
         │    ├── Hash A
         │    │    ├── TX 1 ← Your transaction
         │    │    └── TX 2
         │    └── Hash B
         │         ├── TX 3
         │         └── TX 4
         └── Hash CD
              └── ... (proof path)

4. Confirm transaction is valid if:
   - Merkle proof matches root
   - Block has valid PoW
   - Block is on longest chain
```

### Step 3: Monitor Your Addresses

Use **bloom filters** to privately request relevant transactions:

```
Instead of:
  "Give me all transactions for address TXAI_123..."
  (reveals your address to node)

Use bloom filter:
  "Give me transactions matching pattern: 10101001..."
  (probabilistic, includes false positives for privacy)
```

---

## Installation

### Quick Install

```bash
# Install XAI with light client support
pip install -c constraints.txt -e ".[light-client]"

# Or from package
sudo apt install xai-light-client
```

### From Source

```bash
git clone https://github.com/your-org/xai.git
cd xai
pip install -c constraints.txt -e ".[light-client]"
```

---

## Configuration

### Basic Configuration

Create `~/.xai/light-client.yaml`:

```yaml
# Light Client Mode Configuration
node:
  mode: light_client
  network: testnet

# SPV settings
spv:
  header_download_batch: 2000     # Download 2000 headers at a time
  max_headers_in_memory: 50000    # Keep up to 50k headers in RAM
  checkpoint_interval: 10000      # Checkpoint every 10k blocks
  require_merkle_proofs: true     # Always verify merkle proofs

# Network settings
network:
  type: testnet
  max_peers: 8                    # Connect to 8 full nodes
  bootstrap_peers:
    - "testnet-node1.xai.network:18545"
    - "testnet-node2.xai.network:18545"
    - "testnet-node3.xai.network:18545"

# Storage settings
storage:
  header_db_path: "~/.xai/headers.db"
  max_db_size_mb: 100
  enable_pruning: true

# Performance
performance:
  sync_mode: fast
  header_verification_threads: 2
  bloom_filter_enabled: true
  bloom_false_positive_rate: 0.0001
```

### Mainnet Configuration

```yaml
node:
  mode: light_client
  network: mainnet

network:
  type: mainnet
  bootstrap_peers:
    - "mainnet-node1.xai.network:8545"
    - "mainnet-node2.xai.network:8545"
    - "mainnet-node3.xai.network:8545"
```

### Privacy-Enhanced Configuration

```yaml
# Enhanced privacy settings
privacy:
  bloom_filter_randomization: true   # Add random false positives
  rotate_peer_connections: true      # Change peers periodically
  connection_rotation_minutes: 30    # Rotate every 30 minutes
  address_query_delay_ms: 1000      # Delay between queries
  use_tor: false                     # Use Tor (requires tor daemon)

# More conservative bloom filter
spv:
  bloom_false_positive_rate: 0.001  # Higher rate = more privacy
```

### Performance-Optimized Configuration

```yaml
# Maximum performance
performance:
  sync_mode: fast
  header_verification_threads: 4
  parallel_proof_requests: 8        # Request 8 proofs in parallel
  aggressive_caching: true

network:
  max_peers: 16                     # More peers = faster sync
  connection_timeout: 10
```

---

## Running Light Client

### Start Light Client

```bash
# Start with config file
python -m xai.core.light_client --config ~/.xai/light-client.yaml

# Or use environment variables
export XAI_NETWORK=testnet
export XAI_NODE_MODE=light_client
python -m xai.core.light_client

# Output:
# [INFO] Starting XAI Light Client (testnet)
# [INFO] Connecting to bootstrap peers...
# [INFO] Downloading headers... (0 / 22341)
# [INFO] Progress: 10000 / 22341 (44%)
# [INFO] Progress: 20000 / 22341 (89%)
# [INFO] Sync complete! Height: 22341
# [INFO] Light client ready for queries
```

### Command Line Options

```bash
# Testnet mode
python -m xai.core.light_client --testnet

# Mainnet mode
python -m xai.core.light_client --mainnet

# Custom config
python -m xai.core.light_client --config /path/to/config.yaml

# Custom bootstrap peers
python -m xai.core.light_client \
  --peers node1.xai.io:18545,node2.xai.io:18545

# Verbose logging
python -m xai.core.light_client --log-level DEBUG

# Re-sync from genesis
python -m xai.core.light_client --resync

# Start from checkpoint
python -m xai.core.light_client --checkpoint 100000
```

---

## Using the Light Client

### Python API

```python
from xai.core.light_client import LightClient

# Initialize light client
client = LightClient(config_path="~/.xai/light-client.yaml")
await client.start()

# Get current height
height = await client.get_height()
print(f"Current height: {height}")

# Get block header
header = await client.get_header(block_height=12345)
print(f"Block hash: {header.hash}")
print(f"Merkle root: {header.merkle_root}")

# Verify transaction with merkle proof
tx_id = "0xabc123..."
proof = await client.get_merkle_proof(tx_id, block_height=12345)

is_valid = await client.verify_transaction(
    txid=tx_id,
    merkle_proof=proof,
    block_height=12345
)

if is_valid:
    print("Transaction verified!")
else:
    print("Invalid transaction or proof")

# Get balance (queries multiple peers)
balance = await client.get_balance("TXAI_YOUR_ADDRESS")
print(f"Balance: {balance} XAI")

# Send transaction
tx_hash = await client.send_transaction(
    from_address="TXAI_YOUR_ADDRESS",
    to_address="TXAI_RECIPIENT",
    amount=10.0,
    private_key="YOUR_PRIVATE_KEY"
)

print(f"Transaction sent: {tx_hash}")

# Wait for confirmation
confirmed = await client.wait_for_confirmation(tx_hash, confirmations=3)
print("Transaction confirmed!")

# Clean up
await client.stop()
```

### Wallet CLI (Light Client Mode)

All wallet operations work in light client mode:

```bash
# Check balance (SPV verified)
python src/xai/wallet/cli.py balance \
  --address TXAI_ADDRESS \
  --light-client

# Send transaction
python src/xai/wallet/cli.py send \
  --from TXAI_FROM \
  --to TXAI_TO \
  --amount 10.0 \
  --light-client

# Verify transaction
python src/xai/wallet/cli.py verify-tx \
  TX_HASH \
  --light-client

# Request testnet tokens
python src/xai/wallet/cli.py request-faucet \
  --address TXAI_ADDRESS \
  --light-client
```

---

## Security Considerations

### What SPV Verifies

✅ **SPV Confirms:**
- Transaction is included in a block (merkle proof)
- Block has valid proof-of-work
- Block is part of the longest chain
- Transaction has required confirmations

❌ **SPV Does NOT Verify:**
- Transaction signatures (trusts full nodes)
- Double-spend prevention (assumes honest majority)
- UTXO set validity
- Script execution correctness
- All consensus rules

### Security Best Practices

1. **Connect to Multiple Peers**
   - Use 8+ full nodes
   - Query multiple peers for important transactions
   - Compare responses to detect dishonest nodes

```yaml
network:
  max_peers: 12                 # More peers = more security
  min_peers_for_query: 3        # Require 3 peers to agree
  consensus_threshold: 0.66     # 66% must agree
```

2. **Use Trusted Checkpoints**
   - Hardcode known block hashes
   - Prevents long-range attacks
   - Validate against checkpoints

```yaml
security:
  trusted_checkpoints:
    - height: 100000
      hash: "0x123abc..."
      timestamp: 1704067200
    - height: 200000
      hash: "0x456def..."
      timestamp: 1708723200
```

3. **Wait for Confirmations**
   - Small amounts: 1 confirmation
   - Medium amounts: 3-6 confirmations
   - Large amounts: 6+ confirmations

```python
# Wait for confirmations
await client.wait_for_confirmation(tx_hash, confirmations=6)
```

4. **Verify Critical Transactions**
   - For large amounts, verify with multiple peers
   - Check merkle proof manually
   - Use full node for critical transactions

```python
# Verify with multiple peers
proofs = await client.get_merkle_proof_multi_peer(tx_id, min_peers=5)

if len(proofs) >= 5 and all_proofs_match(proofs):
    print("Transaction verified by 5 peers")
```

5. **Run Your Own Full Node** (Ultimate Security)
   - Connect light client to your trusted full node
   - No trust in third-party nodes
   - Full validation without downloading blockchain

```yaml
network:
  bootstrap_peers:
    - "my-trusted-node.local:18545"  # Your full node
  max_peers: 1                       # Only use your node
```

---

## Privacy Considerations

### Privacy Risks

**Address Disclosure:**
- Light clients reveal addresses when querying balances
- Full nodes can link addresses to IP addresses
- Transaction patterns may be observable

**Mitigation Strategies:**

1. **Use Bloom Filters** (Default)
   - Adds false positives to queries
   - Makes it harder to determine exact addresses

2. **Rotate Connections**
   - Change peers periodically
   - Prevents single node from tracking activity

```yaml
privacy:
  rotate_peer_connections: true
  connection_rotation_minutes: 30
```

3. **Use Tor** (Advanced)
   - Routes all traffic through Tor network
   - Hides IP address

```yaml
privacy:
  use_tor: true
  tor_proxy: "127.0.0.1:9050"
```

4. **Run Multiple Light Clients**
   - Use different clients for different addresses
   - Prevents address linkage

---

## Resource Usage

### Storage Requirements

| Component | Size | Growth Rate |
|-----------|------|-------------|
| Headers Database | ~1.8 MB | ~2 MB/year |
| Bloom Filters | 100 KB | Stable |
| Transaction Cache | 500 KB | Stable (pruned) |
| Peer Database | 50 KB | Stable |
| **Total** | **~3 MB** | **~2 MB/year** |

### Bandwidth Requirements

| Operation | Bandwidth | Frequency |
|-----------|-----------|-----------|
| Initial Header Sync | ~1.8 MB | Once |
| New Header Download | 80 bytes | Every 2 minutes |
| Transaction Verification | 1-5 KB | Per transaction |
| Merkle Proof Request | 300-500 bytes | Per verification |
| **Daily Usage** | **~1-5 MB** | **Typical wallet use** |

### Memory Requirements

| Configuration | RAM Usage |
|---------------|-----------|
| Minimal | 64-128 MB |
| Standard | 128-256 MB |
| Performance-Optimized | 256-512 MB |

---

## Advanced Topics

### Custom Checkpoint Server

Host your own checkpoint server for faster sync:

```python
# checkpoint_server.py
from flask import Flask, jsonify
from xai.core.blockchain import Blockchain

app = Flask(__name__)
blockchain = Blockchain()

@app.route('/checkpoint/latest')
def latest_checkpoint():
    height = blockchain.get_height()
    block = blockchain.get_block(height)

    return jsonify({
        'height': height,
        'hash': block.hash,
        'merkle_root': block.merkle_root,
        'timestamp': block.timestamp,
        'signature': sign_checkpoint(block)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

Configure light client to use it:

```yaml
spv:
  checkpoint_url: "http://my-server.com:8080/checkpoint/latest"
```

### Merkle Proof Verification

Manually verify merkle proofs:

```python
from xai.core.merkle import MerkleTree

# Given a transaction and merkle proof
tx_hash = "0xabc123..."
merkle_proof = [
    "0xdef456...",
    "0x789abc...",
    "0x012def...",
]
merkle_root = "0x345678..."

# Verify
def verify_merkle_proof(tx_hash, proof, root):
    current_hash = tx_hash

    for proof_hash in proof:
        # Combine hashes (order matters)
        if current_hash < proof_hash:
            combined = current_hash + proof_hash
        else:
            combined = proof_hash + current_hash

        current_hash = sha256(combined)

    return current_hash == root

is_valid = verify_merkle_proof(tx_hash, merkle_proof, merkle_root)
```

---

## Troubleshooting

### Slow Initial Sync

**Solution:**
- Use checkpoint sync
- Increase `header_download_batch`
- Connect to more peers

```yaml
spv:
  header_download_batch: 5000
network:
  max_peers: 16
```

### Merkle Proof Verification Fails

**Solution:**
- Ensure connected to honest peers
- Verify block is on main chain
- Check for chain reorganization

```python
# Get proof from multiple peers
proofs = await client.get_merkle_proof_multi_peer(tx_id, min_peers=3)
```

### High Bandwidth Usage

**Solution:**
- Reduce peer count
- Limit bloom filter false positive rate
- Disable aggressive caching

```yaml
network:
  max_peers: 4
spv:
  bloom_false_positive_rate: 0.00001  # Lower = less data
```

### Privacy Concerns

**Solution:**
- Enable Tor
- Rotate connections frequently
- Use bloom filter randomization
- Run your own full node

```yaml
privacy:
  use_tor: true
  rotate_peer_connections: true
  bloom_filter_randomization: true
```

---

## Comparison: Light Client vs Lightweight Node vs Full Node

| Feature | Light Client | Lightweight Node | Full Node |
|---------|--------------|------------------|-----------|
| Storage | ~3 MB | ~500 MB - 2 GB | ~10+ GB |
| Initial Sync | Minutes | Hours | Days |
| Bandwidth | 1-5 MB/day | 50-200 MB/day | 500+ MB/day |
| RAM | 64-256 MB | 512 MB - 2 GB | 2+ GB |
| Validation | Headers only | Full validation | Full validation |
| Mining | ❌ No | ❌ No | ✅ Yes |
| Privacy | ⚠️ Limited | ✅ Good | ✅ Excellent |
| Security | ⚠️ Trusts peers | ✅ Full verification | ✅ Full verification |
| Use Case | Mobile, IoT | Raspberry Pi, Low-power | Production, Mining |

---

## Next Steps

- **[Lightweight Node Guide](lightweight_node_guide.md)** - Full validation with optimizations
- **[Mobile Quick Start](mobile_quickstart.md)** - Integrate light client in mobile apps
- **[Wallet Setup](wallet-setup.md)** - Advanced wallet features
- **[API Documentation](../api/rest-api.md)** - Build apps using light clients

---

*Last Updated: January 2025 | XAI Version: 0.2.0*
