# XAI Blockchain Monitoring - Quick Start

## 1. Install Dependencies (1 minute)

```bash
cd C:\Users\decri\GitClones\Crypto
pip install -r src\xai\requirements.txt
```

## 2. Verify Setup (30 seconds)

```bash
python scripts\tools\verify_monitoring.py
```

## 3. Test Metrics (Optional)

```bash
# Run example node with metrics
python docs\examples\monitoring_integration_example.py

# In another terminal, check metrics
curl http://localhost:8000/metrics
```

## 4. Start Monitoring Stack (2 minutes)

### Option A: Docker Compose (Recommended)

```powershell
cd prometheus
docker compose up -d
```

Access:
- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:12030 (admin/admin)
- **Alertmanager:** http://localhost:9093

### Option B: Manual Installation

See full instructions in `prometheus/README.md`

## 5. Import Dashboards (2 minutes)

1. Open Grafana: http://localhost:12030
2. Login: admin/admin
3. Navigate to **Dashboards** → **Import**
4. Upload each file from `dashboards/grafana/`:
   - `xai_blockchain_overview.json`
   - `xai_network_health.json`
   - `xai_api_performance.json`

## 6. Integrate into Your Node

```python
from src.xai.core.prometheus_metrics import initialize_metrics, get_metrics

# At node startup
metrics = initialize_metrics(
    port=8000,
    version="1.0.0",
    network="mainnet",
    node_id="node-001"
)

# In your mining function
metrics.record_block(
    height=block_number,
    size=block_size,
    difficulty=current_difficulty,
    mining_time=time_taken
)

# In your transaction handler
metrics.record_transaction(
    status='confirmed',
    value=tx_amount,
    fee=tx_fee,
    processing_time=process_time
)

# Update periodically (every 5-10 seconds)
metrics.update_system_metrics()
metrics.update_peer_count(len(peers))
metrics.update_mempool_size(len(mempool))
```

## Key Metrics to Watch

### Critical
- `xai_block_height` - Current blockchain height
- `xai_peers_connected` - Number of peers (should be >0)
- `xai_chain_sync_status` - Sync status (1 = synced)

### Performance
- `xai_block_production_rate_per_minute` - Blocks/min
- `xai_transaction_throughput_per_second` - TX/s
- `xai_system_cpu_usage_percent` - CPU usage
- `xai_system_memory_percent` - Memory usage

### Network
- `xai_network_latency_seconds` - Peer latency
- `xai_network_bandwidth_*_bytes_total` - Network traffic

## Common Commands

### Docker
```bash
# Start stack
docker compose up -d

# View logs
docker compose logs -f

# Stop stack
docker compose down

# Restart
docker compose restart
```

### Check Status
```bash
# Verify setup
python scripts\tools\verify_monitoring.py

# Check metrics endpoint
curl http://localhost:8000/metrics

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets
```

## Troubleshooting

### Port Already in Use
```python
# Use different port in code
metrics = initialize_metrics(port=8001)
```

### Metrics Not Showing
1. Check endpoint: `curl http://localhost:8000/metrics`
2. Check Prometheus targets: http://localhost:9090/targets
3. Verify firewall allows port 8000

### High Memory Usage
Edit `prometheus/prometheus.yml`:
```yaml
storage:
  tsdb:
    retention.time: 7d  # Reduce from 30d
```

## Next Steps

1. Review full documentation: `prometheus/README.md`
2. Customize alert rules: `prometheus/alerts/blockchain_alerts.yml`
3. Set up notifications in Alertmanager
4. Create custom dashboards in Grafana

## Support

- Full README: `prometheus/README.md`
- Example code: `docs/examples/monitoring_integration_example.py`
- Verification: `python scripts/tools/verify_monitoring.py`
