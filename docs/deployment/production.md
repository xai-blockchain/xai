# Production Deployment Guide

This guide assumes hardened configs, explicit allowlists, and monitored endpoints. Do not reuse dev/test secrets.

## Configuration Checklist
- **Secrets**: Provide via env (e.g., `XAI_SECRET_KEY`, `XAI_API_ALLOWED_ORIGINS`, `XAI_API_MAX_JSON_BYTES`). Never commit private keys.
- **CORS**: Strict allowlist of known origins; no wildcards. Use deterministic JSON arrays (sorted hostnames) and keep them under change control:
  ```bash
  export XAI_API_ALLOWED_ORIGINS='["https://wallet.example.com","https://dashboard.example.com"]'
  ```
- **Rate Limits**: Tune `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW`, and endpoint overrides (`/wallet/send`, `/transaction`, `/mine`) to protect public APIs.
- **Request Size**: Set `API_MAX_JSON_BYTES` conservatively (≤1 MB) and mirror it in ingress controllers:
  ```bash
  export XAI_API_MAX_JSON_BYTES=262144  # 256 KB prod limit
  ```
  Update reverse proxies (Nginx `client_max_body_size`, Envoy `max_request_bytes`) to match so clients see the same behavior at every layer.
- **TLS**: Terminate HTTPS at a proxy (Nginx/Envoy). Enforce secure cookies.
- **P2P**: Enable version/capability handshake, subnet/ASN diversity caps, bandwidth token buckets, and reset-storm detection.
- **Partial Sync**: Configure checkpoint bootstrap to reduce recovery time:
  ```bash
  export PARTIAL_SYNC_ENABLED=true
  export P2P_PARTIAL_SYNC_ENABLED=true
  export P2P_PARTIAL_SYNC_MIN_DELTA=1000
  export CHECKPOINT_QUORUM=5
  export CHECKPOINT_MIN_PEERS=3
  export TRUSTED_CHECKPOINT_PUBKEYS="02abc...,03def...,02fed..."
  ```
  Rotating checkpoint signers should be managed like validator keys; see `docs/deployment/partial-sync.md`.

## Deployment Steps (Kubernetes Example)
1. **Secrets/ConfigMaps**: Create manifests for config YAML and env secrets.
2. **Deploy Node**: Use a Deployment/StatefulSet with persistent volumes for chain data; set resource limits.
3. **Ingress/Proxy**: Front with TLS; expose only necessary ports (REST/WS/P2P). Apply the same CORS allowlist and body-size ceilings here to prevent the proxy from accepting payloads the node rejects.
4. **Monitoring**:
   - Scrape `/metrics` with Prometheus.
   - Dashboards: import Grafana JSON from `monitoring/`.
   - Alerts: high 4xx/5xx, mempool pressure, peer drops, sync lag, disk usage.
5. **Smoke Tests**:
   - Run `scripts/tools/send_rejection_smoke_test.sh`.
   - Check `/health`, `/stats`, `/mempool/stats`, `/peers?verbose=true`.
   - Validate WebSocket broadcasts.
   - Verify the node logs show the expected `cors.allowed_origins` and `api.max_json_bytes` during boot; mismatches indicate env drift.
   - If partial sync is enabled, confirm `p2p.partial_sync_applied` appears once during bootstrap. Investigate `p2p.partial_sync_failed` entries.

## Ops Practices
- **Key Rotation**: Rotate API keys regularly; clean up unused keys.
- **Backups**: Back up chain data and keystores; test restores.
- **Upgrades**: Drain/restart nodes one at a time; verify OpenAPI/schema changes.
- **Logging**: Use structured logging; ship to SIEM. Monitor security events (rate-limit, CSRF, signing rejections, CORS or body-size denials, checkpoint failures).
- **Incident Response**: Document on-call runbooks; disable compromised keys quickly; ban abusive peers via peer manager.

## Data Hygiene
- No private keys in images or ConfigMaps.
- Keep `.env` and wallet data out of Git; mount securely.
- Rotate JWT signing secrets on a schedule.
