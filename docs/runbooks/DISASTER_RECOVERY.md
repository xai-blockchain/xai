# Disaster Recovery Runbook

This runbook is for node operators.

## Goals
- Preserve the node data directory
- Restore from the latest checkpoint or snapshot
- Resume block processing

## Steps
1. Stop the node and back up the data directory.
2. If a recent snapshot is available, restore the data directory from it.
3. If no snapshot is available, start the node and let it sync from peers.
4. Verify node health (RPC responds, blocks advance).
5. Rebuild indexes if needed (address index and checkpoints are rebuilt on startup).

## Notes
- Checkpoints are stored under the node data directory.
- WAL entries are used to recover interrupted reorganizations.
