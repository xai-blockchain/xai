# Peer Discovery Usage Examples

## Basic Standalone Usage

```python
from peer_discovery import PeerDiscoveryManager

# Create discovery manager
manager = PeerDiscoveryManager(
    network_type="mainnet",
    my_url="http://your-ip:5000",
    max_peers=50,
    discovery_interval=300  # 5 minutes
)

# Start discovery
manager.start()

# Let it run...
import time
time.sleep(60)

# Check stats
stats = manager.get_stats()
print(f"Connected peers: {stats['connected_peers']}")
print(f"Known peers: {stats['known_peers']}")
print(f"Diversity score: {stats['diversity_score']:.1f}")

# Get connected peer URLs
peers = manager.get_connected_peer_urls()
for peer in peers:
    print(f"  - {peer}")

# Stop when done
manager.stop()
```

## Integration with Blockchain Node

```python
from blockchain import Blockchain
from peer_discovery import PeerDiscoveryManager, setup_peer_discovery_api
from flask import Flask

# Create blockchain and Flask app
blockchain = Blockchain()
app = Flask(__name__)

# Create node with peer discovery
class Node:
    def __init__(self):
        self.blockchain = blockchain
        self.peers = set()

        # Initialize peer discovery
        self.peer_discovery = PeerDiscoveryManager(
            network_type="mainnet",
            my_url="http://your-ip:5000",
            max_peers=50
        )

        # Setup API endpoints
        setup_peer_discovery_api(app, self)

    def start(self):
        # Start peer discovery
        self.peer_discovery.start()

        # Sync peers with blockchain node
        self.peers.update(self.peer_discovery.connected_peers)

        # Start Flask
        app.run(host='0.0.0.0', port=5000)

# Run node
node = Node()
node.start()
```

## Manual Peer Management

```python
from peer_discovery import PeerDiscoveryManager, PeerInfo

manager = PeerDiscoveryManager(
    network_type="mainnet",
    my_url="http://localhost:5000"
)

# Manually add a peer
peer_url = "http://192.168.1.100:5000"
peer = PeerInfo(peer_url)
peer.is_bootstrap = True  # Mark as bootstrap
manager.known_peers[peer_url] = peer

# Update peer metrics manually
manager.update_peer_info(peer_url, success=True, response_time=0.5)
manager.update_peer_info(peer_url, success=True, response_time=0.3)
manager.update_peer_info(peer_url, success=False)

# Check peer quality
peer = manager.known_peers[peer_url]
print(f"Quality: {peer.quality_score}")
print(f"Reliability: {peer.get_reliability():.1f}%")
print(f"Avg Response: {peer.get_avg_response_time():.3f}s")

# Get peer details
details = peer.to_dict()
print(details)
```

## Custom Bootstrap Nodes

```python
from peer_discovery import PeerDiscoveryManager, BootstrapNodes

# Add custom seeds temporarily
custom_seeds = [
    "http://my-seed1.example.com:5000",
    "http://my-seed2.example.com:5000",
]

# Create manager with custom network type
manager = PeerDiscoveryManager(
    network_type="custom",
    my_url="http://localhost:5000"
)

# Manually bootstrap from custom seeds
for seed_url in custom_seeds:
    from peer_discovery import PeerInfo, PeerDiscoveryProtocol

    # Ping seed
    is_alive, response_time = PeerDiscoveryProtocol.ping_peer(seed_url)

    if is_alive:
        # Add to known peers
        peer = PeerInfo(seed_url)
        peer.is_bootstrap = True
        peer.update_success(response_time)
        manager.known_peers[seed_url] = peer

        # Get peers from seed
        peer_list = PeerDiscoveryProtocol.send_get_peers_request(seed_url)
        if peer_list:
            for peer_url in peer_list:
                if peer_url not in manager.known_peers:
                    manager.known_peers[peer_url] = PeerInfo(peer_url)

# Start discovery
manager.start()
```

## Monitoring Peer Health

```python
from peer_discovery import PeerDiscoveryManager

manager = PeerDiscoveryManager(
    network_type="mainnet",
    my_url="http://localhost:5000"
)

manager.start()

# Monitor in background
import time
import threading

def monitor_peers():
    while True:
        stats = manager.get_stats()

        # Check health
        if stats['connected_peers'] < 10:
            print("WARNING: Low peer count!")

        if stats['diversity_score'] < 50:
            print("WARNING: Low peer diversity!")

        if stats['avg_peer_quality'] < 60:
            print("WARNING: Low peer quality!")

        # Print status
        print(f"\nPeer Status:")
        print(f"  Connected: {stats['connected_peers']}/{stats['max_peers']}")
        print(f"  Diversity: {stats['diversity_score']:.1f}/100")
        print(f"  Quality: {stats['avg_peer_quality']:.1f}/100")

        time.sleep(60)  # Check every minute

# Start monitoring
monitor_thread = threading.Thread(target=monitor_peers, daemon=True)
monitor_thread.start()

# Keep running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    manager.stop()
```

## Peer Quality Filtering

```python
from peer_discovery import PeerDiscoveryManager

manager = PeerDiscoveryManager(
    network_type="mainnet",
    my_url="http://localhost:5000"
)

manager.start()
time.sleep(60)

# Get high-quality peers only
high_quality_peers = [
    peer for peer in manager.known_peers.values()
    if peer.quality_score >= 80
]

print(f"High-quality peers: {len(high_quality_peers)}")

for peer in high_quality_peers:
    print(f"  {peer.url}")
    print(f"    Quality: {peer.quality_score}")
    print(f"    Reliability: {peer.get_reliability():.1f}%")
    print(f"    Response: {peer.get_avg_response_time():.3f}s")

# Get most reliable peers
reliable_peers = sorted(
    manager.known_peers.values(),
    key=lambda p: p.get_reliability(),
    reverse=True
)[:10]

print(f"\nTop 10 most reliable peers:")
for peer in reliable_peers:
    print(f"  {peer.url} - {peer.get_reliability():.1f}% reliable")
```

## Geographic Diversity Check

```python
from peer_discovery import PeerDiversityManager

# Create list of peer info objects
peers = [
    PeerInfo("http://192.168.1.100:5000"),
    PeerInfo("http://192.168.1.101:5000"),
    PeerInfo("http://10.0.0.1:5000"),
    PeerInfo("http://172.16.0.1:5000"),
]

# Calculate diversity
diversity = PeerDiversityManager.calculate_diversity_score(peers)
print(f"Diversity score: {diversity:.1f}/100")

# Select diverse subset
diverse_peers = PeerDiversityManager.select_diverse_peers(
    peers,
    count=2,
    prefer_quality=True
)

print(f"\nSelected diverse peers:")
for peer in diverse_peers:
    print(f"  {peer.url} (IP: {peer.ip_address})")
```

## Testing Peer Discovery

```python
# Run built-in tests
from test_peer_discovery import run_tests

success = run_tests()
if success:
    print("All tests passed!")
else:
    print("Some tests failed!")
```

## API Usage Examples

Once integrated into the node, use these API calls:

### Get Peer List
```bash
curl http://localhost:5000/peers/list
```

Response:
```json
{
  "success": true,
  "count": 25,
  "peers": [
    "http://peer1.xaicoin.network:5000",
    "http://peer2.xaicoin.network:5000"
  ]
}
```

### Announce Your Node
```bash
curl -X POST http://peer-node:5000/peers/announce \
  -H "Content-Type: application/json" \
  -d '{"peer_url": "http://your-ip:5000"}'
```

### Get Discovery Stats
```bash
curl http://localhost:5000/peers/discovery/stats
```

Response:
```json
{
  "success": true,
  "stats": {
    "network_type": "mainnet",
    "connected_peers": 25,
    "known_peers": 50,
    "max_peers": 50,
    "diversity_score": 78.5,
    "avg_peer_quality": 82.3,
    "total_discoveries": 150,
    "total_connections": 75,
    "total_failed_connections": 25,
    "is_running": true
  }
}
```

### Get Detailed Peer Info
```bash
curl http://localhost:5000/peers/discovery/details
```

Response:
```json
{
  "success": true,
  "count": 50,
  "peers": [
    {
      "url": "http://peer1.xaicoin.network:5000",
      "ip_address": "192.168.1.100",
      "last_seen": 1699999999.123,
      "quality_score": 95,
      "reliability": 98.5,
      "avg_response_time": 0.125,
      "uptime_hours": 72.5,
      "success_count": 1500,
      "failure_count": 23,
      "is_bootstrap": true,
      "version": "2.0.0",
      "chain_height": 12345
    }
  ]
}
```

## Command Line Usage

Run peer discovery standalone:

```bash
# Basic test
python peer_discovery.py

# With custom parameters (edit __main__ section)
python peer_discovery.py
```

Run tests:

```bash
# Run all tests
python test_peer_discovery.py

# Run specific test
python -m unittest test_peer_discovery.TestPeerInfo.test_peer_creation

# Verbose output
python test_peer_discovery.py -v
```

## Production Deployment

For production, update bootstrap nodes in `peer_discovery.py`:

```python
class BootstrapNodes:
    MAINNET_SEEDS = [
        "http://seed1.xaicoin.network:5000",
        "http://seed2.xaicoin.network:5000",
        "http://seed3.xaicoin.network:5000",
        "http://seed4.xaicoin.network:5000",
        "http://seed5.xaicoin.network:5000",
    ]
```

Replace with your actual production seed node addresses.

## Troubleshooting

### No Peers Discovered

```python
# Check if bootstrap nodes are reachable
from peer_discovery import PeerDiscoveryProtocol, BootstrapNodes

seeds = BootstrapNodes.get_seeds("mainnet")
for seed in seeds:
    is_alive, response_time = PeerDiscoveryProtocol.ping_peer(seed)
    print(f"{seed}: {'✓ Alive' if is_alive else '✗ Dead'} ({response_time:.3f}s)")
```

### Low Diversity

```python
# Check peer IP distribution
from peer_discovery import PeerDiversityManager

manager = PeerDiscoveryManager(network_type="mainnet", my_url="http://localhost:5000")
manager.start()

# Wait a bit
import time
time.sleep(60)

# Check diversity
peers = list(manager.known_peers.values())
diversity = PeerDiversityManager.calculate_diversity_score(peers)

print(f"Diversity: {diversity:.1f}/100")

# Show IP distribution
from collections import Counter
ip_prefixes = [
    PeerDiversityManager.get_ip_prefix(peer.ip_address, 16)
    for peer in peers
]
distribution = Counter(ip_prefixes)

print("\nIP Distribution (/16):")
for prefix, count in distribution.most_common():
    print(f"  {prefix}.x.x: {count} peers")
```

### Performance Issues

```python
# Check peer response times
manager = PeerDiscoveryManager(network_type="mainnet", my_url="http://localhost:5000")
manager.start()

import time
time.sleep(60)

# Show slowest peers
peers = list(manager.known_peers.values())
peers_with_times = [p for p in peers if p.response_times]
peers_with_times.sort(key=lambda p: p.get_avg_response_time(), reverse=True)

print("Slowest peers:")
for peer in peers_with_times[:10]:
    print(f"  {peer.url}: {peer.get_avg_response_time():.3f}s avg")
```
