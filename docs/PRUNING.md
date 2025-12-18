# XAI Blockchain Pruning Guide

Block pruning allows nodes to reduce disk space usage while maintaining chain security and functionality.

## Overview

The XAI blockchain implements configurable block retention policies that enable operators to balance disk space usage against data availability. This is critical for resource-constrained environments and cost optimization.

### Key Features

- **Multiple retention modes**: Block count, time-based, disk threshold, or combined
- **Archival support**: Optional compression before deletion
- **Header preservation**: Keep block headers for SPV verification
- **Finality protection**: Never prune blocks within finality depth
- **Zero-downtime**: Can update policies at runtime
- **CLI management**: Simple command-line tools for operators

## Pruning Modes

### None (Archival)
```bash
export XAI_PRUNE_MODE=none
```
Keeps complete blockchain history. Suitable for archival nodes and block explorers.

### Block Count
```bash
export XAI_PRUNE_MODE=blocks
export XAI_PRUNE_KEEP_BLOCKS=1000
```
Retains the most recent N blocks. Genesis block is always kept.

### Time-Based
```bash
export XAI_PRUNE_MODE=days
export XAI_PRUNE_KEEP_DAYS=30
```
Retains blocks from the last N days.

### Combined (Most Restrictive)
```bash
export XAI_PRUNE_MODE=both
export XAI_PRUNE_KEEP_BLOCKS=1000
export XAI_PRUNE_KEEP_DAYS=30
```
Keeps whichever is more restrictive (retains more blocks).

### Disk Space Threshold
```bash
export XAI_PRUNE_MODE=space
export XAI_PRUNE_DISK_THRESHOLD_GB=50
```
Prunes when blockchain data exceeds threshold.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `XAI_PRUNE_MODE` | `none` | Pruning mode: none, blocks, days, both, space |
| `XAI_PRUNE_KEEP_BLOCKS` | `1000` | Number of recent blocks to retain |
| `XAI_PRUNE_KEEP_DAYS` | `30` | Number of days to retain |
| `XAI_PRUNE_AUTO` | `false` | Enable automatic pruning on new blocks |
| `XAI_PRUNE_ARCHIVE` | `true` | Compress blocks before deletion |
| `XAI_PRUNE_ARCHIVE_PATH` | `data/archive` | Archive directory path |
| `XAI_PRUNE_DISK_THRESHOLD_GB` | `50.0` | Disk threshold in gigabytes |
| `XAI_PRUNE_MIN_FINALIZED_DEPTH` | `100` | Safety margin - never prune recent blocks |
| `XAI_PRUNE_KEEP_HEADERS` | `true` | Preserve headers for pruned blocks |

### Example Configuration

**Light Node (Mobile/IoT)**
```bash
export XAI_PRUNE_MODE=blocks
export XAI_PRUNE_KEEP_BLOCKS=500
export XAI_PRUNE_AUTO=true
export XAI_PRUNE_ARCHIVE=false
```

**Standard Node**
```bash
export XAI_PRUNE_MODE=days
export XAI_PRUNE_KEEP_DAYS=90
export XAI_PRUNE_ARCHIVE=true
```

**Archival Node**
```bash
export XAI_PRUNE_MODE=none
```

## CLI Usage

### Check Status
```bash
python3 -m xai.tools.node_prune_cli status
```

Shows:
- Current pruning mode and configuration
- Chain statistics (total blocks, prunable blocks)
- Historical statistics (blocks pruned, space saved)
- Disk usage

### Show Configuration
```bash
python3 -m xai.tools.node_prune_cli config
```

Displays environment variables and active policy.

### Dry Run (Preview)
```bash
python3 -m xai.tools.node_prune_cli run --dry-run
```

Shows what would be pruned without making changes.

### Run Pruning
```bash
# Use configured retention
python3 -m xai.tools.node_prune_cli run

# Override retention policy
python3 -m xai.tools.node_prune_cli run --keep-blocks 2000
python3 -m xai.tools.node_prune_cli run --keep-days 60
```

**Important**: Stop the node before running manual pruning operations.

### Archive Statistics
```bash
python3 -m xai.tools.node_prune_cli archive-stats
```

Shows archive directory size and block height range.

## Python API

### Basic Usage

```python
from xai.core.blockchain import Blockchain
from xai.core.pruning import BlockPruningManager, PruningPolicy, PruneMode

# Initialize blockchain
blockchain = Blockchain()

# Create pruning manager (uses config from environment)
manager = BlockPruningManager(blockchain)

# Check if pruning should run
if manager.should_prune():
    result = manager.prune_blocks()
    print(f"Pruned {result['pruned']} blocks")
```

### Custom Policy

```python
from xai.core.pruning import PruningPolicy, PruneMode

policy = PruningPolicy(
    mode=PruneMode.BLOCKS,
    retain_blocks=500,
    retain_days=30,
    archive_before_delete=True,
    archive_path="data/archive",
    disk_threshold_gb=25.0,
    min_finalized_depth=100,
    keep_headers_only=True,
)

manager = BlockPruningManager(blockchain, policy=policy)
```

### Runtime Policy Updates

```python
# Update policy without restarting
new_policy = PruningPolicy(
    mode=PruneMode.DAYS,
    retain_blocks=1000,
    retain_days=60,
    # ... other settings
)

manager.set_policy(new_policy)
```

### Query Status

```python
# Get detailed status
status = manager.get_status()
print(f"Mode: {status['mode']}")
print(f"Eligible blocks: {status['chain']['eligible_blocks']}")
print(f"Disk usage: {status['chain']['disk_usage_gb']:.2f} GB")

# Check if specific block is available
if manager.has_full_block(height=1000):
    print("Full block data available")
elif manager.is_block_pruned(height=1000):
    print("Block pruned (may have header only)")
```

## Integration with Node Modes

Pruning integrates with existing node modes:

```python
from xai.performance.node_modes import NodeModeManager

# Initialize with automatic config
mode_manager = NodeModeManager(blockchain, auto_configure=True)

# Pruning manager is initialized if PRUNE_MODE != 'none'
if mode_manager.pruning_manager:
    status = mode_manager.pruning_manager.get_status()
```

## Safety Guarantees

### Finality Protection

Blocks within `min_finalized_depth` of the chain tip are **never pruned**, ensuring:
- Safe chain reorganizations
- Recent blocks always available for validation
- No disruption to consensus

### Genesis Protection

The genesis block (height 0) is **always preserved** regardless of policy.

### Archive Verification

When archiving is enabled:
1. Block is serialized and compressed with gzip level 9
2. Archive file written atomically
3. Original block only pruned after successful archive
4. Failed archives prevent pruning

## Disk Space Calculation

Typical savings by mode:

| Node Type | Retention | Disk Usage (200k blocks) | Savings |
|-----------|-----------|--------------------------|---------|
| Archival | All blocks | 100 GB | 0% |
| Standard | 30 days (~21k blocks) | 11 GB | 89% |
| Light | 1000 blocks | 0.5 GB | 99.5% |

*Note: Actual savings depend on transaction volume and block size.*

## Archive Format

Archived blocks are stored as gzip-compressed JSON:

```
data/archive/
├── block_0001.json.gz
├── block_0002.json.gz
├── block_0003.json.gz
...
```

### Restoring from Archive

```python
# Restore specific block
block_data = manager.restore_block(height=1000)

if block_data:
    print(f"Restored block {height}")
else:
    print("Block not in archive")
```

Archives can also be manually extracted:

```bash
gunzip -c data/archive/block_1000.json.gz | jq
```

## Monitoring

### Prometheus Metrics (Future)

```python
# Suggested metrics for monitoring
pruning_mode{mode="blocks"}
pruning_retention_blocks 1000
pruning_eligible_blocks 500
pruning_disk_usage_bytes 10737418240
pruning_last_run_timestamp 1703001234
pruning_total_pruned_blocks 10000
```

### Logging

Pruning operations emit structured logs:

```json
{
  "event": "pruning.complete",
  "pruned": 100,
  "archived": 100,
  "space_saved": 52428800,
  "timestamp": "2025-12-18T10:30:00Z"
}
```

## Best Practices

### For Validators
- Use `mode=days` with 90+ day retention
- Enable archiving for audit compliance
- Set `min_finalized_depth=200` for safety
- Monitor disk usage alerts

### For RPC Nodes
- Use `mode=blocks` with 5000-10000 blocks
- Enable archiving for historical queries
- Keep headers for SPV clients

### For Light Clients
- Use `mode=blocks` with 500-1000 blocks
- Disable archiving to save space
- Set `min_finalized_depth=100` minimum

### For Archival Nodes
- Use `mode=none`
- Implement separate backup strategy
- Monitor disk capacity proactively

## Troubleshooting

### High Disk Usage After Pruning

Check archive directory size:
```bash
du -sh data/archive/
```

Archives consume space. To fully recover:
```bash
# After verifying backups exist elsewhere
rm -rf data/archive/
```

### Pruning Not Running

1. Check mode: `echo $XAI_PRUNE_MODE`
2. Verify eligibility: Run `--dry-run` to see what would be pruned
3. Check logs for errors

### Cannot Sync from Pruned Node

Pruned nodes cannot serve full historical data to new peers. Solutions:
- Bootstrap from archival node
- Use checkpoint sync
- Restore from backup before pruning

## Migration Guide

### From Old PrunedNode to New System

```python
# Old way (deprecated)
from xai.performance.node_modes import PrunedNode
pruned = PrunedNode(blockchain, keep_blocks=1000)

# New way (recommended)
from xai.core.pruning import BlockPruningManager
manager = BlockPruningManager(blockchain)
# Configure via environment variables
```

The old `PrunedNode` class is maintained for backward compatibility but new deployments should use `BlockPruningManager`.

## Security Considerations

### Data Availability

Pruned nodes:
- Cannot serve full historical blocks to peers
- May fail SPV proofs for pruned blocks
- Unsuitable for block explorers

### Archive Integrity

- Archives are **not encrypted** - sensitive data remains readable
- Archives are **not authenticated** - verify hashes before restoration
- Archives stored locally only - implement backup strategy

### Finality Assumptions

`min_finalized_depth` assumes:
- Chain reorganizations don't exceed this depth
- Consensus is functioning correctly
- Validator set is not compromised

Increase this value on networks with:
- High reorg frequency
- Low validator count
- Recent consensus bugs

## Performance Impact

Pruning operations are:
- **CPU-intensive**: JSON serialization + gzip compression
- **IO-intensive**: Archive writes + block deletions
- **Memory-safe**: Streams large datasets

Run during low-traffic periods or use `XAI_PRUNE_AUTO=false` for manual scheduling.

## Future Enhancements

Planned features:
- [ ] Incremental pruning (background)
- [ ] Pruning progress indicators
- [ ] Archive encryption
- [ ] Remote archive storage (S3, IPFS)
- [ ] Pruning scheduler (cron-like)
- [ ] Metrics export
- [ ] Pruning webhooks/notifications

## References

- [Bitcoin Core Pruning](https://bitcoin.org/en/full-node#reduce-storage)
- [Ethereum State Pruning](https://blog.ethereum.org/2021/03/03/geth-v1-10-0)
- [Node Operation Modes](../src/xai/performance/node_modes.py)
