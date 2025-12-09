# Partial Sync Implementation Plan

This plan lists concrete implementation steps for partial checkpoint-based sync.

1) **Checkpoint transport**
   - Add P2P message `checkpoint_request` with fields: `height`, `hash`, `want_payload`.
   - Add `checkpoint_payload` response carrying: header (height, hash, work, timestamp), state root/UTXO snapshot hash, optional compressed snapshot URL or chunked data.
   - Sign responses with node identity; include cumulative work and proof-of-work target to reject low-work checkpoints.

2) **Selection & validation**
   - Require quorum (>=3) agreeing checkpoints from diverse peers (/16 + ASN constraints); verify signatures and header PoW.
   - Compare against local trusted checkpoints/hardcoded roots; refuse conflicting or lower-work checkpoints.
   - Validate checkpoint metadata structure and hash integrity before applying.

3) **Download/apply**
   - Implement `CheckpointSyncManager` that:
     - Requests checkpoint payload from peers.
     - Streams snapshot to disk, verifies hash, and atomically swaps state DB.
     - Sets chain tip to checkpoint height/hash and persists provenance.
   - Fall back to full sync if checkpoint download/validation fails.

4) **Catch-up**
   - After applying checkpoint, sync headers/blocks from `height+1` with normal validation.
   - Enforce reorg protection: reject forks below latest checkpoint.

5) **Telemetry & safety**
   - Emit structured logs and metrics for checkpoint selection, acceptance, rejection, and failures.
   - Rate-limit checkpoint requests/responses; track peer misbehavior.
   - Add tests: divergent checkpoints, low-work checkpoints, stale replayed checkpoints, successful partial sync to tip.

