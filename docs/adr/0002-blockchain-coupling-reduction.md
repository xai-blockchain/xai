# ADR-0002: Blockchain Coupling Reduction

**Status:** Accepted (Phase 1 Implemented 2025-12-28)
**Date:** 2025-12-28

## Context
`blockchain.py` has 30 XAI-specific imports, creating tight coupling. This makes testing difficult and increases cognitive load.

## Decision
Reduce to ~12 imports via:
1. **Protocol interfaces** for storage, UTXO, validation, indexing, checkpointing
2. **Service containers** grouping related dependencies (gamification, governance, finality)
3. **Dependency injection** via constructor

## Implementation (Phase 1 - Complete)

Created `src/xai/core/manager_interfaces.py` with 8 Protocol interfaces:
- `ChainProvider`: chain, pending_transactions, get_block, get_height
- `ConfigProvider`: difficulty, max_supply, network_type, data_dir, logger
- `StateProvider`: _block_hash_index, _chain_lock, address_index, nonce_tracker
- `UTXOProvider`: utxo_manager, get_balance, get_utxo_set
- `ValidationProvider`: validate_block, validate_transaction, is_valid_proof_of_work
- `StorageProvider`: load_block_from_disk, save_block_to_disk, verify_integrity
- `MiningProvider`: mining_active, calculate_block_reward, get_mining_stats
- `GovernanceProvider`: governance_state, get_active_proposals

Added `_ManagerProtocolProvider` adapter class to Blockchain that implements all protocols.

## Phase 2 (Pending)
- Migrate 9 managers to accept Protocol interfaces instead of Blockchain
- Target managers: MiningManager, ValidationManager, StateManager, ForkManager, ChainState, BlockProcessor, MiningCoordinator, ContractManager, GovernanceManager

## Consequences
**Positive:**
- Testable with mock implementations
- Clear interface contracts
- Reduced import complexity (30 -> 12 target)

**Negative:**
- Initial refactoring effort (Phase 1 complete)
- Need to maintain protocol definitions

**Mixins:** Convert `BlockchainConsensusMixin`, `BlockchainMempoolMixin`, `BlockchainMiningMixin` to Protocol-based composition.
