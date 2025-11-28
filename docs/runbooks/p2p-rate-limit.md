---
title: P2P Rate Limit Alert Runbook
---

# P2P Rate Limiting (xai_p2p_rate_limited_total)

## Summary
Peers are hitting P2P rate caps, suggesting abusive senders, misconfigured peers, or under-provisioned nodes. Alerts: `P2PRateLimitedPeers`, `P2PRateLimitFlood`.

## Triage (5–10 minutes)
- Metrics: `increase(xai_p2p_rate_limited_total[5m])`, `xai_p2p_messages_received_total`, CPU/memory from `kubectl top`.
- Logs: search for `rate_limited` in node logs and correlate peer IDs/IPs.
- Check current caps: `XAI_P2P_MAX_MESSAGE_RATE`, `XAI_P2P_MAX_BANDWIDTH_IN/OUT`.
- Validate trust store enforcement and mTLS flags (`XAI_PEER_REQUIRE_CLIENT_CERT=1`).

## Containment (15 minutes)
- Drop abusive peers: update trust stores (`/etc/xai/trust/trusted_peer_*`) or use reputation ban if available.
- Tighten caps: lower `XAI_P2P_MAX_MESSAGE_RATE` and/or bandwidth limits; apply ConfigMap and rolling restart.
- Ensure `XAI_P2P_SECURITY_LOG_RATE` is sufficient to observe without flooding logs.

## Eradication
- Audit bootstrap/DNS seed lists; remove untrusted entries causing noisy peers.
- Verify clients respect backoff; coordinate with partner operators to fix chatty nodes.
- Consider enabling additional packet filtering (NetworkPolicy) for offender IP ranges.

## Recovery & Verification
- Confirm alerts clear and `xai_p2p_rate_limited_total` growth normalizes.
- Validate healthy throughput: monitor `xai_p2p_messages_received_total` and block propagation latency.
- Run a synthetic broadcast to ensure legitimate traffic is not throttled.

## Lessons / Follow-up
- Keep per-environment caps documented in ConfigMap and Grafana annotations.
- Add SIEM correlation for repeated offenders across clusters.
- Revisit autoscaling thresholds if legitimate load regularly triggers rate limits.
