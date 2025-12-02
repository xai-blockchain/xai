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
- `XAI_P2P_ENABLE_QUIC` (default `0`): Enable QUIC transport (requires `aioquic`). QUIC runs on `p2p_port+1`. Enabled in staging; production requires `ALLOW_PROD_QUIC=1` after soak/latency SLOs pass.
- `XAI_P2P_QUIC_DIAL_TIMEOUT` (default `1.0`): QUIC dial/send timeout in seconds. Keep ≤1.0s in prod; only relax after staging soak data proves stable.

## Deployment Checklist
- Mount trust stores:
  - `trusted_peer_pubkeys.txt` → set `XAI_TRUSTED_PEER_PUBKEYS_FILE=/etc/xai/trust/trusted_peer_pubkeys.txt`
  - `trusted_peer_cert_fps.txt` → set `XAI_TRUSTED_PEER_CERT_FPS_FILE=/etc/xai/trust/trusted_peer_cert_fps.txt`
- Enable mTLS for validators: `XAI_PEER_REQUIRE_CLIENT_CERT=1` and ship CA bundle via `XAI_P2P_CA_BUNDLE=/etc/ssl/certs/ca-bundle.crt` (if custom, mount your bundle).
- Tune rate/bandwidth caps per environment:
  - Mainnet: `XAI_P2P_MAX_MESSAGE_RATE=50`, `XAI_P2P_MAX_BANDWIDTH_IN=524288`, `XAI_P2P_MAX_BANDWIDTH_OUT=524288`, `XAI_PEER_NONCE_TTL_SECONDS=120`.
  - Testnet/Dev: keep defaults but set explicit trust stores to avoid random peers.
- QUIC validation:
  - Staging: enable QUIC and run `scripts/ci/quic_soak_check.sh` (or `pytest tests/xai_tests/integration/test_quic_latency_soak.py`) to capture latency/packet-loss behavior.
  - Prod: require `ALLOW_PROD_QUIC=1` in deploy env and only after staging soak metrics meet SLOs.

## Monitoring/Alerts
- Metrics:
  - `xai_p2p_nonce_replay_total`: rejected messages due to nonce replay.
  - `xai_p2p_rate_limited_total`: messages dropped due to rate limiting.
  - `xai_p2p_invalid_signature_total`: messages rejected for invalid or stale signatures.
  - `xai_p2p_quic_errors_total`: QUIC transport failures (handshake or send errors).
  - `xai_p2p_quic_timeouts_total`: QUIC dial/send timeouts (critical when rising).
- Prometheus rules (production defaults live in `monitoring/prometheus_alerts.yml`):
  - Nonce replay: warning at >3/5m, critical at >15/5m.
  - Rate limiting: warning at >50/5m, critical at >200/5m.
  - Invalid signatures: warning at >5/5m, critical at >25/5m.
  - QUIC errors: warning on any increase in 5m; QUIC dial timeouts: critical when >3/5m.
- Alerts flow via `SecurityEventRouter` (prefixed `p2p.*`) and can be forwarded through `XAI_SECURITY_WEBHOOK_URL` to your SIEM or incident channel.
- Runbooks:
  - [P2P Nonce Replay](../../runbooks/p2p-replay.md)
  - [P2P Rate Limiting](../../runbooks/p2p-rate-limit.md)
  - [P2P Invalid Signatures](../../runbooks/p2p-auth.md)
