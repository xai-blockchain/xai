# XAI Block Explorer - Implementation Guide

## Overview

This guide provides step-by-step instructions for integrating and deploying the professional-grade XAI Block Explorer with all advanced features.

---

## Quick Reference

| File | Purpose |
|------|---------|
| `src/xai/explorer_backend.py` | Main explorer backend with all features |
| `BLOCK_EXPLORER_API.md` | Complete API documentation |
| `BLOCK_EXPLORER_PERFORMANCE.md` | Performance optimization guide |
| `BLOCK_EXPLORER_README.md` | Original local testing guide (still valid) |

---

## Installation

### Prerequisites

```bash
# Python 3.9+
python --version

# Pip package manager
pip --version
```

### Install Dependencies

```bash
# Install WebSocket support
pip install flask-sock

# Or update all dependencies
pip install -r requirements.txt
```

### Verify Installation

```python
python -c "from flask_sock import Sock; print('Flask-Sock installed')"
```

---

## Configuration

### Environment Variables

Create a `.env` file or export environment variables:

```bash
# Node connection
export XAI_NODE_URL=http://localhost:8545

# Explorer port
export EXPLORER_PORT=8082

# Database location (use persistent path for production)
export EXPLORER_DB_PATH=/data/explorer.db

# Optional: Flask debug mode (disable in production)
export FLASK_DEBUG=false

# Optional: CORS allowed origins
export EXPLORER_CORS_ORIGINS=http://localhost:3000,https://example.com
```

### Basic Startup

```bash
# Start blockchain node first
python src/xai/core/node.py &

# In another terminal, start explorer
python src/xai/explorer_backend.py
```

### Docker Deployment

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src ./src
COPY config ./config

# Create data directory
RUN mkdir -p /data

# Environment
ENV XAI_NODE_URL=http://node:8545
ENV EXPLORER_PORT=8082
ENV EXPLORER_DB_PATH=/data/explorer.db
ENV FLASK_DEBUG=false

EXPOSE 8082
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8082/health || exit 1

CMD ["python", "src/xai/explorer_backend.py"]
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  node:
    build:
      context: .
      dockerfile: Dockerfile.node
    ports:
      - "8545:8545"
    environment:
      - XAI_NETWORK=mainnet
    volumes:
      - node_data:/data
    networks:
      - xai

  explorer:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8082:8082"
    environment:
      - XAI_NODE_URL=http://node:8545
      - EXPLORER_DB_PATH=/data/explorer.db
    volumes:
      - explorer_data:/data
    depends_on:
      - node
    networks:
      - xai

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - explorer
    networks:
      - xai

volumes:
  node_data:
  explorer_data:

networks:
  xai:
    driver: bridge
```

**Build and run:**
```bash
docker-compose up -d
```

---

## Feature Integration

### 1. Analytics Dashboard

The analytics engine automatically collects metrics:

**Available Metrics:**
- Network hashrate
- Transaction volume (24h, 7d, 30d)
- Active addresses count
- Average block time
- Mempool size
- Network difficulty

**Usage:**
```python
from xai.explorer_backend import analytics

# Get all analytics at once
dashboard_data = analytics.get_network_hashrate()
dashboard_data.update(analytics.get_transaction_volume())
dashboard_data.update(analytics.get_active_addresses())
```

### 2. Advanced Search

Search supports automatic type detection:

**Search Types:**
- Block height (numeric)
- Block hash (64-char hex)
- Transaction ID (64-char hex)
- Address (starts with XAI or TXAI)

**Implementation:**
```python
from xai.explorer_backend import search_engine

# Search automatically detects type
result = search_engine.search("XAI1234...", user_id="user123")

# Get search suggestions
suggestions = search_engine.get_autocomplete_suggestions("AIX", limit=10)

# View recent searches
recent = search_engine.get_recent_searches(limit=20)
```

### 3. Rich List Management

Track and display top address holders:

```python
from xai.explorer_backend import rich_list, db

# Get top 100 holders
top_holders = rich_list.get_rich_list(limit=100)

# Add address labels
from xai.explorer_backend import AddressLabel

label = AddressLabel(
    address="XAI...",
    label="Binance Exchange",
    category="exchange",
    description="Official Binance wallet"
)
db.add_address_label(label)
```

### 4. Address Labeling System

Create and manage address metadata:

```python
# API endpoint to add label
curl -X POST http://localhost:8082/api/address/XAI.../label \
  -H "Content-Type: application/json" \
  -d '{
    "label": "Main Pool",
    "category": "pool",
    "description": "Mining pool wallet"
  }'

# Retrieve label
curl http://localhost:8082/api/address/XAI.../label
```

### 5. CSV Export

Enable transaction history export:

```python
from xai.explorer_backend import export_manager

# Export address transactions
csv_data = export_manager.export_transactions_csv("XAI...")

# Save to file
with open(f"transactions_{address}.csv", "w") as f:
    f.write(csv_data)
```

### 6. WebSocket Real-Time Updates

Implement real-time blockchain monitoring:

**JavaScript Client:**
```javascript
const ws = new WebSocket("ws://localhost:8082/api/ws/updates");

ws.onopen = () => {
  console.log("Connected to explorer");

  // Send heartbeat every 30 seconds
  setInterval(() => ws.send('ping'), 30000);
};

ws.onmessage = (event) => {
  if (event.data === 'pong') {
    return;  // Heartbeat response
  }

  const update = JSON.parse(event.data);
  console.log("Update received:", update);

  // Handle updates by type
  switch (update.type) {
    case 'new_block':
      console.log("New block mined:", update.data);
      break;
    case 'new_transaction':
      console.log("New transaction:", update.data);
      break;
    case 'difficulty_change':
      console.log("Difficulty updated:", update.data);
      break;
  }
};

ws.onerror = (error) => {
  console.error("WebSocket error:", error);
};

ws.onclose = () => {
  console.log("Disconnected from explorer");
};
```

**Python Client:**
```python
import websocket
import json
import threading
import time

def on_message(ws, message):
    if message == 'pong':
        return
    update = json.loads(message)
    print(f"Update: {update['type']}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Connection closed")

def on_open(ws):
    # Send heartbeat
    def run():
        while True:
            time.sleep(30)
            ws.send('ping')
    threading.Thread(target=run, daemon=True).start()

ws = websocket.WebSocketApp(
    "ws://localhost:8082/api/ws/updates",
    on_message=on_message,
    on_error=on_error,
    on_close=on_close,
    on_open=on_open
)

ws.run_forever()
```

### 7. Database Indexing

The explorer automatically creates optimized indexes:

**Indexes Created:**
- `idx_search_query` - Fast search lookups
- `idx_search_timestamp` - Time-range queries
- `idx_metric_type` - Analytics filtering
- `idx_metric_timestamp` - Historical data
- `idx_address_label` - Label searches
- `idx_analytics_type_time` - Compound queries

**Custom Index (if needed):**
```python
from xai.explorer_backend import db

cursor = db.conn.cursor()
cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_custom ON analytics(metric_type, timestamp DESC)
""")
db.conn.commit()
```

### 8. Caching System

Multi-layer caching for performance:

**Configuration:**
```python
# Environment-based cache settings
CACHE_CONFIG = {
    "hashrate": 300,        # 5 minutes
    "analytics": 600,       # 10 minutes
    "rich_list": 1800,      # 30 minutes
    "searches": 3600,       # 1 hour
}
```

**Manual Cache Control:**
```python
from xai.explorer_backend import db

# Set custom cache
db.set_cache("custom_key", '{"data": "value"}', ttl=600)

# Get cached value
cached = db.get_cache("custom_key")

# Clear specific cache
db.set_cache("rich_list_100", "", ttl=0)  # Expire immediately
```

---

## API Endpoint Testing

### Using cURL

```bash
# Health check
curl http://localhost:8082/health

# Get analytics dashboard
curl http://localhost:8082/api/analytics/dashboard

# Search
curl -X POST http://localhost:8082/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"1000"}'

# Rich list
curl "http://localhost:8082/api/richlist?limit=10"

# Autocomplete
curl "http://localhost:8082/api/search/autocomplete?prefix=AIX&limit=5"
```

### Using Python

```python
import requests
import json

BASE_URL = "http://localhost:8082"

# Health check
response = requests.get(f"{BASE_URL}/health")
print(response.json())

# Analytics
response = requests.get(f"{BASE_URL}/api/analytics/hashrate")
print(f"Hashrate: {response.json()['hashrate']}")

# Search
response = requests.post(
    f"{BASE_URL}/api/search",
    json={"query": "XAI..."}
)
print(response.json())
```

---

## Monitoring & Maintenance

### Health Checks

```bash
# Check explorer health
curl http://localhost:8082/health

# Check node connection
curl http://localhost:8082/health | jq .node
```

### Database Maintenance

```python
from xai.explorer_backend import db

# Optimize database
db._init_database()  # Creates/updates schema

# Manual vacuum (clean up space)
cursor = db.conn.cursor()
cursor.execute("VACUUM")
db.conn.commit()

# Update statistics
cursor.execute("ANALYZE")
db.conn.commit()
```

### Logs

Enable debug logging:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Metrics Export

```bash
# Get performance metrics
curl http://localhost:8082/api/metrics/hashrate?hours=24

# Get search analytics
curl http://localhost:8082/api/metrics/searches?hours=24
```

---

## Common Issues & Solutions

### Issue: "Node unavailable" Error

**Cause:** Explorer can't connect to blockchain node

**Solution:**
```bash
# 1. Check node is running
ps aux | grep "node.py"

# 2. Verify node URL
echo $XAI_NODE_URL

# 3. Test connection
curl http://localhost:8545/stats

# 4. Check firewall
netstat -an | grep 8545
```

### Issue: Database Lock Timeout

**Cause:** Too many concurrent database connections

**Solution:**
```python
# Increase timeout in database initialization
db.conn.execute("PRAGMA busy_timeout=10000")  # 10 seconds

# Or reduce concurrent access
import queue
db_queue = queue.Queue(maxsize=5)
```

### Issue: High Memory Usage

**Cause:** Cache growing too large

**Solution:**
```python
# Reduce cache sizes
export XAI_CACHE_SIZE=256  # Instead of default

# Or manually clear cache
db.set_cache("rich_list_*", "", ttl=0)
```

### Issue: Slow Search Results

**Cause:** Missing indexes or network latency

**Solution:**
```bash
# Verify indexes exist
sqlite3 explorer.db "SELECT name FROM sqlite_master WHERE type='index';"

# Check network latency to node
ping localhost:8545

# Enable query caching
export XAI_CACHE_TTL=600  # Increase TTL
```

---

## Integration with Frontend

### Example React Dashboard

```jsx
import React, { useEffect, useState } from 'react';
import axios from 'axios';

const ExplorerDashboard = () => {
  const [analytics, setAnalytics] = useState(null);
  const [richList, setRichList] = useState([]);

  useEffect(() => {
    // Fetch analytics
    axios.get('http://localhost:8082/api/analytics/dashboard')
      .then(res => setAnalytics(res.data))
      .catch(err => console.error(err));

    // Fetch rich list
    axios.get('http://localhost:8082/api/richlist?limit=10')
      .then(res => setRichList(res.data.richlist))
      .catch(err => console.error(err));

    // Set up WebSocket
    const ws = new WebSocket('ws://localhost:8082/api/ws/updates');
    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);
      if (update.type === 'block_mined') {
        // Refresh analytics
        axios.get('http://localhost:8082/api/analytics/dashboard')
          .then(res => setAnalytics(res.data));
      }
    };

    return () => ws.close();
  }, []);

  if (!analytics) return <div>Loading...</div>;

  return (
    <div className="dashboard">
      <h1>XAI Block Explorer</h1>

      <div className="analytics">
        <div className="metric">
          <h3>Network Hashrate</h3>
          <p>{(analytics.hashrate.hashrate / 1e6).toFixed(2)} MH/s</p>
        </div>

        <div className="metric">
          <h3>Active Addresses</h3>
          <p>{analytics.active_addresses.total_unique_addresses}</p>
        </div>

        <div className="metric">
          <h3>Block Time</h3>
          <p>{analytics.average_block_time.average_block_time_seconds.toFixed(2)}s</p>
        </div>
      </div>

      <div className="rich-list">
        <h2>Top Holders</h2>
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Address</th>
              <th>Balance</th>
              <th>% Supply</th>
            </tr>
          </thead>
          <tbody>
            {richList.map(addr => (
              <tr key={addr.address}>
                <td>{addr.rank}</td>
                <td>{addr.address.substring(0, 10)}...</td>
                <td>{addr.balance.toFixed(2)}</td>
                <td>{addr.percentage_of_supply.toFixed(2)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ExplorerDashboard;
```

---

## Performance Tuning

### Database Optimization

```python
# Enable WAL mode for concurrent access
db.conn.execute("PRAGMA journal_mode=WAL")

# Increase cache size
db.conn.execute("PRAGMA cache_size=-64000")  # 64MB

# Optimize for SSD
db.conn.execute("PRAGMA temp_store=MEMORY")
```

### Flask Optimization

```python
# Use production WSGI server
pip install gunicorn

# Run with multiple workers
gunicorn -w 4 -b 0.0.0.0:8082 src.xai.explorer_backend:app
```

### Connection Pooling

```bash
# Use nginx upstream with connection pooling
upstream explorer {
    keepalive 32;
    server explorer:8082 max_fails=3 fail_timeout=30s;
}
```

---

## Deployment Checklist

- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Set environment variables (node URL, port, database path)
- [ ] Test node connection: `curl http://localhost:8545/stats`
- [ ] Start explorer: `python src/xai/explorer_backend.py`
- [ ] Verify health: `curl http://localhost:8082/health`
- [ ] Test API endpoints with cURL
- [ ] Configure CORS if needed
- [ ] Set up monitoring and alerting
- [ ] Enable persistent database (`EXPLORER_DB_PATH=/data/explorer.db`)
- [ ] Configure reverse proxy (nginx)
- [ ] Set up SSL/TLS certificates
- [ ] Enable log rotation
- [ ] Configure rate limiting
- [ ] Set up automated backups
- [ ] Test WebSocket connections
- [ ] Load test the deployment
- [ ] Configure production WSGI server (gunicorn)

---

## Next Steps

1. **Review API Documentation:** See `BLOCK_EXPLORER_API.md`
2. **Performance Tuning:** See `BLOCK_EXPLORER_PERFORMANCE.md`
3. **Deployment:** Use provided Docker files
4. **Integration:** Connect frontend or external tools
5. **Monitoring:** Set up alerts and dashboards
6. **Maintenance:** Regular database optimization

---

**Last Updated:** 2025-11-19 (UTC)
