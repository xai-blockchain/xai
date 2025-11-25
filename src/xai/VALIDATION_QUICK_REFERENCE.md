# XAI Blockchain - Chain Validation Quick Reference

## One-Liner Integration

```python
from core.blockchain_loader import load_blockchain_with_validation
success, blockchain_data, msg = load_blockchain_with_validation(verbose=True)
```

---

## Command-Line Usage

```bash
# Basic validation
python scripts/validate_chain.py

# Save detailed report
python scripts/validate_chain.py --report

# Quiet mode
python scripts/validate_chain.py --quiet

# Custom data directory
python scripts/validate_chain.py --data-dir /custom/path
```

---

## What Gets Validated

| Check | Description | Critical? |
|-------|-------------|-----------|
| Genesis Block | Index 0, hash "0", valid hash | ✅ Yes |
| Chain Integrity | Hash linkage, sequential indices | ✅ Yes |
| Proof-of-Work | Difficulty requirements met | ✅ Yes |
| Signatures | ECDSA signature verification | ✅ Yes |
| UTXO Set | No double-spends, valid UTXOs | ✅ Yes |
| Balances | No negative balances | ✅ Yes |
| Supply Cap | ≤ 121M XAI total | ✅ Yes |
| Merkle Roots | Transaction integrity | ⚠️ Error |

---

## Files Created

```
xai/
├── core/
│   ├── chain_validator.py          (950+ lines - validator engine)
│   ├── blockchain_loader.py         (350+ lines - loader + recovery)
│   └── CHAIN_VALIDATION_README.md   (documentation)
├── scripts/
│   └── validate_chain.py            (150+ lines - CLI tool)
├── tests/
│   └── test_chain_validator.py      (400+ lines - unit tests)
└── docs/
    ├── CHAIN_VALIDATION_INTEGRATION.md (integration guide)
    ├── CHAIN_VALIDATION_SUMMARY.md     (implementation summary)
    └── VALIDATION_QUICK_REFERENCE.md   (this file)
```

---

## Recovery Process

```
Validation Failed
    ↓
Try Recent Backups (newest first)
    ↓ (all fail)
Try Checkpoints (newest first)
    ↓ (all fail)
Report Failure + Recommend Resync
```

---

## Integration Examples

### With Blockchain Class

```python
from core.blockchain_loader import BlockchainLoader

class Blockchain:
    def __init__(self):
        # Load and validate on startup
        loader = BlockchainLoader(max_supply=121000000.0)
        success, data, msg = loader.load_and_validate(verbose=True)

        if success:
            self._restore_from_dict(data)
        else:
            print(f"Failed: {msg}")
```

### With Node Startup

```python
class BlockchainNode:
    def __init__(self):
        from core.blockchain_loader import load_blockchain_with_validation

        success, blockchain_data, msg = load_blockchain_with_validation()

        if not success:
            print(f"CRITICAL: {msg}")
            sys.exit(1)

        self.blockchain = self._init_from_data(blockchain_data)
```

### Standalone Validation

```python
from core.chain_validator import ChainValidator

validator = ChainValidator(max_supply=121000000.0, verbose=True)
report = validator.validate_chain(blockchain_data)

if report.success:
    print("✓ Valid")
else:
    print(f"✗ Invalid: {len(report.get_critical_issues())} critical issues")
```

---

## Validation Report Structure

```json
{
  "success": true/false,
  "total_blocks": 12345,
  "total_transactions": 67890,
  "validation_time": 12.34,
  "utxo_count": 5678,
  "total_supply": 22400000.0,
  "validations": {
    "genesis_valid": true,
    "chain_integrity": true,
    "signatures_valid": true,
    "pow_valid": true,
    "balances_consistent": true,
    "supply_cap_valid": true,
    "merkle_roots_valid": true
  },
  "issues": {
    "critical": 0,
    "errors": 0,
    "warnings": 0
  }
}
```

---

## Common Issues

| Issue | Meaning | Action |
|-------|---------|--------|
| Checksum failed | File corrupted | Auto-recovery from backup |
| Invalid signature | Transaction tampered | Critical - requires backup |
| Supply cap exceeded | Unauthorized minting | Critical - blockchain invalid |
| Block hash invalid | Corruption or attack | Auto-recovery attempted |
| Negative balance | UTXO corruption | Requires backup recovery |

---

## Performance

| Chain Size | Time |
|------------|------|
| < 1K blocks | < 1s |
| 1K-10K | 1-10s |
| 10K-100K | 10-60s |
| > 100K | 1-5min |

---

## API Quick Reference

### ChainValidator

```python
validator = ChainValidator(
    max_supply=121000000.0,  # Supply cap
    verbose=True              # Print progress
)

report = validator.validate_chain(
    blockchain_data,              # Blockchain dict
    expected_genesis_hash=None    # Optional strict check
)
```

### BlockchainLoader

```python
loader = BlockchainLoader(
    data_dir=None,                # Custom data dir
    max_supply=121000000.0,       # Supply cap
    expected_genesis_hash=None    # Genesis hash
)

success, blockchain_data, msg = loader.load_and_validate(
    verbose=True  # Print progress
)

report = loader.get_validation_report()
```

### ValidationReport

```python
report.success              # bool: Overall success
report.total_blocks         # int: Total blocks
report.total_transactions   # int: Total transactions
report.validation_time      # float: Time taken (seconds)
report.total_supply         # float: Total XAI supply
report.utxo_count          # int: Number of addresses

# Individual checks
report.genesis_valid
report.chain_integrity
report.signatures_valid
report.pow_valid
report.balances_consistent
report.supply_cap_valid
report.merkle_roots_valid

# Issues
report.get_critical_issues()  # Critical failures
report.get_error_issues()     # Errors
report.get_warning_issues()   # Warnings
report.to_dict()             # JSON export
```

---

## Testing

```bash
# Run all tests
python tests/test_chain_validator.py

# Verbose output
python tests/test_chain_validator.py -v
```

---

## Configuration

```python
# Custom supply cap
ChainValidator(max_supply=200000000.0)

# Expected genesis hash
BlockchainLoader(expected_genesis_hash="abc123...")

# Custom data directory
BlockchainLoader(data_dir="/custom/path")

# Quiet mode
load_and_validate(verbose=False)
```

---

## Exit Codes (validate_chain.py)

- `0` - Success (chain valid)
- `1` - Failure (chain invalid)
- `2` - Error (script error)

---

## Issue Severity

- **Critical**: Blockchain unusable (invalid hashes, broken chain)
- **Error**: Serious issues (invalid signatures, merkle roots)
- **Warning**: Minor issues (future timestamps, unusual patterns)

---

## Best Practices

1. ✅ **Always validate on startup**
2. ✅ **Monitor validation reports**
3. ✅ **Keep backups current**
4. ✅ **Test recovery process**
5. ✅ **Run periodic validations**

---

## Emergency Recovery

If validation fails and auto-recovery doesn't work:

```python
from core.blockchain_persistence import BlockchainStorage

storage = BlockchainStorage()

# List available backups
backups = storage.list_backups()
print(backups)

# Manually restore specific backup
success, data, msg = storage.restore_from_backup("blockchain_backup_20250101_120000.json")

# List checkpoints
checkpoints = storage.list_checkpoints()
print(checkpoints)
```

---

## Support Files

- **Integration Guide**: `CHAIN_VALIDATION_INTEGRATION.md`
- **Full README**: `core/CHAIN_VALIDATION_README.md`
- **Summary**: `CHAIN_VALIDATION_SUMMARY.md`
- **This Reference**: `VALIDATION_QUICK_REFERENCE.md`

---

## Status

✅ **Implementation**: Complete
✅ **Testing**: Comprehensive
✅ **Documentation**: Complete
✅ **Production**: Ready

---

**Need More Help?**
- Read `CHAIN_VALIDATION_INTEGRATION.md` for detailed integration steps
- Read `core/CHAIN_VALIDATION_README.md` for complete feature documentation
- Run `python scripts/validate_chain.py --help` for CLI options
