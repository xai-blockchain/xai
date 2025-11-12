# Blockchain Persistence Integration Guide

## Overview

This guide shows how to integrate the `BlockchainStorage` system into `blockchain.py` for automatic saving, loading, and recovery of the XAI blockchain.

## Integration Points

### 1. Import the Storage Module

Add to the imports section of `blockchain.py` (around line 14):

```python
from blockchain_persistence import BlockchainStorage
```

### 2. Initialize Storage in `__init__`

Add to the `Blockchain.__init__` method (after line 247, before `create_genesis_block()`):

```python
# Initialize blockchain persistence
self.storage = BlockchainStorage()

# Try to load existing blockchain from disk
loaded, blockchain_data, message = self.storage.load_from_disk()

if loaded and blockchain_data:
    print(f"Loading existing blockchain: {message}")
    self._restore_from_data(blockchain_data)
else:
    print(f"Starting new blockchain: {message}")
    # Create genesis block (will happen below)
```

### 3. Add Restore Method

Add this new method to the `Blockchain` class (after the `__init__` method, around line 248):

```python
def _restore_from_data(self, blockchain_data: dict):
    """
    Restore blockchain state from loaded data

    Args:
        blockchain_data: Previously saved blockchain data
    """
    # Restore chain
    self.chain = []
    for block_data in blockchain_data.get('chain', []):
        # Reconstruct transactions
        transactions = []
        for tx_data in block_data['transactions']:
            tx = Transaction(
                tx_data['sender'],
                tx_data['recipient'],
                tx_data['amount'],
                tx_data.get('fee', 0.0),
                tx_data.get('public_key'),
                tx_data.get('tx_type', 'normal'),
                tx_data.get('nonce')
            )
            tx.timestamp = tx_data['timestamp']
            tx.txid = tx_data['txid']
            tx.signature = tx_data.get('signature')
            transactions.append(tx)

        # Reconstruct block
        block = Block(
            block_data['index'],
            transactions,
            block_data['previous_hash'],
            block_data['difficulty']
        )
        block.timestamp = block_data['timestamp']
        block.nonce = block_data['nonce']
        block.merkle_root = block_data['merkle_root']
        block.hash = block_data['hash']

        self.chain.append(block)

        # Update UTXO set for each block
        self.update_utxo_set(block)

    # Restore pending transactions
    self.pending_transactions = []
    for tx_data in blockchain_data.get('pending_transactions', []):
        tx = Transaction(
            tx_data['sender'],
            tx_data['recipient'],
            tx_data['amount'],
            tx_data.get('fee', 0.0),
            tx_data.get('public_key'),
            tx_data.get('tx_type', 'normal'),
            tx_data.get('nonce')
        )
        tx.timestamp = tx_data['timestamp']
        tx.txid = tx_data['txid']
        tx.signature = tx_data.get('signature')
        self.pending_transactions.append(tx)

    # Restore difficulty
    self.difficulty = blockchain_data.get('difficulty', self.difficulty)

    print(f"Blockchain restored: {len(self.chain)} blocks, {len(self.pending_transactions)} pending transactions")
```

### 4. Modify `create_genesis_block`

Update the `create_genesis_block` method (around line 248) to check if chain already exists:

```python
def create_genesis_block(self):
    """Create or load the genesis block"""

    # If chain already loaded from disk, skip genesis creation
    if len(self.chain) > 0:
        print(f"Genesis block already loaded from disk: {self.chain[0].hash}")

        # Protect time capsule reserve wallet
        self._protect_time_capsule_reserve(self.chain[0])
        return

    # Original genesis block creation code continues here...
    import os
    genesis_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), Config.GENESIS_FILE)
    # ... rest of existing code
```

### 5. Add Auto-Save After Mining

Update the `mine_pending_transactions` method (around line 550) to save after mining:

```python
def mine_pending_transactions(self, miner_address: str) -> Block:
    """Mine a new block with pending transactions"""
    # ... existing mining code ...

    # Clear pending transactions
    self.pending_transactions = []

    # Log streak bonus if applied
    if streak_bonus > 0:
        print(f"STREAK BONUS: +{streak_bonus:.4f} XAI ({self.streak_tracker.get_streak_bonus(miner_address) * 100:.0f}%)")

    # AUTO-SAVE: Save blockchain to disk after mining
    success, message = self.storage.save_to_disk(self.to_dict())
    if success:
        print(f"Blockchain saved: {message}")
    else:
        print(f"WARNING: Failed to save blockchain: {message}")

    return new_block
```

### 6. Add Manual Save/Load Methods

Add these convenience methods to the `Blockchain` class (around line 1040):

```python
def save_blockchain(self, create_backup: bool = True) -> Tuple[bool, str]:
    """
    Manually save blockchain to disk

    Args:
        create_backup: Whether to create backup

    Returns:
        tuple: (success: bool, message: str)
    """
    return self.storage.save_to_disk(self.to_dict(), create_backup)

def reload_blockchain(self) -> Tuple[bool, str]:
    """
    Reload blockchain from disk

    Returns:
        tuple: (success: bool, message: str)
    """
    loaded, blockchain_data, message = self.storage.load_from_disk()

    if loaded and blockchain_data:
        self._restore_from_data(blockchain_data)
        return True, message
    else:
        return False, message

def verify_blockchain_integrity(self) -> Tuple[bool, str]:
    """
    Verify blockchain file integrity

    Returns:
        tuple: (valid: bool, message: str)
    """
    return self.storage.verify_integrity()

def list_backups(self) -> List[dict]:
    """List all available backups"""
    return self.storage.list_backups()

def list_checkpoints(self) -> List[dict]:
    """List all available checkpoints"""
    return self.storage.list_checkpoints()

def restore_from_backup(self, backup_filename: str) -> Tuple[bool, str]:
    """
    Restore blockchain from specific backup

    Args:
        backup_filename: Name of backup file

    Returns:
        tuple: (success: bool, message: str)
    """
    success, blockchain_data, message = self.storage.restore_from_backup(backup_filename)

    if success and blockchain_data:
        self._restore_from_data(blockchain_data)
        return True, message
    else:
        return False, message
```

## Complete Integration Workflow

### On Blockchain Initialization:

1. Storage system initializes
2. Attempts to load existing blockchain from disk
3. If successful: Restores chain, UTXO set, pending transactions
4. If failed: Creates new genesis block
5. Verifies checksum integrity
6. Falls back to backups/checkpoints if corruption detected

### On Block Mining:

1. Mine block (existing code)
2. Add block to chain (existing code)
3. Process gamification features (existing code)
4. **AUTO-SAVE**: Save complete blockchain to disk
5. Create backup if checkpoint interval reached (every 1000 blocks)

### Data Storage Format:

```json
{
  "metadata": {
    "timestamp": 1699564800.123,
    "block_height": 5000,
    "checksum": "abc123...",
    "version": "1.0"
  },
  "blockchain": {
    "chain": [...],
    "pending_transactions": [...],
    "difficulty": 4,
    "stats": {...}
  }
}
```

## Recovery Scenarios

### Scenario 1: Normal Shutdown/Restart

1. Blockchain saved after each block
2. On restart: Load from `blockchain.json`
3. Resume mining from last block

### Scenario 2: Corrupted Main File

1. Checksum verification fails
2. Auto-recovery from most recent backup
3. If backups corrupted: Recover from checkpoint
4. Continue operations from recovered state

### Scenario 3: Manual Recovery

```python
# List available backups
backups = blockchain.list_backups()

# Restore from specific backup
success, message = blockchain.restore_from_backup('blockchain_backup_20251109_143000.json')

# Verify integrity
valid, message = blockchain.verify_blockchain_integrity()
```

## File Structure

```
aixn/
├── data/
│   ├── blockchain.json              # Main blockchain file
│   ├── blockchain_metadata.json     # Quick metadata access
│   ├── backups/
│   │   ├── blockchain_backup_20251109_120000.json
│   │   ├── blockchain_backup_20251109_130000.json
│   │   └── ... (max 10 backups kept)
│   └── checkpoints/
│       ├── checkpoint_1000.json
│       ├── checkpoint_2000.json
│       ├── checkpoint_3000.json
│       └── ...
```

## Testing Integration

Add this test code to verify the integration:

```python
# test_persistence_integration.py

from core.blockchain import Blockchain
from core.wallet import Wallet

# Create blockchain
blockchain = Blockchain()

# Mine some blocks
wallet = Wallet()
for i in range(5):
    blockchain.mine_pending_transactions(wallet.address)

# Verify auto-save worked
valid, message = blockchain.verify_blockchain_integrity()
print(f"Integrity check: {valid} - {message}")

# List backups
backups = blockchain.list_backups()
print(f"Backups: {len(backups)}")

# List checkpoints
checkpoints = blockchain.list_checkpoints()
print(f"Checkpoints: {len(checkpoints)}")

# Create new blockchain instance (simulates restart)
blockchain2 = Blockchain()
print(f"Reloaded blockchain: {len(blockchain2.chain)} blocks")

# Verify chain integrity
assert len(blockchain2.chain) == len(blockchain.chain)
assert blockchain2.chain[-1].hash == blockchain.chain[-1].hash
print("Persistence test PASSED!")
```

## Performance Considerations

- **Atomic writes**: Uses temp file + rename for crash safety
- **Checksums**: SHA-256 verification on every load
- **Backups**: Created before overwrites (max 10 kept)
- **Checkpoints**: Every 1000 blocks (configurable)
- **Thread-safe**: All operations use locks

## Configuration

Adjust settings in `BlockchainStorageConfig`:

```python
class BlockchainStorageConfig:
    CHECKPOINT_INTERVAL = 1000    # Checkpoint every N blocks
    MAX_BACKUPS = 10              # Max backups to keep
    AUTO_SAVE_INTERVAL = 1        # Auto-save every N blocks
```

## Security Notes

1. **Checksums**: SHA-256 checksums prevent silent corruption
2. **Atomic writes**: No partial writes (temp file + rename)
3. **Backups**: Multiple recovery points
4. **Validation**: Chain validation on load
5. **Permissions**: Data directory should be protected

## Maintenance

### Manual Backup

```python
# Force backup creation
success, message = blockchain.save_blockchain(create_backup=True)
```

### Cleanup Old Data

```python
# Old backups are automatically cleaned (keeps 10 most recent)
# Checkpoints are kept indefinitely (small files, useful for long-term recovery)
```

### Verify Integrity

```python
# Check blockchain file integrity
valid, message = blockchain.verify_blockchain_integrity()
if not valid:
    print(f"WARNING: {message}")
    # Attempt recovery
    success, message = blockchain.reload_blockchain()
```

## Summary

The persistence system provides:

- Automatic saving after each block
- Crash recovery with checksums
- Multiple backup layers (backups + checkpoints)
- Thread-safe operations
- Zero data loss on proper shutdown
- Minimal data loss on crash (max 1 block)
- Easy manual recovery options
