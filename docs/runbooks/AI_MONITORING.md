# AI Monitoring Runbook

This runbook focuses on the AI bridge telemetry helpers that keep the `xai_ai_*` metrics visible, the optional alert webhooks firing, and the watchdog loop running in the production monitoring stack.

## CLI helpers
- `scripts/tools/ai_inspect.py --base-url <NODE>` dumps `/ai/bridge/status`, `/ai/bridge/tasks`, and `/ai/metrics` and can be run in `--watch` mode to poll every 30s.
- `scripts/tools/ai_alert.py --base-url <NODE> --token-threshold 50000 --webhook <URL>` posts token-abuse alerts to Slack/PagerDuty when the `/ai/metrics` payload exceeds the configured threshold; it also prints the consumed-token count.
- The helper scripts can run from CI/cron with the same `API_BASE_URL` used by the schemathesis contract test so automation automatically verifies both API and AI telemetry.

## Monitoring loop
- `scripts/tools/run_monitoring.sh` chains `ai_inspect`, `ai_alert`, and an optional `WH_TOKEN` every 5 minutes. Use systemd/cron to keep this loop running so Prometheus rules such as `AITokensHigh` can be observed in the Grafana `aixn_security_operations` dashboard.
- The loop respects `BASE_URL`, `THRESHOLD`, and `WH_TOKEN` env vars; you can run it alongside the performance orchestrator script when a deploy targets the AI bridge.

## Prometheus integration
- The AI metrics exporter already introduces `xai_ai_tokens_consumed_total` and related counters, which the `AITokensHigh` rule (in `docs/runbooks/AI_MONITORING.md`) uses.
- Pair the `ai_alert` helper with the monitoring stack’s Alertmanager/PagerDuty channels (see `monitoring/alertmanager.yml`) to ensure a webhook fires right after a test scrape detects high token usage.

