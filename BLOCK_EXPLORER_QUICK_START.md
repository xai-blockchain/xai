# XAI Block Explorer - Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies

```bash
pip install flask flask-cors flask-sock requests
```

### 2. Start Blockchain Node

```bash
export XAI_NETWORK=mainnet
python src/xai/core/node.py
```

### 3. Start Explorer

```bash
export XAI_NODE_URL=http://localhost:8545
export EXPLORER_PORT=8082
python src/xai/explorer_backend.py
```

### 4. Test Health

```bash
curl http://localhost:8082/health
```

Expected response:
```json
{
  "status": "healthy",
  "explorer": "running",
  "node": "connected",
  "timestamp": 1234567890.0
}
```

---

## Core API Endpoints

### Analytics

```bash
# Network hashrate
curl http://localhost:8082/api/analytics/hashrate

# Transaction volume (24h/7d/30d)
curl http://localhost:8082/api/analytics/tx-volume?period=24h

# Active addresses
curl http://localhost:8082/api/analytics/active-addresses

# Average block time
curl http://localhost:8082/api/analytics/block-time

# Mempool size
curl http://localhost:8082/api/analytics/mempool

# Network difficulty
curl http://localhost:8082/api/analytics/difficulty

# All analytics at once
curl http://localhost:8082/api/analytics/dashboard
```

### Search

```bash
# Search (auto-detects type)
curl -X POST http://localhost:8082/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"1000"}'

# Autocomplete suggestions
curl "http://localhost:8082/api/search/autocomplete?prefix=AIX&limit=10"

# Recent searches
curl http://localhost:8082/api/search/recent?limit=10
```

### Rich List

```bash
# Top address holders
curl "http://localhost:8082/api/richlist?limit=100"

# Force refresh
curl -X POST "http://localhost:8082/api/richlist/refresh?limit=100"
```

### Address Features

```bash
# Get address label
curl http://localhost:8082/api/address/XAI.../label

# Set address label
curl -X POST http://localhost:8082/api/address/XAI.../label \
  -H "Content-Type: application/json" \
  -d '{
    "label":"Exchange",
    "category":"exchange",
    "description":"Main wallet"
  }'
```

### Export

```bash
# Export transactions as CSV
curl http://localhost:8082/api/export/transactions/XAI... > transactions.csv
```

---

## WebSocket Real-Time Updates

### JavaScript

```javascript
const ws = new WebSocket("ws://localhost:8082/api/ws/updates");

ws.onopen = () => {
  console.log("Connected");
  // Heartbeat
  setInterval(() => ws.send('ping'), 30000);
};

ws.onmessage = (e) => {
  if (e.data !== 'pong') {
    console.log("Update:", JSON.parse(e.data));
  }
};
```

### Python

```python
import websocket
import json
import threading
import time

def on_message(ws, msg):
    if msg != 'pong':
        print(json.loads(msg))

ws = websocket.WebSocketApp(
    "ws://localhost:8082/api/ws/updates",
    on_message=on_message
)

# Heartbeat
def heartbeat():
    while True:
        time.sleep(30)
        ws.send('ping')

threading.Thread(target=heartbeat, daemon=True).start()
ws.run_forever()
```

---

## Environment Variables

```bash
# Node connection
export XAI_NODE_URL=http://localhost:8545

# Explorer port
export EXPLORER_PORT=8082

# Database (persistent recommended for production)
export EXPLORER_DB_PATH=/data/explorer.db

# Debug mode (disable in production)
export FLASK_DEBUG=false
```

---

## Common Operations

### Search by Type

```bash
# Block height (numeric)
curl -X POST http://localhost:8082/api/search \
  -d '{"query":"1000"}'

# Address (XAI or TXAI prefix)
curl -X POST http://localhost:8082/api/search \
  -d '{"query":"XAI1234567890abcdef"}'

# Transaction ID (64-char hex)
curl -X POST http://localhost:8082/api/search \
  -d '{"query":"abc123...def789"}'
```

### Label Management

```bash
# Add label for exchange
curl -X POST http://localhost:8082/api/address/XAI.../label \
  -d '{
    "label":"Binance",
    "category":"exchange",
    "description":"Binance exchange wallet"
  }'

# Add label for pool
curl -X POST http://localhost:8082/api/address/TXAI.../label \
  -d '{
    "label":"Mining Pool",
    "category":"pool",
    "description":"Official mining pool"
  }'

# Add label for whale
curl -X POST http://localhost:8082/api/address/XAI.../label \
  -d '{
    "label":"Large Holder",
    "category":"whale",
    "description":"Major address holder"
  }'
```

### Get Metrics History

```bash
# Hashrate history (last 24 hours)
curl "http://localhost:8082/api/metrics/hashrate?hours=24"

# Active addresses history
curl "http://localhost:8082/api/metrics/active_addresses?hours=24"

# Transaction volume history
curl "http://localhost:8082/api/metrics/tx_volume_24h?hours=24"
```

---

## Docker Quick Start

```bash
# Build image
docker build -t xai-explorer:latest .

# Run container
docker run -d \
  --name explorer \
  -p 8082:8082 \
  -e XAI_NODE_URL=http://node:8545 \
  -v explorer_data:/data \
  xai-explorer:latest

# Or use docker-compose
docker-compose up -d
```

---

## Troubleshooting

### Explorer won't start
```bash
# Check if port is in use
lsof -i :8082

# Try different port
export EXPLORER_PORT=8083
python src/xai/explorer_backend.py
```

### Can't connect to node
```bash
# Verify node is running
curl http://localhost:8545/health

# Check node URL
echo $XAI_NODE_URL

# Try different node URL
export XAI_NODE_URL=http://127.0.0.1:8545
```

### WebSocket connection fails
```bash
# Check firewall
netstat -an | grep 8082

# Enable debug logging
export FLASK_DEBUG=true
```

---

## Performance Tips

1. **Use persistent database** for production:
   ```bash
   export EXPLORER_DB_PATH=/data/explorer.db
   ```

2. **Enable caching** for frequently accessed data (automatic)

3. **Use WebSockets** instead of polling for real-time data

4. **Monitor health regularly**:
   ```bash
   watch -n 5 'curl -s http://localhost:8082/health | jq .'
   ```

5. **Scale horizontally** with load balancer (nginx)

---

## Python Client Example

```python
import requests
import json

class ExplorerClient:
    def __init__(self, base_url="http://localhost:8082"):
        self.base_url = base_url

    def search(self, query):
        return requests.post(
            f"{self.base_url}/api/search",
            json={"query": query}
        ).json()

    def get_hashrate(self):
        return requests.get(
            f"{self.base_url}/api/analytics/hashrate"
        ).json()

    def get_rich_list(self, limit=100):
        return requests.get(
            f"{self.base_url}/api/richlist?limit={limit}"
        ).json()

    def export_csv(self, address):
        return requests.get(
            f"{self.base_url}/api/export/transactions/{address}"
        ).text

# Usage
client = ExplorerClient()

# Search
result = client.search("1000")
print(f"Found: {result['found']}")

# Analytics
hashrate = client.get_hashrate()
print(f"Hashrate: {hashrate['hashrate']}")

# Rich list
holders = client.get_rich_list(10)
print(f"Top holder: {holders['richlist'][0]['address']}")

# Export
csv = client.export_csv("XAI...")
with open("transactions.csv", "w") as f:
    f.write(csv)
```

---

## Next Steps

1. **Review full API documentation**: See `BLOCK_EXPLORER_API.md`
2. **Optimize for production**: See `BLOCK_EXPLORER_PERFORMANCE.md`
3. **Understand implementation details**: See `BLOCK_EXPLORER_IMPLEMENTATION.md`
4. **Deploy with Docker**: Use provided Dockerfile and docker-compose
5. **Integrate with frontend**: Use provided JavaScript client examples
6. **Set up monitoring**: Configure alerts and metrics collection

---

## Support

- **API Docs:** `BLOCK_EXPLORER_API.md`
- **Performance:** `BLOCK_EXPLORER_PERFORMANCE.md`
- **Implementation:** `BLOCK_EXPLORER_IMPLEMENTATION.md`
- **Original Guide:** `src/xai/BLOCK_EXPLORER_README.md`

---

**Last Updated:** 2025-11-19 (UTC)
