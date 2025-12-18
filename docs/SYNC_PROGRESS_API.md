# Sync Progress API

Comprehensive header sync progress tracking for light clients with real-time updates via WebSocket.

## Overview

The Sync Progress API enables mobile apps and light clients to display detailed sync status during initial blockchain synchronization. It tracks three types of sync:

1. **Header Sync** - Light client header verification (SPV)
2. **Checkpoint Sync** - Fast sync using trusted checkpoints
3. **State Sync** - Full node state synchronization

## API Endpoints

### GET /sync/progress

Get light client header sync progress with detailed metrics.

**Response:**
```json
{
  "success": true,
  "progress": {
    "current_height": 12345,
    "target_height": 27000,
    "sync_percentage": 45.72,
    "estimated_time_remaining": 120,
    "sync_state": "syncing",
    "headers_per_second": 10.5,
    "started_at": "2025-12-18T12:00:00",
    "checkpoint_sync_enabled": true,
    "checkpoint_height": 10000
  }
}
```

**Sync States:**
- `syncing` - Actively downloading headers
- `synced` - Fully synchronized
- `stalled` - No progress for 30+ seconds
- `idle` - Not actively syncing

### GET /sync/status

Get comprehensive sync status for all sync types.

**Response:**
```json
{
  "success": true,
  "sync_status": {
    "header_sync": {
      "enabled": true,
      "status": {
        "current_height": 12345,
        "target_height": 27000,
        "sync_percentage": 45.72,
        "sync_state": "syncing"
      }
    },
    "checkpoint_sync": {
      "enabled": true,
      "status": {
        "stage": "downloading",
        "bytes_downloaded": 5242880,
        "total_bytes": 10485760,
        "download_percentage": 50.0,
        "verification_percentage": 0.0,
        "application_percentage": 0.0
      }
    },
    "state_sync": {
      "enabled": true,
      "current_height": 12345,
      "pending_transactions": 42
    }
  }
}
```

## WebSocket Events

Subscribe to real-time sync progress updates on the `sync` channel.

### Subscribe
```javascript
const ws = new WebSocket('ws://localhost:12000/ws');
ws.send(JSON.stringify({
  action: 'subscribe',
  channel: 'sync'
}));
```

### Header Sync Progress Event
```json
{
  "channel": "sync",
  "type": "sync_progress",
  "data": {
    "percentage": 45.5,
    "current": 12345,
    "target": 27000,
    "eta_seconds": 120,
    "headers_per_second": 10.5,
    "sync_state": "syncing"
  }
}
```

### Checkpoint Sync Progress Event
```json
{
  "channel": "sync",
  "type": "checkpoint_progress",
  "data": {
    "stage": "downloading",
    "bytes_downloaded": 5242880,
    "total_bytes": 10485760,
    "download_percentage": 50.0
  }
}
```

## Implementation Details

### Light Client Service

The `LightClientService` class tracks header sync progress:

```python
from xai.core.light_client_service import LightClientService

service = LightClientService(blockchain)

# Start tracking sync
service.start_sync(target_height=27000)

# Update progress as headers are received
service.update_sync_progress(12345)

# Get current progress
progress = service.get_sync_progress()
print(f"Sync: {progress.sync_percentage:.1f}%")
print(f"ETA: {progress.estimated_time_remaining}s")
```

### Checkpoint Sync Manager

The `CheckpointSyncManager` tracks checkpoint download and verification:

```python
from xai.core.checkpoint_sync import CheckpointSyncManager

sync_manager = CheckpointSyncManager(blockchain)

# Set progress callback for real-time updates
def on_progress(data):
    print(f"Stage: {data['stage']}")
    print(f"Download: {data['download_percentage']:.1f}%")

sync_manager.set_progress_callback(on_progress)

# Perform checkpoint sync
success = sync_manager.fetch_validate_apply()

# Get final progress
progress = sync_manager.get_checkpoint_sync_progress()
```

## Mobile App Integration

### React Native Example

```javascript
import { useState, useEffect } from 'react';

function SyncProgressBar() {
  const [progress, setProgress] = useState(null);

  useEffect(() => {
    const ws = new WebSocket('ws://node:12000/ws');

    ws.onopen = () => {
      // Subscribe to sync channel
      ws.send(JSON.stringify({
        action: 'subscribe',
        channel: 'sync'
      }));
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.channel === 'sync' && message.type === 'sync_progress') {
        setProgress(message.data);
      }
    };

    return () => ws.close();
  }, []);

  if (!progress) return <div>Loading...</div>;

  const formatETA = (seconds) => {
    if (!seconds) return 'Calculating...';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  return (
    <div>
      <h3>Blockchain Sync</h3>
      <ProgressBar value={progress.percentage} />
      <p>Block {progress.current} of {progress.target}</p>
      <p>Speed: {progress.headers_per_second.toFixed(1)} blocks/sec</p>
      <p>ETA: {formatETA(progress.eta_seconds)}</p>
      <p>Status: {progress.sync_state}</p>
    </div>
  );
}
```

### Flutter Example

```dart
import 'package:web_socket_channel/web_socket_channel.dart';
import 'dart:convert';

class SyncProgressWidget extends StatefulWidget {
  @override
  _SyncProgressWidgetState createState() => _SyncProgressWidgetState();
}

class _SyncProgressWidgetState extends State<SyncProgressWidget> {
  final channel = WebSocketChannel.connect(
    Uri.parse('ws://node:12000/ws'),
  );

  Map<String, dynamic>? progress;

  @override
  void initState() {
    super.initState();

    // Subscribe to sync channel
    channel.sink.add(jsonEncode({
      'action': 'subscribe',
      'channel': 'sync'
    }));

    // Listen for updates
    channel.stream.listen((message) {
      final data = jsonDecode(message);
      if (data['channel'] == 'sync' && data['type'] == 'sync_progress') {
        setState(() {
          progress = data['data'];
        });
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    if (progress == null) {
      return CircularProgressIndicator();
    }

    return Column(
      children: [
        LinearProgressIndicator(
          value: progress!['percentage'] / 100,
        ),
        Text('Block ${progress!['current']} of ${progress!['target']}'),
        Text('${progress!['headers_per_second'].toFixed(1)} blocks/sec'),
        Text('ETA: ${formatETA(progress!['eta_seconds'])}'),
      ],
    );
  }

  String formatETA(int? seconds) {
    if (seconds == null) return 'Calculating...';
    int mins = seconds ~/ 60;
    int secs = seconds % 60;
    return '${mins}m ${secs}s';
  }

  @override
  void dispose() {
    channel.sink.close();
    super.dispose();
  }
}
```

## Testing

Comprehensive test suite in `tests/xai_tests/unit/test_sync_progress.py`:

- Light client sync progress tracking
- Checkpoint sync progress tracking
- API endpoint responses
- WebSocket event broadcasting

Run tests:
```bash
pytest tests/xai_tests/unit/test_sync_progress.py -v
```

## Performance Characteristics

- **Update Frequency**: WebSocket updates every 2 seconds
- **Memory Usage**: ~100 data points retained (rolling window)
- **Stall Detection**: 30 seconds without progress triggers stalled state
- **Speed Calculation**: Moving average over last 10 samples

## Security Considerations

- API endpoints inherit existing authentication requirements
- WebSocket connections subject to rate limiting (100 msg/min per client)
- Progress data is read-only and cannot influence sync behavior
- No sensitive information exposed in progress metrics
