# State Snapshot & Recovery Runbook

Operators use this guide to capture deterministic blockchain snapshots, verify their integrity, and restore new validators from the archived state.  The runbook references the `scripts/tools/state_snapshot.py` CLI shipped alongside the node so there is one canonical workflow for every environment.

## 1. Prerequisites
- Node process stopped (or the validator switched to read-only mode) to avoid partial writes.
- Access to the node filesystem (block data lives in `<repo>/data` or `<repo>/data_testnet` depending on network).
- Python virtualenv with project dependencies installed (for the CLI).
- Secure storage for snapshot artifacts (encrypted S3 bucket, immutable backup target, offline disk).

## 2. Snapshot Capture
1. **Sanity checks**
   - Confirm `systemctl status xai-node` (or your supervisor) shows the node is stopped.
   - Ensure disk space can accommodate an additional copy of the data directory.
2. **Run the CLI**
   ```bash
   cd /opt/xai   # project root
   source venv/bin/activate
   python scripts/tools/state_snapshot.py create \
     --data-dir data \
     --output snapshots/mainnet-state-$(date +%Y%m%dT%H%M%S).tar.gz \
     --label "mainnet-prod"
   ```
3. **Artifacts**
   - `.tar.gz` archive containing `data/blocks`, `utxo_set.json`, and `pending_transactions.json`.
   - Manifest JSON (`<snapshot>.tar.gz.json`) with block height, hashes for each component, genesis/latest block IDs, and SHA256 of the archive itself.
4. **Upload**
   - Encrypt before leaving the host (e.g., `age`, `gpg`, or S3 default encryption).
   - Record the manifest hash in your change log for later verification.

## 3. Verification
Use the `verify` subcommand against any archive/manifest pair:
```bash
python scripts/tools/state_snapshot.py verify \
  --snapshot snapshots/mainnet-state-20240101T000000.tar.gz \
  --manifest snapshots/mainnet-state-20240101T000000.tar.gz.json
```
The CLI recalculates SHA256 for the archive and all tracked files, verifying length, genesis hash, and block height.  Run this step immediately after upload and again before restoration to detect tampering/bit rot.

## 4. Restoration
1. Provision a clean machine with the desired network configuration.
2. Stop any running node process and move the existing `data` directory aside (`mv data data.bak`).
3. Run:
   ```bash
   python scripts/tools/state_snapshot.py restore \
     --snapshot snapshots/mainnet-state-20240101T000000.tar.gz \
     --target data \
     --force
   ```
   The CLI verifies the archive hash, extracts into a temporary directory, and copies files into `--target`.
4. Reconfigure validator (API keys, peer lists, etc.) as needed, then restart the node.  The node should report the restored height and hash during startup logs.

## 5. Automation Hooks
- Integrate `state_snapshot.py create` into scheduled jobs (cron, systemd timer, GitHub Actions self-hosted runners) with retention policies (e.g., keep 14 daily, 6 weekly, 6 monthly).
- Stream manifest metadata into monitoring (Prometheus or ticket trackers) so operators know the last successful backup time/height.
- Combine with infrastructure snapshots (EBS, LVM) for bare-metal recovery, but retain the application-level archive for portability and audit trails.

## 6. Security Considerations
- Treat snapshot archives as sensitive: they contain full UTXO sets and pending transactions.  Encrypt at rest and in transit.
- Store manifest files separately from the archives so tampering with one can be detected.
- Rotate the storage credentials (S3 IAM roles, SSH keys) on the same cadence as API keys.

## 7. Validation Checklist
- ✅ CLI exit code 0 for `create`, `verify`, `restore`.
- ✅ Manifest hash recorded in change log / ticket.
- ✅ Post-restore node logs show expected height/hash.
- ✅ Governance and monitoring teams notified of snapshot completion.

Following this runbook ensures every validator can capture reproducible state, bootstrap new nodes quickly, and satisfy audit/compliance requirements for disaster recovery.
