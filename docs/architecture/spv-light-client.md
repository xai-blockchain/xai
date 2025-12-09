# SPV Header Ingestion (Design Outline)

Goal: verify external UTXO chain transactions with an SPV header chain instead of trusting HTTP explorers.

## Requirements
- Maintain a pruned header chain per supported UTXO coin (BTC/LTC/DOGE/BCH/ZEC/DASH).
- Validate proof-of-work and difficulty per header; reject invalid/low-work branches.
- Enforce checkpointed anchors (hardcoded or peer quorum) to prevent long-range attacks.
- Expose `get_best_header(chain)` and `get_confirmations(tx_block_height)` for `CrossChainVerifier`.

## Flow
1. **Header download**: fetch headers from trusted RPC/peers; verify PoW/difficulty as appended.
2. **Storage**: persist headers in a bounded DB (height → header, cumulative work); prune to last N blocks or anchored checkpoints.
3. **Fork handling**: track competing branches by cumulative work; select best chain, enforce reorg limits relative to anchors.
4. **Merkle proof check**: verify tx merkle proof against the header’s merkle root.
5. **Confirmations**: compute `best_height - tx_block_height + 1` from validated header chain, not remote explorer response.

## Safety
- Require TLS + pinned endpoints for header fetch, or authenticated P2P sources.
- Reject headers that violate difficulty or timestamp rules.
- Cache and rate-limit header fetches; ban peers serving invalid headers.
- Periodically checkpoint header chain hashes for quick restart.

## Next Steps
- Implement `HeaderStore` with PoW/difficulty validation and persistence.
- Wire `CrossChainVerifier` to prefer SPV header data when available, falling back to HTTP only if disabled.
- Add tests: invalid difficulty, bad merkle proof, fork with lower cumulative work, checkpoint enforcement.
