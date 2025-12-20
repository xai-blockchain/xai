---
sidebar_position: 2
---

# WebSocket API

The XAI WebSocket API provides real-time updates for blockchain events.

## Connection

```
Testnet: ws://localhost:12003
Mainnet: ws://localhost:8547
```

## Subscribing to Events

### New Blocks

```json
{
  "action": "subscribe",
  "channel": "blocks"
}
```

**Events:**
```json
{
  "type": "block",
  "data": {
    "height": 12345,
    "hash": "abc123...",
    "timestamp": 1640000000
  }
}
```

### New Transactions

```json
{
  "action": "subscribe",
  "channel": "transactions"
}
```

**Events:**
```json
{
  "type": "transaction",
  "data": {
    "txid": "abc123...",
    "sender": "TXAI_FROM",
    "recipient": "TXAI_TO",
    "amount": 10.0
  }
}
```

### Address Updates

```json
{
  "action": "subscribe",
  "channel": "address",
  "address": "TXAI_ADDRESS"
}
```

**Events:**
```json
{
  "type": "balance_update",
  "data": {
    "address": "TXAI_ADDRESS",
    "balance": 100.5,
    "delta": +10.0
  }
}
```

## Examples

### JavaScript

```javascript
const ws = new WebSocket('ws://localhost:12003');

ws.onopen = () => {
  // Subscribe to new blocks
  ws.send(JSON.stringify({
    action: 'subscribe',
    channel: 'blocks'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('New block:', data);
};
```

### Python

```python
import websocket
import json

def on_message(ws, message):
    data = json.loads(message)
    print('Received:', data)

def on_open(ws):
    ws.send(json.dumps({
        'action': 'subscribe',
        'channel': 'blocks'
    }))

ws = websocket.WebSocketApp(
    'ws://localhost:12003',
    on_message=on_message,
    on_open=on_open
)
ws.run_forever()
```

## Resources

- [REST API](rest-api)
- [Python SDK](../developers/python-sdk)
- [Developer Overview](../developers/overview)
