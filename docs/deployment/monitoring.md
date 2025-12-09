# Monitoring & Logging

This page outlines monitoring/logging for production/testnet nodes.

- **Prometheus**: scrape `/metrics` (see `docker/` compose files). Track rate limits, mempool pressure, peer counts, and security events.
- **Grafana**: import dashboards from `monitoring/`. Key panels: 4xx/5xx rates, mempool depth/fees, peer churn, sync height, resource usage.
- **Logs**: Structured logging enabled; ship to SIEM. Security events use `event` keys (rate limits, CSRF, signing failures).
- **Alerts**: High 429/403 rates, sync lag, peer drops, disk usage, mempool pressure spikes.
- **Smoke tests**: `scripts/tools/send_rejection_smoke_test.sh` validates rejection telemetry after deploy.
- **TLS/Proxy**: Terminate HTTPS at proxy; ensure headers preserved for logging client info if needed.***
