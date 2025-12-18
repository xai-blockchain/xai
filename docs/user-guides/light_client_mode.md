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

## Security: Understanding the Trust Model

Light clients are secure for most use cases, but it's important to understand what they verify and what they trust.

### What Light Clients Verify

When you use a light client, you get cryptographic proof of:

- ✅ **Transaction Inclusion** - Your transaction is definitely in this block
- ✅ **Proof-of-Work** - The block required real computational work to create
- ✅ **Chain Validity** - The block is part of the longest chain
- ✅ **Confirmations** - How many blocks have been built on top

This means you can be confident that:
- Your payment was included in the blockchain
- The block is legitimate (not fake)
- The network accepts this transaction

### What Light Clients Trust Full Nodes For

Light clients DO NOT verify everything. You trust full nodes for:

- ❌ **Transaction Validity** - That the sender actually had the funds
- ❌ **Double-Spend Prevention** - That funds weren't spent twice
- ❌ **All Consensus Rules** - That all blockchain rules were followed

### How to Stay Safe

#### 1. Use Multiple Full Nodes

Never trust a single node. Connect to several and compare responses:

```python
# Check your transaction with multiple nodes
# If they all agree, it's safe to trust
nodes = [
    "node1.xai.network:18545",
    "node2.xai.network:18545",
    "node3.xai.network:18545",
]

# Verify transaction with all nodes
# If majority agree, trust the result
```

**Rule of Thumb:** For important transactions, require at least 3 nodes to give the same answer.

#### 2. Wait for Multiple Confirmations

More confirmations = more security. Each confirmation makes it exponentially harder to reverse your transaction.

```python
# For different security levels
small_payment = 1    # ~2 minutes, suitable for <$100
medium_payment = 3   # ~6 minutes, suitable for <$10,000
large_payment = 6    # ~12 minutes, suitable for any amount
```

**Real-World Analogy:** Like waiting for a check to clear - more time = more confidence.

#### 3. Run Your Own Full Node (Advanced)

The most secure option is running your own full node and connecting your light client to it:

```python
# Connect only to your own trusted node
my_node = "192.168.1.100:18545"
```

**Benefits:**
- Zero trust in third parties
- Complete privacy (your node doesn't spy on you)
- Full validation of all rules
- Still get light client benefits (fast sync, low bandwidth)

**When to consider this:**
- Running a business accepting XAI payments
- Managing large amounts of XAI
- High privacy requirements
- Maximum security needs

#### 4. Understand Attack Scenarios

**What could go wrong with a light client?**

| Attack | Risk Level | How to Protect |
|--------|-----------|----------------|
| Dishonest node shows fake transaction | Low | Connect to multiple nodes |
| All your nodes are malicious | Very Low | Use well-known public nodes |
| Long-range attack (fake old blocks) | Low | Wait for confirmations |
| Eclipse attack (all nodes controlled) | Very Low | Connect to diverse nodes |

**Important:** Light clients are very secure for typical use cases. Most attacks require controlling many nodes or massive computational power.

---

## Privacy Considerations

### Privacy Trade-offs

Light clients sacrifice some privacy for convenience. Here's what you should know:

**What Full Nodes Can See:**
- Which addresses you're checking balances for
- Your IP address (unless you use Tor)
- When you're online and using your wallet
- Patterns of when you check certain addresses

**What Full Nodes CANNOT See:**
- Your private keys (always stays on your device)
- Transactions you haven't made yet
- Addresses you don't query about
- Your full wallet contents (only what you ask about)

### Improving Your Privacy

#### Basic: Connect to Your Own Node

The simplest privacy improvement is running your own full node:

```python
# Connect to your own node - perfect privacy
my_private_node = "192.168.1.100:18545"
```

Now no third party knows what you're doing!

#### Advanced: Use Tor (Optional)

Route your light client traffic through Tor to hide your IP address:

```bash
# Install Tor
sudo apt install tor

# Configure your light client to use Tor
# (Future: Tor configuration will be added)
```

#### Intermediate: Change Nodes Frequently

Don't let any single node track all your activity:

```python
import random
import time

nodes = [
    "node1.xai.network:18545",
    "node2.xai.network:18545",
    "node3.xai.network:18545",
    "node4.xai.network:18545",
]

# Rotate which node you use every 30 minutes
current_node = random.choice(nodes)
```

### Privacy Tips

1. **Don't reuse addresses** - Generate new address for each payment
2. **Use your own node** - Best privacy option
3. **Be aware of timing** - Querying right after a transaction reveals it's yours
4. **Consider full node for high privacy** - Full nodes don't reveal what you're looking for

---

## Resource Usage: What Light Clients Actually Use

One of the biggest advantages of light clients is how little they need from your device.

### Storage (Disk Space)

Light clients are tiny compared to full nodes:

| What | Size | How Often It Grows |
|------|------|-------------------|
| Block Headers | ~1.8 MB | +2 MB per year |
| Recent Transaction Proofs | ~500 KB | Stays constant (old ones deleted) |
| Configuration & Peers | ~50 KB | Barely grows |
| **Total** | **~3 MB** | **~2 MB/year** |

**Comparison:**
- Light Client: 3 MB (size of 2 photos)
- Full Node: 100+ GB (size of 25,000+ photos)

### Bandwidth (Internet Data)

Light clients use very little data:

| Activity | Data Used | How Often |
|----------|-----------|-----------|
| Initial sync | ~2-5 MB | Once ever |
| Daily header updates | ~60 KB | Automatic |
| Checking balance | ~1-2 KB | When you check |
| Verifying a payment | ~500 bytes | Per payment |
| Sending a transaction | ~1 KB | Per send |

**Daily Usage:** 1-5 MB for normal wallet use (less than loading one webpage!)

### Memory (RAM)

Light clients need very little RAM:

| Usage Pattern | RAM Needed |
|--------------|------------|
| Mobile wallet (background) | 32-64 MB |
| Mobile wallet (active use) | 64-128 MB |
| Desktop wallet | 128-256 MB |

**Comparison:** A single browser tab uses more RAM than a light client!

### Battery Usage (Mobile Devices)

Light clients are battery-friendly:

- **Background sync:** Minimal impact (updates every few minutes)
- **Active use:** Similar to messaging app
- **No mining:** Light clients can't mine, saving lots of energy

### CPU Usage

Very low computational requirements:

- Verifying merkle proofs: Milliseconds
- Checking header proof-of-work: ~1 second per header
- No complex validation: Light clients don't validate full blocks

---

## Mobile Wallet Integration

Light clients are perfect for mobile apps! Here's how to integrate XAI light client into your mobile wallet.

### Checking Sync Progress

Mobile apps should show sync progress to users. XAI provides a built-in sync progress API:

```python
from xai.core.light_client_service import LightClientService

service = LightClientService(blockchain)

# Start syncing headers
service.start_sync(target_height=50000)

# Update progress as headers download
while syncing:
    service.update_sync_progress()
    progress = service.get_sync_progress()

    print(f"Syncing: {progress.sync_percentage:.1f}%")
    print(f"Block {progress.current_height} of {progress.target_height}")
    print(f"Speed: {progress.headers_per_second:.1f} headers/sec")

    if progress.estimated_time_remaining:
        mins = progress.estimated_time_remaining // 60
        print(f"ETA: {mins} minutes")

    if progress.sync_state == "synced":
        print("Sync complete!")
        break
```

### Mobile-Optimized Sync Manager

For mobile apps with network constraints, use the MobileSyncManager:

```python
from xai.mobile.sync_manager import (
    MobileSyncManager,
    NetworkCondition,
    SyncState
)
from xai.core.chunked_sync import ChunkedStateSyncService

# Initialize services
chunked_service = ChunkedStateSyncService(blockchain, storage_dir="~/.xai/sync")
mobile_sync = MobileSyncManager(
    chunked_service=chunked_service,
    storage_dir="~/.xai/mobile",
    min_free_space_mb=100,
    enable_background_sync=True
)

# Configure network conditions
if on_wifi:
    condition = NetworkCondition(
        bandwidth_limit=0,  # Unlimited on WiFi
        connection_type="wifi",
        is_metered=False,
        signal_strength=100
    )
else:  # On cellular
    condition = NetworkCondition(
        bandwidth_limit=500_000,  # 500 KB/s on cellular
        connection_type="4g",
        is_metered=True,
        signal_strength=75
    )

mobile_sync.set_network_condition(condition)

# Set progress callback for UI updates
def on_progress(data):
    state = data['state']
    stats = data['statistics']

    print(f"State: {state}")
    print(f"Downloaded: {stats['bytes_downloaded'] / 1024 / 1024:.1f} MB")
    print(f"Speed: {stats['average_speed'] / 1024:.1f} KB/s")

mobile_sync.set_progress_callback(on_progress)

# Pause/resume based on app state
def on_app_background():
    mobile_sync.pause_sync()

def on_app_foreground():
    mobile_sync.resume_sync()
```

### Example: React Native Integration

Here's a complete example for a React Native wallet:

```javascript
import { useEffect, useState } from 'react';
import { XAILightClient } from '@xai/mobile-sdk';

function WalletSyncScreen() {
  const [progress, setProgress] = useState({
    percentage: 0,
    current: 0,
    target: 0,
    state: 'idle'
  });

  useEffect(() => {
    const client = new XAILightClient({
      network: 'testnet',
      onProgress: (data) => {
        setProgress({
          percentage: data.sync_percentage,
          current: data.current_height,
          target: data.target_height,
          state: data.sync_state
        });
      }
    });

    client.startSync();

    return () => client.stop();
  }, []);

  if (progress.state === 'synced') {
    return <WalletHomeScreen />;
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Syncing Blockchain</Text>
      <ProgressBar progress={progress.percentage / 100} />
      <Text>Block {progress.current} of {progress.target}</Text>
      <Text>{progress.percentage.toFixed(1)}% complete</Text>
    </View>
  );
}
```

### Bandwidth Optimization for Mobile

Save data with smart sync strategies:

```python
import wifi_detection  # Your platform's WiFi detection

def should_sync():
    """Only sync on WiFi to save mobile data"""
    if wifi_detection.is_connected_to_wifi():
        return True

    # Or ask user permission for cellular sync
    return ask_user("Sync on cellular data?")

if should_sync():
    service.start_sync(target_height=latest_height)
else:
    print("Waiting for WiFi connection...")
```

### See Also

- [Sync Progress API Documentation](../SYNC_PROGRESS_API.md) - Complete API reference
- [Mobile Quick Start Guide](mobile_quickstart.md) - Full mobile SDK documentation

---

## Troubleshooting Common Issues

### "Sync is taking forever"

**Problem:** Initial header sync seems very slow

**Solutions:**
1. **Check your internet connection** - Header sync needs steady connection
2. **Try different nodes** - Some nodes may be slow or overloaded
3. **Be patient** - Even "slow" sync is usually under 10 minutes
4. **Check if stuck** - If no progress for 5+ minutes, restart

```python
# Check sync status
progress = service.get_sync_progress()
print(f"State: {progress.sync_state}")  # Should show "syncing"
print(f"Speed: {progress.headers_per_second} headers/sec")  # Should be > 0

# If stalled, restart sync
if progress.sync_state == "stalled":
    service.start_sync(target_height=latest_height)
```

### "Transaction verification failed"

**Problem:** Your transaction merkle proof doesn't verify

**Possible Causes:**
1. **Transaction isn't confirmed yet** - Wait for it to be included in a block
2. **Node gave wrong proof** - Try a different node
3. **Chain reorganization** - Block was orphaned, transaction will be in different block

**Solution:**
```python
# Try getting proof from multiple nodes
nodes = ["node1.xai.network:18545", "node2.xai.network:18545", "node3.xai.network:18545"]
for node in nodes:
    # Connect to node and get proof
    proof = get_proof_from_node(node, tx_id)
    if verify_proof(proof):
        print(f"Verified using {node}")
        break
```

### "Using too much mobile data"

**Problem:** Light client consuming cellular data allowance

**Solutions:**
1. **Sync only on WiFi** - Wait for WiFi before syncing
2. **Use less frequent checks** - Don't check balance every minute
3. **Reduce header sync frequency** - Only sync when needed

```python
# Only sync on WiFi
if not on_wifi():
    print("Waiting for WiFi to sync...")
    # Don't start sync
else:
    service.start_sync(target_height=latest_height)
```

### "Not enough storage space"

**Problem:** Device says not enough space for sync

**Note:** This shouldn't happen - light clients need only ~3 MB!

**Solution:**
- Check you have at least 10 MB free
- Clear old transaction proofs
- Restart app to reset storage

### "Can't connect to any nodes"

**Problem:** Unable to connect to full nodes

**Solutions:**
1. **Check internet connection**
2. **Try different nodes** - Public nodes may be down
3. **Check firewall** - Some networks block blockchain ports
4. **Run your own node** - Most reliable option

---

## Comparison: Choosing the Right Node Type

Not sure if a light client is right for you? Here's how different node types compare:

| Feature | Light Client (SPV) | Lightweight Node | Full Node |
|---------|-------------------|------------------|-----------|
| **Storage** | ~3 MB | ~1-2 GB | ~100+ GB |
| **Initial Sync** | 2-10 minutes | 1-4 hours | 1-3 days |
| **Daily Data** | 1-5 MB | 50-200 MB | 500+ MB |
| **RAM Needed** | 64-128 MB | 512 MB - 1 GB | 2+ GB |
| **Validation** | Headers + proofs only | Everything | Everything |
| **Can Mine** | No | No | Yes |
| **Privacy** | Limited | Good | Excellent |
| **Security** | Trusts majority of nodes | Fully validates | Fully validates |
| **Best For** | Mobile, wallets, quick access | Home servers, Raspberry Pi | Business, mining, serving others |
| **Trust Model** | Trust full nodes | Trust no one | Trust no one |

### Quick Decision Guide

**Choose a Light Client if:**
- You're building a mobile wallet
- You want fast, easy setup
- Storage/bandwidth are limited
- You're okay trusting well-known nodes
- You just want to send/receive XAI

**Choose a Lightweight Node if:**
- You want full validation
- You have modest hardware (Raspberry Pi)
- You want better privacy
- Storage isn't a major concern
- See: [Lightweight Node Guide](lightweight_node_guide.md)

**Choose a Full Node if:**
- You're running a business
- You want to mine XAI
- You need maximum security
- You want to help the network
- Privacy is critical

---

## Summary

Light clients using SPV (Simplified Payment Verification) let you use XAI without downloading the entire blockchain:

**Key Points:**
- ✅ Only ~3 MB storage needed (vs 100+ GB for full node)
- ✅ Sync in minutes (vs days for full node)
- ✅ Perfect for mobile wallets and quick access
- ✅ Cryptographically verifies transactions are in blocks
- ⚠️ Trusts full nodes for complete validation
- ⚠️ Less privacy than running own node

**Best Practices:**
1. Connect to multiple nodes (at least 3)
2. Wait for 6 confirmations for important transactions
3. For maximum security, run your own full node and connect to it
4. For mobile, use WiFi-only sync to save data

**Getting Started:**
```python
from xai.core.light_client import LightClient
from xai.core.light_client_service import LightClientService

# Create light client
client = LightClient()

# Connect to service
service = LightClientService(blockchain)

# Start syncing
service.start_sync(target_height=latest_height)

# You're ready to verify transactions!
```

---

## Next Steps

- **[Mobile Quick Start Guide](mobile_quickstart.md)** - Build mobile wallets with light client
- **[Sync Progress API](../SYNC_PROGRESS_API.md)** - Track sync progress in your app
- **[Lightweight Node Guide](lightweight_node_guide.md)** - Full validation with lower resources
- **[Wallet Setup Guide](wallet-setup.md)** - Complete wallet features
- **[Testnet Guide](TESTNET_GUIDE.md)** - Try it on testnet first

---

## Questions?

- **Docs:** Check [FAQ](faq.md) for common questions
- **Support:** Visit [troubleshooting guide](troubleshooting.md)
- **Community:** Join XAI community channels

---

*Last Updated: December 2025 | XAI Version: 0.2.0*
*Documentation for XAI Light Client (SPV) Implementation*
