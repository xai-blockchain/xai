# XAI Blockchain - Monitoring Infrastructure Index

Complete index and navigation guide for the monitoring and observability infrastructure.

## Quick Navigation

### For Operations/DevOps
1. Start here: [MONITORING_GUIDE.md](../MONITORING_GUIDE.md) - Complete operations guide
2. Setup checklist: [MONITORING_SETUP_CHECKLIST.md](../MONITORING_SETUP_CHECKLIST.md)
3. Quick reference: [monitoring/README.md](../monitoring/README.md)

### For Developers
1. Integration guide: [METRICS_INTEGRATION.md](./METRICS_INTEGRATION.md)
2. Metrics module: [src/xai/core/metrics.py](../src/xai/core/metrics.py)
3. Logging setup: [src/xai/core/logging_config.py](../src/xai/core/logging_config.py)

### For System Administrators
1. Infrastructure summary: [MONITORING_INFRASTRUCTURE_SUMMARY.md](../MONITORING_INFRASTRUCTURE_SUMMARY.md)
2. Docker deployment: [docker/monitoring/docker-compose.yml](../docker/monitoring/docker-compose.yml)
3. Configuration: [docker/monitoring/](../docker/monitoring/)

---

## File Directory Structure

```
C:\Users\decri\GitClones\Crypto\
│
├── MONITORING_GUIDE.md                          # Main operations guide (900+ lines)
├── MONITORING_SETUP_CHECKLIST.md                # Deployment checklist (600+ lines)
├── MONITORING_INFRASTRUCTURE_SUMMARY.md         # Complete overview
│
├── monitoring/                                  # Alert configurations
│   ├── README.md                               # Quick reference
│   ├── prometheus_alerts.yml                   # Alert rules (40+ rules)
│   ├── alertmanager.yml                        # Alert routing config
│   └── alert_templates.tmpl                    # Notification templates
│
├── docker/monitoring/                          # Docker deployment stack
│   ├── docker-compose.yml                      # Complete stack (400+ lines)
│   ├── prometheus.yml                          # Prometheus config
│   ├── grafana/
│   │   ├── grafana.ini                         # Grafana configuration
│   │   ├── datasources/
│   │   │   └── prometheus.yml                  # Datasource config
│   │   └── dashboards/
│   │       ├── blockchain_overview.json        # Main dashboard
│   │       ├── node_health.json                # System metrics
│   │       └── transaction_metrics.json        # TX analytics
│   ├── loki/
│   │   └── loki-config.yml                     # Log storage config
│   └── promtail/
│       └── promtail-config.yml                 # Log shipper config
│
├── src/xai/core/
│   ├── metrics.py                              # Metrics module (900+ lines)
│   └── logging_config.py                       # Logging module (500+ lines)
│
└── docs/
    ├── MONITORING_INDEX.md                     # This file
    └── METRICS_INTEGRATION.md                  # Developer integration guide
```

---

## Core Components

### 1. Prometheus Metrics (`src/xai/core/metrics.py`)

**What it does:** Collects and exports blockchain metrics in Prometheus format

**Metric Categories:**
- Block metrics (100 metrics)
- Transaction metrics (1000+ metrics)
- Network metrics (200+ metrics)
- System metrics (50+ metrics)
- API metrics (500+ metrics)
- Mining metrics (100+ metrics)
- Blockchain state (50+ metrics)
- Validation metrics (20+ metrics)
- AI task metrics (10+ metrics)

**Key Methods:**
```python
# Initialize
initialize_metrics(port=8000, version="1.0.0", network="mainnet", node_id="")

# Get global instance
get_metrics()

# Export metrics
metrics.export_prometheus()

# Record events
metrics.record_block(height, size, difficulty, mining_time, validation_time)
metrics.record_transaction(status, value, fee, processing_time)
metrics.update_peer_count(count, active)
metrics.record_api_request(endpoint, method, status, duration)
```

**Usage Example:**
```python
from xai.core.metrics import initialize_metrics

metrics = initialize_metrics(
    port=8000,
    version="1.0.0",
    network="mainnet",
    node_id="xai-node-1"
)

# Record a block
metrics.record_block(
    height=1234,
    size=5000,
    difficulty=1000,
    mining_time=30,
    validation_time=0.5
)
```

---

### 2. Structured Logging (`src/xai/core/logging_config.py`)

**What it does:** Provides JSON-formatted logging for log aggregation

**Features:**
- JSON output format
- Rotating file handlers
- Multiple log levels
- Integration with ELK, Loki, Datadog
- Thread-safe operations

**Key Functions:**
```python
# Setup logger
logger = setup_logging(
    name="module.name",
    log_file="/var/log/xai/module.json",
    level="INFO"
)

# Log with context
logger.info("Block validated", height=1234, time=0.5)

# Preset configurations
blockchain_logger = setup_blockchain_logging()
api_logger = setup_api_logging()
network_logger = setup_network_logging()
mining_logger = setup_mining_logging()
```

---

### 3. Prometheus Configuration (`docker/monitoring/prometheus.yml`)

**What it does:** Defines what metrics to scrape and how often

**Scrape Targets:**
- XAI Node (main): `xai-node:9090`
- Additional nodes: `xai-node-2:9090`, `xai-node-3:9090`
- PostgreSQL: `postgres:9187`
- Redis: `redis:9121`
- Node Exporter: `node-exporter:9100`
- Docker: `docker-exporter:9323`
- Validators: `validator-1:9090`

**Configuration:**
- Scrape interval: 15s
- Evaluation interval: 15s
- Retention period: 30 days
- AlertManager: `alertmanager:9093`

---

### 4. Alert Rules (`monitoring/prometheus_alerts.yml`)

**What it does:** Defines conditions that trigger alerts

**Alert Severity Levels:**
- **Critical** (40+ rules): Immediate action required
- **Warning** (30+ rules): Should be addressed soon
- **Info** (20+ rules): Informational tracking

**Example Alerts:**
- NodeDown - Node offline for 2 minutes
- LowPeerCount - Less than 2 connected peers
- HighCPUUsage - CPU > 80%
- LowBlockProductionRate - No blocks in 10 minutes
- HighAPIErrorRate - Error rate > 10%
- LargeMempool - Transaction pool > 10k

---

### 5. AlertManager (`monitoring/alertmanager.yml`)

**What it does:** Routes alerts to appropriate channels

**Routing Rules:**
- **Critical** → PagerDuty + Slack + Email
- **Network** → Network team Slack
- **System** → System alerts Slack
- **Blockchain** → Blockchain alerts Slack
- **API** → API alerts Slack
- **Info** → Daily digest

**Notification Channels:**
- Slack (5 different channels)
- PagerDuty (on-call rotation)
- Email (SMTP-based)

---

### 6. Grafana Dashboards

**Three Production Dashboards:**

#### 1. Blockchain Overview
- Block production rate
- Current height
- Transaction throughput (TPS)
- Peer count
- Mining time percentiles
- Transaction pool size
- Network hashrate

**Access:** http://localhost:3000/d/xai-overview

#### 2. Node Health
- CPU usage (gauge and trends)
- Memory usage (gauge and trends)
- Disk usage (gauge and trends)
- Process uptime
- Thread count
- Memory in bytes

**Access:** http://localhost:3000/d/xai-node-health

#### 3. Transaction Metrics
- Transaction rate by status
- Mempool size
- Processing time percentiles
- Fee distribution
- Status breakdown (pie chart)
- Transaction count trends
- Value distribution

**Access:** http://localhost:3000/d/xai-transactions

---

## Documentation Files

### 1. MONITORING_GUIDE.md (900+ lines)
**Comprehensive operations manual**

Contents:
- Architecture overview
- Component descriptions
- Deployment instructions
- Configuration guide
- Dashboard documentation
- Alerting setup
- Logging configuration
- Troubleshooting guide
- Best practices
- Maintenance procedures
- Appendix with PromQL examples

### 2. MONITORING_SETUP_CHECKLIST.md (600+ lines)
**Step-by-step deployment checklist**

12 Phases:
1. Pre-deployment verification
2. Core infrastructure setup
3. Metrics module integration
4. Docker deployment
5. Configuration verification
6. Metrics data collection
7. Logging configuration
8. Alert configuration
9. Production hardening
10. Documentation & runbooks
11. Testing & validation
12. Performance optimization

### 3. METRICS_INTEGRATION.md (500+ lines)
**Developer integration guide**

Covers:
- Quick integration (3 steps)
- Node initialization examples
- Recording metrics for each category
- API integration patterns
- Complete working examples
- Best practices
- Troubleshooting

### 4. monitoring/README.md (300+ lines)
**Quick reference**

Includes:
- Quick start commands
- File structure
- Component descriptions
- Environment variables
- Usage examples
- Troubleshooting
- Maintenance tasks

### 5. MONITORING_INFRASTRUCTURE_SUMMARY.md
**Complete overview**

Provides:
- File listing with descriptions
- Component statistics
- Key features
- Quick start instructions
- Integration points
- Support resources

---

## Deployment Instructions

### Quick Start (5 minutes)

1. **Start monitoring stack:**
   ```bash
   cd docker/monitoring
   docker-compose up -d
   ```

2. **Verify services are running:**
   ```bash
   docker-compose ps
   ```

3. **Access services:**
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000 (admin/admin)
   - AlertManager: http://localhost:9093

### Full Deployment (30 minutes)

1. Follow [MONITORING_SETUP_CHECKLIST.md](../MONITORING_SETUP_CHECKLIST.md)
2. Configure environment variables in `.env`
3. Integrate metrics into node code
4. Configure alerts and notifications
5. Verify data collection
6. Test dashboards

### Production Deployment (1-2 hours)

1. Complete setup checklist
2. Configure backups
3. Set up monitoring for monitors
4. Create runbooks
5. Train team
6. Implement monitoring for production

---

## Common Tasks

### View Metrics
```bash
# In Prometheus UI
http://localhost:9090/

# Via API
curl 'http://localhost:9090/api/v1/query?query=xai_block_height'
```

### Test Alerts
```bash
# Trigger test alert
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

### Check Logs
```bash
# View structured logs
tail -f /var/log/xai/blockchain.json | jq .

# Or in Loki UI
# http://localhost:3000/explore
```

### Modify Alerts
```bash
# Edit alert rules
vim monitoring/prometheus_alerts.yml

# Restart Prometheus
docker-compose restart prometheus
```

### Update Dashboards
```bash
# Edit dashboard JSON
vim docker/monitoring/grafana/dashboards/blockchain_overview.json

# Reimport or use API
```

---

## Architecture Diagram

```
XAI Blockchain Nodes
        │
        │ HTTP /metrics
        ▼
Prometheus (9090)
    │
    ├─ Alert Rules Evaluation
    │
    ├─ Metrics Storage
    │
    └─ Query API
        │
        ├─→ Grafana (3000)
        │   └─→ Dashboards
        │       • blockchain_overview
        │       • node_health
        │       • transaction_metrics
        │
        ├─→ AlertManager (9093)
        │   └─→ Notification Channels
        │       • Slack
        │       • PagerDuty
        │       • Email
        │
        └─→ Monitoring Users
            └─→ PromQL Queries

Logging Pipeline
        │
        ├─ Structured JSON Logs
        │
        ├─→ Loki (3100) [Optional]
        │   └─→ Promtail (9080)
        │       └─→ Log Search
        │
        └─→ Log Files
            ├─ blockchain.json
            ├─ api.json
            ├─ network.json
            └─ mining.json
```

---

## Performance Metrics

### System Requirements
- **CPU:** 2+ cores
- **Memory:** 4+ GB
- **Disk:** 20+ GB (for 30-day retention)
- **Network:** 10+ Mbps

### Expected Performance
- **Prometheus Query:** < 500ms
- **Grafana Dashboard:** < 2 seconds load
- **Alert Evaluation:** 15s interval
- **Metrics Overhead:** < 2% CPU, < 100MB memory

---

## Maintenance Schedule

| Frequency | Task | Details |
|-----------|------|---------|
| Daily | Review alerts | Check dashboard |
| Weekly | Backup data | Prometheus snapshots |
| Monthly | Adjust thresholds | Based on trends |
| Quarterly | Update stack | Security patches |
| Annually | Capacity planning | Growth analysis |

---

## Support & Resources

### Internal Documentation
- [MONITORING_GUIDE.md](../MONITORING_GUIDE.md) - Complete guide
- [METRICS_INTEGRATION.md](./METRICS_INTEGRATION.md) - Integration guide
- [monitoring/README.md](../monitoring/README.md) - Quick reference
- [MONITORING_SETUP_CHECKLIST.md](../MONITORING_SETUP_CHECKLIST.md) - Setup checklist

### External Resources
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [AlertManager Documentation](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [Loki Documentation](https://grafana.com/docs/loki/)

### Getting Help
1. Check troubleshooting section in [MONITORING_GUIDE.md](../MONITORING_GUIDE.md)
2. Review [monitoring/README.md](../monitoring/README.md)
3. Check Docker logs: `docker logs <container>`
4. Verify configuration in component UIs

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-01-15 | Initial release with complete monitoring infrastructure |

---

## Next Steps

1. **Deploy Monitoring:**
   - Follow [MONITORING_SETUP_CHECKLIST.md](../MONITORING_SETUP_CHECKLIST.md)
   - Start with [Quick Start](#quick-start-5-minutes)

2. **Integrate Metrics:**
   - Follow [METRICS_INTEGRATION.md](./METRICS_INTEGRATION.md)
   - Update node code to record metrics

3. **Configure Alerts:**
   - Review [monitoring/prometheus_alerts.yml](../monitoring/prometheus_alerts.yml)
   - Configure notification channels
   - Test alert routing

4. **Monitor Production:**
   - Use [MONITORING_GUIDE.md](../MONITORING_GUIDE.md) as reference
   - Follow maintenance schedule
   - Optimize based on actual metrics

---

**Last Updated:** 2024-01-15
**Status:** Production Ready
**Version:** 1.0.0
**Maintainer:** XAI DevOps Team

For questions or issues, refer to the documentation above or check the troubleshooting section in [MONITORING_GUIDE.md](../MONITORING_GUIDE.md).
