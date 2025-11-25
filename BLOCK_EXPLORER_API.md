# XAI Block Explorer - Production API Documentation

## Overview

The XAI Block Explorer is a professional-grade blockchain explorer with advanced analytics, search capabilities, real-time updates, and data export features. This document describes all API endpoints, data formats, and integration patterns.

**Version:** 2.0.0
**Base URL:** `http://localhost:8082`
**Underlying Node API:** `http://localhost:8545`

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Features](#core-features)
3. [Analytics API](#analytics-api)
4. [Search API](#search-api)
5. [Rich List API](#rich-list-api)
6. [Address Labeling](#address-labeling)
7. [Export API](#export-api)
8. [WebSocket Real-Time Updates](#websocket-real-time-updates)
9. [Error Handling](#error-handling)
10. [Performance & Caching](#performance--caching)
11. [Rate Limiting](#rate-limiting)
12. [Authentication](#authentication)
13. [Examples](#examples)

---

## Quick Start

### Installation

```bash
pip install flask flask-cors flask-sock requests
```

### Running the Explorer

```bash
# Start the blockchain node
export XAI_NODE_URL=http://localhost:8545
python src/xai/core/node.py

# In another terminal, start the explorer
export XAI_NODE_URL=http://localhost:8545
export EXPLORER_PORT=8082
python src/xai/explorer_backend.py
```

### Health Check

```bash
curl http://localhost:8082/health
```

### Explorer Information

```bash
curl http://localhost:8082/
```

---

## Core Features

### 1. Advanced Search
- Search by block height, block hash, transaction ID, or address
- Automatic query type detection
- Search history tracking
- Autocomplete suggestions
- Results caching for performance

### 2. Real-Time Analytics
- Network hashrate calculation
- Transaction volume metrics (24h, 7d, 30d)
- Active addresses count
- Average block time
- Mempool visualization
- Network difficulty tracking

### 3. Rich List
- Top 100 address holders
- Address labeling and categorization
- Percentage of total supply
- Cached for 10-minute intervals

### 4. Advanced Features
- Address labeling system (exchange, pool, whale, etc.)
- Transaction CSV export
- WebSocket real-time updates
- Comprehensive metrics history
- Multi-period analytics aggregation

---

## Analytics API

All analytics endpoints return JSON with the following structure:

```json
{
  "data": { ... },
  "timestamp": 1234567890.0,
  "cached": false
}
```

### Get Network Hashrate

Returns estimated network hashrate based on difficulty and block time.

**Endpoint:**
```
GET /api/analytics/hashrate
```

**Response:**
```json
{
  "hashrate": 1234567.89,
  "difficulty": 9876543,
  "block_height": 1000,
  "unit": "hashes/second",
  "timestamp": 1234567890.0
}
```

**Cache:** 5 minutes

---

### Get Transaction Volume

Returns transaction metrics for specified period.

**Endpoint:**
```
GET /api/analytics/tx-volume?period=24h
```

**Parameters:**
- `period` (string): "24h", "7d", or "30d" (default: "24h")

**Response:**
```json
{
  "period": "24h",
  "total_transactions": 15234,
  "unique_transactions": 14982,
  "average_tx_per_block": 12.5,
  "total_fees_collected": 1234.56,
  "timestamp": 1234567890.0
}
```

**Cache:** 5 minutes

---

### Get Active Addresses Count

Returns number of unique addresses that have participated in transactions.

**Endpoint:**
```
GET /api/analytics/active-addresses
```

**Response:**
```json
{
  "total_unique_addresses": 5234,
  "timestamp": 1234567890.0
}
```

**Cache:** 5 minutes

---

### Get Average Block Time

Calculates average time between blocks over the entire blockchain history.

**Endpoint:**
```
GET /api/analytics/block-time
```

**Response:**
```json
{
  "average_block_time_seconds": 62.3,
  "blocks_sampled": 999,
  "timestamp": 1234567890.0
}
```

**Cache:** 5 minutes

---

### Get Mempool Size

Returns pending transaction statistics.

**Endpoint:**
```
GET /api/analytics/mempool
```

**Response:**
```json
{
  "pending_transactions": 42,
  "total_value": 5000.0,
  "total_fees": 50.42,
  "avg_fee": 1.2,
  "timestamp": 1234567890.0
}
```

**Cache:** 5 minutes

---

### Get Network Difficulty

Returns current network difficulty.

**Endpoint:**
```
GET /api/analytics/difficulty
```

**Response:**
```json
{
  "current_difficulty": 9876543,
  "timestamp": 1234567890.0
}
```

---

### Get Analytics Dashboard

Returns all analytics metrics in a single call.

**Endpoint:**
```
GET /api/analytics/dashboard
```

**Response:**
```json
{
  "hashrate": { ... },
  "transaction_volume": { ... },
  "active_addresses": { ... },
  "average_block_time": { ... },
  "mempool": { ... },
  "difficulty": { ... },
  "timestamp": 1234567890.0
}
```

---

## Search API

### Perform Search

Searches for blocks, transactions, or addresses with automatic type detection.

**Endpoint:**
```
POST /api/search
Content-Type: application/json
```

**Request Body:**
```json
{
  "query": "1000",
  "user_id": "user_xyz"
}
```

**Parameters:**
- `query` (string, required): Search term
- `user_id` (string, optional): User identifier for tracking (default: "anonymous")

**Response (Block Height):**
```json
{
  "query": "1000",
  "type": "block_height",
  "found": true,
  "results": {
    "index": 1000,
    "hash": "0x...",
    "previous_hash": "0x...",
    "timestamp": 1234567890,
    "nonce": 12345,
    "difficulty": 9876543,
    "transactions": [ ... ],
    "merkle_root": "0x..."
  },
  "timestamp": 1234567890.0
}
```

**Response (Transaction ID):**
```json
{
  "query": "txid123...",
  "type": "transaction_id",
  "found": true,
  "results": {
    "found": true,
    "block": 1000,
    "confirmations": 5,
    "transaction": {
      "txid": "...",
      "sender": "XAI...",
      "recipient": "TXAI...",
      "amount": 100.0,
      "fee": 1.0,
      "timestamp": 1234567890,
      "type": "transfer"
    }
  },
  "timestamp": 1234567890.0
}
```

**Response (Address):**
```json
{
  "query": "XAI...",
  "type": "address",
  "found": true,
  "results": {
    "address": "XAI...",
    "balance": 5000.0,
    "transactions": [ ... ],
    "transaction_count": 15
  },
  "timestamp": 1234567890.0
}
```

**Error Response:**
```json
{
  "query": "invalid",
  "type": "unknown",
  "found": false,
  "error": "Search query could not be interpreted",
  "timestamp": 1234567890.0
}
```

---

### Get Autocomplete Suggestions

Returns suggested search queries based on recent searches.

**Endpoint:**
```
GET /api/search/autocomplete?prefix=AIX&limit=10
```

**Parameters:**
- `prefix` (string, required): Search prefix
- `limit` (integer, optional): Maximum suggestions (default: 10, max: 50)

**Response:**
```json
{
  "suggestions": [
    "XAI1234567890abcdef...",
    "XAI9876543210fedcba..."
  ]
}
```

---

### Get Recent Searches

Returns list of recently performed searches across all users.

**Endpoint:**
```
GET /api/search/recent?limit=10
```

**Parameters:**
- `limit` (integer, optional): Number of searches (default: 10, max: 100)

**Response:**
```json
{
  "recent": [
    {
      "query": "XAI...",
      "type": "address",
      "timestamp": 1234567890.0
    },
    {
      "query": "1000",
      "type": "block_height",
      "timestamp": 1234567889.5
    }
  ]
}
```

---

## Rich List API

### Get Top Address Holders

Returns list of richest addresses on the blockchain.

**Endpoint:**
```
GET /api/richlist?limit=100
```

**Parameters:**
- `limit` (integer, optional): Number of addresses (default: 100, max: 1000)

**Response:**
```json
{
  "richlist": [
    {
      "rank": 1,
      "address": "XAI...",
      "balance": 1000000.0,
      "label": "Main Pool",
      "category": "pool",
      "percentage_of_supply": 5.25
    },
    {
      "rank": 2,
      "address": "TXAI...",
      "balance": 500000.0,
      "label": "Founder",
      "category": "whale",
      "percentage_of_supply": 2.63
    }
  ]
}
```

---

### Refresh Rich List

Force recalculation of the rich list (requires authentication in production).

**Endpoint:**
```
POST /api/richlist/refresh?limit=100
```

**Parameters:**
- `limit` (integer, optional): Number of addresses

**Response:**
```json
{
  "richlist": [ ... ]
}
```

---

## Address Labeling

The address labeling system allows marking addresses with metadata for easier identification (exchange, pool, whale, contract, etc.).

### Get Address Label

**Endpoint:**
```
GET /api/address/{address}/label
```

**Response (Labeled):**
```json
{
  "address": "XAI...",
  "label": "Binance Pool",
  "category": "exchange",
  "description": "Official exchange wallet"
}
```

**Response (Unlabeled):**
```json
{
  "label": null
}
```

---

### Set Address Label

Sets or updates a label for an address. Requires authentication in production.

**Endpoint:**
```
POST /api/address/{address}/label
Content-Type: application/json
```

**Request Body:**
```json
{
  "label": "Binance Pool",
  "category": "exchange",
  "description": "Official exchange wallet"
}
```

**Parameters:**
- `label` (string, required): Human-readable label
- `category` (string, optional): Category type (exchange, pool, whale, contract, burn, other)
- `description` (string, optional): Additional description

**Response:**
```json
{
  "success": true,
  "label": {
    "address": "XAI...",
    "label": "Binance Pool",
    "category": "exchange",
    "description": "Official exchange wallet",
    "created_at": 1234567890.0
  }
}
```

---

## Export API

### Export Address Transactions as CSV

Exports all transactions for an address in CSV format.

**Endpoint:**
```
GET /api/export/transactions/{address}
```

**Response:**
```
Content-Type: text/csv
Content-Disposition: attachment; filename=transactions_XAI....csv

txid,timestamp,from,to,amount,fee,type
abc123...,2024-01-15T10:30:45,XAI...,TXAI...,100.0,1.0,transfer
def456...,2024-01-15T10:25:30,TXAI...,XAI...,50.0,0.5,transfer
```

---

## WebSocket Real-Time Updates

The WebSocket endpoint provides real-time blockchain updates via persistent connections.

### Connection

**Endpoint:**
```
ws://localhost:8082/api/ws/updates
```

### Client Behavior

1. Connect to the WebSocket endpoint
2. Send `ping` messages periodically to keep connection alive
3. Receive JSON updates with new blockchain data

### Heartbeat

Client should send heartbeat every 30 seconds:

```javascript
setInterval(() => {
  ws.send('ping');
}, 30000);
```

### Server Response

On successful heartbeat:
```
pong
```

### Update Messages

Format of data updates from server:

```json
{
  "type": "block_mined",
  "data": {
    "index": 1001,
    "hash": "0x...",
    "timestamp": 1234567890
  },
  "timestamp": 1234567890.0
}
```

### Update Types

- `new_block`: New block mined
- `new_transaction`: New transaction in mempool
- `difficulty_change`: Network difficulty updated
- `analytics_update`: Analytics metrics updated

---

## Error Handling

All error responses follow this format:

```json
{
  "error": "Description of what went wrong",
  "timestamp": 1234567890.0
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK - Request successful |
| 400 | Bad Request - Invalid parameters |
| 404 | Not Found - Resource doesn't exist |
| 500 | Internal Server Error - Server problem |
| 503 | Service Unavailable - Node unavailable |

### Common Errors

**Invalid query:**
```json
{
  "error": "Query required"
}
```

**Node unavailable:**
```json
{
  "error": "Unable to fetch stats"
}
```

**Search not found:**
```json
{
  "found": false,
  "error": "Item not found in blockchain"
}
```

---

## Performance & Caching

The explorer implements a multi-layer caching strategy for optimal performance:

### Cache Layers

1. **SQLite Database Cache** (TTL: 300 seconds)
   - Recent searches
   - Analytics metrics
   - Address labels

2. **In-Memory HTTP Response Cache**
   - Dashboard data
   - Top addresses
   - Network statistics

3. **Historical Metrics**
   - Stored in SQLite for trend analysis
   - Accessible via `/api/metrics/<type>?hours=24`

### Cache Management

- Automatic TTL expiration
- Manual refresh available for rich list
- Efficient query indexing
- Concurrent access management via thread locks

### Performance Tips

1. Use the dashboard endpoint to get all analytics in one request
2. Cache WebSocket connections for real-time updates
3. Leverage autocomplete to reduce failed searches
4. Use `?limit=10` for rich list to reduce data transfer
5. Monitor cache hit rates via browser DevTools

---

## Rate Limiting

While the explorer doesn't enforce strict rate limiting, following these guidelines ensures good performance for all users:

**Recommended Limits:**
- Analytics endpoints: 1 request per 5 seconds
- Search endpoints: 1 request per second
- Rich list: 1 request per minute
- WebSocket connections: 1 per client

**Exceeding these limits** may result in temporary degraded performance due to node load.

---

## Authentication

The explorer uses optional authentication. In production:

1. **Admin endpoints** (label management) require API key
2. **Search history** is anonymized by default
3. **User tracking** is opt-in via `user_id` parameter

### Setting Authentication (Production)

Add environment variable:
```bash
export EXPLORER_API_KEY=your_secret_key
```

Then include in requests:
```bash
curl -H "X-API-Key: your_secret_key" ...
```

---

## Examples

### Python Client

```python
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8082"

class ExplorerClient:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()

    def search(self, query):
        """Search for block, transaction, or address"""
        response = self.session.post(
            f"{self.base_url}/api/search",
            json={"query": query}
        )
        return response.json()

    def get_analytics(self):
        """Get all analytics"""
        response = self.session.get(f"{self.base_url}/api/analytics/dashboard")
        return response.json()

    def get_rich_list(self, limit=100):
        """Get top address holders"""
        response = self.session.get(
            f"{self.base_url}/api/richlist",
            params={"limit": limit}
        )
        return response.json()

    def export_transactions(self, address):
        """Export address transactions"""
        response = self.session.get(
            f"{self.base_url}/api/export/transactions/{address}"
        )
        return response.text

# Usage
client = ExplorerClient()

# Search
result = client.search("1000")
print(f"Found block: {result['found']}")

# Analytics
analytics = client.get_analytics()
print(f"Network hashrate: {analytics['hashrate']['hashrate']}")

# Rich list
rich_list = client.get_rich_list(10)
print(f"Top holder: {rich_list['richlist'][0]['address']}")

# Export
csv = client.export_transactions("XAI...")
print(csv)
```

### JavaScript Client

```javascript
const BASE_URL = "http://localhost:8082";

class ExplorerClient {
  async search(query) {
    const response = await fetch(`${BASE_URL}/api/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query })
    });
    return response.json();
  }

  async getAnalytics() {
    const response = await fetch(`${BASE_URL}/api/analytics/dashboard`);
    return response.json();
  }

  async getRichList(limit = 100) {
    const response = await fetch(
      `${BASE_URL}/api/richlist?limit=${limit}`
    );
    return response.json();
  }

  connectWebSocket(onUpdate) {
    const ws = new WebSocket(`ws://localhost:8082/api/ws/updates`);

    ws.onopen = () => {
      // Send heartbeat
      setInterval(() => ws.send('ping'), 30000);
    };

    ws.onmessage = (event) => {
      if (event.data !== 'pong') {
        const update = JSON.parse(event.data);
        onUpdate(update);
      }
    };

    return ws;
  }
}

// Usage
const client = new ExplorerClient();

// Search
client.search("1000").then(result => {
  console.log("Block found:", result.found);
});

// Analytics
client.getAnalytics().then(analytics => {
  console.log("Hashrate:", analytics.hashrate.hashrate);
});

// Real-time updates
const ws = client.connectWebSocket((update) => {
  console.log("Update:", update);
});
```

### cURL Examples

```bash
# Get hashrate
curl http://localhost:8082/api/analytics/hashrate

# Search for address
curl -X POST http://localhost:8082/api/search \
  -H "Content-Type: application/json" \
  -d '{"query":"XAI..."}'

# Get rich list
curl "http://localhost:8082/api/richlist?limit=10"

# Export transactions
curl http://localhost:8082/api/export/transactions/XAI... > transactions.csv

# Get search autocomplete
curl "http://localhost:8082/api/search/autocomplete?prefix=AIX&limit=5"
```

---

## Database Schema

The explorer uses SQLite with optimized indexing:

### Tables

**search_history**
- `id`: Primary key
- `query`: Search term
- `search_type`: block_height, block_hash, transaction_id, address
- `user_id`: Anonymous or user identifier
- `timestamp`: Search timestamp
- `result_found`: Boolean success indicator
- Indexes: query, timestamp

**address_labels**
- `address`: Primary key
- `label`: Human-readable label
- `category`: exchange, pool, whale, contract, burn, other
- `description`: Additional notes
- `created_at`: Creation timestamp
- Indexes: label

**analytics**
- `id`: Primary key
- `metric_type`: hashrate, tx_volume, active_addresses, etc.
- `timestamp`: Metric timestamp
- `value`: Numeric value
- `data`: Additional JSON data
- Indexes: metric_type, timestamp

**explorer_cache**
- `key`: Cache key
- `value`: Cached value (JSON)
- `ttl`: Expiration timestamp

---

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/xai ./src/xai

ENV XAI_NODE_URL=http://node:8545
ENV EXPLORER_PORT=8082
ENV EXPLORER_DB_PATH=/data/explorer.db

EXPOSE 8082

CMD ["python", "src/xai/explorer_backend.py"]
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `XAI_NODE_URL` | `http://localhost:8545` | Blockchain node URL |
| `EXPLORER_PORT` | `8082` | Explorer port |
| `EXPLORER_DB_PATH` | `:memory:` | SQLite database path |
| `FLASK_DEBUG` | `false` | Enable Flask debug mode |

### Production Checklist

- [ ] Set `FLASK_DEBUG=false`
- [ ] Use persistent database (`EXPLORER_DB_PATH=/data/explorer.db`)
- [ ] Configure CORS properly
- [ ] Set up API key authentication
- [ ] Enable HTTPS in reverse proxy
- [ ] Configure rate limiting
- [ ] Set up monitoring/alerting
- [ ] Regular database backups
- [ ] Log rotation

---

## Monitoring

### Health Endpoint

```bash
curl http://localhost:8082/health
```

Returns:
```json
{
  "status": "healthy",
  "explorer": "running",
  "node": "connected",
  "timestamp": 1234567890.0
}
```

### Key Metrics to Monitor

1. **Node Connection** - Is blockchain node accessible?
2. **Database Performance** - Query response times
3. **Cache Hit Ratio** - Percentage of cached responses
4. **WebSocket Connections** - Active real-time connections
5. **API Response Times** - Endpoint latency
6. **Search Success Rate** - Percentage of successful searches

---

## Troubleshooting

### Explorer Can't Connect to Node

**Problem:** `"node": "disconnected"` in health check

**Solutions:**
1. Verify node is running: `curl http://localhost:8545/health`
2. Check `XAI_NODE_URL` environment variable
3. Verify firewall allows connection
4. Check node logs for errors

### Search Returns "Unknown Type"

**Problem:** Search query not recognized

**Solutions:**
1. Ensure block heights are numeric only
2. Addresses must start with XAI or TXAI
3. Transaction IDs should be 64 characters
4. Check for leading/trailing spaces

### Analytics Return "Unable to fetch"

**Problem:** Analytics endpoints return error

**Solutions:**
1. Check node connection (see above)
2. Verify node has blocks
3. Try `/health` endpoint
4. Check node logs

### WebSocket Connections Dropping

**Problem:** Real-time connections frequently disconnect

**Solutions:**
1. Increase heartbeat interval (30 seconds)
2. Check network connectivity
3. Verify firewall allows WebSocket
4. Monitor server resource usage

---

## Future Enhancements

Planned features for upcoming releases:

1. **Transaction Graph Visualization** - Visual transaction flows
2. **Network Topology Map** - P2P network visualization
3. **Advanced Filtering** - Filter addresses by activity level
4. **Price Feed Integration** - Real-time price data
5. **Mobile App** - Native iOS/Android explorer
6. **GraphQL API** - Alternative to REST
7. **Smart Contract Support** - Contract verification and analysis
8. **Governance Integration** - Voting and proposal tracking

---

## Support & Contributing

For issues, questions, or contributions:

1. Check the troubleshooting section
2. Review existing GitHub issues
3. Submit detailed bug reports with logs
4. Propose enhancements via discussions

---

## License

XAI Block Explorer is part of the XAI blockchain project.

---

**Last Updated:** 2025-11-19 (UTC)
**Maintainer:** XAI Development Team
