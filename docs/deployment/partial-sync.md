# Partial / Checkpoint Sync Guide

XAI nodes can bootstrap from signed checkpoints instead of downloading the entire chain. This guide explains how to configure, operate, and monitor the partial-sync pipeline now wired into `P2PNetworkManager.sync_with_network()`.

## Overview
- Nodes request checkpoint metadata from peers via `get_checkpoint`/`checkpoint`.
- Metadata includes height, block hash, cumulative work, and (optionally) a payload URL or inline state data.
- `CheckpointSyncManager` enforces quorum (`CHECKPOINT_QUORUM`), peer diversity (`CHECKPOINT_MIN_PEERS`), and signature validation (`TRUSTED_CHECKPOINT_PUBKEYS`).
- When a checkpoint is accepted, the node applies the UTXO/state snapshot, updates `latest_checkpoint_height`, logs provenance, and then resumes normal block sync above that height.

## Configuration

| Variable | Description |
| --- | --- |
| `PARTIAL_SYNC_ENABLED` (default `true`) | Enables partial sync at the node level (checked before bootstrapping in `node.start_services`). |
| `XAI_FORCE_PARTIAL_SYNC` | Set to `1`, `true`, or `yes` to force checkpoint bootstrap even if the local chain is non-empty. |
| `P2P_PARTIAL_SYNC_ENABLED` (default `true`) | Allows the P2P manager to attempt checkpoint application before HTTP/WS sync. |
| `P2P_PARTIAL_SYNC_MIN_DELTA` (default `100`) | Minimum height delta between the advertised checkpoint and local height before partial sync is attempted (prevents unnecessary replays). |
| `CHECKPOINT_QUORUM` (default `3`) | Minimum number of agreeing peers required before a checkpoint payload is considered. |
| `CHECKPOINT_MIN_PEERS` (default `2`) | Minimum distinct peers (respecting ASN/`/16` diversity) required for a candidate. |
| `TRUSTED_CHECKPOINT_PUBKEYS` | Comma-separated list of hex-encoded public keys allowed to sign checkpoint payloads. Leave empty for dev/test. |
| `CHECKPOINT_REQUEST_RATE_SECONDS` (default `30`) | Rate limit for broadcasting checkpoint requests to peers. |
| `XAI_CHECKPOINT_URL` / metadata `url` | Optional HTTP(S) endpoint or local file path where the payload can be fetched if not embedded in the P2P response. |

Set these variables in your deployment manifests (Kubernetes Secrets, systemd environment, `.env`, etc.). Example `.env` snippet for a validator:

```bash
export PARTIAL_SYNC_ENABLED=true
export P2P_PARTIAL_SYNC_ENABLED=true
export P2P_PARTIAL_SYNC_MIN_DELTA=500
export CHECKPOINT_QUORUM=5
export CHECKPOINT_MIN_PEERS=3
export TRUSTED_CHECKPOINT_PUBKEYS="02abc...,03def..."   # signer committee
```

## Bootstrapping Workflow

1. Node starts, P2P manager connects peers, and checkpoint metadata is collected.
2. If the advertised checkpoint height exceeds the local height by at least `P2P_PARTIAL_SYNC_MIN_DELTA`, `_attempt_partial_sync()` invokes `CheckpointSyncManager.fetch_validate_apply()`.
3. The manager fetches payloads (inline or via URL), verifies integrity hash + signature + cumulative work, and enforces quorum/diversity.
4. On success:
   - UTXO/state snapshots are restored.
   - `checkpoint_manager.latest_checkpoint_height` is updated.
   - Structured log entry: `event="p2p.partial_sync_applied"` with height/source metadata.
5. Remaining blocks are fetched via HTTP/WS to catch up from `height+1`.

If any step fails, the node logs `event="p2p.partial_sync_failed"` (with the failure reason) and continues with the legacy full sync path without aborting startup.

## Operations & Monitoring

- **Structured Logs**:
  - `p2p.partial_sync_meta_failed`: checkpoint metadata unavailable or malformed.
  - `p2p.partial_sync_failed`: validation or application failure (check `height` extra field).
  - `p2p.partial_sync_applied`: checkpoint successfully applied (includes `height` and `source`).
- **Metrics**: `CheckpointSyncManager` updates `xai_checkpoint_height`, `xai_checkpoint_work`, and `xai_checkpoint_accepted_total`.
- **Security Events**: peer misbehavior (bad signatures, insufficient diversity) is recorded via the global security router.
- **Force rebootstrap**: set `XAI_FORCE_PARTIAL_SYNC=1` before restarting a node to reapply the latest checkpoint (useful for recovery tests or after wiping local state).

## Hardening Recommendations

1. **Trusted Signers**: Configure `TRUSTED_CHECKPOINT_PUBKEYS` with a quorum of operator keys. Keep the private keys offline except when publishing checkpoints.
2. **Quorum & Diversity**: Increase `CHECKPOINT_QUORUM` and `CHECKPOINT_MIN_PEERS` on mainnet to reduce eclipse risk. Combine with existing ASN/`/16` limits.
3. **Payload Hosting**: Serve payloads via HTTPS with basic auth or pre-signed URLs. Include hashes in metadata so tampering is detectable.
4. **Rate Limiting**: Respect `CHECKPOINT_REQUEST_RATE_SECONDS` to avoid flooding peers; alerts should fire if repeated requests occur without success.
5. **Audit Trail**: Periodically export `CheckpointSyncManager.get_provenance()` for forensic records (height/hash/source/timestamp/work).

## Troubleshooting

- **Partial sync never triggers**: ensure the remote checkpoint height exceeds local height by `P2P_PARTIAL_SYNC_MIN_DELTA`. Lower the delta or force with `XAI_FORCE_PARTIAL_SYNC`.
- **Validation failures**: verify signer keys (`TRUSTED_CHECKPOINT_PUBKEYS`) and ensure payloads include correct signatures and cumulative work values.
- **Peers provide conflicting checkpoints**: check structured logs for `checkpoint.rejected` or `p2p.partial_sync_failed` detailing the rejection reason. Investigate offending peers.
- **Need to disable partial sync**: set `PARTIAL_SYNC_ENABLED=false` and `P2P_PARTIAL_SYNC_ENABLED=false`. The node will revert to traditional sync.

For architectural background see `docs/architecture/partial-checkpoint-sync.md`; for the payload structure see `docs/architecture/checkpoint-payload-format.md`.
