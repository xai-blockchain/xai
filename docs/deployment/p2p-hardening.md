# P2P Hardening and Transport Security

Production nodes must enforce strict peer auth, replay protection, and bandwidth/rate controls. Configure these environment variables and deploy trust stores with your manifests.

## Core Settings
- `XAI_PEER_REQUIRE_CLIENT_CERT` (default `0`): Require mutual TLS. Set to `1` on validator/mainnet nodes.
- `XAI_P2P_MAX_MESSAGE_RATE` (default `100`): Messages per second before rate limiting kicks in.
- `XAI_P2P_SECURITY_LOG_RATE` (default `20`): Throttling for P2P security log events.
- `XAI_P2P_MAX_BANDWIDTH_IN` / `XAI_P2P_MAX_BANDWIDTH_OUT` (default `1048576` bytes/sec): Bandwidth guardrails with disconnect on exceed.
- `XAI_PEER_NONCE_TTL_SECONDS` (default `300`): TTL for signed message nonces to block replay.
- `XAI_TRUSTED_PEER_PUBKEYS_FILE`: Path to a file containing hex-encoded peer pubkeys, one per line (with `#` comments allowed).
- `XAI_TRUSTED_PEER_CERT_FPS_FILE`: Path to pinned TLS certificate fingerprints (hex SHA-256), one per line.
- `XAI_P2P_DNS_SEEDS` / `XAI_P2P_BOOTSTRAP_NODES`: Optional discovery lists; omit on private networks.

## Deployment Checklist
- Mount trust stores:
  - `trusted_peer_pubkeys.txt` → set `XAI_TRUSTED_PEER_PUBKEYS_FILE=/etc/xai/trust/trusted_peer_pubkeys.txt`
  - `trusted_peer_cert_fps.txt` → set `XAI_TRUSTED_PEER_CERT_FPS_FILE=/etc/xai/trust/trusted_peer_cert_fps.txt`
- Enable mTLS for validators: `XAI_PEER_REQUIRE_CLIENT_CERT=1` and ship CA bundle via `XAI_P2P_CA_BUNDLE=/etc/ssl/certs/ca-bundle.crt` (if custom, mount your bundle).
- Tune rate/bandwidth caps per environment:
  - Mainnet: `XAI_P2P_MAX_MESSAGE_RATE=50`, `XAI_P2P_MAX_BANDWIDTH_IN=524288`, `XAI_P2P_MAX_BANDWIDTH_OUT=524288`, `XAI_PEER_NONCE_TTL_SECONDS=120`.
  - Testnet/Dev: keep defaults but set explicit trust stores to avoid random peers.

## Monitoring/Alerts
- Metrics:
  - `xai_p2p_nonce_replay_total`: rejected messages due to nonce replay.
  - `xai_p2p_rate_limited_total`: messages dropped due to rate limiting.
- Prometheus rules (examples):
  ```
  - alert: XAIP2PReplaySpike
    expr: increase(xai_p2p_nonce_replay_total[5m]) > 10
    for: 2m
    labels: {severity: warning}
    annotations:
      summary: "P2P nonce replay surge"

  - alert: XAIP2PRateLimitSpike
    expr: increase(xai_p2p_rate_limited_total[5m]) > 25
    for: 2m
    labels: {severity: warning}
    annotations:
      summary: "P2P rate limiting triggered frequently"
  ```
- Alerts flow via `SecurityEventRouter` (prefixed `p2p.*`) and can be forwarded through `XAI_SECURITY_WEBHOOK_URL`.
