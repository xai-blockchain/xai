# Trust Store Rotation Runbook

## Summary
Rotate trusted peer public keys and TLS certificate fingerprints without disrupting validators.

## Steps
1) Prepare new trust store files:
   - `trusted_peer_pubkeys.txt` with new/old keys (one per line, comments with `#`).
   - `trusted_peer_cert_fps.txt` with new/old SHA-256 fingerprints.
2) Update ConfigMap:
   - Apply updated `xai-blockchain-trust` ConfigMap (or Helm values) with both old and new entries.
3) Roll nodes:
   - `kubectl rollout restart statefulset/xai-blockchain-node -n xai-blockchain`
   - Wait for readiness before proceeding to next step.
4) Deprecate old entries:
   - Remove old keys/fingerprints once all nodes are confirmed running with the new trust store.
   - Re-apply ConfigMap and rollout again to drop deprecated entries.
5) Verification:
   - Check `Peer connected` logs and ensure no `untrusted_client_certificate` or `untrusted_sender`.
   - Run `k8s/verify-deployment.sh` to ensure P2P and SIEM probes are healthy.

## Notes
- Keep `XAI_PEER_REQUIRE_CLIENT_CERT=1` enforced during rotation.
- Coordinate rotations during low-traffic windows to reduce reconnect churn.
- If using Helm, update `values-p2p-hardening.yaml` equivalents and `helm upgrade`.
