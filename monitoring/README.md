# XAI Blockchain - Monitoring Infrastructure

Complete monitoring and observability stack for production deployment.

## Quick Start

### Start Monitoring Stack

```bash
cd docker/monitoring
docker-compose up -d
```

### Access Services

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **AlertManager**: http://localhost:9093
- **Node Exporter**: http://localhost:9100/metrics

### Configuration Files

This directory contains:

1. **prometheus_alerts.yml** - Alert rules for critical conditions
   - Node availability
   - Network health
   - Block production
   - Transaction processing
   - System resources
   - API health
   - Mining metrics
   - Chain synchronization

2. **alertmanager.yml** - Alert routing and notification configuration
   - Routes alerts by severity and service
   - Slack integration
   - PagerDuty on-call integration
   - Email notifications
   - Alert inhibition rules

3. **alert_templates.tmpl** - Notification templates
   - Slack message formatting
   - Email templates
   - PagerDuty integration

## File Structure

```
monitoring/
├── README.md                          # This file
├── prometheus_alerts.yml              # Alert rules
├── alertmanager.yml                   # Alert routing config
├── alert_templates.tmpl               # Notification templates

docker/monitoring/
├── docker-compose.yml                 # Complete monitoring stack
├── prometheus.yml                     # Prometheus configuration
├── grafana/
│   ├── grafana.ini                    # Grafana config
│   ├── datasources/
│   │   └── prometheus.yml             # Prometheus datasource
│   └── dashboards/
│       ├── blockchain_overview.json   # Main dashboard
│       ├── node_health.json           # System metrics
│       └── transaction_metrics.json   # TX analytics
├── loki/
│   └── loki-config.yml                # Log aggregation
└── promtail/
    └── promtail-config.yml            # Log shipper

src/xai/core/
├── metrics.py                         # Prometheus metrics module
└── logging_config.py                  # Structured JSON logging
```

## Key Components

### Prometheus Metrics (`src/xai/core/metrics.py`)

Exports metrics across categories:

- **Block Metrics**: Height, size, mining time, difficulty
- **Transaction Metrics**: Count, pool size, fees, throughput
- **Network Metrics**: Peers, bandwidth, latency, messages
- **System Metrics**: CPU, memory, disk, uptime
- **API Metrics**: Request rate, latency, errors
- **Mining Metrics**: Hashrate, attempts, success rate
- **Blockchain State**: Sync status, reorgs, orphaned blocks

### Alert Rules (`prometheus_alerts.yml`)

Comprehensive alerting for:

- Critical conditions (node down, no peers, out of space)
- Performance issues (high latency, low throughput)
- Resource constraints (CPU, memory, disk)
- Network problems (connection issues, high errors)
- Blockchain anomalies (sync issues, reorgs)

### Dashboards

Three production-ready Grafana dashboards:

1. **Blockchain Overview** - Network-wide metrics
2. **Node Health** - System resource monitoring
3. **Transaction Metrics** - Transaction pool and processing

### Structured Logging (`src/xai/core/logging_config.py`)

JSON-formatted logs for aggregation:

```python
from xai.core.logging_config import setup_logging

logger = setup_logging(
    name="xai.blockchain",
    log_file="/var/log/xai/blockchain.json"
)

logger.info("Block mined", height=100, time=2.5)
```

## Environment Variables

Create `.env` file for notifications:

```bash
# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# PagerDuty
PAGERDUTY_SERVICE_KEY=your_service_key

# Email
ALERT_EMAIL_CRITICAL=devops@xai.network
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=alerts@xai.network
EMAIL_PASSWORD=your_password
```

## Usage

### Check Metrics

```bash
# View all metrics
curl http://localhost:9090/api/v1/query?query=up

# Get specific metric
curl 'http://localhost:9090/api/v1/query?query=xai_block_height'

# Query with time range
curl 'http://localhost:9090/api/v1/query_range?query=rate(xai_blocks_total[5m])&start=2024-01-15T00:00:00Z&end=2024-01-15T12:00:00Z&step=1m'
```

### View Alerts

```bash
# List all alerts in Prometheus
curl http://localhost:9090/api/v1/alerts

# List alerts in AlertManager
curl http://localhost:9093/api/v1/alerts

# View alert groups
curl http://localhost:9093/api/v1/alerts/groups
```

### Grafana Queries

Common PromQL queries:

```promql
# Block production rate (blocks/min)
rate(xai_blocks_total[5m]) * 60

# Transactions per second
rate(xai_transactions_total[1m])

# Average peer count
avg(xai_peers_connected)

# CPU usage
avg(xai_system_cpu_usage_percent)

# Block validation p95
histogram_quantile(0.95, rate(xai_block_validation_time_seconds_bucket[5m]))

# Memory usage percentage
avg(xai_system_memory_percent)
```

## Troubleshooting

### Prometheus Not Scraping

```bash
# Check if metrics endpoint is reachable
curl http://xai-node:9090/metrics

# View scrape configuration
docker exec xai-prometheus cat /etc/prometheus/prometheus.yml

# Check logs
docker logs xai-prometheus | grep error
```

### Alerts Not Firing

```bash
# Verify AlertManager is running
docker logs xai-alertmanager

# Check configuration syntax
docker exec xai-alertmanager amtool config routes

# Test with manual alert
curl -XPOST http://localhost:9093/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {"alertname": "Test", "severity": "critical"},
      "annotations": {"summary": "Test alert"}
    }]
  }'
```

### No Data in Grafana

```bash
# Verify Prometheus datasource in Grafana UI
# Configuration → Data Sources → Prometheus (Test)

# Check if metrics exist
curl 'http://localhost:9090/api/v1/label/__name__/values' | jq '.data[] | select(startswith("xai"))'

# View recent scrape results
# Prometheus UI → Targets → Show details
```

## Maintenance

### Backup Prometheus Data

```bash
# Backup current data
docker exec xai-prometheus tar czf /prometheus-backup.tar.gz /prometheus
docker cp xai-prometheus:/prometheus-backup.tar.gz ./backups/

# Restore from backup
docker exec xai-prometheus tar xzf /prometheus-backup.tar.gz -C /
```

### Update Components

```bash
# Pull latest images
docker pull prom/prometheus:latest
docker pull grafana/grafana:latest
docker pull prom/alertmanager:latest

# Restart services
docker-compose up -d
```

### Clean Up

```bash
# Remove all monitoring containers
docker-compose down

# Remove volumes (warning: deletes data)
docker-compose down -v
```

## Performance Tuning

### Prometheus

- Adjust scrape interval: `scrape_interval: 15s`
- Increase retention: `--storage.tsdb.retention.time=30d`
- Enable compression: `--storage.tsdb.wal-compression`

### Grafana

- Increase max data points: `maxDataPoints: 3000`
- Enable query caching
- Use recording rules for complex queries

### AlertManager

- Batch notifications: `group_wait: 10s`
- Throttle repeated alerts: `repeat_interval: 4h`
- Use inhibition rules to reduce noise

## See Also

- [MONITORING_GUIDE.md](../MONITORING_GUIDE.md) - Complete monitoring guide
- [src/xai/core/metrics.py](../src/xai/core/metrics.py) - Metrics implementation
- [src/xai/core/logging_config.py](../src/xai/core/logging_config.py) - Logging setup

## Support

For issues or questions:
1. Check [MONITORING_GUIDE.md](../MONITORING_GUIDE.md) troubleshooting section
2. Review component logs: `docker logs <container>`
3. Verify configuration syntax in Prometheus/AlertManager UIs
4. Check network connectivity between services

---

**Last Updated:** 2024-01-15
**Version:** 1.0.0
