# XAI Blockchain - Monitoring & Logging Quick Reference

## Quick Start

```python
# Import
from structured_logger import StructuredLogger, LogContext
from monitoring import MetricsCollector

# Initialize
logger = StructuredLogger('XAI_Node')
metrics = MetricsCollector()

# Log events
logger.info("Message", key="value")

# Record metrics
metrics.record_block_mined(block_index=1, mining_time=5.2)
```

## Common Logging Patterns

### Block Mining
```python
logger.block_mined(
    block_index=100,
    block_hash='0x123abc...',
    miner='XAI1234...',
    tx_count=50,
    reward=50.0,
    mining_time=5.2
)
```

### Transaction
```python
logger.transaction_submitted(
    txid='0xabc...',
    sender='XAI111...',
    recipient='XAI222...',
    amount=100.0,
    fee=0.01
)
```

### With Correlation ID
```python
with LogContext() as ctx:
    logger.info("Request started")
    # All logs share correlation_id
    logger.info("Request completed")
```

### Time Operations
```python
with PerformanceTimer(logger, 'operation_name'):
    # Code to time
    pass
```

## Common Metrics

### Record Block
```python
metrics.record_block_mined(block_index=1, mining_time=5.2)
```

### Record Transaction
```python
metrics.record_transaction_processed(processing_time=0.05)
```

### Record Peer Connection
```python
metrics.record_peer_connected(peer_count=5)
```

### Record API Request
```python
metrics.record_api_request('/blocks', duration=0.05)
```

## Monitoring Endpoints

### Prometheus Metrics
```python
@app.route('/metrics')
def metrics():
    return metrics.export_prometheus(), 200, {'Content-Type': 'text/plain'}
```

### Health Check
```python
@app.route('/health')
def health():
    return jsonify(metrics.get_health_status())
```

### Stats
```python
@app.route('/monitoring/stats')
def stats():
    return jsonify(metrics.get_stats())
```

## Alert Configuration

```python
from monitoring import AlertLevel

# Add alert rule
metrics.add_alert_rule(
    'high_cpu',
    lambda: metrics.get_metric('xai_node_cpu_usage_percent').value > 80,
    'CPU usage above 80%',
    AlertLevel.WARNING
)
```

## Log Levels

```python
logger.debug("Detailed debug info")      # DEBUG
logger.info("General information")       # INFO
logger.warn("Warning message")           # WARN
logger.error("Error occurred")           # ERROR
logger.critical("Critical failure")      # CRITICAL
```

## Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `xai_blocks_mined_total` | Counter | Total blocks mined |
| `xai_chain_height` | Gauge | Current blockchain height |
| `xai_pending_transactions` | Gauge | Pending transactions |
| `xai_peers_connected` | Gauge | Connected peers |
| `xai_node_cpu_usage_percent` | Gauge | CPU usage |
| `xai_node_memory_usage_percent` | Gauge | Memory usage |

## Prometheus Queries

```promql
# Block mining rate
rate(xai_blocks_mined_total[5m])

# Average block time
rate(xai_block_mining_duration_seconds_sum[5m]) /
rate(xai_block_mining_duration_seconds_count[5m])

# Transaction throughput (per minute)
rate(xai_transactions_processed_total[1m]) * 60

# CPU usage
xai_node_cpu_usage_percent

# Memory usage
xai_node_memory_usage_percent
```

## Health Status Values

- `healthy` - All systems normal
- `degraded` - System operational but with issues
- `unhealthy` - Critical issues detected

## Files & Locations

### Source Files
- `structured_logger.py` - Structured logging system
- `monitoring.py` - Metrics & monitoring system
- `monitoring_integration_example.py` - Integration examples

### Log Files
- `logs/xai_blockchain.json.log` - JSON formatted logs
- `logs/xai_blockchain.log` - Human-readable logs

### Documentation
- `MONITORING_AND_LOGGING_GUIDE.md` - Complete guide
- `IMPLEMENTATION_SUMMARY.md` - Implementation details
- `QUICK_REFERENCE.md` - This file

## Testing

```bash
# Test structured logger
python structured_logger.py

# Test monitoring system
python monitoring.py

# Test integration
python monitoring_integration_example.py
```

## Common Troubleshooting

### No logs appearing
Check log directory permissions:
```python
log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)
```

### Metrics not updating
Ensure monitoring is initialized with blockchain:
```python
metrics = MetricsCollector(blockchain=self.blockchain)
```

### High log volume
Increase log level:
```python
logger = StructuredLogger('XAI_Node', log_level='WARN')
```

## Privacy & Security

- ✅ Addresses truncated: `XAI123...def`
- ✅ Sensitive data redacted: `REDACTED`
- ✅ No IP addresses logged
- ✅ No personal data included

## Performance

- Memory: ~7MB overhead
- CPU: <1% for monitoring
- Logs: ~10MB per day
- Rotation: 30 days, 100MB max

## Support

1. Check `MONITORING_AND_LOGGING_GUIDE.md` for detailed docs
2. Review `monitoring_integration_example.py` for examples
3. Test with provided example scripts
