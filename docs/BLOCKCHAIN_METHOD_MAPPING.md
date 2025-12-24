# Blockchain.py Method Mapping - Detailed Extraction Plan

This document maps every method in blockchain.py to its target module with exact line numbers.

## Module 1: blockchain_serialization.py

**Responsibility:** Block/chain serialization, disk loading, export/import

| Method | Lines | Description |
|--------|-------|-------------|
| `deserialize_block` (classmethod) | 836-873 | Convert dict to Block object |
| `deserialize_chain` (classmethod) | 874-908 | Convert list of dicts to chain |
| `_load_from_disk` | 909-990 | Fast header-only chain loading |
| `_load_from_disk_full` | 991-1011 | Full block loading with transactions |
| `to_dict` | 3706-3727 | Serialize blockchain to dict |
| `from_dict` | 3728-3777 | Deserialize blockchain from dict |
| `_block_to_full_dict` | 3778-3799 | Convert block to full dict representation |
| `get_blockchain_data_provider` | 3813-3829 | Return API data provider interface |

**Total:** 8 methods, ~260 lines

## Module 2: blockchain_wal.py

**Responsibility:** Write-ahead logging for crash recovery

| Method | Lines | Description |
|--------|-------|-------------|
| `_write_reorg_wal` | 4039-4092 | Record start of chain reorganization |
| `_commit_reorg_wal` | 4094-4126 | Mark reorg as successfully completed |
| `_rollback_reorg_wal` | 4127-4158 | Mark reorg as rolled back |
| `_recover_from_incomplete_reorg` | 4160-4211 | Detect and recover from crash mid-reorg |

**Total:** 4 methods, ~176 lines

## Module 3: transaction_query.py

**Responsibility:** Transaction history queries and address indexing

| Method | Lines | Description |
|--------|-------|-------------|
| `get_transaction_history_window` | 713-806 | Indexed query with pagination |
| `get_transaction_history` | 807-814 | Legacy wrapper for compatibility |
| `_transaction_from_dict` (staticmethod) | 815-835 | Deserialize transaction from dict |

**Total:** 3 methods, ~123 lines

## Module 4: blockchain_contracts.py

**Responsibility:** Smart contract lifecycle management

| Method | Lines | Description |
|--------|-------|-------------|
| `derive_contract_address` | 1193-1200 | Generate deterministic contract address |
| `register_contract` | 1202-1225 | Register new contract deployment |
| `get_contract_state` | 1227-1240 | Retrieve contract state snapshot |
| `normalize_contract_abi` | 1242-1271 | Validate and normalize ABI JSON |
| `store_contract_abi` | 1273-1295 | Persist contract ABI with verification |
| `get_contract_abi` | 1296-1308 | Retrieve stored ABI |
| `get_contract_interface_metadata` | 1310-1326 | Get interface detection results |
| `update_contract_interface_metadata` | 1328-1351 | Update interface support flags |
| `get_contract_events` | 1352-1376 | Query contract event logs |
| `_rebuild_contract_state` | 1377-1387 | Reconstruct contract state from chain |
| `sync_smart_contract_vm` | 1388-1401 | Synchronize VM with contract state |

**Total:** 11 methods, ~208 lines

## Module 5: blockchain_trading.py

**Responsibility:** Decentralized trading system with ECDSA verification

| Method | Lines | Description |
|--------|-------|-------------|
| `register_trade_session` | 3831-3836 | Create trade session token |
| `record_trade_event` | 3838-3842 | Log trade events for diagnostics |
| `submit_trade_order` | 3844-3958 | Submit order with ECDSA signature verification |
| `_normalize_trade_order` | 3959-4018 | Validate and normalize order fields |
| `get_trade_orders` | 4020-4022 | List active trade orders |
| `get_trade_matches` | 4024-4026 | List trade matches |
| `reveal_trade_secret` | 4028-4033 | Settle HTLC-based trade |

**Total:** 7 methods, ~203 lines

## Module 6: blockchain_governance.py

**Responsibility:** On-chain governance proposal system

| Method | Lines | Description |
|--------|-------|-------------|
| `_rebuild_governance_state_from_chain` | 1012-1022 | Replay governance from genesis |
| `_transaction_to_governance_transaction` | 1091-1115 | Convert tx to governance tx |
| `_find_pending_proposal_payload` | 1116-1128 | Locate proposal data in mempool |
| `_process_governance_block_transactions` | 1129-1139 | Process governance txs in block |
| `_apply_governance_transaction` | 1140-1165 | Apply governance state change |
| `_run_governance_execution` | 1166-1191 | Execute approved proposal |
| `submit_governance_proposal` | 3433-3490 | Submit new governance proposal |
| `cast_governance_vote` | 3492-3535 | Cast vote on proposal |
| `submit_code_review` | 3537-3583 | Submit code review for proposal |
| `execute_governance_proposal` | 3584-3619 | Execute approved proposal (public API) |
| `vote_implementation` | 3620-3663 | Vote on implementation PR |
| `execute_proposal` | 3664-3676 | Execute proposal by ID |
| `get_governance_proposal` | 3677-3682 | Retrieve proposal details |
| `list_governance_proposals` | 3683-3705 | List proposals by status |

**Total:** 14 methods, ~451 lines

## Module 7: transaction_factory.py

**Responsibility:** Transaction creation with sponsorship and nonces

| Method | Lines | Description |
|--------|-------|-------------|
| `validate_transaction` | 1630-1633 | Validate single transaction |
| `create_transaction` | 1634-1795 | Create transaction with full validation and sponsorship |

**Total:** 2 methods, ~165 lines

## Module 8: block_validator.py

**Responsibility:** Block validation before chain addition

| Method | Lines | Description |
|--------|-------|-------------|
| `add_block` | 1796-1813 | Public entry point with chain lock |
| `_add_block_internal` | 1815-2008 | Core validation and state update logic |
| `verify_block_signature` | 2009-2037 | ECDSA signature verification for blocks |
| `calculate_merkle_root` | 2038-2041 | Delegate to BlockProcessor |

**Total:** 4 methods, ~245 lines

## Module 9: block_validation_helpers.py

**Responsibility:** Validation utility functions

| Method | Lines | Description |
|--------|-------|-------------|
| `is_chain_valid` | 2873-2882 | Quick chain validity check |
| `_extract_timestamp` | 2883-2894 | Extract timestamp from block/header |
| `_median_time_from_history` | 2895-2915 | Calculate median timestamp |
| `_validate_block_timestamp` | 2916-2963 | Validate block timestamp rules |
| `_validate_header_version` | 2964-2992 | Check block header version |
| `_block_within_size_limits` | 2993-3022 | Enforce block size limits |
| `_record_timestamp_metrics` | 3023-3070 | Record timestamp drift metrics |
| `get_recent_timestamp_drift` | 3071-3074 | Get recent drift history |

**Total:** 8 methods, ~197 lines

## Module 10: chain_validator.py

**Responsibility:** Full chain validation and reorganization

| Method | Lines | Description |
|--------|-------|-------------|
| `validate_chain` | 2042-2279 | Full chain validation with security checks |
| `_calculate_block_work` | 2280-2313 | Calculate PoW for single block |
| `_calculate_chain_work` | 2315-2330 | Calculate cumulative chain work |
| `_handle_fork` | 2332-2391 | Handle competing fork blocks |
| `_prune_orphans` | 2393-2407 | Remove old orphan blocks |
| `_attempt_lineage_sync` | 2409-2463 | Sync using block ancestry |
| `replace_chain` | 2465-2777 | Replace chain with longer valid chain |
| `_find_fork_point` | 2778-2786 | Find where chains diverge |
| `_validate_chain_structure` | 2787-2872 | Validate chain structure integrity |

**Total:** 9 methods, ~830 lines

## Module 11: orphan_processor.py

**Responsibility:** Orphan block and transaction handling

| Method | Lines | Description |
|--------|-------|-------------|
| `_add_block_to_chain` | 3085-3177 | Add validated block to chain |
| `_process_orphan_blocks` | 3178-3248 | Attempt to promote orphan blocks |
| `_process_orphan_transactions` | 3249-3297 | Revalidate orphan transactions |
| `_check_orphan_chains_for_reorg` | 3298-3371 | Check if orphans form longer chain |

**Total:** 4 methods, ~286 lines

## Module 12: blockchain_finality.py

**Responsibility:** BFT finality and validator consensus

| Method | Lines | Description |
|--------|-------|-------------|
| `submit_finality_vote` | 637-685 | Record validator vote for block |
| `get_finality_certificate` | 687-699 | Retrieve finality certificate |
| `is_block_finalized` | 701-709 | Check if block reached finality |
| `_handle_finality_misbehavior` | 543-573 | Slash malicious validators |

**Total:** 4 methods, ~105 lines

## Module 13: blockchain_recovery.py

**Responsibility:** Chain reset and checkpoint restoration

| Method | Lines | Description |
|--------|-------|-------------|
| `reset_chain_state` | 1406-1505 | Reset blockchain to genesis |
| `restore_checkpoint` | 1507-1613 | Restore from checkpoint file |

**Total:** 2 methods, ~207 lines

## Module 14: blockchain_initialization.py

**Responsibility:** Bootstrap blockchain components

| Method | Lines | Description |
|--------|-------|-------------|
| `__init__` | 129-224 | Main initialization orchestrator |
| `_init_storage` | 225-281 | Initialize storage and indexes |
| `_init_consensus` | 282-345 | Load validator set and consensus params |
| `_init_mining` | 346-419 | Configure mining subsystem |
| `_init_governance` | 420-435 | Initialize governance state |
| `_initialize_finality_manager` | 436-446 | Create finality manager |
| `_initialize_slashing_manager` | 448-468 | Create slashing manager |
| `_load_validator_set` | 469-534 | Load validator identities |
| `_derive_address_from_public` | 536-541 | Derive address from pubkey |

**Total:** 9 methods, ~413 lines

## Module 15: blockchain_queries.py (Optional)

**Responsibility:** Simple query methods

| Method | Lines | Description |
|--------|-------|-------------|
| `get_block` | 587-597 | Get block by index |
| `get_block_by_hash` | 599-625 | Get block by hash |
| `get_circulating_supply` | 627-629 | Delegate to ChainState |
| `get_balance` | 631-635 | Delegate to ChainState |
| `get_total_supply` | 3800-3809 | Alias for circulating supply |

**Total:** 5 methods, ~60 lines

**Note:** These could remain in blockchain.py as simple delegators

## Supporting Methods (Stay in blockchain.py)

These methods coordinate between modules:

| Method | Lines | Description |
|--------|-------|-------------|
| `create_genesis_block` | 1402-1404 | Delegate to BlockProcessor |
| `get_latest_block` | 1614-1629 | Simple chain tip access |
| `_rebuild_nonce_tracker` | 1023-1059 | Coordinate nonce rebuild |
| `_record_state_snapshot` | 3372-3380 | Debugging snapshots |
| `compute_state_snapshot` | 3381-3401 | Delegate to ChainState |
| `get_stats` | 3402-3428 | Aggregate stats from all modules |
| `should_pause_mining` | 3075-3084 | Delegate to MiningCoordinator |

## Properties (Stay in blockchain.py)

| Property | Lines | Description |
|----------|-------|-------------|
| `blockchain` | 576-578 | Self-reference for compatibility |
| `utxo_set` | 581-583 | Delegate to UTXOManager |

## Inner Classes (Stay in blockchain.py)

| Class | Lines | Description |
|-------|-------|-------------|
| `_GamificationBlockchainAdapter` | 101-127 | Adapter for gamification modules |

## Summary by Module

| Module | Methods | Lines | Complexity |
|--------|---------|-------|------------|
| blockchain_serialization.py | 8 | ~260 | Low |
| blockchain_wal.py | 4 | ~176 | Low |
| transaction_query.py | 3 | ~123 | Low |
| blockchain_contracts.py | 11 | ~208 | Medium |
| blockchain_trading.py | 7 | ~203 | Medium |
| blockchain_governance.py | 14 | ~451 | High |
| transaction_factory.py | 2 | ~165 | Medium |
| block_validator.py | 4 | ~245 | High |
| block_validation_helpers.py | 8 | ~197 | Medium |
| chain_validator.py | 9 | ~830 | **Very High** |
| orphan_processor.py | 4 | ~286 | High |
| blockchain_finality.py | 4 | ~105 | Medium |
| blockchain_recovery.py | 2 | ~207 | High |
| blockchain_initialization.py | 9 | ~413 | High |
| **blockchain.py (remaining)** | ~20 | ~500-800 | Medium |

**Total Methods Extracted:** 89 of 105
**Total Methods Remaining:** ~16 (coordinators and delegators)

## Extraction Order (By Risk Level)

### Phase 1 - Low Risk (No State Modification)
1. blockchain_serialization.py - Pure conversion functions
2. blockchain_wal.py - Isolated file I/O
3. transaction_query.py - Read-only queries

### Phase 2 - Medium Risk (Business Logic)
4. blockchain_contracts.py - Contract lifecycle
5. blockchain_trading.py - Trade system
6. transaction_factory.py - Transaction creation
7. blockchain_finality.py - Finality voting

### Phase 3 - High Risk (Core Validation)
8. block_validation_helpers.py - Utility validators
9. block_validator.py - Block validation
10. orphan_processor.py - Orphan handling

### Phase 4 - Very High Risk (Chain Logic)
11. chain_validator.py - Chain validation and reorg
12. blockchain_governance.py - Governance execution

### Phase 5 - Critical (Coordination)
13. blockchain_recovery.py - State recovery
14. blockchain_initialization.py - Bootstrap

## Testing Checklist Per Module

For each extracted module, verify:

- [ ] All imports resolve correctly
- [ ] No circular dependencies
- [ ] Unit tests pass in isolation
- [ ] Integration tests with blockchain pass
- [ ] Type checking passes (mypy)
- [ ] Linting passes (pylint, black)
- [ ] No performance regression
- [ ] API backward compatibility maintained
- [ ] Documentation updated

## Migration Template

For each module extraction:

```python
# 1. Create new module file
from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xai.core.blockchain import Blockchain

class ModuleName:
    def __init__(self, blockchain: 'Blockchain'):
        self.blockchain = blockchain
        self.logger = get_structured_logger()

    def method_name(self, ...):
        # Extracted code here
        pass

# 2. Update blockchain.py
from xai.core.module_name import ModuleName

class Blockchain:
    def __init__(self):
        # ...
        self.module_name = ModuleName(self)

    def method_name(self, ...):
        """Delegator - real implementation in module_name.py"""
        return self.module_name.method_name(...)
```

## Success Metrics

After refactoring:
- blockchain.py: **< 1000 lines** (currently 4,211)
- Largest module: **< 1000 lines** (chain_validator.py at ~850)
- Cyclomatic complexity: **< 15 per function**
- Test coverage: **> 90%** maintained
- No circular imports
- All existing tests pass
