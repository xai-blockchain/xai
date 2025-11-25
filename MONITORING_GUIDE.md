# XAI Blockchain - Comprehensive Monitoring and Observability Guide

Complete guide for deploying, configuring, and operating the monitoring infrastructure for the XAI blockchain network.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Components](#components)
4. [Deployment](#deployment)
5. [Configuration](#configuration)
6. [Dashboards](#dashboards)
7. [Alerting](#alerting)
8. [Logging](#logging)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)

---

## Overview

The XAI monitoring infrastructure provides comprehensive observability into blockchain operations through:

- **Real-time metrics** via Prometheus
- **Visual dashboards** with Grafana
- **Intelligent alerting** with AlertManager
- **Structured logging** for audit trails and debugging
- **Performance tracking** with histograms and percentiles
- **System health** monitoring for resource utilization

### Key Benefits

- Proactive detection of issues before they impact network
- Historical data for trend analysis and capacity planning
- Multi-level alerting for different severity issues
- Integration with incident management systems
- Production-grade reliability and scalability

---

## Architecture

### Component Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    XAI Blockchain Nodes                    │
│              (Expose metrics on port 9090)                  │
└────────────────┬────────────────────────────────────────────┘
                 │ Metrics (15s interval)
                 ▼
         ┌───────────────────┐
         │   Prometheus      │
         │   (Port 9090)     │◄──── Rule Evaluation
         │                   │      (15s interval)
         └───────┬───────────┘
                 │
         ┌───────┴──────────────┬──────────────┐
         │                      │              │
    Alerts             Metrics Storage      Rules
         │                      │              │
         ▼                      ▼              ▼
    ┌──────────────┐    ┌────────────┐  ┌──────────────┐
    │ AlertManager │    │  Grafana   │  │  Loki        │
    │ (Port 9093)  │    │(Port 3000) │  │  (Logging)   │
    └────────┬─────┘    └────────────┘  └──────────────┘
             │
    ┌────────┴─────────────────┬──────────────┐
    │                          │              │
   Slack                 PagerDuty          Email
  Channel             (On-Call)          Alerts
```

### Data Flow

1. **Node** → Exports Prometheus metrics on `/metrics` endpoint
2. **Prometheus** → Scrapes metrics every 15 seconds
3. **Alert Rules** → Evaluated against metrics
4. **AlertManager** → Routes triggered alerts to destinations
5. **Grafana** → Queries Prometheus for dashboard data
6. **Logging** → Structured JSON logs for aggregation

---

## Components

### 1. Prometheus Metrics Module (`src/xai/core/metrics.py`)

Comprehensive metrics collection covering:

#### Block Metrics
- `xai_blocks_total` - Total blocks mined (counter)
- `xai_block_height` - Current blockchain height (gauge)
- `xai_block_size_bytes` - Block size distribution (histogram)
- `xai_block_mining_time_seconds` - Mining time (histogram)
- `xai_block_validation_time_seconds` - Validation time (histogram)
- `xai_block_difficulty` - Current difficulty (gauge)

#### Transaction Metrics
- `xai_transactions_total` - Total transactions (counter, by status)
- `xai_transaction_pool_size` - Mempool size (gauge)
- `xai_transaction_throughput_per_second` - TPS (gauge)
- `xai_transaction_value_xai` - Transaction value (histogram)
- `xai_transaction_fee_xai` - Transaction fees (histogram)
- `xai_transaction_processing_time_seconds` - Processing time (histogram)

#### Network Metrics
- `xai_peers_connected` - Connected peer count (gauge)
- `xai_peers_active` - Active peers (gauge)
- `xai_network_latency_seconds` - Peer latency (histogram)
- `xai_network_messages_total` - Message count (counter, by type)
- `xai_network_errors_total` - Network errors (counter, by type)
- `xai_network_bandwidth_*_bytes_total` - Bandwidth usage (counter)

#### System Metrics
- `xai_system_cpu_usage_percent` - CPU usage (gauge)
- `xai_system_memory_*` - Memory metrics (gauge)
- `xai_system_disk_*` - Disk usage (gauge)
- `xai_process_uptime_seconds` - Process uptime (gauge)
- `xai_process_num_threads` - Thread count (gauge)

#### API Metrics
- `xai_api_requests_total` - API requests (counter)
- `xai_api_request_duration_seconds` - Request latency (histogram)
- `xai_api_active_connections` - Active connections (gauge)
- `xai_api_errors_total` - API errors (counter)

#### Mining Metrics
- `xai_mining_hashrate` - Current hashrate (gauge)
- `xai_mining_attempts_total` - Mining attempts (counter)
- `xai_mining_success_total` - Successful mines (counter)
- `xai_mining_blocks_found_total` - Blocks found (counter)

#### Blockchain State
- `xai_chain_sync_status` - Sync status (gauge: 1=synced, 0=syncing)
- `xai_chain_sync_percentage` - Sync progress (gauge)
- `xai_chain_reorgs_total` - Chain reorganizations (counter)
- `xai_orphaned_blocks_total` - Orphaned blocks (counter)

#### Wallet Control Metrics
- `xai_withdrawals_daily_total` - Number of user withdrawals approved in the current 24h window (counter)
- `xai_withdrawals_rate_per_minute` - Rolling one-minute rate of approved withdrawals (gauge)
- `xai_withdrawals_time_locked_total` - Count of withdrawals routed through the time-lock queue (counter)
- `xai_withdrawals_time_locked_backlog` - Current backlog of pending time-locked withdrawals (gauge). Alert when this grows unexpectedly to spot unreviewed large transfers.
- `XAI_WITHDRAWAL_EVENT_LOG` (env var) controls where recent withdrawal events are persisted (`monitoring/withdrawals_events.jsonl` by default). The JSONL log feeds alert debugging via `scripts/tools/withdrawal_alert_probe.py`.

#### Withdrawal Alert Probe

Use `scripts/tools/withdrawal_alert_probe.py` to shake out alert thresholds in staging before promoting to production:

```bash
python scripts/tools/withdrawal_alert_probe.py \
  --events-log monitoring/withdrawals_events.jsonl \
  --locks-file data/wallet/time_locked_withdrawals.json \
  --rate-threshold 15 \
  --backlog-threshold 5
```

The CLI prints the observed per-minute withdrawal rate, total volume, and a top offenders table for the selected window. Operations teams can run the probe alongside synthetic withdrawal bursts in staging to confirm whether 15/min and backlog>5 thresholds are appropriate.

- Production nodes expose `/admin/withdrawals/telemetry` (requires an admin API key) to return the live `rate_per_minute`, `time_locked_backlog`, and the last 20 recorded withdrawals straight from `MetricsCollector`. Use it when an alert fires to grab the offending addresses without shelling into the host.

##### CI Integration

- The staging deployment workflow (`.github/workflows/deploy-staging.yml`) runs the probe after integration tests. Configure these GitHub settings so the step reads the real staging files:
  1. In the repository settings, add secrets:
     - `STAGING_WITHDRAWAL_EVENTS_LOG` (absolute path to the JSONL log on the staging host, e.g., `/var/lib/xai/monitoring/withdrawals_events.jsonl`)
     - `STAGING_TIMELOCK_FILE` (path to the persisted time-lock snapshot, e.g., `/var/lib/xai/data/time_locked_withdrawals.json`)
  2. (Optional) Add repository variables `WITHDRAWAL_RATE_THRESHOLD` and `TIMELOCK_BACKLOG_THRESHOLD` if you want the workflow output to reflect custom alert targets. Defaults remain `15` and `5` if unset.
- If the secrets are not present the workflow falls back to the repo defaults, still printing a probe summary (likely “No withdrawal events found”), so deployments never block.
- A follow-up step runs `withdrawal_threshold_calibrator.py` and appends the recommendation to the GitHub Actions job summary (`Withdrawal Threshold Recommendation` section). Check the summary after each staging deploy to see up-to-date percentile math without downloading logs. The same summary is piped into Slack automatically, and PagerDuty only fires when the recommended thresholds exceed the currently configured values so responders only get paged when action is required.
- The workflow also writes `threshold_details.json` (structured summary) and pipes it through `scripts/tools/threshold_artifact_ingest.py`. Each deploy now uploads the JSON + Markdown summary + an append-only history file (`monitoring/withdrawal_threshold_history.jsonl`) so dashboards and tickets can ingest an exact copy of the telemetry without screen scraping.
- Set the repository variable `WITHDRAWAL_CALIBRATION_ISSUE` to the GitHub issue number that should receive a permanent comment after each calibration. When the variable is populated, the staging workflow invokes `scripts/tools/threshold_artifact_publish.py`, which posts the Markdown summary to that issue using the built-in `GITHUB_TOKEN`. Use this to maintain an external runbook/discussion even if GitHub artifacts expire.
- Optionally configure additional publication targets:
  - Secret `WITHDRAWAL_CALIBRATION_SLACK_WEBHOOK`: Slack Incoming Webhook URL that will receive the same Markdown summary (handy for #runbooks or private security channels).
  - Repo variable `WITHDRAWAL_CALIBRATION_JIRA_ISSUE` plus secrets `JIRA_BASE_URL`, `JIRA_EMAIL`, and `JIRA_API_TOKEN`: enables the workflow to post a Jira comment via the REST API after every calibration.

##### Tuning Thresholds

1. Trigger a staging deployment (merge to `develop` or manually dispatch).
2. Watch the “Withdrawal telemetry probe” step in GitHub Actions → the log lists the measured rate, volume, and top users for the last minute.
3. For deeper analysis, run `scripts/tools/withdrawal_threshold_calibrator.py` against the persisted `withdrawals_events.jsonl` to compute percentiles and suggested thresholds with configurable headroom.
4. Compare the observed peak rate/backlog against the configured thresholds:
   - If real traffic stays far below the limits, lower `WITHDRAWAL_RATE_THRESHOLD` / `TIMELOCK_BACKLOG_THRESHOLD` repo variables to catch spikes sooner.
   - If staging tests regularly exceed the limits, raise the variables (and update `prometheus/alerts/security_operations.yml`) so alerts fire only on genuine anomalies.
- Commit any rule updates and rerun staging to verify the probe output aligns with the new targets before promoting to production.

##### Threshold Artifacts & History

`threshold_details.json` captures everything the calibrator computes (percentiles, max rate, backlog snapshot, top users, recommended thresholds, and current repo vars). After each staging deploy the workflow feeds this JSON into `scripts/tools/threshold_artifact_ingest.py`, which:

- Appends a normalized record to `monitoring/withdrawal_threshold_history.jsonl`
- Emits a Markdown summary (`threshold_summary.md`) suitable for pasting into incident tickets or Confluence
- Prints the same Markdown to stdout so the GitHub job log mirrors what went into Slack/PagerDuty
- (Optional) Calls `scripts/tools/threshold_artifact_publish.py` to post the Markdown to GitHub Issues, Slack webhooks, or Jira issues once the corresponding environment variables are configured.
- Enforces retention if `--max-history-entries` is set (the staging workflow keeps the most recent 500 entries by default). Tweak this number to match your log retention goals or run the CLI manually to prune older entries.

You can replay the ingestion locally against any artifact:

```bash
python scripts/tools/threshold_artifact_ingest.py \
  --details threshold_details.json \
  --history-file monitoring/withdrawal_threshold_history.jsonl \
  --environment staging \
  --max-history-entries 500 \
  --markdown-output threshold_summary.md \
  --print-markdown

# Publish to GitHub + Slack + Jira (all optional)
python scripts/tools/threshold_artifact_publish.py \
  --details threshold_details.json \
  --markdown threshold_summary.md \
  --github-repo your-org/your-repo \
  --issue-number 1234 \
  --slack-webhook https://hooks.slack.com/... \
  --jira-base-url https://yourcompany.atlassian.net \
  --jira-issue-key OPS-42 \
  --jira-email ops@example.com \
  --jira-api-token <token>
```

The history JSONL is intentionally append-only and includes timestamps, commit SHA (auto-detected), recommendations, current thresholds, and the inputs used for the run. Point custom Grafana dashboards or runbooks at this log if you want longitudinal plots of recommended vs. configured limits, or feed it into incident templates so responders can see prior calibrations alongside the current alert.

###### Shipping the History File to Loki/Grafana

1. Update `docker/monitoring/promtail/promtail-config.yml` (or the equivalent promtail deployment) with the provided scrape job:

```yaml
  - job_name: withdrawal-threshold-history
    static_configs:
      - targets:
          - localhost
        labels:
          job: withdrawal_threshold_history
          __path__: /var/lib/xai/monitoring/withdrawal_threshold_history.jsonl
    pipeline_stages:
      - json:
          expressions:
            generated_at: generated_at
            environment: environment
            recommended_rate: recommended_rate
            recommended_backlog: recommended_backlog
            current_rate_threshold: current_rate_threshold
            current_backlog_threshold: current_backlog_threshold
            alert_required: alert_required
      - timestamp:
          source: generated_at
          format: RFC3339Nano
      - labels:
          environment:
          alert_required:
```

   Adjust the `__path__` to wherever the JSONL history lives on the node (`/var/lib/xai/...` when using the provided deployment).
2. Import `dashboards/grafana/aixn_withdrawal_threshold_history.json` in Grafana. The dashboard includes:
   - A comparison panel for recommended vs. configured withdrawal rate thresholds (Loki queries using `unwrap recommended_rate` / `current_rate_threshold`)
   - A similar panel for backlog thresholds
   - A table showing the latest calibrations and whether `alert_required` was triggered
3. (Optional) Point alert panels at the same job to ensure the on-call view stays in sync with GitHub ticket comments.
4. Use the `--max-history-entries` flag on `threshold_artifact_ingest.py` (staging uses 500) or a periodic cron invocation to prune the JSONL file so it never grows without bound on production disks.

For an end-to-end checklist covering promtail mounts, Grafana import, Slack/Jira/issue secrets, and verification steps, see `monitoring/WITHDRAWAL_THRESHOLD_RUNBOOK.md`.

---

## Deployment

### Prerequisites

```bash
# Required services
- Docker and Docker Compose
- Prometheus 2.30+
- Grafana 8.0+
- AlertManager 0.21+
- Node Exporter (optional, for system metrics)
```

### Quick Start

1. **Ensure monitoring directory exists:**
   ```bash
   mkdir -p monitoring/
   mkdir -p docker/monitoring/grafana/dashboards
   mkdir -p docker/monitoring/grafana/datasources
   ```

2. **Configure environment variables:**
   ```bash
   # .env file
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
   PAGERDUTY_SERVICE_KEY=your_pagerduty_service_key
   ALERT_EMAIL_CRITICAL=devops@xai.network
   EMAIL_SMTP_HOST=smtp.gmail.com
   EMAIL_SMTP_PORT=587
   EMAIL_USERNAME=alerts@xai.network
   EMAIL_PASSWORD=your_email_password
   ```

3. **Start monitoring stack:**
   ```bash
   # Using Docker Compose
   docker-compose -f docker/monitoring/docker-compose.yml up -d
   ```

4. **Verify services are running:**
   ```bash
   # Check Prometheus
   curl http://localhost:9090/

   # Check Grafana
   curl http://localhost:3000/

   # Check AlertManager
   curl http://localhost:9093/
   ```

### Docker Compose Setup

Create `docker/monitoring/docker-compose.yml`:

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: xai-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/prometheus_alerts.yml:/etc/prometheus/rules/alerts.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:latest
    container_name: xai-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_INSTALL_PLUGINS=grafana-piechart-panel
    volumes:
      - ./docker/monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
      - ./docker/monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - grafana_data:/var/lib/grafana
    networks:
      - monitoring
    depends_on:
      - prometheus

  alertmanager:
    image: prom/alertmanager:latest
    container_name: xai-alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager.yml:/etc/alertmanager/config.yml
      - ./monitoring/alert_templates.tmpl:/etc/alertmanager/templates.tmpl
      - alertmanager_data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/config.yml'
      - '--storage.path=/alertmanager'
    networks:
      - monitoring

  node-exporter:
    image: prom/node-exporter:latest
    container_name: xai-node-exporter
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    networks:
      - monitoring

volumes:
  prometheus_data:
  grafana_data:
  alertmanager_data:

networks:
  monitoring:
    driver: bridge
```

---

## Configuration

### Prometheus Configuration

**File:** `docker/monitoring/prometheus.yml`

Key settings:
- **scrape_interval**: 15s (how often to scrape metrics)
- **evaluation_interval**: 15s (how often to evaluate alert rules)
- **retention**: 30 days (how long to store data)
- **alertmanagers**: Points to AlertManager service

### Alert Rules

**File:** `monitoring/prometheus_alerts.yml`

Organized into alert groups:

#### Critical Alerts (immediate action required)
- **NodeDown** - Node unavailable for 2 minutes
- **NoPeersConnected** - No peer connections
- **CriticalCPUUsage** - CPU > 95%
- **CriticalMemoryUsage** - Memory > 95%
- **CriticalDiskSpace** - Disk < 5%

#### Warning Alerts
- **LowPeerCount** - < 2 peers
- **HighNetworkErrorRate** - Network error rate > 0.5/sec
- **LowBlockProductionRate** - No blocks in 10 minutes
- **ChainNotSynced** - Chain not synced for 10 minutes
- **HighCPUUsage** - CPU > 80%
- **HighMemoryUsage** - Memory > 85%

#### Info Alerts
- **HighTransactionFees** - Fee trend information
- **LowTransactionThroughput** - TPS information

### AlertManager Configuration

**File:** `monitoring/alertmanager.yml`

Routing rules:
- **critical** → PagerDuty + Slack + Email (immediate)
- **network** → Network team Slack channel
- **system** → System alerts channel (grouped)
- **api** → API team alerts
- **info** → Daily digest

---

## Dashboards

### 1. Blockchain Overview (`blockchain_overview.json`)

Main dashboard showing:
- Block production rate
- Current blockchain height
- Transaction throughput (TPS)
- Network peer count
- Mining time percentiles
- Transaction pool size
- Network hashrate

**Access:** http://localhost:3000/d/xai-overview

### 2. Node Health (`node_health.json`)

System resource monitoring:
- CPU usage (gauge and trends)
- Memory usage (gauge and trends)
- Disk usage (gauge and trends)
- Process uptime
- Thread count
- Memory in bytes

**Access:** http://localhost:3000/d/xai-node-health

### 3. Transaction Metrics (`transaction_metrics.json`)

Transaction-focused view:
- Transaction rate by status
- Current mempool size
- Transaction processing time (p95, median)
- Transaction fees (p95, median)
- Transactions by status (pie chart)
- Transaction value distribution

**Access:** http://localhost:3000/d/xai-transactions

### 4. Security Operations (`aixn_security_operations.json`)

Track authentication + security posture in one board:
- **Security Event Rate** (`increase(xai_security_events_total[5m])`)
- **Warnings vs Critical** stacked bar (`increase(xai_security_events_warning_total[5m])`, `increase(xai_security_events_critical_total[5m])`)
- **API Key Audit Stream** table (labels from `api_key_audit` events via Loki/ELK)
- **Peer Auth Coverage** single stat showing percentage of connected peers advertising `XAI_PEER_API_KEY` (use custom exporter or JSON field)
- **Webhook Delivery Lag** panel from the node logs (count of `_SecurityWebhookForwarder.dropped_events` via Prom tail)

Files to provision:
- Grafana JSON: `dashboards/grafana/aixn_security_operations.json`
- Prometheus rules: `prometheus/alerts/security_operations.yml`

Sample Grafana panel snippet:
```json
{
  "type": "timeseries",
  "title": "Security Warnings vs Critical",
  "targets": [
    {"expr": "increase(xai_security_events_warning_total[5m])", "legendFormat": "warnings"},
    {"expr": "increase(xai_security_events_critical_total[5m])", "legendFormat": "critical"}
  ],
  "fieldConfig": {
    "defaults": {"unit": "events", "thresholds": {"mode": "absolute", "steps": [{"color": "green"}, {"color": "red", "value": 1}]}}
  }
}
```

> **Tip:** Set `XAI_SECURITY_WEBHOOK_URL`/`XAI_SECURITY_WEBHOOK_TOKEN` on every node so WARN+/CRITICAL events reach PagerDuty/Slack even if Prometheus or Alertmanager are offline. The dashboard panels then validate webhook performance by charting dropped events.
> **Key Management:** Generate an encrypted queue key via `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` and export it as `XAI_SECURITY_WEBHOOK_QUEUE_KEY` so the persisted webhook backlog is unreadable at rest.

### Importing Dashboards

1. **Method 1: Auto-provision via Docker Compose**
   - Place JSON files in `docker/monitoring/grafana/dashboards/`
   - Dashboards automatically imported on startup

2. **Method 2: Manual import**
   - Go to Grafana → Dashboards → Import
   - Paste dashboard JSON content
   - Select Prometheus datasource

### Customizing Dashboards

Edit JSON files directly:
- **gridPos**: Position (x, y, width, height)
- **targets**: Prometheus queries (PromQL expressions)
- **panels**: Individual visualization panels
- **fieldConfig**: Display settings (thresholds, units, colors)

---

## Alerting

### Alert Routing

Alerts are routed based on severity and service:

```
Critical (severity=critical)
├─ Node Down → PagerDuty (5 min rotation)
├─ High Resource → Email + Slack
└─ Chain Issues → Network team

Warning (severity=warning)
├─ Low Peers → Network Slack
├─ Sync Issues → Blockchain Slack
└─ Performance → API Slack

Info (severity=info)
└─ Daily Digest → General Slack (10am UTC)
```

### Notification Channels

#### Slack Integration
```yaml
slack_configs:
  - channel: "#blockchain-alerts"
    title: "{{ .GroupLabels.alertname }}"
    text: "{{ .Annotations.description }}"
    send_resolved: true
```

#### PagerDuty Integration
```yaml
pagerduty_configs:
  - service_key: "${PAGERDUTY_SERVICE_KEY}"
    description: "{{ .GroupLabels.alertname }}"
```

#### Email Alerts
```yaml
email_configs:
  - to: "${ALERT_EMAIL_CRITICAL}"
    from: "alertmanager@xai.network"
    smarthost: "${EMAIL_SMTP_HOST}:${EMAIL_SMTP_PORT}"
```

### Testing Alerts

1. **Generate test alert:**
   ```bash
   # Use Prometheus UI to trigger rule evaluation
   # Or manually send to AlertManager:

   curl -XPOST http://localhost:9093/api/v1/alerts \
     -H 'Content-Type: application/json' \
     -d '{
       "alerts": [{
         "status": "firing",
         "labels": {
           "alertname": "TestAlert",
           "severity": "critical",
           "service": "blockchain"
         },
         "annotations": {
           "summary": "Test alert",
           "description": "This is a test alert"
         }
       }]
     }'
   ```

2. **Check AlertManager status:**
   ```bash
   # View active alerts
   curl http://localhost:9093/api/v1/alerts

   # View alert groups
   curl http://localhost:9093/api/v1/alerts/groups
   ```

### Security Event Alerts

- Every call to `log_security_event` (including API key issuance/revocation) now feeds the metrics collector via `SecurityEventRouter`.
- Prometheus scrapes three counters for dashboards and rule evaluations:
  - `xai_security_events_total`
  - `xai_security_events_warning_total`
  - `xai_security_events_critical_total`
- Example rule to page on unexpected key revocations:

```yaml
groups:
  - name: security.rules
    rules:
      - alert: ApiKeyRevocations
        expr: increase(xai_security_events_warning_total[5m]) > 0
        for: 0m
        labels:
          severity: critical
          service: security
        annotations:
          summary: "API key rotation detected"
          description: "api_key_audit events exceeded the allowed threshold. Inspect secure_keys/api_keys.json.log and PagerDuty incident."

      - alert: WithdrawalRateSpike
        expr: xai_withdrawals_rate_per_minute > 15
        for: 2m
        labels:
          severity: warning
          service: withdrawals
        annotations:
          summary: "Withdrawal velocity exceeded baseline"
          description: "One-minute withdrawal rate stayed above 15/min for 2 minutes. Investigate potential automated draining."

      - alert: TimeLockBacklogGrowing
        expr: xai_withdrawals_time_locked_backlog > 5
        for: 10m
        labels:
          severity: warning
          service: withdrawals
        annotations:
          summary: "Time-locked queue accumulating"
          description: "More than five withdrawals are stuck in the time-lock queue for over 10 minutes."
```

Because `PEER_AUTH_BOOTSTRAP.md` also relies on API key events, this alerting path doubles as the monitoring hook for node join/rotation approval flows.

To guarantee delivery even if Prometheus is unreachable, set `XAI_SECURITY_WEBHOOK_URL` (and optional `XAI_SECURITY_WEBHOOK_TOKEN`, `XAI_SECURITY_WEBHOOK_TIMEOUT`) on every node. The runtime sends WARN/ERROR/CRITICAL `log_security_event` payloads directly to that webhook so PagerDuty/Slack/Webex integrations continue operating during outages.

---

## Logging

### Structured JSON Logging

The metrics module includes structured logging for JSON-formatted output:

```python
from xai.core.metrics import StructuredLogger

logger = StructuredLogger(
    name="xai.blockchain",
    log_file="/var/log/xai/blockchain.json"
)

# Log with structured data
logger.info(
    "Block validated",
    block_height=1234,
    validation_time=1.5,
    transactions=150
)
```

Output format:
```json
{
  "timestamp": "2024-01-15T10:30:45.123456Z",
  "level": "info",
  "name": "xai.blockchain",
  "message": "Block validated",
  "block_height": 1234,
  "validation_time": 1.5,
  "transactions": 150
}
```

### Log Aggregation

#### ELK Stack Integration
```yaml
# Filebeat configuration
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/xai/*.json
  json.message_key: message
  json.keys_under_root: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "xai-%{+yyyy.MM.dd}"
```

#### Loki Integration
```yaml
# Promtail configuration
scrape_configs:
  - job_name: xai-logs
    static_configs:
      - targets:
          - localhost
        labels:
          job: xai
          __path__: /var/log/xai/*.json
```

---

## Troubleshooting

### Common Issues

#### 1. Prometheus Not Scraping Metrics

**Problem:** Targets showing as "DOWN" in Prometheus UI

**Solutions:**
```bash
# Check target is reachable
curl http://xai-node:9090/metrics

# Verify DNS resolution
docker exec xai-prometheus nslookup xai-node

# Check Prometheus logs
docker logs xai-prometheus | grep "error"

# Verify firewall rules
docker exec xai-prometheus nc -zv xai-node 9090
```

#### 2. Alerts Not Firing

**Problem:** Alert rules not triggering

**Solutions:**
```bash
# Check alert rule evaluation
curl http://localhost:9090/api/v1/query?query=up

# View rule status
curl http://localhost:9090/api/v1/rules

# Check AlertManager configuration
curl http://localhost:9093/api/v1/status

# Verify alert manager logs
docker logs xai-alertmanager | grep -i error
```

#### 3. Grafana Dashboards Blank

**Problem:** No data showing in dashboards

**Solutions:**
```bash
# Verify Prometheus datasource
# In Grafana: Configuration → Data Sources → Test

# Check for data in Prometheus
curl 'http://localhost:9090/api/v1/query?query=up'

# Verify time range in dashboard
# Default: Last 6 hours

# Check dashboard queries in Network tab
```

#### 4. High Memory Usage

**Problem:** Prometheus using excessive memory

**Solutions:**
```yaml
# Increase retention period carefully
--storage.tsdb.retention.time=15d  # Reduce from 30d

# Limit cardinality
metric_relabel_configs:
  - source_labels: [__name__]
    regex: '.*_bucket'
    action: drop

# Check for label explosion
curl 'http://localhost:9090/api/v1/label/__name__/values'
```

---

## Best Practices

### 1. Metrics

- **Use appropriate metric types**
  - Counter: always increasing values (requests, errors)
  - Gauge: values that can go up/down (CPU, memory)
  - Histogram: observations of values (latency, size)

- **Meaningful labels**
  ```python
  # Good: semantic labels
  network_latency_seconds{peer="node-5", region="us-east"}

  # Bad: too high cardinality
  request_duration_seconds{user_id="12345", timestamp="..."}
  ```

- **Name conventions**
  - Prefix with component: `xai_`
  - Use `_total` for counters
  - Use `_seconds` for durations
  - Use `_bytes` for sizes

### 2. Alerting

- **Meaningful alert messages**
  ```yaml
  # Good: actionable
  description: "Node {{ $labels.instance }} has no peers. Check network connectivity."

  # Bad: vague
  description: "Alert fired"
  ```

- **Alert fatigue prevention**
  - Set reasonable thresholds
  - Use `for` clause (1m minimum)
  - Implement inhibition rules
  - Don't alert on expected spikes

- **Runbook links**
  ```yaml
  annotations:
    runbook: "https://docs.xai.network/runbooks/{{ $labels.alertname | toLower }}"
  ```

### 3. Dashboards

- **Single responsibility**
  - One dashboard per role (blockchain, ops, development)
  - Keep related panels together

- **Clear labeling**
  - Use descriptive titles
  - Add description/help text
  - Include units in axis labels

- **Performance**
  - Limit panels per dashboard (max 20)
  - Use appropriate time ranges
  - Avoid complex queries

### 4. Security

- **Sensitive data**
  - Don't expose secrets in labels
  - Use relabeling to remove sensitive data
  ```yaml
  metric_relabel_configs:
    - source_labels: [auth_token]
      action: drop
  ```

- **Access control**
  - Restrict Prometheus UI access
  - Use Grafana RBAC for dashboard permissions
  - Separate monitoring for sensitive data

- **Encryption**
  - Use HTTPS for Grafana
  - Encrypt alerts in transit
  - Secure credential storage

### 5. Scaling

- **Multiple Prometheus instances**
  ```yaml
  # Federation setup
  - job_name: 'federation'
    scrape_interval: 30s
    honor_labels: true
    metrics_path: '/federate'
    params:
      match[]:
        - '{job="xai-node"}'
    static_configs:
      - targets:
        - 'prometheus-1:9090'
  ```

- **Data retention**
  - Balance retention with storage
  - Archive old data to cold storage
  - Use `-storage.tsdb.retention.time`

- **Remote storage**
  ```yaml
  # Send metrics to remote storage
  remote_write:
    - url: "http://cortex:9009/api/prom/push"
      write_relabel_configs:
        - source_labels: [__name__]
          regex: '(xai_|up)'
          action: keep
  ```

---

## Maintenance

### Regular Tasks

| Task | Frequency | Description |
|------|-----------|-------------|
| Review alert thresholds | Monthly | Adjust based on network growth |
| Backup Prometheus data | Weekly | Preserve historical metrics |
| Update Grafana | Quarterly | Security patches, new features |
| Audit alert routing | Monthly | Ensure correct team notifications |
| Test disaster recovery | Quarterly | Verify backup and restore |
| Review dashboard usage | Monthly | Remove unused, update outdated |

### Updating Monitoring Components

```bash
# Update Prometheus
docker pull prom/prometheus:latest
docker-compose up -d prometheus

# Update Grafana
docker pull grafana/grafana:latest
docker-compose up -d grafana

# Backup before updates
docker exec xai-prometheus tar czf /tmp/prometheus-backup.tar.gz /prometheus
docker cp xai-prometheus:/tmp/prometheus-backup.tar.gz ./backups/
```

---

## Support and Resources

- **Prometheus Documentation**: https://prometheus.io/docs/
- **Grafana Documentation**: https://grafana.com/docs/
- **AlertManager Guide**: https://prometheus.io/docs/alerting/latest/alertmanager/
- **XAI Documentation**: https://docs.xai.network

---

## Appendix: Quick Reference

### Common PromQL Queries

```promql
# Block production rate (blocks per minute)
rate(xai_blocks_total[5m]) * 60

# Current network hashrate
xai_mining_hashrate

# Transaction throughput
rate(xai_transactions_total[5m])

# Peer connectivity
xai_peers_connected

# CPU usage average
avg(xai_system_cpu_usage_percent)

# High memory alert threshold
xai_system_memory_percent > 85

# API error rate
rate(xai_api_errors_total[5m]) / rate(xai_api_requests_total[5m])

# Block validation p95 percentile
histogram_quantile(0.95, rate(xai_block_validation_time_seconds_bucket[5m]))
```

### Useful Endpoints

```
Prometheus UI:     http://localhost:9090/
Prometheus Query:  http://localhost:9090/api/v1/query
Grafana UI:        http://localhost:3000/
AlertManager UI:   http://localhost:9093/
Node Metrics:      http://xai-node:9090/metrics
```

---

**Last Updated:** 2024-01-15
**Version:** 1.0.0
**Maintainers:** DevOps Team
