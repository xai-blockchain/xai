# Blockchain.py Refactoring - Quick Start Guide

This guide provides step-by-step instructions for implementing the refactoring plan.

## Prerequisites

Before starting:
- [ ] Read `BLOCKCHAIN_REFACTORING_PLAN.md` (comprehensive analysis)
- [ ] Review `BLOCKCHAIN_METHOD_MAPPING.md` (method-by-method breakdown)
- [ ] Study `BLOCKCHAIN_ARCHITECTURE_DIAGRAM.txt` (visual overview)
- [ ] Ensure all tests currently pass: `pytest tests/ -v`
- [ ] Create a feature branch: `git checkout -b refactor/blockchain-modularization`

## Phase 1: Foundation Modules (Start Here)

### Step 1.1: Extract blockchain_wal.py

**Why first?** Self-contained, no dependencies, critical for crash safety.

```bash
# Create the file
touch src/xai/core/blockchain_wal.py
```

**Implementation:**
```python
"""Write-Ahead Log for crash-safe chain reorganization"""
from __future__ import annotations
import json
import os
import time
from typing import TYPE_CHECKING, Any

from xai.core.structured_logger import get_structured_logger

if TYPE_CHECKING:
    from xai.core.blockchain import Blockchain

class BlockchainWAL:
    """Manages write-ahead logging for atomic chain reorganizations"""

    def __init__(self, blockchain: 'Blockchain'):
        self.blockchain = blockchain
        self.logger = get_structured_logger()
        self.wal_path = os.path.join(blockchain.data_dir, "reorg_wal.json")

    def write_reorg_wal(self, old_tip: str | None, new_tip: str | None,
                        fork_point: int | None) -> dict[str, Any]:
        """Record start of chain reorganization (lines 4039-4092)"""
        # Copy method body from blockchain.py:4039-4092
        # ... implementation ...
        pass

    def commit_reorg_wal(self, wal_entry: dict[str, Any]) -> None:
        """Mark reorg as committed (lines 4094-4126)"""
        # Copy method body from blockchain.py:4094-4126
        pass

    def rollback_reorg_wal(self, wal_entry: dict[str, Any]) -> None:
        """Mark reorg as rolled back (lines 4127-4158)"""
        # Copy method body from blockchain.py:4127-4158
        pass

    def recover_from_incomplete_reorg(self) -> None:
        """Detect and recover from crash mid-reorg (lines 4160-4211)"""
        # Copy method body from blockchain.py:4160-4211
        pass
```

**Update blockchain.py:**
```python
# Add import at top
from xai.core.blockchain_wal import BlockchainWAL

class Blockchain:
    def _init_storage(self, ...):
        # ... existing code ...
        self.wal = BlockchainWAL(self)
        self.wal.recover_from_incomplete_reorg()  # was self._recover_from_incomplete_reorg()

    # Replace methods with delegators
    def _write_reorg_wal(self, old_tip, new_tip, fork_point):
        return self.wal.write_reorg_wal(old_tip, new_tip, fork_point)

    def _commit_reorg_wal(self, wal_entry):
        return self.wal.commit_reorg_wal(wal_entry)

    def _rollback_reorg_wal(self, wal_entry):
        return self.wal.rollback_reorg_wal(wal_entry)

    def _recover_from_incomplete_reorg(self):
        return self.wal.recover_from_incomplete_reorg()
```

**Test:**
```bash
pytest tests/test_blockchain.py -k wal -v
pytest tests/test_blockchain.py -k reorg -v
```

**Commit:**
```bash
git add src/xai/core/blockchain_wal.py src/xai/core/blockchain.py
git commit -m "refactor: extract WAL logic to blockchain_wal.py

- Move write-ahead log methods to dedicated module
- Maintain crash recovery functionality
- 176 lines extracted from blockchain.py
- All tests passing"
```

### Step 1.2: Extract blockchain_serialization.py

```bash
touch src/xai/core/blockchain_serialization.py
```

**Key methods to extract (from METHOD_MAPPING.md):**
- `deserialize_block` (836-873)
- `deserialize_chain` (874-908)
- `_load_from_disk` (909-990)
- `_load_from_disk_full` (991-1011)
- `to_dict` (3706-3727)
- `from_dict` (3728-3777)
- `_block_to_full_dict` (3778-3799)
- `get_blockchain_data_provider` (3813-3829)

**Test:**
```bash
pytest tests/test_blockchain.py -k "serial or load or dict" -v
```

**Commit after tests pass**

### Step 1.3: Extract transaction_query.py

```bash
touch src/xai/core/transaction_query.py
```

**Key methods:**
- `get_transaction_history_window` (713-806)
- `get_transaction_history` (807-814)
- `_transaction_from_dict` (815-835)

**Test and commit**

## Phase 2: Business Logic Modules

### Step 2.1: Extract blockchain_contracts.py

```bash
touch src/xai/core/blockchain_contracts.py
```

**Methods (11 total):** See METHOD_MAPPING.md lines 1193-1401

**Template:**
```python
"""Smart contract lifecycle management"""
from __future__ import annotations
import hashlib
import json
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xai.core.blockchain import Blockchain

class BlockchainContracts:
    def __init__(self, blockchain: 'Blockchain'):
        self.blockchain = blockchain
        self.logger = get_structured_logger()

    def derive_contract_address(self, sender: str, nonce: int | None) -> str:
        """Lines 1193-1200"""
        pass

    # ... add remaining 10 methods
```

### Step 2.2: Extract blockchain_trading.py

```bash
touch src/xai/core/blockchain_trading.py
```

**Methods (7 total):** See METHOD_MAPPING.md lines 3831-4034

**Important:** This module includes ECDSA signature verification. Test thoroughly.

### Step 2.3: Extract blockchain_governance.py

```bash
touch src/xai/core/blockchain_governance.py
```

**Methods (14 total):** See METHOD_MAPPING.md

**Note:** Largest business logic module (~470 lines). Take extra care with testing.

### Step 2.4: Extract transaction_factory.py

```bash
touch src/xai/core/transaction_factory.py
```

**Methods (2 total):**
- `validate_transaction` (1630-1633)
- `create_transaction` (1634-1795) - LARGE method with sponsorship logic

## Phase 3: Core Validation Modules (High Risk)

### Step 3.1: Extract block_validation_helpers.py

**Why first?** Utilities used by other validators. No state modification.

```bash
touch src/xai/core/block_validation_helpers.py
```

**Methods (8 total):** Lines 2873-3074

### Step 3.2: Extract block_validator.py

```bash
touch src/xai/core/block_validator.py
```

**Methods (4 total):** Lines 1796-2041

**Critical:** Block validation is on the hot path. Performance test after extraction.

### Step 3.3: Extract orphan_processor.py

```bash
touch src/xai/core/orphan_processor.py
```

**Methods (4 total):** Lines 3085-3371

### Step 3.4: Extract chain_validator.py (LARGEST MODULE)

**Warning:** This is the most complex extraction (~850 lines).

```bash
touch src/xai/core/chain_validator.py
```

**Methods (9 total):** Lines 2042-2872

**Testing strategy:**
```bash
# Run comprehensive validation tests
pytest tests/test_blockchain.py -k "validate or chain or fork or reorg" -v

# Run performance benchmarks
pytest tests/benchmarks/ -v

# Check for regressions in chain sync
pytest tests/test_chain_sync.py -v
```

**Consider:** Break this into TWO modules if complexity is too high:
- `chain_validator.py` - Validation logic
- `chain_reorganizer.py` - Reorg and fork handling

## Phase 4: System Coordination (Critical)

### Step 4.1: Extract blockchain_finality.py

```bash
touch src/xai/core/blockchain_finality.py
```

**Methods (4 total):** Lines 543-573, 637-709

### Step 4.2: Extract blockchain_recovery.py

```bash
touch src/xai/core/blockchain_recovery.py
```

**Methods (2 total):** Lines 1406-1613

**Critical:** Chain reset and checkpoint restore are destructive operations. Test exhaustively.

### Step 4.3: Extract blockchain_initialization.py (LAST)

**Why last?** Coordinates all other modules. Requires all previous modules to exist.

```bash
touch src/xai/core/blockchain_initialization.py
```

**Methods (9 total):** Lines 129-541

## Testing Strategy

### After Each Module Extraction

1. **Unit tests** - Test the new module in isolation
2. **Integration tests** - Test with blockchain coordinator
3. **Regression tests** - Run full test suite
4. **Type checking** - `mypy src/xai/core/blockchain*.py`
5. **Linting** - `pylint src/xai/core/blockchain*.py`

### Before Merging to Main

```bash
# Full test suite
pytest tests/ -v --cov=src/xai/core

# Coverage report
pytest tests/ --cov=src/xai/core --cov-report=html

# Performance benchmarks
pytest tests/benchmarks/ -v

# Check for circular imports
python -c "from xai.core.blockchain import Blockchain; print('OK')"

# Type checking
mypy src/xai/core/
```

## Common Pitfalls & Solutions

### Pitfall 1: Circular Imports

**Problem:** `blockchain.py` imports module, module imports `Blockchain`

**Solution:** Use TYPE_CHECKING
```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xai.core.blockchain import Blockchain

class MyModule:
    def __init__(self, blockchain: 'Blockchain'):  # String annotation
        self.blockchain = blockchain
```

### Pitfall 2: Missing Dependencies

**Problem:** Extracted module references `self.something` that doesn't exist

**Solution:** Pass dependencies explicitly or use `self.blockchain.something`
```python
class MyModule:
    def method(self):
        # Instead of: self.utxo_manager
        # Use: self.blockchain.utxo_manager
        balance = self.blockchain.utxo_manager.get_balance(address)
```

### Pitfall 3: Breaking Existing Tests

**Problem:** Tests import methods directly from blockchain module

**Solution:** Keep delegators in blockchain.py for backward compatibility
```python
class Blockchain:
    def old_method(self, *args, **kwargs):
        """Backward compatibility - delegates to new module"""
        return self.module_name.old_method(*args, **kwargs)
```

### Pitfall 4: Lost Context in Logging

**Problem:** Log messages don't include enough context after extraction

**Solution:** Pass context from blockchain to module
```python
self.logger.info(
    "Contract registered",
    address=address,
    chain_height=self.blockchain.chain_length,  # Add context
)
```

## Success Checklist

After completing all phases:

- [ ] `blockchain.py` is < 1000 lines
- [ ] All extracted modules < 1000 lines
- [ ] No circular import errors
- [ ] All tests pass (`pytest tests/ -v`)
- [ ] Coverage > 90% (`pytest --cov`)
- [ ] Type checking passes (`mypy src/xai/core/`)
- [ ] No linting errors (`pylint src/xai/core/`)
- [ ] Performance benchmarks show no regression
- [ ] Documentation updated (module docstrings)
- [ ] Code review completed
- [ ] PR merged to main

## Rollback Plan

If extraction causes critical issues:

```bash
# Identify problematic commit
git log --oneline | grep refactor

# Revert specific commit
git revert <commit-hash>

# Or reset to pre-refactoring state
git reset --hard <commit-before-refactoring>

# Force push if already pushed (use with caution)
git push --force-with-lease origin refactor/blockchain-modularization
```

## Timeline Tracking

| Phase | Estimated | Actual | Status |
|-------|-----------|--------|--------|
| Phase 1: Foundation | 2-3 hrs | | ⬜ Not Started |
| Phase 2: Business Logic | 4-5 hrs | | ⬜ Not Started |
| Phase 3: Core Validation | 6-8 hrs | | ⬜ Not Started |
| Phase 4: Coordination | 3-4 hrs | | ⬜ Not Started |
| Testing & Integration | 4-6 hrs | | ⬜ Not Started |
| **Total** | **19-26 hrs** | | |

## Next Steps

1. **Start with Phase 1, Step 1.1** (blockchain_wal.py)
2. **Test thoroughly after each extraction**
3. **Commit small, atomic changes**
4. **Document any deviations from plan**
5. **Update this checklist as you progress**

## Questions?

Refer to detailed documentation:
- Comprehensive plan: `BLOCKCHAIN_REFACTORING_PLAN.md`
- Method mapping: `BLOCKCHAIN_METHOD_MAPPING.md`
- Architecture: `BLOCKCHAIN_ARCHITECTURE_DIAGRAM.txt`
- Summary: `BLOCKCHAIN_REFACTORING_SUMMARY.md`
