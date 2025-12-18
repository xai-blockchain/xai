# XAI Light Client Mode - User Guide

Your complete guide to running XAI in light client mode using Simplified Payment Verification (SPV). Designed for mobile devices, wallets, and resource-constrained environments.

---

## What is a Light Client?

A **light client** (also called an SPV client) lets you verify your transactions and check your balance without downloading the entire blockchain. Think of it like checking your bank balance on your phone - you don't need to download the bank's entire database to see your account.

### How It Works

Instead of downloading every transaction ever made, a light client:

1. **Downloads only block headers** - Small summaries (~80 bytes each) instead of full blocks (~1 MB each)
2. **Requests merkle proofs** - Mathematical proofs that your transaction is in a block
3. **Verifies cryptographically** - Uses the proof to confirm your transaction is real

### Benefits

- **Tiny Storage:** Only ~2-5 MB instead of several gigabytes
- **Fast Sync:** Ready in minutes instead of hours or days
- **Low Data Usage:** Uses only ~1-5 MB per day
- **Mobile-Friendly:** Perfect for phones and tablets
- **Battery Efficient:** Minimal CPU and energy usage
- **Always Up-to-Date:** Syncs quickly when you open your wallet

### Trade-offs

- **Privacy:** Full nodes you connect to can see which addresses you're checking
- **Trust Required:** You trust that the majority of full nodes are honest
- **Limited Validation:** Only verifies that transactions exist, not all blockchain rules

---

## When Should You Use Light Client Mode?

### Perfect For

- **Mobile Wallet Apps** - iOS and Android wallets
- **Browser Extensions** - Chrome, Firefox, Safari wallets
- **Desktop Wallets** - Quick setup without long sync times
- **IoT Devices** - Smart home devices, hardware wallets
- **Quick Checks** - Just want to see your balance or send a payment
- **Development & Testing** - Fast iteration without full node overhead

### Not Recommended For

- **Mining** - Requires full blockchain validation
- **Running Public APIs** - Need full node for serving data
- **Block Explorers** - Must have complete transaction history
- **High Privacy Requirements** - Full nodes offer better privacy
- **Business Critical Validation** - When you must verify everything yourself

### Need Full Validation?

If you need complete verification but want lower resource usage than a full node, check out the [Lightweight Node Guide](lightweight_node_guide.md) which offers full validation with optimizations.

---

## Understanding SPV: How Light Clients Work

SPV (Simplified Payment Verification) is the technology that makes light clients possible. Here's how it works in plain English:

### Step 1: Download Block Headers Only

Instead of downloading entire blocks, you only download the "header" - a tiny summary of each block.

```
Full Block (~1 MB):              Block Header (~80 bytes):
┌──────────────────────┐        ┌──────────────────┐
│ Header Information   │   →    │ Block Number     │
│   Block Number       │        │ Previous Hash    │
│   Previous Hash      │        │ Merkle Root      │
│   Merkle Root        │        │ Timestamp        │
│   Timestamp          │        │ Difficulty       │
│   Difficulty         │        │ Nonce            │
│   Nonce              │        └──────────────────┘
├──────────────────────┤
│ All Transactions     │        Saves ~99% bandwidth!
│   TX 1 (250 bytes)   │
│   TX 2 (250 bytes)   │
│   TX 3 (250 bytes)   │
│   ... (4,000 more)   │
└──────────────────────┘
```

**Savings:** Downloading 100,000 headers = ~8 MB vs. 100,000 full blocks = ~100 GB

### Step 2: Request Proof for Your Transactions

When you want to verify a specific transaction (like a payment to you), you ask a full node for a "merkle proof":

```
1. You ask: "Is transaction ABC123 really in block 50,000?"
2. Full node sends you a merkle proof (~500 bytes)
3. You verify the proof matches the merkle root in the header
4. If it matches, the transaction is confirmed!

Visual Example:
                Merkle Root (in block header)
                        │
            ┌───────────┴───────────┐
         Hash AB                 Hash CD
            │                       │
      ┌─────┴─────┐           ┌─────┴─────┐
   Hash A      Hash B      Hash C      Hash D
      │           │           │           │
   ┌──┴──┐    ┌──┴──┐    ┌──┴──┐    ┌──┴──┐
  TX 1  TX 2  TX 3  TX 4  TX 5  TX 6  TX 7  TX 8
   ↑
   Your transaction

The proof shows: TX 2, Hash B, Hash CD
You verify by hashing up to the root!
```

**What This Proves:**
- ✅ Your transaction is definitely in this block
- ✅ The block is valid (has proof-of-work)
- ✅ The block is on the longest chain

**What This Doesn't Prove:**
- ❌ That the transaction follows all rules (you trust the full nodes)
- ❌ That there's no double-spend elsewhere

### Step 3: Security Through Multiple Confirmations

Light clients wait for multiple blocks to be built on top of your transaction's block before considering it final:

```
Your TX in Block 100
   ↓
Block 101 built on top (1 confirmation)
   ↓
Block 102 built on top (2 confirmations)
   ↓
Block 103 built on top (3 confirmations)
   ↓
...

After 6 confirmations, reverting would require massive computational power.
This makes your transaction practically irreversible.
```

**Recommended Confirmations:**
- Small payment (<$100): 1-2 confirmations (~4 minutes)
- Medium payment ($100-$10,000): 3-6 confirmations (~12 minutes)
- Large payment (>$10,000): 6+ confirmations (~20+ minutes)

---

## Getting Started with Light Client Mode

### Installation

The XAI light client is included in the standard XAI installation. No special packages needed!

```bash
# Install XAI
pip install xai

# Or install from source
git clone https://github.com/xai-foundation/xai.git
cd xai
pip install -e .
```

### Quick Start

The easiest way to use light client mode is through Python:

```python
from xai.core.light_client import LightClient, BlockHeader
from xai.core.light_client_service import LightClientService

# Create a light client instance
client = LightClient()

# Add headers as you receive them from full nodes
header = BlockHeader(
    index=12345,
    timestamp=1704067200.0,
    previous_hash="0xabc123...",
    merkle_root="0xdef456...",
    difficulty=1000,
    nonce=42,
    hash="0x789abc..."
)

# The light client validates and stores the header
if client.add_header(header):
    print(f"Header {header.index} added successfully!")
    print(f"Current chain height: {client.get_chain_height()}")
```

---

## Connecting to Full Nodes

Light clients need to connect to full nodes to get block headers and transaction proofs. You have several options:

### Option 1: Public XAI Nodes (Easiest)

Connect to public XAI infrastructure nodes:

```python
from xai.core.light_client_service import LightClientService

# Connect to public testnet nodes
service = LightClientService(blockchain)

# Public testnet nodes (no configuration needed)
public_nodes = [
    "testnet-node1.xai.network:18545",
    "testnet-node2.xai.network:18545",
    "testnet-node3.xai.network:18545",
]
```

### Option 2: Your Own Trusted Node (Most Secure)

Run your own full node and connect your light client to it:

```python
# Connect to your own node
my_trusted_node = "192.168.1.100:18545"  # Your full node IP

# Now you don't trust any third parties!
```

**Why this is more secure:**
- You control the full node
- No privacy concerns (your node doesn't spy on you)
- No trust required in third parties
- Still get light client benefits (fast sync, low storage)

### Option 3: Multiple Nodes for Security

Connect to several nodes and require agreement:

```python
# Require 3 out of 5 nodes to agree before trusting data
nodes = [
    "node1.xai.network:18545",
    "node2.xai.network:18545",
    "node3.xai.network:18545",
    "node4.xai.network:18545",
    "node5.xai.network:18545",
]

# If 3+ nodes give the same answer, trust it
min_agreement = 3
```

---

## How to Verify Transactions

Here's how to verify that a transaction is included in the blockchain using SPV:

### Step 1: Get the Transaction Proof

When you want to verify a specific transaction, ask a full node for the merkle proof:

```python
from xai.core.light_client_service import LightClientService

# Initialize service with your blockchain instance
service = LightClientService(blockchain)

# Request proof for a specific transaction
tx_id = "0xabc123def456..."  # Your transaction ID
proof_data = service.get_transaction_proof(tx_id)

if proof_data:
    print(f"Transaction found in block {proof_data['block_index']}")
    print(f"Block hash: {proof_data['block_hash']}")
    print(f"Merkle root: {proof_data['merkle_root']}")
else:
    print("Transaction not found in blockchain")
```

### Step 2: Verify the Proof

Now verify that the proof is valid:

```python
# Verify the proof (requires minimum 6 confirmations by default)
is_valid, message = service.verify_proof(
    txid=tx_id,
    proof_data=proof_data,
    min_confirmations=6
)

if is_valid:
    print(f"✓ Transaction verified! {message}")
    # Transaction is confirmed and safe to accept
else:
    print(f"✗ Verification failed: {message}")
    # Don't accept this transaction
```

### Step 3: Check Confirmation Count

For important transactions, always check how many confirmations it has:

```python
from xai.core.light_client import LightClient, SPVProof

client = LightClient()

# Assuming you have an SPVProof object
confirmations = client.get_confirmations(tx_id)
print(f"Transaction has {confirmations} confirmations")

# Check if it meets your security requirements
if client.is_transaction_confirmed(tx_id, min_confirmations=6):
    print("Transaction is confirmed and secure!")
else:
    print(f"Waiting for more confirmations...")
```

### Complete Example: Verify a Payment

Here's a complete example of verifying a payment you received:

```python
from xai.core.light_client import LightClient, SPVProof
from xai.core.light_client_service import LightClientService

def verify_payment(tx_id, min_confirmations=6):
    """
    Verify that a payment transaction is confirmed.

    Args:
        tx_id: Transaction ID to verify
        min_confirmations: Minimum confirmations required

    Returns:
        True if payment is verified and confirmed
    """
    # Initialize services
    service = LightClientService(blockchain)
    client = LightClient()

    # Get transaction proof from full node
    proof_data = service.get_transaction_proof(tx_id)
    if not proof_data:
        print(f"❌ Transaction {tx_id} not found")
        return False

    # Verify the merkle proof
    is_valid, message = service.verify_proof(
        txid=tx_id,
        proof_data=proof_data,
        min_confirmations=min_confirmations
    )

    if is_valid:
        tx_data = proof_data['transaction']
        print(f"✅ Payment verified!")
        print(f"   From: {tx_data['from']}")
        print(f"   To: {tx_data['to']}")
        print(f"   Amount: {tx_data['amount']} XAI")
        print(f"   Block: {proof_data['block_index']}")
        print(f"   {message}")
        return True
    else:
        print(f"❌ Verification failed: {message}")
        return False

# Example usage
payment_tx_id = "0x1234567890abcdef..."
if verify_payment(payment_tx_id, min_confirmations=6):
    # Safe to credit user's account
    print("Payment confirmed - crediting account")
else:
    # Wait for more confirmations
    print("Payment not yet confirmed - please wait")
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
