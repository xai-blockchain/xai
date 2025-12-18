# Mobile Telemetry Usage Guide

## Overview

The mobile telemetry system tracks performance metrics from mobile clients to optimize their experience based on real usage data.

## Components

### 1. MobileTelemetryCollector

Collects and aggregates telemetry events from mobile clients.

```python
from xai.mobile.telemetry import MobileTelemetryCollector

collector = MobileTelemetryCollector(max_events=10000)

# Record a sync event
collector.record_sync_event(
    client_id='device_abc123',
    bytes_sent=1024,
    bytes_received=50000,
    duration_ms=250,
    connection_type='wifi',
    blocks_synced=100,
    battery_start=95.0,
    battery_end=94.5
)

# Get aggregated statistics
stats = collector.get_stats(time_window_hours=24)
print(f"Average latency: {stats.avg_latency_ms}ms")
print(f"Total bandwidth: {stats.total_bytes_sent + stats.total_bytes_received} bytes")

# Get bandwidth breakdown by operation
bandwidth = collector.get_bandwidth_by_operation()
print(f"Sync operations used: {bandwidth['sync']['total']} bytes")

# Get battery impact analysis
battery = collector.get_battery_impact_by_operation()
print(f"Sync avg battery drain: {battery['sync']['avg_drain']}%")
```

### 2. NetworkOptimizer

Adapts mobile client behavior based on network conditions.

```python
from xai.mobile.network_optimizer import NetworkOptimizer

optimizer = NetworkOptimizer(
    enable_compression=True,
    max_queue_size=1000
)

# Update network profile
profile = optimizer.update_network_profile(
    connection_type='cellular',
    signal_strength=3,
    latency_ms=150,
    estimated_bandwidth_kbps=2000,
    is_metered=True
)

print(f"Quality score: {profile.quality_score()}")
print(f"Recommended mode: {profile.recommended_mode()}")

# Get optimized sync parameters
base_params = {
    'batch_size': 50,
    'poll_interval': 30,
    'include_full_blocks': True
}
optimized = optimizer.optimize_sync_params(base_params)
print(f"Optimized batch size: {optimized['batch_size']}")
print(f"Use compression: {optimized['use_compression']}")

# Queue transaction for offline submission
optimizer.queue_transaction(
    tx_id='tx_abc123',
    tx_data={'from': 'addr1', 'to': 'addr2', 'amount': 100},
    priority=5
)

# Get queued transactions when connection restored
queued = optimizer.get_queued_transactions(max_count=10)
for tx in queued:
    print(f"Submit queued transaction: {tx.tx_id}")
```

### 3. API Endpoints

Integration with the node API for telemetry submission.

#### Submit Telemetry (POST /api/v1/telemetry/mobile)

```bash
curl -X POST http://localhost:12001/api/v1/telemetry/mobile \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "event_type": "sync",
        "timestamp": 1234567890.0,
        "client_id": "device_abc123",
        "bytes_sent": 1024,
        "bytes_received": 50000,
        "duration_ms": 250,
        "latency_ms": 75,
        "connection_type": "wifi",
        "signal_strength": 4,
        "battery_level_start": 95.0,
        "battery_level_end": 94.5,
        "metadata": {
          "blocks_synced": 100
        }
      }
    ]
  }'
```

Response includes optimization recommendations:
```json
{
  "success": true,
  "processed": 1,
  "failed": 0,
  "total": 1,
  "recommendations": {
    "bandwidth_mode": "full",
    "recommended_batch_size": 50,
    "use_compression": false
  }
}
```

#### Get Optimization Recommendations (POST /api/v1/telemetry/mobile/optimize)

```bash
curl -X POST http://localhost:12001/api/v1/telemetry/mobile/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "connection_type": "cellular",
    "signal_strength": 2,
    "latency_ms": 200,
    "bandwidth_kbps": 1000,
    "is_metered": true,
    "operation": "sync"
  }'
```

Response:
```json
{
  "success": true,
  "network_profile": {
    "connection_type": "cellular",
    "quality_score": 0.45,
    "recommended_mode": "low"
  },
  "bandwidth_mode": "low",
  "recommended_batch_size": 12,
  "optimized_sync_params": {
    "batch_size": 12,
    "poll_interval": 60,
    "include_full_blocks": false,
    "include_tx_details": true,
    "use_compression": true
  },
  "recommendations": {
    "use_compression": true,
    "reduce_polling": true,
    "queue_offline": false
  }
}
```

#### Get Telemetry Statistics (GET /api/v1/telemetry/mobile/stats)

Public endpoint with limited statistics:

```bash
curl http://localhost:12001/api/v1/telemetry/mobile/stats?hours=24
```

Response:
```json
{
  "success": true,
  "time_window_hours": 24,
  "event_count": 1523,
  "avg_latency_ms": 85.3,
  "latency_percentiles": {
    "p50": 75.0,
    "p95": 150.0,
    "p99": 250.0
  },
  "connection_type_distribution": {
    "wifi": 1200,
    "cellular": 323
  },
  "event_type_distribution": {
    "sync": 800,
    "api_call": 600,
    "transaction": 123
  }
}
```

#### Get Full Summary (GET /api/v1/telemetry/mobile/summary)

Admin-only endpoint with comprehensive statistics:

```bash
curl -H "Authorization: Bearer <admin_token>" \
  http://localhost:12001/api/v1/telemetry/mobile/summary?hours=24
```

## Mobile Client Integration

### Swift (iOS)

```swift
struct TelemetryEvent: Codable {
    let eventType: String
    let timestamp: Double
    let clientId: String
    let bytesSent: Int
    let bytesReceived: Int
    let durationMs: Double
    let connectionType: String
    let batteryLevelStart: Double?
    let batteryLevelEnd: Double?
}

class TelemetryManager {
    private let nodeURL = "http://your-node:12001"
    private var events: [TelemetryEvent] = []

    func recordSyncEvent(bytesSent: Int, bytesReceived: Int, duration: TimeInterval) {
        let event = TelemetryEvent(
            eventType: "sync",
            timestamp: Date().timeIntervalSince1970,
            clientId: UIDevice.current.identifierForVendor?.uuidString ?? "unknown",
            bytesSent: bytesSent,
            bytesReceived: bytesReceived,
            durationMs: duration * 1000,
            connectionType: getConnectionType(),
            batteryLevelStart: getBatteryLevel(),
            batteryLevelEnd: nil
        )
        events.append(event)

        if events.count >= 10 {
            submitTelemetry()
        }
    }

    func submitTelemetry() {
        guard !events.isEmpty else { return }

        let payload = ["events": events]
        // Submit to /api/v1/telemetry/mobile
        // Handle recommendations in response
    }
}
```

### Kotlin (Android)

```kotlin
data class TelemetryEvent(
    val eventType: String,
    val timestamp: Double,
    val clientId: String,
    val bytesSent: Int,
    val bytesReceived: Int,
    val durationMs: Double,
    val connectionType: String,
    val batteryLevelStart: Float?,
    val batteryLevelEnd: Float?
)

class TelemetryManager(private val context: Context) {
    private val nodeUrl = "http://your-node:12001"
    private val events = mutableListOf<TelemetryEvent>()

    fun recordSyncEvent(bytesSent: Int, bytesReceived: Int, duration: Long) {
        val event = TelemetryEvent(
            eventType = "sync",
            timestamp = System.currentTimeMillis() / 1000.0,
            clientId = Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID),
            bytesSent = bytesSent,
            bytesReceived = bytesReceived,
            durationMs = duration.toDouble(),
            connectionType = getConnectionType(),
            batteryLevelStart = getBatteryLevel(),
            batteryLevelEnd = null
        )
        events.add(event)

        if (events.size >= 10) {
            submitTelemetry()
        }
    }
}
```

## Optimization Use Cases

### 1. Adaptive Sync Batch Size

```python
# Client detects poor connection
profile = optimizer.update_network_profile(
    connection_type='cellular',
    signal_strength=1,
    latency_ms=500,
    estimated_bandwidth_kbps=100
)

# Get recommended batch size
batch_size = optimizer.get_recommended_batch_size('sync')
# Returns: 5 (reduced from default 50)

# Use smaller batches to avoid timeouts
sync_blocks(batch_size=batch_size)
```

### 2. Low-Bandwidth Mode

```python
mode = optimizer.get_bandwidth_mode()

if mode == BandwidthMode.LOW or mode == BandwidthMode.MINIMAL:
    # Disable optional data
    include_full_blocks = False
    include_tx_details = False
    # Enable compression
    use_compression = True
    # Reduce polling frequency
    poll_interval = 120  # 2 minutes
```

### 3. Offline Transaction Queue

```python
# Queue transaction when offline
if connection_type == 'offline':
    optimizer.queue_transaction(
        tx_id='tx_123',
        tx_data=transaction_data,
        priority=10  # High priority
    )

# Submit when connection restored
if connection_restored:
    queued = optimizer.get_queued_transactions()
    for tx in queued:
        try:
            submit_transaction(tx.tx_data)
            optimizer.remove_transaction(tx.tx_id)
        except Exception as e:
            optimizer.mark_retry(tx.tx_id)
```

### 4. Battery-Aware Sync

```python
# Analyze battery impact
battery_impact = collector.get_battery_impact_by_operation()
sync_drain = battery_impact['sync']['avg_drain']

# Reduce sync frequency if high battery drain
if sync_drain > 0.5:  # More than 0.5% per sync
    # Increase sync interval
    sync_interval = min(sync_interval * 1.5, 300)
```

## Metrics to Track

### Bandwidth Metrics
- Bytes sent/received per operation type
- Total data usage per hour/day
- Bandwidth efficiency (useful data vs overhead)

### Performance Metrics
- API call latency (p50, p95, p99)
- Sync duration and throughput
- Operation success rates

### Battery Metrics
- Battery drain per operation type
- Battery drain per MB transferred
- Power efficiency on WiFi vs cellular

### Resource Metrics
- Memory usage trends
- Storage usage growth
- Cache hit rates

## Best Practices

1. **Batch telemetry submissions** - Submit events in batches of 10-50 to reduce API calls
2. **Anonymous client IDs** - Use device-specific but anonymous identifiers
3. **Respect metered connections** - Reduce data usage on cellular
4. **Handle offline gracefully** - Queue operations and submit when online
5. **Monitor battery impact** - Adjust sync frequency based on power consumption
6. **Use compression** - Enable compression on cellular and poor connections
7. **Implement backoff** - Exponential backoff for failed operations
8. **Cache aggressively** - Minimize redundant data transfers
