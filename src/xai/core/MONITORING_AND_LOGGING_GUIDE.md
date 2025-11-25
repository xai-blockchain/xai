# XAI Blockchain - Monitoring and Logging Guide

## Overview

The XAI blockchain now includes comprehensive monitoring and structured logging systems for production-grade observability.

### Features

**Structured Logging (`structured_logger.py`):**
- JSON format for machine parsing
- Multiple log levels (DEBUG, INFO, WARN, ERROR, CRITICAL)
- Daily log rotation with 100MB size limit
- Correlation IDs for request tracking
- Privacy-preserving (addresses truncated, sensitive data sanitized)
- Performance timing utilities

**Monitoring & Metrics (`monitoring.py`):**
- Prometheus-compatible metrics export
- Real-time system metrics (CPU, memory, disk)
- Blockchain metrics (blocks, transactions, difficulty)
- Network metrics (peers, P2P messages)
- Performance metrics (mining time, validation time)
- Health check endpoint
- Alert system with configurable rules

---

## Quick Start

### 1. Basic Usage

```python
from structured_logger import StructuredLogger, LogContext
from monitoring import MetricsCollector

# Initialize
logger = StructuredLogger('XAI_Node', log_level='INFO')
metrics = MetricsCollector()

# Log events
logger.info("Node started", network="mainnet", port=5000)

# Track metrics
metrics.record_block_mined(block_index=1, mining_time=5.2)
metrics.record_transaction_processed(processing_time=0.05)
```

### 2. Integration with Blockchain

```python
class Blockchain:
    def __init__(self):
        self.logger = StructuredLogger('XAI_Blockchain')
        self.metrics = MetricsCollector(blockchain=self)

    def mine_pending_transactions(self, miner_address):
        with LogContext() as ctx:
            start_time = time.time()

            # Mine block
            block = Block(...)
            block.mine_block()

            mining_time = time.time() - start_time

            # Log event
            self.logger.block_mined(
                block_index=block.index,
                block_hash=block.hash,
                miner=miner_address,
                tx_count=len(block.transactions),
                reward=self.block_reward,
                mining_time=mining_time
            )

            # Record metrics
            self.metrics.record_block_mined(block.index, mining_time)

            return block
```

### 3. Add Monitoring Endpoints

```python
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/metrics', methods=['GET'])
def prometheus_metrics():
    """Prometheus metrics endpoint"""
    return metrics.export_prometheus(), 200, {'Content-Type': 'text/plain'}

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify(metrics.get_health_status())

@app.route('/monitoring/stats', methods=['GET'])
def monitoring_stats():
    """Detailed monitoring statistics"""
    return jsonify({
        'metrics': metrics.get_stats(),
        'logger': logger.get_stats()
    })

@app.route('/monitoring/alerts', methods=['GET'])
def get_alerts():
    """Get active monitoring alerts"""
    return jsonify({
        'alerts': metrics.get_active_alerts()
    })
```

---

## Structured Logging

### Log Levels

```python
logger.debug("Detailed debugging info", variable=value)
logger.info("General information", event="startup")
logger.warn("Warning message", issue="high_latency")
logger.error("Error occurred", error=str(e))
logger.critical("Critical system failure", component="database")
```

### Blockchain-Specific Logging

```python
# Block mining
logger.block_mined(
    block_index=100,
    block_hash='0x123abc...',
    miner='XAI1234567890abcdef',
    tx_count=50,
    reward=50.0,
    mining_time=5.2
)

# Transaction events
logger.transaction_submitted(
    txid='0xabcdef...',
    sender='XAI1111...',
    recipient='XAI2222...',
    amount=100.0,
    fee=0.01
)

logger.transaction_confirmed(
    txid='0xabcdef...',
    block_index=100
)

# Network events
logger.network_event('peer_connected', peer_count=5)
logger.network_event('block_received', peer='192.168.1.1')

# Security events
logger.security_event(
    'rate_limit_exceeded',
    severity='WARN',
    endpoint='/send',
    requests=120
)

# Performance events
logger.performance_event('block_validation', 0.05, 'seconds')

# API requests
logger.api_request('/blocks', 'GET', status_code=200, duration_ms=45.2)

# Governance events
logger.governance_event('proposal_submitted', proposal_id='abc123')

# Wallet events
logger.wallet_event('wallet_created', address='XAI1234...')
```

### Correlation IDs

Track related log entries across operations:

```python
from structured_logger import LogContext

# Auto-generated correlation ID
with LogContext() as ctx:
    logger.info("Processing request")
    process_transaction()
    logger.info("Request completed")

# Custom correlation ID
with LogContext(custom_id='req-12345'):
    logger.info("Custom correlation ID")
```

### Performance Timing

Time operations automatically:

```python
from structured_logger import PerformanceTimer

with PerformanceTimer(logger, 'block_validation'):
    validate_block(block)
    # Automatically logs duration when block exits
```

### Log Output

**JSON format** (`xai_blockchain.json.log`):
```json
{
  "timestamp": "2025-01-15T10:30:45.123456Z",
  "level": "INFO",
  "logger": "XAI_Blockchain",
  "message": "Block #100 mined",
  "module": "blockchain",
  "function": "mine_block",
  "line": 467,
  "correlation_id": "a1b2c3d4e5f6g7h8",
  "thread": {
    "id": 12345,
    "name": "MainThread"
  },
  "block_index": 100,
  "block_hash": "0x123abc...",
  "miner": "XAI123...def",
  "transaction_count": 50,
  "block_reward": 50.0,
  "mining_time_seconds": 5.2
}
```

**Human-readable format** (`xai_blockchain.log`):
```
[2025-01-15 10:30:45 UTC] INFO     [a1b2c3d4e5f6g7h8] Block #100 mined
[2025-01-15 10:30:46 UTC] INFO     [a1b2c3d4e5f6g7h8] Broadcasting block to 5 peers
```

---

## Metrics & Monitoring

### Tracked Metrics

#### Blockchain Metrics
- `xai_blocks_mined_total` - Total blocks mined (counter)
- `xai_transactions_processed_total` - Total transactions (counter)
- `xai_chain_height` - Current blockchain height (gauge)
- `xai_difficulty` - Current mining difficulty (gauge)
- `xai_pending_transactions` - Pending transactions in mempool (gauge)
- `xai_total_supply` - Total XAI in circulation (gauge)

#### Network Metrics
- `xai_peers_connected` - Number of connected peers (gauge)
- `xai_p2p_messages_received_total` - P2P messages received (counter)
- `xai_p2p_messages_sent_total` - P2P messages sent (counter)
- `xai_blocks_received_total` - Blocks received from network (counter)
- `xai_blocks_propagated_total` - Blocks propagated to network (counter)

#### Performance Metrics
- `xai_block_mining_duration_seconds` - Block mining time (histogram)
- `xai_block_propagation_duration_seconds` - Block propagation time (histogram)
- `xai_transaction_validation_duration_seconds` - Transaction validation time (histogram)
- `xai_mempool_size_bytes` - Mempool size in bytes (gauge)

#### System Metrics
- `xai_node_cpu_usage_percent` - CPU usage (gauge)
- `xai_node_memory_usage_bytes` - Memory usage in bytes (gauge)
- `xai_node_memory_usage_percent` - Memory usage percentage (gauge)
- `xai_node_disk_usage_bytes` - Disk usage in bytes (gauge)
- `xai_node_uptime_seconds` - Node uptime (gauge)

#### API Metrics
- `xai_api_requests_total` - Total API requests (counter)
- `xai_api_errors_total` - Total API errors (counter)
- `xai_api_request_duration_seconds` - API request duration (histogram)

#### Consensus Metrics
- `xai_consensus_forks_total` - Chain forks detected (counter)
- `xai_consensus_reorgs_total` - Chain reorganizations (counter)
- `xai_consensus_finalized_height` - Last finalized block height (gauge)

### Recording Metrics

```python
# Block mined
metrics.record_block_mined(block_index=100, mining_time=5.2)

# Transaction processed
metrics.record_transaction_processed(processing_time=0.05)

# Peer connected
metrics.record_peer_connected(peer_count=5)

# P2P message
metrics.record_p2p_message('sent')  # or 'received'

# Block propagation
metrics.record_block_propagation(propagation_time=0.5)

# API request
metrics.record_api_request('/blocks', duration=0.05, error=False)
```

### Prometheus Integration

**Scrape Configuration** (`prometheus.yml`):
```yaml
scrape_configs:
  - job_name: 'xai_blockchain'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

**Prometheus Metrics Output**:
```
# HELP xai_blocks_mined_total Total number of blocks mined
# TYPE xai_blocks_mined_total counter
xai_blocks_mined_total 100

# HELP xai_chain_height Current blockchain height
# TYPE xai_chain_height gauge
xai_chain_height 100

# HELP xai_block_mining_duration_seconds Time taken to mine a block
# TYPE xai_block_mining_duration_seconds histogram
xai_block_mining_duration_seconds_bucket{le="1"} 5
xai_block_mining_duration_seconds_bucket{le="5"} 45
xai_block_mining_duration_seconds_bucket{le="10"} 95
xai_block_mining_duration_seconds_bucket{le="+Inf"} 100
xai_block_mining_duration_seconds_sum 520.5
xai_block_mining_duration_seconds_count 100
```

### Health Checks

**Health Check Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:45.123456",
  "uptime_seconds": 3600,
  "checks": {
    "cpu": {
      "status": "healthy",
      "usage_percent": 45.2
    },
    "memory": {
      "status": "healthy",
      "usage_percent": 62.5
    },
    "mempool": {
      "status": "healthy",
      "pending_transactions": 150
    },
    "blockchain": {
      "status": "healthy",
      "chain_height": 100
    }
  },
  "alerts": []
}
```

**Status Values**:
- `healthy` - All systems operating normally
- `degraded` - System operational but experiencing issues
- `unhealthy` - Critical issues detected

---

## Alert System

### Configuring Alerts

```python
from monitoring import AlertLevel

# High CPU alert
metrics.add_alert_rule(
    name='high_cpu',
    condition=lambda: metrics.get_metric('xai_node_cpu_usage_percent').value > 80,
    message='CPU usage above 80%',
    level=AlertLevel.WARNING
)

# Large mempool alert
metrics.add_alert_rule(
    name='large_mempool',
    condition=lambda: metrics.get_metric('xai_pending_transactions').value > 5000,
    message='Mempool has more than 5000 pending transactions',
    level=AlertLevel.WARNING
)

# No peers alert
metrics.add_alert_rule(
    name='no_peers',
    condition=lambda: metrics.get_metric('xai_peers_connected').value == 0,
    message='Node has no connected peers',
    level=AlertLevel.CRITICAL
)

# High memory alert
metrics.add_alert_rule(
    name='high_memory',
    condition=lambda: metrics.get_metric('xai_node_memory_usage_percent').value > 85,
    message='Memory usage above 85%',
    level=AlertLevel.CRITICAL
)
```

### Alert Levels

- `INFO` - Informational alerts
- `WARNING` - Warning conditions that should be investigated
- `CRITICAL` - Critical issues requiring immediate attention

### Retrieving Alerts

```python
# Get active alerts
active_alerts = metrics.get_active_alerts()

# Clear specific alert
metrics.clear_alert('high_cpu')
```

---

## Log Rotation

Logs are automatically rotated:
- **Daily rotation** at midnight UTC
- **Size limit**: 100MB per file
- **Retention**: 30 days of backups
- **Format**: Both JSON and human-readable

Log files location:
```
logs/
├── xai_blockchain.json.log         # Current JSON log
├── xai_blockchain.json.log.2025-01-14  # Previous day
├── xai_blockchain.log              # Current human-readable log
└── xai_blockchain.log.2025-01-14   # Previous day
```

---

## Best Practices

### 1. Use Correlation IDs for Request Tracking

```python
@app.route('/send', methods=['POST'])
def send_transaction():
    with LogContext() as ctx:
        logger.info("Transaction request received")

        # All logs within this context share correlation ID
        tx = create_transaction()
        validate_transaction(tx)
        broadcast_transaction(tx)

        logger.info("Transaction request completed")
```

### 2. Time Critical Operations

```python
with PerformanceTimer(logger, 'block_validation'):
    result = validate_block(block)
```

### 3. Log at Appropriate Levels

- `DEBUG`: Detailed diagnostic information
- `INFO`: General operational events
- `WARN`: Warnings about potential issues
- `ERROR`: Error conditions that don't stop the system
- `CRITICAL`: Critical failures requiring immediate attention

### 4. Include Context in Logs

```python
# Good - includes context
logger.error("Block validation failed",
            block_index=100,
            block_hash=block.hash[:16],
            error=str(e))

# Bad - minimal context
logger.error("Validation failed")
```

### 5. Monitor Key Metrics

Set up alerts for:
- High CPU/memory usage
- Large mempool size
- No connected peers
- Slow block propagation
- High API error rate

### 6. Regular Health Checks

```python
# Check health every 5 minutes
def periodic_health_check():
    while True:
        health = metrics.get_health_status()
        if health['status'] != 'healthy':
            send_notification(health)
        time.sleep(300)
```

---

## Grafana Dashboard

**Example Queries**:

```promql
# Block mining rate
rate(xai_blocks_mined_total[5m])

# Average block mining time
rate(xai_block_mining_duration_seconds_sum[5m]) /
rate(xai_block_mining_duration_seconds_count[5m])

# Transaction throughput
rate(xai_transactions_processed_total[1m]) * 60

# Mempool size
xai_pending_transactions

# Peer count
xai_peers_connected

# CPU usage
xai_node_cpu_usage_percent

# Memory usage
xai_node_memory_usage_percent
```

---

## Troubleshooting

### High Log Volume

Increase log level to reduce output:
```python
logger = StructuredLogger('XAI_Blockchain', log_level='WARN')
```

### Metrics Not Updating

Check that the monitoring thread is running:
```python
metrics = MetricsCollector(blockchain=blockchain, update_interval=5)
```

### Missing Logs

Check log directory permissions:
```python
log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)
```

### Alert Fatigue

Adjust alert thresholds to reduce false positives:
```python
# Increase threshold
condition=lambda: metrics.get_metric('xai_node_cpu_usage_percent').value > 90
```

---

## Testing

Run the example integration:
```bash
cd C:\Users\decri\GitClones\Crypto\xai\core
python monitoring_integration_example.py
```

This will:
- Initialize logging and monitoring
- Simulate blockchain activity
- Display health status
- Export Prometheus metrics
- Show logger statistics

---

## Production Deployment

### 1. Configure Log Levels

```python
# Production
logger = StructuredLogger('XAI_Node', log_level='INFO')

# Development
logger = StructuredLogger('XAI_Node', log_level='DEBUG')
```

### 2. Set Up Prometheus

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'xai_mainnet_nodes'
    static_configs:
      - targets: ['node1:5000', 'node2:5000', 'node3:5000']
    metrics_path: '/metrics'
```

### 3. Set Up Grafana

1. Add Prometheus as data source
2. Import XAI blockchain dashboard
3. Configure alerts in Grafana

### 4. Configure Log Aggregation

Use a log aggregation service (ELK, Splunk, etc.) to collect JSON logs:

```json
{
  "timestamp": "2025-01-15T10:30:45.123456Z",
  "level": "INFO",
  "logger": "XAI_Blockchain",
  "message": "Block #100 mined",
  "block_index": 100,
  "correlation_id": "a1b2c3d4e5f6g7h8"
}
```

### 5. Set Up Alerting

Configure alerts for:
- Node down (no metrics for 1 minute)
- High resource usage (CPU > 80%, Memory > 85%)
- No peers (isolated node)
- Large mempool (> 5000 pending transactions)
- High API error rate (> 5%)

---

## API Endpoints

### GET /metrics
Prometheus-compatible metrics endpoint.

**Response**: Prometheus text format
```
# HELP xai_blocks_mined_total Total number of blocks mined
# TYPE xai_blocks_mined_total counter
xai_blocks_mined_total 100
```

### GET /health
Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:45.123456",
  "uptime_seconds": 3600,
  "checks": {...},
  "alerts": []
}
```

### GET /monitoring/stats
Detailed monitoring statistics.

**Response**:
```json
{
  "metrics": {
    "metrics_count": 25,
    "alerts_count": 0,
    "uptime_seconds": 3600,
    "metrics": {...},
    "performance": {...}
  },
  "logger": {
    "log_counts": {
      "DEBUG": 0,
      "INFO": 150,
      "WARN": 5,
      "ERROR": 0,
      "CRITICAL": 0
    },
    "total_logs": 155
  }
}
```

### GET /monitoring/alerts
Get active alerts.

**Response**:
```json
{
  "alerts": [
    {
      "name": "high_cpu",
      "message": "CPU usage above 80%",
      "level": "warning",
      "metric_name": "xai_node_cpu_usage_percent",
      "threshold": 80,
      "current_value": 85.2,
      "timestamp": "2025-01-15T10:30:45.123456",
      "active": true
    }
  ]
}
```

---

## Summary

The XAI blockchain monitoring and logging system provides:

✅ **Comprehensive observability** with structured logs and metrics
✅ **Production-ready** with log rotation and retention
✅ **Privacy-preserving** with address truncation and data sanitization
✅ **Prometheus-compatible** for industry-standard monitoring
✅ **Real-time alerts** for proactive issue detection
✅ **Performance tracking** for optimization
✅ **Health checks** for uptime monitoring
✅ **Correlation IDs** for request tracing

For questions or issues, refer to the example code in `monitoring_integration_example.py`.
