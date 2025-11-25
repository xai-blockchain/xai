# XAI Blockchain - Monitoring Setup Checklist

Complete checklist for deploying and configuring the monitoring infrastructure.

## Pre-Deployment Checklist

### Prerequisites
- [ ] Docker and Docker Compose installed (v20.10+)
- [ ] At least 4GB RAM available for monitoring stack
- [ ] 10GB free disk space for Prometheus data retention
- [ ] Network connectivity between services
- [ ] Slack workspace for alerts (optional but recommended)
- [ ] PagerDuty account for on-call (optional)

### Repository Structure
- [ ] `src/xai/core/metrics.py` - Prometheus metrics module
- [ ] `src/xai/core/logging_config.py` - Structured logging
- [ ] `monitoring/` directory exists
- [ ] `docker/monitoring/` directory exists

---

## Phase 1: Core Infrastructure

### Prometheus Setup
- [ ] Copy/verify `docker/monitoring/prometheus.yml`
- [ ] Create `monitoring/prometheus_alerts.yml`
- [ ] Verify scrape configs point to correct targets
- [ ] Set retention period (default: 30 days)
- [ ] Test Prometheus configuration:
  ```bash
  docker run --rm -v $(pwd):/etc/prometheus prom/prometheus:latest --config.file=/etc/prometheus/prometheus.yml --dry-run
  ```

### AlertManager Setup
- [ ] Create `monitoring/alertmanager.yml`
- [ ] Create `monitoring/alert_templates.tmpl`
- [ ] Configure notification channels:
  - [ ] Slack webhook URL
  - [ ] PagerDuty service key (if using)
  - [ ] Email SMTP settings (if using)
- [ ] Test AlertManager configuration:
  ```bash
  docker run --rm -v $(pwd)/monitoring:/etc/alertmanager prom/alertmanager:latest --config.file=/etc/alertmanager/alertmanager.yml --dry-run
  ```

### Grafana Setup
- [ ] Create Grafana datasource config: `docker/monitoring/grafana/datasources/prometheus.yml`
- [ ] Create three dashboards:
  - [ ] `blockchain_overview.json`
  - [ ] `node_health.json`
  - [ ] `transaction_metrics.json`
- [ ] Create Grafana config: `docker/monitoring/grafana/grafana.ini`
- [ ] Set admin password in docker-compose.yml

---

## Phase 2: Metrics Module Integration

### Metrics Module
- [ ] Verify `src/xai/core/metrics.py` exists and is complete
- [ ] Check Python dependencies:
  ```bash
  pip list | grep -E "prometheus|psutil|pythonjsonlogger"
  ```
- [ ] Test metrics module:
  ```python
  from xai.core.metrics import initialize_metrics
  metrics = initialize_metrics()
  metrics.record_block(height=1, size=1000, difficulty=100, mining_time=10)
  print(metrics.export_prometheus())
  ```

### Logging Configuration
- [ ] Verify `src/xai/core/logging_config.py` exists
- [ ] Test logging setup:
  ```python
  from xai.core.logging_config import setup_logging
  logger = setup_logging(name="test", log_file="/tmp/test.json")
  logger.info("Test message", value=123)
  ```

### Node Integration
- [ ] Update node initialization to use metrics:
  ```python
  from xai.core.metrics import initialize_metrics
  self.metrics = initialize_metrics(...)
  ```
- [ ] Update block mining to record metrics:
  ```python
  self.metrics.record_block(height, size, difficulty, mining_time)
  ```
- [ ] Update transaction processing to record metrics:
  ```python
  self.metrics.record_transaction(status, value, fee, processing_time)
  ```
- [ ] Update API routes to record metrics:
  ```python
  self.metrics.record_api_request(endpoint, method, status, duration)
  ```
- [ ] Add metrics endpoint:
  ```python
  @app.route("/metrics", methods=["GET"])
  def prometheus_metrics():
      return self.metrics.export_prometheus()
  ```

---

## Phase 3: Docker Deployment

### Docker Compose
- [ ] Create `docker/monitoring/docker-compose.yml`
- [ ] Create environment file `.env` with:
  ```bash
  SLACK_WEBHOOK_URL=...
  PAGERDUTY_SERVICE_KEY=...
  ALERT_EMAIL_CRITICAL=...
  EMAIL_SMTP_HOST=...
  EMAIL_SMTP_PORT=...
  EMAIL_USERNAME=...
  EMAIL_PASSWORD=...
  ```
- [ ] Start monitoring stack:
  ```bash
  cd docker/monitoring
  docker-compose up -d
  ```
- [ ] Verify all services are running:
  ```bash
  docker-compose ps
  docker-compose logs --tail=50 prometheus
  ```

### Service Verification
- [ ] Prometheus accessible: http://localhost:9090
- [ ] Grafana accessible: http://localhost:3000
- [ ] AlertManager accessible: http://localhost:9093
- [ ] Node Exporter accessible: http://localhost:9100/metrics

### Network Configuration
- [ ] Verify docker network: `docker network ls | grep monitoring`
- [ ] Check network connectivity:
  ```bash
  docker exec xai-prometheus ping grafana
  docker exec xai-grafana ping prometheus
  docker exec xai-alertmanager ping prometheus
  ```

---

## Phase 4: Configuration Verification

### Prometheus Configuration
- [ ] Verify scrape configs in Prometheus UI:
  - Navigate to http://localhost:9090/targets
  - All targets should show "UP"
- [ ] Check alert rules:
  - Navigate to http://localhost:9090/alerts
  - Rules should be loaded

### AlertManager Configuration
- [ ] Verify routing configuration:
  ```bash
  docker exec xai-alertmanager amtool config routes
  ```
- [ ] Test alert notification (Slack):
  ```bash
  curl -XPOST http://localhost:9093/api/v1/alerts \
    -H 'Content-Type: application/json' \
    -d '{
      "alerts": [{
        "status": "firing",
        "labels": {"alertname": "TestAlert", "severity": "critical"},
        "annotations": {"summary": "Test"}
      }]
    }'
  ```
- [ ] Check Slack channel for notification

### Grafana Configuration
- [ ] Login to Grafana (http://localhost:3000)
  - Username: `admin`
  - Password: (from environment)
- [ ] Verify Prometheus datasource:
  - Configuration → Data Sources → Prometheus
  - Click "Test" button
- [ ] Verify dashboards are imported:
  - Should see 3 dashboards in Dashboards list
- [ ] Test each dashboard:
  - [ ] Blockchain Overview - shows block data
  - [ ] Node Health - shows system metrics
  - [ ] Transaction Metrics - shows tx data

---

## Phase 5: Metrics Data Collection

### Start Generating Metrics
- [ ] Start blockchain node:
  ```bash
  python -m xai.core.node --network testnet
  ```
- [ ] Node should expose metrics:
  ```bash
  curl http://localhost:9090/metrics
  ```

### Monitor Metric Collection
- [ ] Check Prometheus targets (should be UP):
  ```bash
  curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[]'
  ```
- [ ] Query sample metrics:
  ```bash
  curl 'http://localhost:9090/api/v1/query?query=xai_block_height'
  ```
- [ ] Watch metrics in Prometheus UI
- [ ] Verify data appears in Grafana dashboards

---

## Phase 6: Logging Configuration

### Structured Logging Setup
- [ ] Create log directory:
  ```bash
  mkdir -p /var/log/xai
  chmod 755 /var/log/xai
  ```
- [ ] Configure node to use structured logging:
  ```python
  from xai.core.logging_config import setup_blockchain_logging
  logger = setup_blockchain_logging(environment="production")
  ```
- [ ] Verify JSON logs are being written:
  ```bash
  tail -f /var/log/xai/blockchain.json | jq .
  ```

### Optional: Log Aggregation (Loki)
- [ ] Start Loki stack:
  ```bash
  docker-compose --profile logs up -d
  ```
- [ ] Verify Loki is running:
  ```bash
  curl http://localhost:3100/loki/api/v1/labels
  ```
- [ ] Add Loki datasource to Grafana
- [ ] Create log search dashboard

---

## Phase 7: Alert Configuration

### Alert Rules Review
- [ ] Review critical alerts:
  - [ ] NodeDown
  - [ ] NoPeersConnected
  - [ ] CriticalCPUUsage
  - [ ] CriticalMemoryUsage
- [ ] Review warning alerts
- [ ] Verify alert thresholds are appropriate
- [ ] Test alert firing manually

### Notification Configuration
- [ ] For Slack:
  - [ ] Webhook URL configured
  - [ ] Channel permissions verified
  - [ ] Notification format tested
- [ ] For PagerDuty:
  - [ ] Service key configured
  - [ ] Service integration verified
  - [ ] Escalation policy set
- [ ] For Email:
  - [ ] SMTP credentials verified
  - [ ] Test email sent successfully

### Alert Routing
- [ ] Critical alerts route to PagerDuty
- [ ] Warning alerts route to Slack
- [ ] Info alerts route to daily digest
- [ ] Inhibition rules working correctly

---

## Phase 8: Production Hardening

### Security
- [ ] Prometheus UI access restricted (firewall/reverse proxy)
- [ ] Grafana HTTPS enabled (reverse proxy)
- [ ] AlertManager protected from external access
- [ ] Credentials stored securely (not in code)
- [ ] Logs don't contain sensitive data

### Backup & Recovery
- [ ] Prometheus data backed up regularly:
  ```bash
  docker exec xai-prometheus tar czf /prometheus-backup.tar.gz /prometheus
  ```
- [ ] Grafana dashboards backed up:
  ```bash
  docker cp xai-grafana:/var/lib/grafana/dashboards ./backups/
  ```
- [ ] AlertManager config backed up
- [ ] Restore procedure tested

### Resource Limits
- [ ] Set container resource limits:
  ```yaml
  services:
    prometheus:
      deploy:
        resources:
          limits:
            cpus: '2'
            memory: 2G
  ```
- [ ] Monitor resource usage regularly
- [ ] Adjust retention/scrape intervals as needed

### Monitoring the Monitors
- [ ] Prometheus self-monitoring enabled
- [ ] AlertManager health checks configured
- [ ] Grafana health checks configured
- [ ] Alert on monitoring stack failures

---

## Phase 9: Documentation & Runbooks

### Documentation
- [ ] MONITORING_GUIDE.md reviewed and updated
- [ ] METRICS_INTEGRATION.md reviewed
- [ ] Architecture diagrams created
- [ ] Configuration documented

### Runbooks
- [ ] Create runbooks for each critical alert:
  - [ ] NodeDown - recovery procedure
  - [ ] NoPeersConnected - peer connectivity
  - [ ] High resource usage - troubleshooting
  - [ ] Chain sync issues - sync recovery
- [ ] Document escalation procedures
- [ ] Create incident response playbooks

### Team Training
- [ ] Team trained on monitoring stack
- [ ] Dashboard interpretation documented
- [ ] Alert response procedures documented
- [ ] On-call rotation configured

---

## Phase 10: Testing & Validation

### Functional Testing
- [ ] [ ] Test block mining metrics
  ```bash
  # Mine a block and verify metric recorded
  ```
- [ ] Test transaction metrics
  ```bash
  # Send transaction and verify metric recorded
  ```
- [ ] Test API metrics
  ```bash
  curl -X GET http://localhost:5000/blocks
  # Verify API metric recorded
  ```
- [ ] Test error metrics
  ```bash
  # Trigger error and verify recorded
  ```

### Alert Testing
- [ ] Test all critical alerts fire correctly
- [ ] Test all warning alerts fire correctly
- [ ] Test alert inhibition rules work
- [ ] Test notification delivery to all channels
- [ ] Test alert resolution notification

### Load Testing
- [ ] Simulate sustained block production
- [ ] Monitor system resource usage
- [ ] Check Prometheus scrape success rate
- [ ] Verify no data loss under load

### Disaster Recovery
- [ ] Test Prometheus data recovery from backup
- [ ] Test Grafana dashboard recovery
- [ ] Test AlertManager config recovery
- [ ] Document RTO/RPO targets

---

## Phase 11: Performance Optimization

### Prometheus Tuning
- [ ] Review query performance in Prometheus UI
- [ ] Create recording rules for complex queries:
  ```yaml
  - record: instance:requests:rate5m
    expr: rate(request_total[5m])
  ```
- [ ] Reduce cardinality of metrics if needed
- [ ] Enable WAL compression:
  ```yaml
  --storage.tsdb.wal-compression
  ```

### Grafana Tuning
- [ ] Optimize dashboard queries
- [ ] Set appropriate time ranges
- [ ] Enable query caching where appropriate
- [ ] Review dashboard load times

### AlertManager Tuning
- [ ] Adjust group_wait and group_interval
- [ ] Set appropriate repeat_interval
- [ ] Optimize inhibition rules
- [ ] Review notification delivery times

---

## Phase 12: Ongoing Maintenance

### Daily Tasks
- [ ] [ ] Review alert dashboard
- [ ] [ ] Check for any failed scrapes
- [ ] [ ] Monitor disk usage trends

### Weekly Tasks
- [ ] [ ] Review metrics trends
- [ ] [ ] Check alert rule effectiveness
- [ ] [ ] Verify backup completion

### Monthly Tasks
- [ ] [ ] Review and adjust alert thresholds
- [ ] [ ] Update runbooks based on incidents
- [ ] [ ] Capacity planning review
- [ ] [ ] Security audit

### Quarterly Tasks
- [ ] [ ] Update monitoring stack components
- [ ] [ ] Review and optimize dashboards
- [ ] [ ] Disaster recovery drill
- [ ] [ ] Performance tuning review

---

## Documentation Links

- [MONITORING_GUIDE.md](MONITORING_GUIDE.md) - Complete monitoring guide
- [monitoring/README.md](monitoring/README.md) - Monitoring directory overview
- [docs/METRICS_INTEGRATION.md](docs/METRICS_INTEGRATION.md) - Metrics integration guide
- [src/xai/core/metrics.py](src/xai/core/metrics.py) - Metrics implementation
- [src/xai/core/logging_config.py](src/xai/core/logging_config.py) - Logging configuration

---

## Completion Status

```
Phase 1: Core Infrastructure       [ ] Complete
Phase 2: Metrics Module             [ ] Complete
Phase 3: Docker Deployment          [ ] Complete
Phase 4: Configuration Verification [ ] Complete
Phase 5: Metrics Data Collection    [ ] Complete
Phase 6: Logging Configuration      [ ] Complete
Phase 7: Alert Configuration        [ ] Complete
Phase 8: Production Hardening       [ ] Complete
Phase 9: Documentation & Runbooks   [ ] Complete
Phase 10: Testing & Validation      [ ] Complete
Phase 11: Performance Optimization  [ ] Complete
Phase 12: Ongoing Maintenance       [ ] Complete

Overall Status: [ ] READY FOR PRODUCTION
```

---

**Last Updated:** 2024-01-15
**Status:** Production Ready
**Maintainer:** DevOps Team
