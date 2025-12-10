# Node Configuration Reference

This is a quick reference for common configuration knobs. Defaults are defined in `Config`/`SecurityConfig`.

## Core

- `network.host` / `network.port`: Bind address/port (use `127.0.0.1` for local dev).
- `network.p2p_port`: Peer-to-peer port.
- `blockchain.difficulty`, `blockchain.block_time`, `blockchain.reward`, `blockchain.halving_interval`: Consensus params.

## API

- `api.enabled`: Enable REST.
- `api.allowed_origins` (`API_ALLOWED_ORIGINS`): CORS allowlist.
- `api.max_json_bytes` (`API_MAX_JSON_BYTES`): Max JSON body size (bytes).
- `api.rate_limit`/`api.rate_window_seconds`: Global rate limit defaults.
- `api.api_key_required`: Require API key by default.

## Security

- `security.secret_key`: Flask secret; use a strong value in production.
- `security.jwt_expiry`: Access token lifetime (seconds).
- `SecurityConfig.RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW`: Per-IP limits.
- `SecurityConfig.ENDPOINT_LIMITS`: Overrides for sensitive endpoints (send/wallet/mine/transaction).
- `SecurityConfig.MAX_BODY_SIZE`, `MAX_URL_LENGTH`: Request size guards.
- `SecurityConfig.CSRF_ENABLED`: Enable/disable CSRF checks.

## Logging

- `logging.level`: DEBUG/INFO/WARN/ERROR.
- `logging.file`, `logging.max_size`, `logging.backup_count`: Log rotation settings.

## Metrics/Monitoring

- Prometheus/Grafana compose files live under `docker/`; `/metrics` exposes Prometheus format.

## Environment Variables

Most config keys have environment overrides (e.g., `XAI_API_ALLOWED_ORIGINS`, `XAI_API_MAX_JSON_BYTES`, `XAI_SECRET_KEY`). Use env vars for secrets in production; do not hardcode keys in YAML.***
 
### Partial Sync Controls

- `XAI_PARTIAL_SYNC_ENABLED` (`PARTIAL_SYNC_ENABLED`): Enable/disable checkpoint bootstrap at the node level.
- `XAI_P2P_PARTIAL_SYNC_ENABLED` (`P2P_PARTIAL_SYNC_ENABLED`): Allow the P2P manager to run checkpoint sync before HTTP/WS sync.
- `XAI_P2P_PARTIAL_SYNC_MIN_DELTA` (`P2P_PARTIAL_SYNC_MIN_DELTA`): Minimum height delta (remote minus local) before attempting partial sync.
- `XAI_FORCE_PARTIAL_SYNC`: Force a checkpoint bootstrap even if the local chain is non-empty (set to `1/true/yes` prior to restart).

See `docs/deployment/partial-sync.md` for full guidance.
