# XAI Blockchain - Metrics Integration Guide

Guide for integrating the monitoring metrics into your blockchain node operations.

## Table of Contents

1. [Quick Integration](#quick-integration)
2. [Node Initialization](#node-initialization)
3. [Recording Metrics](#recording-metrics)
4. [API Integration](#api-integration)
5. [Examples](#examples)
6. [Best Practices](#best-practices)

---

## Quick Integration

### 1. Import Metrics Module

```python
from xai.core.metrics import initialize_metrics, get_metrics
```

### 2. Initialize Metrics on Startup

```python
# In your node initialization
metrics = initialize_metrics(
    port=8000,
    version="1.0.0",
    network="mainnet",
    node_id="xai-node-1",
    log_file="/var/log/xai/metrics.json"
)
```

### 3. Record Events Throughout Lifecycle

```python
metrics = get_metrics()

# When a block is mined
metrics.record_block(
    height=1234,
    size=5000,
    difficulty=1000,
    mining_time=30,
    validation_time=0.5
)

# When a transaction is processed
metrics.record_transaction(
    status="confirmed",
    value=100,
    fee=0.001,
    processing_time=0.5
)

# Update peer count
metrics.update_peer_count(5, active=3)

# Update mempool
metrics.update_mempool_size(250)
```

---

## Node Initialization

### Complete Initialization Example

```python
from xai.core.node import BlockchainNode
from xai.core.metrics import initialize_metrics
from xai.core.logging_config import setup_logging

class MonitoredBlockchainNode(BlockchainNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize metrics
        self.metrics = initialize_metrics(
            port=8000,
            version="1.0.0",
            network="mainnet",
            node_id=self.node_id,
            log_file="/var/log/xai/blockchain.json"
        )

        # Initialize logging
        self.logger = setup_logging(
            name="xai.blockchain",
            log_file="/var/log/xai/blockchain.json",
            level="INFO"
        )

        self.logger.info("Node initialized", node_id=self.node_id)

    def start(self):
        """Start the node with metrics tracking"""
        self.logger.info("Starting blockchain node")
        super().start()
        self.metrics.update_system_metrics()

    def mine_block(self):
        """Mine block with metrics recording"""
        start_time = time.time()

        try:
            block = super().mine_block()
            mining_time = time.time() - start_time

            # Record successful mining
            self.metrics.record_block(
                height=block.height,
                size=len(str(block)),
                difficulty=self.difficulty,
                mining_time=mining_time
            )

            self.logger.info(
                "Block mined",
                height=block.height,
                mining_time=mining_time
            )

            return block

        except Exception as e:
            self.logger.error("Mining failed", error=str(e))
            raise
```

---

## Recording Metrics

### Block Metrics

```python
# Record a new block
metrics.record_block(
    height=1000,           # Block height
    size=5000,             # Block size in bytes
    difficulty=1000,       # Current difficulty
    mining_time=30,        # Time to mine in seconds
    validation_time=0.5    # Time to validate
)

# Update blockchain height
metrics.block_height.set(1000)

# Track mining difficulty adjustments
metrics.mining_difficulty.set(1500)

# Record block production rate (blocks per minute)
metrics.block_production_rate.set(6.0)
```

### Transaction Metrics

```python
# Record a transaction
metrics.record_transaction(
    status="confirmed",     # pending, confirmed, failed
    value=100,             # Transaction value in XAI
    fee=0.001,             # Transaction fee in XAI
    processing_time=0.5    # Processing time in seconds
)

# Update mempool size
metrics.update_mempool_size(250)

# Record throughput
metrics.transaction_throughput.set(10.5)

# Track transaction by wallet
metrics.record_wallet_transaction(
    address="xai1abc...",
    tx_type="send"
)
```

### Network Metrics

```python
# Update peer information
metrics.update_peer_count(
    count=5,      # Total connected peers
    active=3      # Active peers
)

# Record network message
metrics.record_network_message(
    message_type="block"    # block, transaction, ping
)

# Record network error
metrics.record_network_error(
    error_type="timeout"    # timeout, connection_refused
)

# Record network latency
metrics.network_latency.observe(0.05)  # 50ms latency
```

### Mining Metrics

```python
# Update mining hashrate
metrics.update_mining_hashrate(1000000)  # 1M H/s

# Record mining attempt
metrics.record_mining_attempt(success=False)

# Record successful mining
metrics.record_mining_attempt(success=True)
```

### System Metrics

```python
# Update system resource metrics (called periodically)
metrics.update_system_metrics()

# This updates:
# - CPU usage
# - Memory usage
# - Disk usage
# - Process uptime
# - Thread count
```

### API Metrics

```python
# In your API request handler
start_time = time.time()

try:
    # Handle request
    result = handle_request()
    status = 200
except Exception as e:
    status = 500

duration = time.time() - start_time

# Record API metric
metrics.record_api_request(
    endpoint="/blocks",
    method="GET",
    status=status,
    duration=duration
)
```

---

## API Integration

### Flask Route Wrapper

```python
from functools import wraps
from time import time

def record_api_metrics(f):
    """Decorator to record API metrics"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        metrics = get_metrics()
        start = time()

        try:
            result = f(*args, **kwargs)
            status = 200
            return result
        except Exception as e:
            status = 500
            raise
        finally:
            duration = time() - start
            metrics.record_api_request(
                endpoint=request.path,
                method=request.method,
                status=status,
                duration=duration
            )

    return decorated_function

# Usage in routes
@app.route("/blocks", methods=["GET"])
@record_api_metrics
def get_blocks():
    """Get blocks with metrics"""
    blocks = blockchain.chain
    return jsonify(blocks)
```

### Metrics Endpoint in Node API

```python
# In NodeAPIRoutes._setup_core_routes()

@self.app.route("/metrics", methods=["GET"])
def prometheus_metrics():
    """Prometheus metrics endpoint"""
    try:
        metrics_output = self.node.metrics.export_prometheus()
        return metrics_output, 200, {"Content-Type": "text/plain; version=0.0.4"}
    except Exception as e:
        return f"# Error: {e}\n", 500, {"Content-Type": "text/plain"}
```

---

## Examples

### Complete Node with Monitoring

```python
import time
import threading
from xai.core.blockchain import Blockchain
from xai.core.metrics import initialize_metrics
from xai.core.logging_config import setup_logging

class MonitoredNode:
    def __init__(self, node_id, port=9090):
        self.node_id = node_id
        self.blockchain = Blockchain()

        # Initialize monitoring
        self.metrics = initialize_metrics(
            port=port,
            version="1.0.0",
            network="testnet",
            node_id=node_id,
            log_file=f"/var/log/xai/{node_id}.json"
        )

        self.logger = setup_logging(
            name=f"xai.{node_id}",
            log_file=f"/var/log/xai/{node_id}.json"
        )

        # Start metrics update thread
        self.metrics_thread = threading.Thread(
            target=self._update_metrics_loop,
            daemon=True
        )
        self.metrics_thread.start()

    def _update_metrics_loop(self):
        """Periodically update system metrics"""
        while True:
            try:
                self.metrics.update_system_metrics()
                self.metrics.update_peer_count(len(self.peers))
                self.metrics.update_mempool_size(len(self.mempool))
                time.sleep(10)
            except Exception as e:
                self.logger.error("Metrics update failed", error=str(e))

    def mine(self):
        """Mine a block with metrics"""
        start_time = time.time()

        self.logger.info("Mining block", height=len(self.blockchain.chain))

        try:
            # Mine block
            block = self.blockchain.mine_pending_transactions()
            mining_time = time.time() - start_time

            # Record metrics
            self.metrics.record_block(
                height=block.height,
                size=len(str(block)),
                difficulty=self.blockchain.difficulty,
                mining_time=mining_time
            )

            self.logger.info(
                "Block mined successfully",
                height=block.height,
                mining_time=mining_time
            )

        except Exception as e:
            self.logger.error("Mining failed", error=str(e))
```

### Transaction Processing with Metrics

```python
def process_transaction(self, tx):
    """Process transaction with metrics"""
    start_time = time.time()

    try:
        # Validate transaction
        self.blockchain.validate_transaction(tx)

        # Add to mempool
        self.blockchain.pending_transactions.append(tx)

        # Record metrics
        processing_time = time.time() - start_time
        self.metrics.record_transaction(
            status="pending",
            value=tx.value,
            fee=tx.fee,
            processing_time=processing_time
        )

        self.logger.info(
            "Transaction received",
            tx_hash=tx.hash[:8],
            value=tx.value,
            fee=tx.fee
        )

        return True

    except Exception as e:
        self.logger.error("Transaction rejected", error=str(e))
        return False
```

### Supply Metrics Tracking

```python
def update_supply_metrics(self):
    """Update supply metrics"""
    total_supply = self.calculate_total_supply()
    circulating = self.calculate_circulating_supply()

    self.metrics.update_supply_metrics(
        total=total_supply,
        circulating=circulating
    )

    self.logger.info(
        "Supply updated",
        total_supply=total_supply,
        circulating=circulating,
        percentage=circulating/total_supply*100
    )
```

---

## Best Practices

### 1. Thread Safety

```python
# Use get_metrics() to get thread-safe global instance
metrics = get_metrics()

# All metric recording operations are thread-safe
# The metrics module handles locking internally
```

### 2. Performance

```python
# Don't record metrics in hot loops
# Instead, record periodically or batch updates

def batch_record_transactions(self, transactions):
    """Record multiple transactions efficiently"""
    metrics = get_metrics()

    for tx in transactions:
        # Record transaction
        metrics.record_transaction(
            status="confirmed",
            value=tx.value,
            fee=tx.fee,
            processing_time=tx.processing_time
        )

# Or update counters once per block
total_fees = sum(tx.fee for tx in block.transactions)
metrics.transaction_fee.observe(total_fees / len(block.transactions))
```

### 3. Error Handling

```python
# Always wrap metrics recording in try-except
try:
    metrics.record_block(
        height=block.height,
        size=block_size,
        difficulty=difficulty,
        mining_time=mining_time
    )
except Exception as e:
    logger.warning("Failed to record block metrics", error=str(e))
    # Continue operation, don't fail if metrics unavailable
```

### 4. Meaningful Labels

```python
# Good: semantic labels for grouping
metrics.api_requests_total.labels(
    endpoint="/blocks",
    method="GET",
    status="200"
).inc()

# Avoid: high cardinality labels
# Don't use user_id, timestamp, or other unique values as labels
```

### 5. Structured Logging

```python
# Include relevant context in logs
logger.info(
    "Block validated",
    block_height=1234,
    validation_time=0.5,
    transactions=150,
    block_size=5000,
    difficulty=1000,
)

# This creates searchable, analyzable logs
```

### 6. Health Checks

```python
def is_healthy(self):
    """Check node health using metrics"""
    metrics = get_metrics()

    # Check synchronization
    synced = metrics.chain_sync_status._value.get() == 1

    # Check peer connectivity
    peers = metrics.peers_connected._value.get()
    has_peers = peers >= 2

    # Check API responsiveness
    recent_requests = (
        metrics.api_requests_total._metrics.values()
    )

    return synced and has_peers and recent_requests
```

---

## Troubleshooting

### Metrics Not Appearing in Prometheus

1. Verify metrics endpoint is exposed:
   ```bash
   curl http://localhost:8000/metrics
   ```

2. Check Prometheus configuration targets:
   ```bash
   curl http://localhost:9090/api/v1/targets
   ```

3. Check scrape logs:
   ```bash
   docker logs xai-prometheus | grep xai
   ```

### High Memory Usage from Metrics

1. Reduce cardinality of labels (avoid unique values)
2. Enable compression in Prometheus
3. Reduce retention period
4. Filter unwanted metrics with relabel_configs

### Alerts Not Triggering

1. Check alert rule syntax:
   ```bash
   curl http://localhost:9090/api/v1/rules
   ```

2. Verify metric values match alert conditions
3. Check alert evaluation interval

---

## Support

See [MONITORING_GUIDE.md](../MONITORING_GUIDE.md) for complete documentation and troubleshooting.

---

**Last Updated:** 2024-01-15
**Version:** 1.0.0
