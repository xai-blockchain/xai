# Withdrawal Processing Pipeline

The withdrawal processor continuously audits pending exchange withdrawals, enforces timelocks, and applies layered risk controls before funds leave custody.

## Architecture

- `ExchangeWalletManager` now persists every withdrawal with `status=pending`, keeps an in-memory cache of active requests, and exposes helpers to list, update, or refund them.
- `WithdrawalProcessor` evaluates the pending queue on an interval (default 45s) and produces deterministic settlement decisions:
  - **Deferred** – still in timelock window or daily limits reached.
  - **Completed** – settlement hash generated, status marked `completed`.
  - **Flagged** – manual review required; request removed from the automated queue.
  - **Failed** – blocked destination, invalid metadata, or unacceptable risk; funds are automatically refunded to the originating wallet.
- `BlockchainNode` instantiates the processor when the exchange wallet is available and runs the worker thread automatically. Shutdown hooks stop the worker cleanly.

## Risk Controls

1. **Per-transaction limits** – configurable `MAX_PER_TX` rejects requests beyond the allowed amount.
2. **Timelock scaling** – withdrawals above `LOCK_AMOUNT_THRESHOLD` accrue `LOCK_DURATION_SECONDS * multiplier` delay (capped at 4×).
3. **Daily volume enforcement** – `MAX_DAILY_VOLUME` caps rolling 24h totals per address.
4. **Destination policy** – `BLOCKED_DESTINATIONS` immediately fails (and refunds) suspicious routes.
5. **Compliance metadata** – missing 2FA, low KYC scores, or PEP flags increase risk and can force manual review.
6. **Audit-ready settlement IDs** – every completion produces a SHA-256 digest containing the user, currency, amount, and timestamp.

## Configuration

Configure via `Config.WITHDRAWAL_PROCESSOR`, e.g.:

```python
WITHDRAWAL_PROCESSOR = {
    "DATA_DIR": "/var/lib/xai/withdrawals",
    "LOCK_AMOUNT_THRESHOLD": 5000.0,
    "LOCK_DURATION_SECONDS": 3600,
    "MAX_PER_TX": 250000.0,
    "MAX_DAILY_VOLUME": 1_000_000.0,
    "MANUAL_REVIEW_THRESHOLD": 0.7,
    "INTERVAL_SECONDS": 60,
    "BLOCKED_DESTINATIONS": ["scam-domain", "aml:blacklist"],
}
```

## Testing

Run the dedicated unit suite:

```bash
pytest tests/xai_tests/unit/test_withdrawal_processor.py
```

The tests cover:
- Successful settlement + deterministic hashes.
- Timelock enforcement for large withdrawals.
- Blocked destination handling with automatic refunds.

These tests must run inside the project virtual environment (`python3 -m venv .venv && source .venv/bin/activate`).

## Admin API Visibility

Operations can query `/admin/withdrawals/status` (admin token required) to retrieve:
- Queue depth and per-status counts (pending/completed/flagged/failed)
- A limited list of withdrawals per requested status (default all statuses)
- The latest processor run summary (checked/completed/flagged/failed/deferred counts + queue depth)

Example:

```
curl -H "X-Admin-Token: $ADMIN_TOKEN" \
     "https://node.example.com/admin/withdrawals/status?status=pending,flagged&limit=25"
```

## Prometheus Metrics

`MetricsCollector` now exposes processor statistics:

| Metric | Type | Description |
| --- | --- | --- |
| `xai_withdrawal_processor_completed_total` | counter | Number of withdrawals settled by the processor |
| `xai_withdrawal_processor_flagged_total` | counter | Number of withdrawals sent to manual review |
| `xai_withdrawal_processor_failed_total` | counter | Number of withdrawals rejected (blocked destinations, invalid metadata, etc.) |
| `xai_withdrawal_pending_queue` | gauge | Current pending queue depth |

Scrape these metrics alongside existing withdrawal telemetry to drive Grafana dashboards and alerting.

Both `monitoring/dashboards/grafana/aixn_security_operations.json` and its production counterpart now contain:
- A `Withdrawal Processor Queue Depth` stat panel reading `xai_withdrawal_pending_queue`.
- A `Withdrawal Processor Outcomes (24h)` time-series panel charting the 24h deltas for completed, flagged, and failed withdrawals.

## Grafana Import Runbook

Follow `docs/monitoring/grafana_import.md` after updating any dashboard JSON. The guide walks through:
1. Validating and importing the dashboard into staging and production Grafana.
2. Querying Prometheus directly to verify `xai_withdrawal_pending_queue` and `xai_withdrawal_processor_*` metrics are available.
3. Visual validation that the new panels render in Grafana and display live data.
