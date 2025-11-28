# AI Monitoring & Alerts

## Metrics
- `/ai/metrics`: JSON snapshot of queue/completed/tokens/bridge syncs plus custom counters.
- `/metrics`: Prometheus endpoint exporting `xai_ai_*` counters/gauges.

## Grafana Dashboard
- Import `dashboards/ai_bridge_dashboard.json` into Grafana (Dashboard → Manage → Import).
- Point the data source to your Prometheus scrape target for `/metrics`.
- Visualize `xai_ai_bridge_queue_events_total`, `xai_ai_completed_tasks_total`, `xai_ai_tokens_consumed_total`, and `xai_ai_bridge_last_sync_timestamp`.
- Save and share the dashboard URL so the community can continuously monitor AI task throughput.

## Alerts
Adjust your alertmanager to load `alerts/ai_bridge.rules` (see the provided file) so `AITokensHigh` fires when tokens spike beyond 100k in an hour. Pair the rule with `tools/ai_alert.py --base-url http://localhost:8545 --token-threshold 50000 --webhook https://hooks.example/ai` so Prometheus alerts reach your Slack/Teams webhook.

## CLI Helpers
- `python tools/ai_inspect.py --base-url http://localhost:8545` prints bridge status, tasks, and metrics repeatedly (optionally `--watch`).
- `python tools/ai_alert.py --base-url http://localhost:8545 --token-threshold 50000 --webhook https://hooks.example/ai` triggers alerts when token usage exceeds thresholds.
- `bash tools/run_monitoring.sh` can be scheduled (cron/systemd) so monitoring reports/alerts run every 5 minutes.

## CI Integration
- Run `python -m py_compile core/node.py core/blockchain_ai_bridge.py core/ai_metrics.py` and `python -m pytest tests/test_ai_bridge.py -vv` in your CI pipeline to verify the AI monitoring and bridge flows after each change.
- Include `prometheus/ai_bridge_scrape.yml` as an example scrape config so operators can register the bridge endpoint quickly.
- Include `prometheus/ai_bridge_scrape.yml` as an example scrape config so operators can register the bridge endpoint quickly.
