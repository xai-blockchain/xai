# Testnet Deployment Guide

This guide covers bringing up a testnet node with hardened defaults and API limits.

## Prerequisites
- Kubernetes or Docker environment for isolation (recommended).
- Valid config files (`config/testnet.yaml`) with testnet seeds.
- Secrets stored as env vars (no private keys in repo).

## Steps

1) **Prepare Config**
   - Copy `config/testnet.yaml` and set:
     - `network.host: 0.0.0.0`
     - `network.port`: testnet P2P port
     - `api.allowed_origins`: explicit allowlist
     - `api.max_json_bytes`: 1 MB (or stricter)
     - `api.rate_limit`/`api.rate_window_seconds`: tuned for public-facing nodes
   - Set env vars for secrets: `XAI_SECRET_KEY`, `XAI_API_ALLOWED_ORIGINS`, `XAI_API_MAX_JSON_BYTES`.
   - Always keep the allowlist deterministic (stable order + casing) so ConfigMaps and reload diffs track real changes.

2) **Run with Docker Compose (example)**
   ```bash
   docker compose -f docker/docker-compose.testnet.yml up -d
   ```
   - Includes Prometheus/Grafana stack; ensure `XAI_NODE_URL` matches the testnet node.

3) **P2P Hardening**
   - Enable `/16` and ASN diversity (see `SecurityConfig`).
   - Enforce version/capability handshake; reject peers failing auth.
   - Configure bandwidth token buckets (inbound/outbound).
   - (Optional) Enable checkpoint-based partial sync to accelerate bootstrap:
     ```bash
     export PARTIAL_SYNC_ENABLED=true
     export P2P_PARTIAL_SYNC_ENABLED=true
     export P2P_PARTIAL_SYNC_MIN_DELTA=200
     export CHECKPOINT_QUORUM=3
     export CHECKPOINT_MIN_PEERS=2
     export TRUSTED_CHECKPOINT_PUBKEYS="02abc...,03def..."
     ```
     See `docs/deployment/partial-sync.md` for signer requirements and monitoring.

4) **API Hardening**
   - Require API keys for state-changing endpoints.
   - Enforce CSRF for POST/PUT/DELETE.
   - Set CORS allowlist; never use `*`. Populate via env:
     ```bash
     export XAI_API_ALLOWED_ORIGINS='["https://testnet-wallet.example.com","https://ops-console.example.com"]'
     ```
   - Keep `API_MAX_JSON_BYTES` low to prevent payload abuse and propagate the same limit through ingress/proxies:
     ```bash
     export XAI_API_MAX_JSON_BYTES=524288  # 512 KB for public testnet
     ```
   - Document these values alongside the release so auditors can reproduce the policy.

5) **Monitoring**
   - Expose `/metrics` to Prometheus; import Grafana dashboards from `monitoring/`.
   - Alert on:
     - High 429/403 rates (abuse)
     - Peer drops/reset storms
     - Mempool pressure spikes
   - Run `scripts/tools/send_rejection_smoke_test.sh` after deploy to validate rejection telemetry.

6) **Backups & Data**
   - Persist node data volumes; keep testnet wallets and keystores out of the repo.
   - Rotate API keys and clean up unused peers periodically.

7) **Upgrades**
   - Drain traffic before restarting nodes.
   - Verify OpenAPI/doc updates and apply schema migrations if needed.

8) **Post-Deploy Checks**
   - `GET /health` and `/stats` should report synced status.
   - Validate `/mempool/stats`, `/peers?verbose=true`, and `/address/<addr>/nonce` responses.
   - Confirm WebSocket `/ws` broadcasts blocks/txs.
   - Inspect `/config/runtime` (if enabled) or logs to ensure the configured origins + body limits match the exported env vars.
   - Look for structured logs `p2p.partial_sync_applied` (if enabled). Absence may mean checkpoints were unavailable; fall back to full sync is expected.
