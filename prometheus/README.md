# XAI Blockchain - Prometheus Monitoring Setup

Complete monitoring infrastructure for the XAI blockchain using Prometheus and Grafana.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Metrics Reference](#metrics-reference)
- [Dashboards](#dashboards)
- [Alerting](#alerting)
- [Troubleshooting](#troubleshooting)

## Overview

This monitoring setup provides comprehensive observability for the XAI blockchain, including:

- **Block production metrics** - Block height, mining time, difficulty
- **Transaction metrics** - Throughput, mempool size, fees
- **Network health** - Peer count, bandwidth, latency
- **API performance** - Request rates, response times, error rates
- **System resources** - CPU, memory, disk usage
- **AI service metrics** - Task execution, success rates

## Architecture

```
┌─────────────────┐
│  XAI Node      │
│  (Port 8000)    │──┐
└─────────────────┘  │
                     │    ┌──────────────┐      ┌──────────────┐
┌─────────────────┐  │    │  Prometheus  │      │   Grafana    │
│  Block Explorer │  ├───▶│  (Port 9090) │─────▶│  (Port 3000) │
│  (Port 5001)    │  │    └──────────────┘      └──────────────┘
└─────────────────┘  │            │
                     │            │
┌─────────────────┐  │            ▼
│  AI Services    │──┘    ┌──────────────┐
│  (Port 8001)    │       │ Alertmanager │
└─────────────────┘       │ (Port 9093)  │
                          └──────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
# Install Python monitoring packages
pip install prometheus-client grafana-api python-json-logger

# Install Prometheus (Windows)
# Download from https://prometheus.io/download/
# Extract to C:\prometheus

# Install Grafana (Windows)
# Download from https://grafana.com/grafana/download
# Extract to C:\grafana
```

### 2. Start Metrics Collection

```python
# In your XAI node startup code
from src.xai.core.prometheus_metrics import initialize_metrics

# Initialize metrics server
metrics = initialize_metrics(
    port=8000,
    version="1.0.0",
    network="mainnet",
    node_id="node-001"
)

# Metrics are now exposed at http://localhost:8000/metrics
```

### 3. Start Prometheus

```bash
# Windows
cd C:\prometheus
.\prometheus.exe --config.file=C:\Users\decri\GitClones\Crypto\prometheus\prometheus.yml

# Linux/Mac
prometheus --config.file=/path/to/xai/prometheus/prometheus.yml
```

Access Prometheus at: http://localhost:9090

### 4. Start Grafana

```bash
# Windows
cd C:\grafana\bin
.\grafana-server.exe

# Linux/Mac
grafana-server
```

Access Grafana at: http://localhost:12030
- Default credentials: admin/admin

### 5. Import Dashboards

1. Open Grafana (http://localhost:12030)
2. Go to **Dashboards** → **Import**
3. Upload JSON files from `dashboards/grafana/`:
   - `xai_blockchain_overview.json`
   - `xai_network_health.json`
   - `xai_api_performance.json`

## Installation

### Installing Prometheus

#### Windows

```powershell
# Download Prometheus
$version = "2.47.0"
Invoke-WebRequest -Uri $url -OutFile "prometheus.zip"
Expand-Archive -Path "prometheus.zip" -DestinationPath "C:\"
Rename-Item "C:\prometheus-$version.windows-amd64" "C:\prometheus"

# Create Windows service (optional)
New-Service -Name "Prometheus" -BinaryPathName "C:\prometheus\prometheus.exe --config.file=C:\Users\decri\GitClones\Crypto\prometheus\prometheus.yml" -DisplayName "Prometheus Monitoring" -StartupType Automatic
```

#### Linux

```bash
# Download and install
tar xvfz prometheus-*.tar.gz
sudo mv prometheus-2.47.0.linux-amd64 /opt/prometheus

# Create systemd service
sudo cat > /etc/systemd/system/prometheus.service <<EOF
[Unit]
Description=Prometheus
After=network.target

[Service]
Type=simple
User=prometheus
ExecStart=/opt/prometheus/prometheus --config.file=/path/to/xai/prometheus/prometheus.yml
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable prometheus
sudo systemctl start prometheus
```

### Installing Grafana

#### Windows

```powershell
# Download Grafana
$version = "10.2.0"
$url = "https://dl.grafana.com/oss/release/grafana-$version.windows-amd64.zip"
Invoke-WebRequest -Uri $url -OutFile "grafana.zip"
Expand-Archive -Path "grafana.zip" -DestinationPath "C:\"
```

#### Linux

```bash
# Ubuntu/Debian
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
sudo apt-get update
sudo apt-get install grafana

sudo systemctl enable grafana-server
sudo systemctl start grafana-server
```

## Configuration

### Prometheus Configuration

The main configuration file is `prometheus/prometheus.yml`. Key sections:

#### Scrape Intervals

```yaml
global:
  scrape_interval: 15s      # How often to scrape targets
  evaluation_interval: 15s  # How often to evaluate rules
```

#### Adding New Targets

```yaml
scrape_configs:
  - job_name: 'my-new-service'
    static_configs:
      - targets: ['localhost:8002']
        labels:
          service: 'custom_service'
```

#### Multi-Node Setup

```yaml
scrape_configs:
  - job_name: 'xai-cluster'
    static_configs:
      - targets:
        - 'node1.example.com:8000'
        - 'node2.example.com:8000'
        - 'node3.example.com:8000'
```

### Metrics Integration

#### Basic Integration

```python
from src.xai.core.prometheus_metrics import get_metrics

metrics = get_metrics()

# Record a new block
metrics.record_block(
    height=12345,
    size=50000,
    difficulty=1000000,
    mining_time=45.5
)

# Record a transaction
metrics.record_transaction(
    status='confirmed',
    value=100.0,
    fee=0.001,
    processing_time=0.25
)

# Update peer count
metrics.update_peer_count(8)
```

#### Advanced Integration

```python
import time
from src.xai.core.prometheus_metrics import get_metrics

metrics = get_metrics()

# API endpoint timing
@app.route('/api/blocks')
def get_blocks():
    start_time = time.time()
    try:
        # Your API logic
        result = fetch_blocks()

        # Record success
        duration = time.time() - start_time
        metrics.record_api_request('/api/blocks', 'GET', 200, duration)
        return result
    except Exception as e:
        # Record failure
        duration = time.time() - start_time
        metrics.record_api_request('/api/blocks', 'GET', 500, duration)
        raise

# Mining operation
def mine_block():
    start_time = time.time()
    attempts = 0

    while True:
        attempts += 1
        metrics.record_mining_attempt(success=False)

        if check_proof():
            mining_time = time.time() - start_time
            metrics.record_mining_attempt(success=True)
            metrics.record_block(
                height=current_height,
                size=block_size,
                difficulty=current_difficulty,
                mining_time=mining_time
            )
            break
```

## Metrics Reference

### Block Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `xai_blocks_total` | Counter | Total blocks mined |
| `xai_block_height` | Gauge | Current blockchain height |
| `xai_block_size_bytes` | Histogram | Block size distribution |
| `xai_block_mining_time_seconds` | Histogram | Mining time distribution |
| `xai_block_difficulty` | Gauge | Current mining difficulty |
| `xai_block_production_rate_per_minute` | Gauge | Blocks produced per minute |

### Transaction Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `xai_transactions_total{status}` | Counter | Total transactions by status |
| `xai_transaction_pool_size` | Gauge | Mempool size |
| `xai_transaction_throughput_per_second` | Gauge | TX/s throughput |
| `xai_transaction_value_xai` | Histogram | Transaction value distribution |
| `xai_transaction_fee_xai` | Histogram | Transaction fee distribution |

### Network Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `xai_peers_connected` | Gauge | Connected peer count |
| `xai_network_bandwidth_sent_bytes_total` | Counter | Total bytes sent |
| `xai_network_bandwidth_received_bytes_total` | Counter | Total bytes received |
| `xai_network_latency_seconds` | Histogram | Network latency distribution |
| `xai_network_messages_total{message_type}` | Counter | Network messages by type |

### API Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `xai_api_requests_total{endpoint,method,status}` | Counter | API requests |
| `xai_api_request_duration_seconds{endpoint,method}` | Histogram | API response times |
| `xai_api_active_connections` | Gauge | Active API connections |

### System Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `xai_system_cpu_usage_percent` | Gauge | CPU usage % |
| `xai_system_memory_usage_bytes` | Gauge | Memory usage bytes |
| `xai_system_memory_percent` | Gauge | Memory usage % |
| `xai_system_disk_usage_bytes` | Gauge | Disk usage bytes |
| `xai_system_disk_percent` | Gauge | Disk usage % |
| `xai_process_uptime_seconds` | Gauge | Process uptime |

## Dashboards

### XAI Blockchain Overview

**File:** `dashboards/grafana/xai_blockchain_overview.json`

Key panels:
- Blockchain height over time
- Block production rate
- Transaction throughput
- Network peer count
- System resource usage

### Network Health

**File:** `dashboards/grafana/xai_network_health.json`

Key panels:
- Peer connections
- Network latency percentiles
- Bandwidth usage
- Message types distribution

### API Performance

**File:** `dashboards/grafana/xai_api_performance.json`

Key panels:
- Request rate by endpoint
- Response time percentiles (p50, p95, p99)
- Success/error rates
- Top slowest endpoints

## Alerting

### Alert Configuration

Alerts are defined in `prometheus/alerts/blockchain_alerts.yml`.

### Key Alerts

#### Critical Alerts

- **BlockProductionStopped** - No blocks for 5 minutes
- **NoPeersConnected** - Node is isolated
- **CriticalDiskUsage** - Disk >95% full

#### Warning Alerts

- **LowBlockProductionRate** - Below expected rate
- **LowPeerCount** - <3 peers connected
- **HighMemoryUsage** - Memory >90%
- **HighAPIErrorRate** - API errors >5%

### Setting Up Alertmanager

1. **Install Alertmanager**

```bash
# Download and extract
tar xvfz alertmanager-*.tar.gz
sudo mv alertmanager-0.26.0.linux-amd64 /opt/alertmanager
```

2. **Configure Alertmanager**

Create `alertmanager.yml`:

```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'email'

receivers:
  - name: 'email'
    email_configs:
      - to: 'alerts@yourblockchain.network'
        from: 'prometheus@yourblockchain.network'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'your-username'
        auth_password: 'your-password'
```

3. **Enable in Prometheus**

Update `prometheus.yml`:

```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['localhost:9093']
```

## Troubleshooting

### Metrics Not Appearing

**Problem:** Prometheus shows no metrics from XAI node

**Solutions:**
1. Check metrics endpoint is accessible:
   ```bash
   curl http://localhost:8000/metrics
   ```
2. Verify Prometheus target is up:
   - Go to http://localhost:9090/targets
   - Check if `xai-node` target is UP
3. Check firewall rules allow port 8000

### High Memory Usage

**Problem:** Prometheus consuming too much memory

**Solutions:**
1. Reduce retention time in `prometheus.yml`:
   ```yaml
   storage:
     tsdb:
       retention.time: 15d  # Default is 15d
   ```
2. Reduce scrape frequency for less critical targets
3. Enable remote storage for long-term metrics

### Dashboard Not Loading

**Problem:** Grafana dashboard shows "No data"

**Solutions:**
1. Verify Prometheus data source is configured:
   - Go to Configuration → Data Sources
   - Add Prometheus: http://localhost:9090
2. Check time range in dashboard
3. Verify metrics are being collected in Prometheus

### Port Conflicts

**Problem:** "Port already in use" error

**Solutions:**
1. Change metrics port in your code:
   ```python
   metrics = initialize_metrics(port=8001)  # Use different port
   ```
2. Update `prometheus.yml` to match new port
3. Check for other services using the port:
   ```bash
   # Windows
   netstat -ano | findstr :8000

   # Linux
   lsof -i :8000
   ```

## Best Practices

### 1. Metric Naming

- Use consistent prefixes (`xai_`)
- Follow Prometheus naming conventions
- Include units in names (`_seconds`, `_bytes`, `_total`)

### 2. Label Usage

- Keep cardinality low (avoid user IDs, timestamps as labels)
- Use meaningful label names
- Be consistent across metrics

### 3. Performance

- Use recording rules for frequently queried metrics
- Set appropriate scrape intervals
- Monitor Prometheus resource usage

### 4. Security

- Use authentication for Prometheus/Grafana in production
- Restrict metrics endpoint access
- Use HTTPS for external access

## Example Queries

### Block Production

```promql
# Average blocks per minute (last hour)
rate(xai_blocks_total[1h]) * 60

# Time since last block
time() - timestamp(xai_block_height)

# Average block size (last 24h)
avg_over_time(xai_block_size_bytes[24h])
```

### Network Health

```promql
# Peer count change
delta(xai_peers_connected[1h])

# Network bandwidth (last 5 minutes)
rate(xai_network_bandwidth_sent_bytes_total[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(xai_network_latency_seconds_bucket[5m]))
```

### Transaction Throughput

```promql
# Transactions per second
rate(xai_transactions_total[1m])

# Transaction success rate
rate(xai_transactions_total{status="confirmed"}[5m]) /
rate(xai_transactions_total[5m])

# Average transaction fee
rate(xai_transaction_fee_xai_sum[5m]) /
rate(xai_transaction_fee_xai_count[5m])
```

## Advanced Features

### Remote Write

For long-term storage, configure remote write to services like:
- Thanos
- Cortex
- Grafana Cloud
- AWS Timestream

### Federation

For multi-datacenter setups:

```yaml
scrape_configs:
  - job_name: 'federate'
    scrape_interval: 15s
    honor_labels: true
    metrics_path: '/federate'
    params:
      'match[]':
        - '{job="xai-node"}'
    static_configs:
      - targets:
        - 'dc1-prometheus:9090'
        - 'dc2-prometheus:9090'
```

## Support

For issues or questions:
- Documentation: https://docs.yourblockchain.network
- Community: https://discord.gg/yourblockchain

## License

MIT License - See LICENSE file for details
