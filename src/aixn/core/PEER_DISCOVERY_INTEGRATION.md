# Peer Discovery Integration Guide

## Overview

The peer discovery system automatically bootstraps network connectivity and maintains a healthy peer network. This guide shows how to integrate it into the XAI blockchain node.

## Integration Steps

### 1. Import the Module

Add to the top of `node.py`:

```python
from peer_discovery import PeerDiscoveryManager, setup_peer_discovery_api
```

### 2. Initialize in BlockchainNode.__init__()

Add after the P2P security initialization (around line 62):

```python
# Initialize P2P security
from p2p_security import P2PSecurityManager
self.p2p_security = P2PSecurityManager()

# Initialize peer discovery (NEW)
from peer_discovery import PeerDiscoveryManager, setup_peer_discovery_api
self.peer_discovery_manager = PeerDiscoveryManager(
    network_type=Config.NETWORK_TYPE.value if hasattr(Config.NETWORK_TYPE, 'value') else 'mainnet',
    my_url=f"http://{self.host}:{self.port}",
    max_peers=50,
    discovery_interval=300  # 5 minutes
)
print("✅ Peer Discovery initialized")
```

### 3. Setup API Routes

Add in the `setup_routes()` method, after the existing routes are defined:

```python
# Setup peer discovery API endpoints (NEW)
setup_peer_discovery_api(self.app, self)
```

### 4. Start Discovery on Node Startup

Modify the `run()` method to start peer discovery. Add before starting auto-mining (around line 2335):

```python
# Start peer discovery (NEW)
if hasattr(self, 'peer_discovery_manager'):
    self.peer_discovery_manager.start()
    print("✅ Peer discovery started")
```

### 5. Enhanced add_peer() Method

Update the `add_peer()` method to use the discovery manager (around line 2224):

```python
def add_peer(self, peer_url: str):
    """Add peer node with security checks"""
    # Extract IP from URL (simplified)
    import re
    ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', peer_url)
    ip_address = ip_match.group(1) if ip_match else "unknown"

    # Security check
    can_accept, error = self.p2p_security.can_accept_peer(peer_url, ip_address)
    if not can_accept:
        print(f"Peer rejected: {peer_url} - {error}")
        return False

    if peer_url not in self.peers:
        # Check max peers limit
        from p2p_security import P2PSecurityConfig
        if len(self.peers) >= P2PSecurityConfig.MAX_PEERS_TOTAL:
            print(f"Max peers reached ({P2PSecurityConfig.MAX_PEERS_TOTAL})")
            return False

        self.peers.add(peer_url)
        self.p2p_security.track_peer_connection(peer_url, ip_address)

        # Update peer discovery manager (NEW)
        if hasattr(self, 'peer_discovery_manager'):
            self.peer_discovery_manager.connected_peers.add(peer_url)
            self.peer_discovery_manager.update_peer_info(peer_url, success=True)

        print(f"Added peer: {peer_url}")
        self.logger.peer_connected(len(self.peers))

    return True
```

### 6. Track Peer Interactions

Update `broadcast_block()` to track peer quality (around line 2263):

```python
def broadcast_block(self, block):
    """Broadcast new block to all peers"""
    # Record block first seen (for propagation monitoring)
    self.blockchain.consensus_manager.propagation_monitor.record_block_first_seen(block.hash)

    for peer in self.peers:
        try:
            start_time = time.time()
            requests.post(
                f"{peer}/block/receive",
                json=block.to_dict(),
                timeout=2
            )
            response_time = time.time() - start_time

            # Update peer quality (NEW)
            if hasattr(self, 'peer_discovery_manager'):
                self.peer_discovery_manager.update_peer_info(peer, success=True, response_time=response_time)
        except:
            # Update peer failure (NEW)
            if hasattr(self, 'peer_discovery_manager'):
                self.peer_discovery_manager.update_peer_info(peer, success=False)
            pass
```

### 7. Update Stats Endpoint

Enhance the `/stats` endpoint to include peer discovery info (around line 197):

```python
@self.app.route('/stats', methods=['GET'])
def get_stats():
    """Get blockchain statistics"""
    stats = self.blockchain.get_stats()
    stats['miner_address'] = self.miner_address
    stats['peers'] = len(self.peers)
    stats['is_mining'] = self.is_mining
    stats['node_uptime'] = time.time() - self.start_time

    # Add peer discovery stats (NEW)
    if hasattr(self, 'peer_discovery_manager'):
        stats['peer_discovery'] = self.peer_discovery_manager.get_stats()

    return jsonify(stats)
```

## New API Endpoints

The integration adds these new endpoints:

### GET /peers/list
Get list of known peers for peer exchange protocol.

**Response:**
```json
{
  "success": true,
  "count": 25,
  "peers": [
    "http://peer1.xaicoin.network:5000",
    "http://peer2.xaicoin.network:5000",
    ...
  ]
}
```

### POST /peers/announce
Accept peer announcement from other nodes.

**Request:**
```json
{
  "peer_url": "http://newnode.example.com:5000"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Peer added"
}
```

### GET /peers/discovery/stats
Get peer discovery statistics.

**Response:**
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

### GET /peers/discovery/details
Get detailed information about all known peers.

**Response:**
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
    },
    ...
  ]
}
```

## Configuration

You can customize peer discovery behavior by modifying the initialization parameters:

```python
self.peer_discovery_manager = PeerDiscoveryManager(
    network_type='mainnet',  # or 'testnet', 'devnet'
    my_url=f"http://{self.host}:{self.port}",
    max_peers=50,  # Maximum peers to maintain
    discovery_interval=300  # Seconds between discovery rounds (5 minutes)
)
```

## Bootstrap Nodes Configuration

Edit the bootstrap nodes in `peer_discovery.py`:

```python
class BootstrapNodes:
    """Hardcoded bootstrap/seed nodes for network discovery"""

    # Production seed nodes
    MAINNET_SEEDS = [
        "http://seed1.xaicoin.network:5000",
        "http://seed2.xaicoin.network:5000",
        # Add your actual seed nodes here
    ]
```

## Features

### Automatic Network Bootstrap
- Connects to hardcoded seed nodes on startup
- Requests peer lists from seeds
- Announces itself to the network

### Peer Exchange Protocol
- GET /peers/list - Share known peers
- POST /peers/announce - Accept peer announcements
- Automatic peer list exchange every 5 minutes

### Peer Quality Scoring
- Tracks response times
- Monitors success/failure rates
- Calculates reliability percentage
- Auto-disconnects low-quality peers

### Network Diversity
- Prefers geographically diverse peers
- Distributes connections across IP ranges
- Prevents concentration in single subnet
- Eclipse attack resistance

### Dead Peer Removal
- Removes peers inactive for 1+ hour
- Automatic cleanup every 5 minutes
- Maintains healthy peer list

### Background Discovery
- Runs in separate thread
- Periodic discovery every 5 minutes
- Auto-connects to best peers
- Maintains target peer count

## Testing

Test the peer discovery system:

```bash
# Start a node
python node.py --port 5000

# Check peer discovery stats
curl http://localhost:5000/peers/discovery/stats

# View detailed peer info
curl http://localhost:5000/peers/discovery/details

# Check overall stats
curl http://localhost:5000/stats
```

## Troubleshooting

### No peers discovered
- Check if bootstrap nodes are accessible
- Verify network connectivity
- Check firewall settings
- Ensure correct network_type (mainnet/testnet)

### Low diversity score
- Connect to peers in different regions
- Check if too many peers from same subnet
- Add more diverse bootstrap nodes

### Peers disconnecting
- Check peer quality scores
- Verify network stability
- Ensure peers are running compatible versions

## Security Features

The peer discovery integrates with the existing P2P security:

- **Sybil Attack Protection**: Limits connections per IP
- **Eclipse Attack Protection**: Enforces peer diversity
- **Reputation System**: Tracks peer behavior
- **Rate Limiting**: Prevents message flooding
- **Automatic Banning**: Blocks malicious peers

## Performance

The peer discovery system is optimized for performance:

- Background thread for non-blocking operation
- Efficient peer selection algorithms
- Minimal network overhead
- Smart discovery intervals
- Caching of peer information

## Monitoring

Monitor peer discovery health:

```python
# In your monitoring code
stats = node.peer_discovery_manager.get_stats()

if stats['connected_peers'] < 10:
    print("WARNING: Low peer count")

if stats['diversity_score'] < 50:
    print("WARNING: Low peer diversity")

if stats['avg_peer_quality'] < 60:
    print("WARNING: Low peer quality")
```
