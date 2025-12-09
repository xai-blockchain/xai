# Production Deployment Guide

This guide assumes hardened configs, explicit allowlists, and monitored endpoints. Do not reuse dev/test secrets.

## Configuration Checklist
- **Secrets**: Provide via env (e.g., `XAI_SECRET_KEY`, `XAI_API_ALLOWED_ORIGINS`, `XAI_API_MAX_JSON_BYTES`). Never commit private keys.
- **CORS**: Strict allowlist of known origins; no wildcards.
- **Rate Limits**: Tune `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW`, and endpoint overrides (`/wallet/send`, `/transaction`, `/mine`) to protect public APIs.
- **Request Size**: Set `API_MAX_JSON_BYTES` conservatively (≤1MB) and enforce `MAX_BODY_SIZE`, `MAX_URL_LENGTH`.
- **TLS**: Terminate HTTPS at a proxy (Nginx/Envoy). Enforce secure cookies.
- **P2P**: Enable version/capability handshake, subnet/ASN diversity caps, bandwidth token buckets, and reset-storm detection.

## Deployment Steps (Kubernetes Example)
1. **Secrets/ConfigMaps**: Create manifests for config YAML and env secrets.
2. **Deploy Node**: Use a Deployment/StatefulSet with persistent volumes for chain data; set resource limits.
3. **Ingress/Proxy**: Front with TLS; expose only necessary ports (REST/WS/P2P).
4. **Monitoring**:
   - Scrape `/metrics` with Prometheus.
   - Dashboards: import Grafana JSON from `monitoring/`.
   - Alerts: high 4xx/5xx, mempool pressure, peer drops, sync lag, disk usage.
5. **Smoke Tests**:
   - Run `scripts/tools/send_rejection_smoke_test.sh`.
   - Check `/health`, `/stats`, `/mempool/stats`, `/peers?verbose=true`.
   - Validate WebSocket broadcasts.

## Ops Practices
- **Key Rotation**: Rotate API keys regularly; clean up unused keys.
- **Backups**: Back up chain data and keystores; test restores.
- **Upgrades**: Drain/restart nodes one at a time; verify OpenAPI/schema changes.
- **Logging**: Use structured logging; ship to SIEM. Monitor security events (rate-limit, CSRF, signing rejections).
- **Incident Response**: Document on-call runbooks; disable compromised keys quickly; ban abusive peers via peer manager.

## Data Hygiene
- No private keys in images or ConfigMaps.
- Keep `.env` and wallet data out of Git; mount securely.
- Rotate JWT signing secrets on a schedule.
