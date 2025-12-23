# XAI Blockchain - Grafana Metrics Integration

**Target Audience**: AI coding agents and developers

## Metrics Architecture

**Status**: ✅ Metrics fully implemented and wired
**Location**: `/xai/src/xai/core/prometheus_metrics.py`
**Namespace**: `xai_*`
**Dashboard**: XAI Compute Network Live Metrics (Grafana Cloud)

### Metrics Endpoint

XAI exposes Prometheus metrics on **1 port**:

**Port 8000** - All XAI blockchain metrics
- Block production metrics
- Transaction processing
- Network statistics
- AI task execution
- Mining operations
- System resources
- API request tracking

## Available Metrics

### Core Metrics (Always Available)
```python
# Blocks
xai_blocks_total
xai_block_height
xai_block_size_bytes
xai_block_mining_time_seconds
xai_block_difficulty
xai_block_production_rate_per_minute

# Transactions
xai_transactions_total{status}  # status: pending, confirmed, failed
xai_transaction_pool_size
xai_transaction_throughput_per_second
xai_transaction_value_xai
xai_transaction_fee_xai
xai_transaction_processing_time_seconds

# Network
xai_peers_connected
xai_network_bandwidth_sent_bytes_total
xai_network_bandwidth_received_bytes_total
xai_network_latency_seconds
xai_network_messages_total{message_type}

# AI-Specific (Unique to XAI)
xai_ai_tasks_total{provider,status}
xai_ai_task_duration_seconds{provider}

# API
xai_api_requests_total{endpoint,method,status}
xai_api_request_duration_seconds{endpoint,method}
xai_api_active_connections

# Mining
xai_mining_hashrate
xai_mining_attempts_total
xai_mining_success_total

# Supply/Economics
xai_total_supply_xai
xai_circulating_supply_xai
xai_wallet_balance_xai{address}

# System Resources
xai_system_cpu_usage_percent
xai_system_memory_usage_bytes
xai_system_disk_usage_bytes
xai_process_uptime_seconds

# Chain State
xai_chain_sync_status
xai_orphaned_blocks_total
xai_chain_reorgs_total
```

**Full list**: See `/blockchain-projects/METRICS_REFERENCE.md`

## Exposing Metrics

### Automatic Exposure
Metrics are **automatically exposed** when the XAI node starts. The node starts a Prometheus HTTP server on port 8000.

```bash
cd /home/decri/blockchain-projects/xai
source .venv/bin/activate
python -m xai.core.node
```

**Output shows**:
```
✓ XAI Prometheus metrics server started on http://localhost:8000/metrics
```

**Metrics immediately available at**: `http://localhost:8000/metrics`

### Implementation Details

The metrics server is started automatically in the node startup sequence:

```python
# In xai/src/xai/core/node.py (simplified)
from xai.core.node_metrics_server import start_metrics_server_if_enabled
from xai.core.prometheus_metrics import BlockchainMetrics

# Initialize metrics collector
metrics = BlockchainMetrics(port=8000)

# Start Prometheus HTTP server
start_metrics_server_if_enabled(port=8000, enabled=True)
```

### Verification

```bash
# Check metrics endpoint
curl -s http://localhost:8000/metrics | grep xai_

# Check specific metrics
curl -s http://localhost:8000/metrics | grep xai_block_height
curl -s http://localhost:8000/metrics | grep xai_transactions_total

# Verify Prometheus is scraping
curl -s http://localhost:9091/targets | grep xai
```

## Prometheus Configuration

**Location**: `/etc/prometheus/prometheus.yml`

```yaml
scrape_configs:
  # XAI Node
  - job_name: 'xai-node'
    static_configs:
      - targets: ['localhost:8000']
        labels:
          blockchain: xai
          component: node
```

**Remote Write**: Configured to send to Grafana Cloud (already set up)

## Grafana Dashboard

**Location**: Grafana Cloud - https://altrestackmon.grafana.net
**Dashboard Name**: "XAI Compute Network Live Metrics"
**Public Access**: Enabled (share via external link)

### Accessing the Dashboard

1. **Grafana Cloud** (recommended for investors/stakeholders):
   ```
   https://altrestackmon.grafana.net/dashboards
   Click: "XAI Compute Network Live Metrics"
   Share → Share externally → Copy external link
   ```

2. **Local Grafana** (development):
   ```
   http://localhost:12030
   Login: admin/admin
   ```

### Dashboard Panels

The dashboard shows:
- Block production rate and mining time
- Transaction throughput and pool size
- Network peer count and bandwidth
- AI task execution metrics (unique to XAI)
- Mining hashrate and success rate
- Token supply and distribution
- System resource utilization
- Chain sync status

### Specialized Dashboards

In addition to the primary overview panel, dedicated JSON dashboards ship with the repo:

- **XAI P2P Security** - `monitoring/dashboards/grafana/xai-p2p-security.json`
- **XAI Mempool Overview** - `monitoring/dashboards/grafana/xai-mempool-overview.json`
- **XAI Consensus Overview** *(new)* - `monitoring/dashboards/grafana/xai-consensus-overview.json`

These mirror the docker-ready copies under `docker/monitoring/grafana/dashboards/` so testnet stacks automatically provision real-time views for each subsystem.

## Implementation Architecture

### Metrics Class

Metrics are defined in `BlockchainMetrics` class:

```python
class BlockchainMetrics:
    def __init__(self, port: int = 8000, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        self.metrics_port = port

        # Define all metrics
        self.blocks_total = Counter("xai_blocks_total", ...)
        self.block_height = Gauge("xai_block_height", ...)
        # ... 40+ metrics
```

### Metrics Updates

Metrics are updated throughout the XAI codebase:

```python
# In blockchain.py
metrics.blocks_total.inc()
metrics.block_height.set(block.index)
metrics.block_size_bytes.observe(block.size)

# In transaction_pool.py
metrics.transaction_pool_size.set(len(self.pending))
metrics.transactions_total.labels(status="confirmed").inc()

# In mining.py
metrics.mining_attempts_total.inc()
metrics.mining_hashrate.set(current_hashrate)

# In ai/task_executor.py
metrics.ai_tasks_total.labels(provider="openai", status="success").inc()
```

### No Additional Wiring Required

All metrics are:
1. ✅ Already implemented in code
2. ✅ Automatically registered on node start
3. ✅ Automatically exposed on HTTP endpoint (port 8000)
4. ✅ Automatically scraped by Prometheus
5. ✅ Automatically pushed to Grafana Cloud
6. ✅ Automatically displayed on dashboard

**Just start the node - metrics flow automatically.**

## Troubleshooting

### Metrics Not Showing

```bash
# 1. Verify virtual environment is activated
source .venv/bin/activate

# 2. Verify node is running
ps aux | grep "python -m xai.core.node"

# 3. Check metrics endpoint responds
curl http://localhost:8000/metrics

# 4. Verify Prometheus is scraping
curl http://localhost:9091/targets | grep xai

# 5. Check Prometheus logs
sudo journalctl -u prometheus -n 50

# 6. Check node logs
tail -f ~/.xai/logs/xai.log
```

### Port 8000 Already in Use

```bash
# Find what's using port 8000
sudo lsof -i :8000

# Kill the process (if needed)
sudo kill -9 <PID>

# Or change XAI metrics port in config/default.yaml
```

### Empty Dashboard

**Cause**: Node not running
**Solution**: Start the XAI node

```bash
cd /home/decri/blockchain-projects/xai
source .venv/bin/activate
python -m xai.core.node
```

Metrics appear within 15 seconds of node start (Prometheus scrape interval).

## Adding New Metrics

To add custom metrics (AI agents can do this):

1. **Add metric to BlockchainMetrics class** in `prometheus_metrics.py`:
   ```python
   class BlockchainMetrics:
       def __init__(self, ...):
           # ... existing metrics
           self.my_new_metric = Counter(
               "xai_my_new_metric_total",
               "Description of metric",
               registry=self.registry
           )
   ```

2. **Update metric in relevant code**:
   ```python
   # In the appropriate module
   from xai.core.prometheus_metrics import get_blockchain_metrics

   metrics = get_blockchain_metrics()
   metrics.my_new_metric.inc()
   ```

3. **Add to dashboard**: Edit dashboard JSON, add new panel with query:
   ```promql
   xai_my_new_metric_total
   ```

No Prometheus config changes needed - new metrics auto-discovered.

## Virtual Environment Reminder

**CRITICAL**: Always activate the virtual environment before running:

```bash
cd /home/decri/blockchain-projects/xai
source .venv/bin/activate
```

Without activation, metrics server dependencies (`prometheus_client`) won't be available.

## Reference Documents

- **Metrics List**: `/home/decri/blockchain-projects/METRICS_REFERENCE.md`
- **Setup Status**: `/home/decri/blockchain-projects/SETUP_STATUS.md`
- **Prometheus Config**: `/etc/prometheus/prometheus.yml`
- **Dashboard JSON**: `/home/decri/blockchain-projects/dashboards/xai-compute-dashboard.json`
- **XAI Project Guide**: `/home/decri/blockchain-projects/xai/CLAUDE.md`
