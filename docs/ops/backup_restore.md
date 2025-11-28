# Backup & Restore Runbook

## Backup
- **Data:** snapshot `~/.xai/` (blocks, UTXO data, nonces).
- **Keys:** back up wallet files and node identity keys separately; encrypt at rest.
- **Configs:** export ConfigMap/Secrets (`kubectl get cm/secrets -o yaml`) and trust stores.
- **Frequency:** at least daily for mainnet validators; before upgrades.

## Restore
1) Provision node with same version and trust stores.
2) Restore data snapshot to `~/.xai/`.
3) Restore ConfigMap/Secrets/trust stores.
4) Start node and run integrity checks:
   - `GET /health`, `compute_state_snapshot` digests
   - Run `k8s/verify-deployment.sh` (metrics + SIEM probe)
5) Monitor P2P/security alerts for anomalies.

## Notes
- Keep backups encrypted and access-controlled.
- Verify backups periodically via test restores.
- Rotate keys after suspected compromise; update trust stores accordingly.
