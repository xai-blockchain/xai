# Mempool Tuning and Admission Controls

Hardened mempool policy protects validators from spam, replay attempts, and stuck transactions. Configure these environment variables before starting a node.

## Core Admission Limits
- `XAI_MEMPOOL_MAX_SIZE` (default `10000`): Cap on pending transactions. When full, lowest fee-rate txs are evicted.
- `XAI_MEMPOOL_MAX_PER_SENDER` (default `100`): Per-address pending cap to prevent single-sender floods.
- `XAI_MEMPOOL_MIN_FEE_RATE` (default `0.0000001`): Minimum fee-per-byte required for mempool admission. Raise on mainnet to tighten spam resistance.
- `XAI_MEMPOOL_MAX_AGE_SECONDS` (default `86400`): Expire transactions older than this window.

## Invalid-Submission Backoff
- `XAI_MEMPOOL_INVALID_TX_THRESHOLD` (default `3`): Number of invalid submissions before a sender is temporarily banned.
- `XAI_MEMPOOL_INVALID_BAN_SECONDS` (default `900`): Ban duration applied after threshold is crossed.
- `XAI_MEMPOOL_INVALID_WINDOW_SECONDS` (default `900`): Rolling window used to count invalid attempts.

## Alert Thresholds (Monitoring)
- `XAI_MEMPOOL_ALERT_INVALID_DELTA` (default `50`): Fire warning when invalid mempool rejections increase by this amount between metric scrapes.
- `XAI_MEMPOOL_ALERT_BAN_DELTA` (default `10`): Fire warning when banned-sender submissions increase by this amount between scrapes.
- `XAI_MEMPOOL_ALERT_ACTIVE_BANS` (default `1`): Fire warning when active bans reach or exceed this count.

## Recommended Profiles
- **Mainnet**: `XAI_MEMPOOL_MIN_FEE_RATE=0.000001`, `XAI_MEMPOOL_INVALID_TX_THRESHOLD=2`, `XAI_MEMPOOL_INVALID_BAN_SECONDS=1800`, `XAI_MEMPOOL_ALERT_INVALID_DELTA=20`, `XAI_MEMPOOL_ALERT_BAN_DELTA=5`.
- **Testnet/Dev**: Keep defaults or lower caps to surface issues quickly (e.g., `XAI_MEMPOOL_MIN_FEE_RATE=0`, `XAI_MEMPOOL_INVALID_BAN_SECONDS=120`).

## Observability
- Prometheus metrics exposed:
  - `xai_mempool_rejected_invalid_total`
  - `xai_mempool_rejected_banned_total`
  - `xai_mempool_rejected_low_fee_total`
  - `xai_mempool_rejected_sender_cap_total`
- `xai_mempool_evicted_low_fee_total`
- `xai_mempool_expired_total`
- `xai_mempool_active_bans`
- Alerts are raised when rejection surges or active bans breach thresholds. Integrate your alert handler to consume these warnings.
- Alerts also dispatch through the global `SecurityEventRouter`, which can forward to webhooks when `XAI_SECURITY_WEBHOOK_URL` is configured. Connect this to your SIEM/incident channel for visibility.

## Quick Ops Playbook
- **Test locally**: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/pytest tests/xai_tests/test_mempool_security.py`
- **Enable webhook alerting**:
  - `export XAI_SECURITY_WEBHOOK_URL=https://hooks.example.com/xai-alerts`
  - Optional auth: `export XAI_SECURITY_WEBHOOK_TOKEN=Bearer\ xai-prod-token`
  - Verify: send a synthetic alert by hitting `/metrics` or invoking a small script that calls `SecurityEventRouter.dispatch(...)`.
- **Prometheus alert rules (example)**:
  - Trigger on invalid surge:
    ```
    - alert: XAIInvalidMempoolSurge
      expr: increase(xai_mempool_rejected_invalid_total[5m]) > 20
      for: 2m
      labels: {severity: warning}
      annotations:
        summary: "Spike in invalid mempool submissions"
    ```
  - Trigger on banned sender surge:
    ```
    - alert: XAIBannedSenderSurge
      expr: increase(xai_mempool_rejected_banned_total[5m]) > 5
      for: 2m
      labels: {severity: warning}
      annotations:
        summary: "Spike in banned sender submissions"
    ```
  - Trigger on active bans:
    ```
    - alert: XAIMempoolActiveBans
      expr: xai_mempool_active_bans > 0
      for: 10m
      labels: {severity: warning}
      annotations:
        summary: "Senders currently rate-limited from mempool"
    ```
