---
title: P2P Nonce Replay Alert Runbook
---

# P2P Nonce Replay (xai_p2p_nonce_replay_total)

## Summary
High volumes of replayed P2P messages indicate abuse or misconfigured peers resending stale signed payloads. Alerts: `P2PNonceReplaySpike`, `P2PNonceReplayFlood`.

## Triage (5–10 minutes)
- Check metrics: `increase(xai_p2p_nonce_replay_total[5m])`, `xai_p2p_rate_limited_total`, peer counts, `xai_peers_connected`.
- Inspect offending peers: `kubectl logs -n xai-blockchain deployment/xai-blockchain-node | grep "p2p.replay_detected"`.
- Validate mTLS: ensure `XAI_PEER_REQUIRE_CLIENT_CERT=1` and trust stores mounted (`/etc/xai/trust/*`).
- Verify nonce TTL: `XAI_PEER_NONCE_TTL_SECONDS` aligns with production (e.g., 120s).

## Containment (15 minutes)
- Ban abusive peers: `kubectl exec -n xai-blockchain statefulset/xai-blockchain-node -- python - <<'PY'` to call reputation manager ban API (if exposed) or update deny-lists in `trusted_peer_*` files.
- Increase rate limits temporarily: bump `XAI_P2P_MAX_MESSAGE_RATE` downwards and `XAI_P2P_SECURITY_LOG_RATE` upwards for visibility; reload ConfigMap and rollout.
- If flood persists, scale out validators to absorb while rate limits evict offenders.

## Eradication
- Rotate peer keys/certs for impacted validators if trust was misconfigured.
- Remove untrusted DNS seeds/bootstrap nodes from `XAI_P2P_DNS_SEEDS` / `XAI_P2P_BOOTSTRAP_NODES`.
- Validate clocks on peers (NTP) to avoid timestamp/nonce reuse from skew.

## Recovery & Verification
- Confirm alerts clear and metrics decay to baseline (<3/5m).
- Validate P2P connectivity: `kubectl get pods -n xai-blockchain -o wide` and `kubectl logs ... | grep "Peer connected"`.
- Run synthetic signed message through allowed peers; ensure it is accepted once and replay is rejected with alert increment.

## Lessons / Follow-up
- Add offending IPs/fingerprints to deny-lists.
- Tighten TTL if replay surface remains high.
- Ensure SIEM webhook (`XAI_SECURITY_WEBHOOK_URL`) delivered events; resend test via `SecurityEventRouter.dispatch("p2p.replay_detected", {"peer":"test"}, "WARNING")`.
