# Partial / Checkpoint-Based Sync (Design Notes)

This document outlines how XAI nodes perform partial sync using checkpoints instead of downloading the full chain. Implementation now lives in:

- `src/xai/core/checkpoint_sync.py` (`CheckpointSyncManager`)
- `src/xai/core/node_p2p.py` (`_attempt_partial_sync`, `sync_with_network`)
- `docs/deployment/partial-sync.md` (operations guide)

## Goals
- Bootstrap from a trusted checkpoint to reduce initial sync time.
- Verify chain continuity from checkpoint height to tip with full validation.
- Exchange checkpoints via P2P (`get_checkpoint` / `checkpoint`) with signature and diversity validation.
- Reject checkpoints that conflict with local trust roots or have insufficient cumulative work.

## Flow
1. **Checkpoint discovery**: on startup, request latest checkpoint metadata from peers; require quorum (e.g., 3+ agreeing hashes) and peer diversity.
2. **Trust evaluation**:
   - Validate checkpoint signature (operator key or committee) and cumulative work reported.
   - Compare to local hardcoded/trusted checkpoints; refuse lower-work or conflicting checkpoints.
3. **State application**:
   - Download checkpoint payload (UTXO/state snapshot + block header) and verify integrity hash.
   - Apply snapshot to state DB and set chain tip to checkpoint height/hash.
   - Persist `latest_checkpoint_height` and provenance metadata.
4. **Catch-up**:
   - Sync headers/blocks from checkpoint height+1 to tip using normal validation and fork choice.
   - Enforce reorg protection: no fork below `latest_checkpoint_height`.
5. **Safety**:
   - Rate-limit checkpoint requests/responses; refuse untrusted peers.
   - Require minimum confirmations/work on the checkpoint block.
   - Maintain audit log of accepted/rejected checkpoints.

## Open Items
- Complete streamed snapshot download + chunked persistence for very large checkpoints (current implementation supports metadata + inline payloads/URLs).
- Add light-client header validation for checkpoint chain proofs (ensure PoW targets and signatures are validated independently of payload).
- Expand integration tests covering: divergent checkpoints, low-work checkpoints, replayed stale checkpoints, successful partial sync to tip, and forced rebootstrap scenarios.
