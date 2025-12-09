# WebSocket Message Formats

The `/ws` endpoint shares the same authentication path as REST (API key/session token). Messages use JSON objects with a `type` field to aid routing.

## Client → Server

```json
// Subscribe to feeds
{ "type": "subscribe", "topics": ["blocks", "transactions", "mempool"] }

// Unsubscribe
{ "type": "unsubscribe", "topics": ["mempool"] }

// Ping (optional keepalive)
{ "type": "ping", "id": "optional-correlation-id" }
```

## Server → Client

```json
// New block header
{
  "type": "block",
  "block": {
    "index": 1234,
    "hash": "0x...",
    "previous_hash": "0x...",
    "timestamp": 1700000000,
    "tx_count": 42,
    "miner": "XAI..."
  }
}

// New transaction
{
  "type": "tx",
  "tx": {
    "txid": "0x...",
    "sender": "XAI...",
    "recipient": "XAI...",
    "amount": 1.23,
    "fee": 0.001,
    "timestamp": 1700000001
  }
}

// Mempool pressure update
{
  "type": "mempool_stats",
  "pending": 1024,
  "pressure": "high",
  "p50_fee": 0.0005,
  "p95_fee": 0.002
}

// Keepalive
{ "type": "pong", "id": "echoed-correlation-id" }

// Error
{
  "type": "error",
  "error": "unauthorized|invalid_message|rate_limited",
  "message": "human readable detail"
}
```

## Error Handling

- Invalid messages return `type: "error"`; severe auth failures close the socket.
- Rate limits mirror REST; excessive subscribe/unsubscribe churn triggers `rate_limited` errors.
- Clients should handle disconnects and resubscribe as needed.***
