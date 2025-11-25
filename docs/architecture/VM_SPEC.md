# Virtual Machine Specification (Draft)

This document defines the execution rules for the forthcoming XAI smart-contract virtual machine.  The initial release targets EVM compatibility while keeping the door open for WASM execution in a later phase.  The spec mirrors canonical Ethereum semantics wherever possible so existing tooling (Remix, Foundry, Hardhat) works with minimal changes.

## 1. Scope & Goals

- Deterministic execution with opcode-level equivalence to the Ethereum yellow paper unless explicitly documented.
- Pluggable execution engines: `EVMExecutor` ships first, `WASMExecutor` can be added under the same trait.
- Integration with the existing PoW consensus pipeline (`Blockchain.add_block`, `ConsensusManager.validate_block`).
- Native interoperability with current modules (withdrawal guards, MEV mitigation, etc.) by exposing execution receipts and event logs to monitoring.

## 2. Transaction Model

| Field | Description |
| --- | --- |
| `tx_type` | `contract_deploy`, `contract_call`, or `legacy` (non-contract). |
| `gas_limit` | Maximum gas the sender authorizes (per-transaction). |
| `gas_price` | Tip paid to the miner (`gas_price * gas_used`).  Optional base fee support is plumbed through `vm.fee_market`. |
| `data` | ABI-encoded payload for deployments/calls.  Stored under `Transaction.metadata["data"]`. |
| `value` | Native token amount transferred to the contract. |
| `nonce` | Monotonically increasing per sender (already enforced by `NonceTracker`). |

Transactions are serialized within blocks exactly as other payloads today; block headers gain `gasUsed`, `gasLimit`, and `logsBloom`.

## 3. State Model

- **Accounts**: Differentiated into EOAs (externally owned accounts) and contract accounts.  Both share `{nonce, balance}`; contract accounts add `{storage_root, code_hash}`.
- **Storage**: 256-bit key/value trie.  Stored off-chain via `BlockchainStorage` with snapshots keyed by block height.
- **Receipts**: Capture `{status, gas_used, logs, bloom}`; persisted for RPC queries and event subscriptions.

The `EVMState` helper mediates between the VM and the canonical blockchain state (UTXO set continues to back legacy transfers until migration planning defines a unified ledger).

## 4. Execution Environment

- **Opcodes**: All Frontier → Istanbul opcodes supported; later forks (Berlin, London, etc.) may be added behind feature flags.
- **Gas Accounting**: Gas is deducted per opcode using the canonical schedule.  Out-of-gas triggers immediate revert with `status=0`.
- **Call Depth**: Max 1024 nested calls (configurable).  Excess depth halts with `STACK_EXCEPTION`.
- **Memory**: Byte-addressable, dynamically expanding in 32-byte words with the standard quadratic gas formula.
- **Precompiles**: Secp256k1 recover, SHA256, RIPEMD160, identity, BLAKE2, and ed25519 (for bridge proofs).  Implemented in `xai.core.vm.precompiles`.
- **Environmental Info**: `BLOCKHASH`, `COINBASE`, `TIMESTAMP`, `NUMBER`, `DIFFICULTY`, `CHAINID`, `GASLIMIT`, `BASEFEE`.  All fields sourced from the existing `Block` object or `Config`.

## 5. Integration Hooks

1. **Transaction Admission**
   - `TransactionValidator` verifies `gas_limit <= Config.MAX_TRANSACTION_GAS`.
   - New mempool priority queue sorts by `gas_price`.
2. **Block Validation**
   - `ConsensusManager.validate_block` ensures `gasUsed <= gasLimit`.
   - Blocks include `receipts_root` (Merkle root of receipts) to keep multi-client implementations aligned.
3. **State Commit**
   - After executing contract transactions, the VM commits storage writes to a journal that is flushed when the block is finalized.  Rollbacks are handled in-memory during reorgs.
4. **APIs**
   - `/contracts/call` (eth_call equivalent) runs the VM in read-only mode without touching state.
   - `/contracts/gas-estimate` executes in estimation mode, returning the upper bound for `gas_limit`.

## 6. Security & Determinism

- Execution is single-threaded per block to preserve determinism (parallelization may land later via speculative execution once consensus accounts for it).
- Gas refunds track per-transaction upper bounds to avoid DoS via excessive refunds.
- Access lists (EIP-2929) can be enabled to reduce random I/O costs; default off until profiling completes.
- Logs feed into the existing `SecurityEventRouter` and Prometheus exporters so contract anomalies surface like native modules.

## 7. Testing Requirements

- **Opcode test vectors**: Mirror Ethereum’s `GeneralStateTests` and `VMTests`.
- **Cross-client determinism**: Multi-node harness replays the same contract transactions across at least three nodes and asserts identical state roots, receipts, and logs.
- **Fuzzing**: Property-based tests hitting opcode combinations, boundary gas cases, and revert paths.
- **Integration**: End-to-end flows covering deploy → event emission → log subscription over the websocket bridge.

## 8. WASM Roadmap

Once the EVM engine is stable, a `WASMExecutor` can be added by implementing the same interfaces defined in `xai.core.vm.executor.BaseExecutor`.  Contracts compile to WASM modules with deterministic import bindings.  Gas metering occurs via instruction counting and host function guards.

---

This spec is versioned; any consensus-impacting change (opcode cost, block field, environmental semantics) requires an update here, a governance proposal, and new regression tests before activation.
