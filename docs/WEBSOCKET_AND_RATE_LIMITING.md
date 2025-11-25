# XAI Blockchain - WebSocket API & Rate Limiting Guide

Complete guide for WebSocket real-time updates and rate limiting.

## Table of Contents

- [WebSocket API](#websocket-api)
- [Connection Management](#connection-management)
- [Event Types](#event-types)
- [Rate Limiting](#rate-limiting)
- [Best Practices](#best-practices)

---

## WebSocket API

The WebSocket API provides real-time updates for blockchain events.

### Connection Endpoints

| Environment | URL |
|---|---|
| Local | `ws://localhost:5000/ws` |
| Testnet | `wss://testnet-api.xai-blockchain.io/ws` |
| Production | `wss://api.xai-blockchain.io/ws` |

### Basic Connection

```python
import websocket
import json
import threading

def on_message(ws, message):
    """Handle incoming messages."""
    data = json.loads(message)
    print(f"Event type: {data['type']}")
    print(f"Data: {data['data']}")

def on_error(ws, error):
    """Handle errors."""
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    """Handle connection close."""
    print("Connection closed")

def on_open(ws):
    """Handle connection open."""
    print("WebSocket connected")

# Create connection
ws = websocket.WebSocketApp(
    "ws://localhost:5000/ws",
    on_open=on_open,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)

# Run in thread
wst = threading.Thread(target=ws.run_forever)
wst.daemon = True
wst.start()
```

### Connection with Authentication

```python
import websocket
import json

ws_url = "ws://localhost:5000/ws"
api_key = "your-api-key"

# Add API key to connection
ws = websocket.create_connection(
    ws_url,
    header=[f"X-API-Key: {api_key}"]
)

# Receive messages
while True:
    try:
        message = ws.recv()
        data = json.loads(message)
        print(f"Received: {data}")
    except websocket.WebSocketException:
        break

ws.close()
```

---

## Connection Management

### Automatic Reconnection

```python
import websocket
import json
import time
import threading

class WebSocketManager:
    def __init__(self, url, api_key=None):
        self.url = url
        self.api_key = api_key
        self.ws = None
        self.running = False
        self.reconnect_delay = 5
        self.max_reconnect_delay = 60
    
    def connect(self):
        """Connect to WebSocket."""
        try:
            headers = []
            if self.api_key:
                headers.append(f"X-API-Key: {self.api_key}")
            
            self.ws = websocket.create_connection(
                self.url,
                header=headers
            )
            self.running = True
            self.reconnect_delay = 5
            print("Connected to WebSocket")
        except Exception as e:
            print(f"Connection failed: {e}")
            self.reconnect()
    
    def reconnect(self):
        """Attempt to reconnect with exponential backoff."""
        if not self.running:
            return
        
        print(f"Reconnecting in {self.reconnect_delay}s...")
        time.sleep(self.reconnect_delay)
        
        # Exponential backoff
        self.reconnect_delay = min(
            self.reconnect_delay * 2,
            self.max_reconnect_delay
        )
        
        self.connect()
    
    def run(self):
        """Run the WebSocket listener."""
        self.connect()
        
        while self.running:
            try:
                message = self.ws.recv()
                if message:
                    data = json.loads(message)
                    self.on_message(data)
            except websocket.WebSocketConnectionClosedException:
                print("Connection closed")
                self.reconnect()
            except Exception as e:
                print(f"Error: {e}")
                self.reconnect()
    
    def on_message(self, data):
        """Override this method to handle messages."""
        print(f"Received: {data}")
    
    def start(self):
        """Start listener in background thread."""
        thread = threading.Thread(target=self.run)
        thread.daemon = True
        thread.start()
        return thread
    
    def stop(self):
        """Stop the WebSocket."""
        self.running = False
        if self.ws:
            self.ws.close()

# Usage
manager = WebSocketManager("ws://localhost:5000/ws", api_key="your-key")
manager.start()

# Do other work...
time.sleep(60)

manager.stop()
```

### Connection with Heartbeat

```python
import websocket
import json
import threading
import time

class WebSocketWithHeartbeat:
    def __init__(self, url):
        self.url = url
        self.ws = None
        self.running = False
    
    def connect(self):
        """Connect to WebSocket."""
        self.ws = websocket.create_connection(self.url)
        self.running = True
    
    def send_heartbeat(self):
        """Send periodic heartbeat."""
        while self.running:
            try:
                self.ws.ping()
                time.sleep(30)  # Every 30 seconds
            except Exception as e:
                print(f"Heartbeat failed: {e}")
                break
    
    def run(self):
        """Run the WebSocket listener."""
        self.connect()
        
        # Start heartbeat thread
        hb_thread = threading.Thread(target=self.send_heartbeat)
        hb_thread.daemon = True
        hb_thread.start()
        
        try:
            while self.running:
                message = self.ws.recv()
                if message:
                    data = json.loads(message)
                    print(f"Received: {data}")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the WebSocket."""
        self.running = False
        if self.ws:
            self.ws.close()
```

---

## Event Types

### Block Event

Emitted when a new block is mined.

```json
{
  "type": "block",
  "data": {
    "number": 12345,
    "hash": "0x1234567890abcdef...",
    "parent_hash": "0x...",
    "timestamp": 1699564800,
    "miner": "0x...",
    "difficulty": "12345678",
    "gas_used": "5000000",
    "gas_limit": "8000000",
    "transactions": 150
  }
}
```

**Python Handler:**
```python
def handle_block_event(data):
    block_data = data['data']
    print(f"New block #{block_data['number']}")
    print(f"Hash: {block_data['hash']}")
    print(f"Transactions: {block_data['transactions']}")
```

### Transaction Event

Emitted for transaction state changes.

```json
{
  "type": "transaction",
  "data": {
    "hash": "0x...",
    "from": "0x...",
    "to": "0x...",
    "amount": "1000000000000000000",
    "status": "pending",
    "timestamp": 1699564800,
    "fee": "21000000000000"
  }
}
```

**Python Handler:**
```python
def handle_transaction_event(data):
    tx_data = data['data']
    print(f"Transaction: {tx_data['hash'][:16]}...")
    print(f"Status: {tx_data['status']}")
    print(f"Amount: {float(tx_data['amount']) / 1e18:.6f} XAI")
```

### Balance Change Event

Emitted when wallet balance changes.

```json
{
  "type": "balance_change",
  "data": {
    "address": "0x...",
    "balance": "1000000000000000000",
    "locked_balance": "500000000000000000",
    "available_balance": "500000000000000000",
    "timestamp": 1699564800
  }
}
```

**Python Handler:**
```python
def handle_balance_event(data):
    balance_data = data['data']
    address = balance_data['address']
    balance = float(balance_data['balance']) / 1e18
    print(f"Balance update for {address[:16]}...")
    print(f"New balance: {balance:.6f} XAI")
```

### Proposal Event

Emitted for governance proposal updates.

```json
{
  "type": "proposal_update",
  "data": {
    "proposal_id": 1,
    "title": "Increase mining reward",
    "status": "active",
    "votes_for": 1000,
    "votes_against": 200,
    "votes_abstain": 50,
    "timestamp": 1699564800
  }
}
```

**Python Handler:**
```python
def handle_proposal_event(data):
    prop_data = data['data']
    print(f"Proposal {prop_data['proposal_id']}: {prop_data['title']}")
    print(f"Status: {prop_data['status']}")
    print(f"Votes: {prop_data['votes_for']} for, {prop_data['votes_against']} against")
```

### Price Update Event

Emitted for price data updates.

```json
{
  "type": "price_update",
  "data": {
    "symbol": "XAI",
    "price": "10.50",
    "change_24h": "2.5",
    "change_percent_24h": "31.25",
    "timestamp": 1699564800
  }
}
```

**Python Handler:**
```python
def handle_price_event(data):
    price_data = data['data']
    print(f"Price: ${price_data['price']}")
    print(f"24h change: {price_data['change_percent_24h']}%")
```

### Event Router

```python
class EventRouter:
    def __init__(self):
        self.handlers = {}
    
    def register(self, event_type, handler):
        """Register handler for event type."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
    
    def route(self, event_data):
        """Route event to registered handlers."""
        event_type = event_data.get('type')
        
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                try:
                    handler(event_data)
                except Exception as e:
                    print(f"Handler error: {e}")

# Usage
router = EventRouter()
router.register('block', handle_block_event)
router.register('transaction', handle_transaction_event)
router.register('balance_change', handle_balance_event)

# In WebSocket message handler
def on_message(message):
    data = json.loads(message)
    router.route(data)
```

---

## Rate Limiting

### Understanding Rate Limits

All API endpoints are rate limited to prevent abuse:

- **Standard tier**: 100 requests per minute
- **Premium tier**: 1,000 requests per minute
- **Enterprise tier**: Custom limits

### Rate Limit Headers

Every API response includes rate limit information:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1699564800
```

| Header | Value | Description |
|---|---|---|
| X-RateLimit-Limit | 100 | Requests allowed in window |
| X-RateLimit-Remaining | 99 | Requests remaining in window |
| X-RateLimit-Reset | Timestamp | When limit resets (Unix time) |

### Checking Rate Limit Status

```python
import requests
from datetime import datetime

def check_rate_limit():
    response = requests.get(
        "https://api.xai-blockchain.io/stats",
        headers={"X-API-Key": "your-api-key"}
    )
    
    limit = int(response.headers.get('X-RateLimit-Limit', 0))
    remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
    reset_timestamp = int(response.headers.get('X-RateLimit-Reset', 0))
    
    reset_time = datetime.fromtimestamp(reset_timestamp)
    
    print(f"Rate limit: {remaining}/{limit}")
    print(f"Resets at: {reset_time}")
    
    return {
        'limit': limit,
        'remaining': remaining,
        'reset_timestamp': reset_timestamp
    }
```

### Handling Rate Limits

```python
from xai_sdk import RateLimitError
import time

def api_call_with_rate_limit_handling(func):
    """Decorator to handle rate limits."""
    def wrapper(*args, **kwargs):
        while True:
            try:
                return func(*args, **kwargs)
            except RateLimitError as e:
                wait_time = e.retry_after or 60
                print(f"Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
    
    return wrapper

@api_call_with_rate_limit_handling
def get_balance(address):
    return client.wallet.get_balance(address)
```

### Rate Limiting Strategy

```python
class RateLimitManager:
    def __init__(self, requests_per_minute=100):
        self.requests_per_minute = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute
        self.last_request_time = 0
    
    def wait_if_needed(self):
        """Wait if necessary to respect rate limit."""
        import time
        
        now = time.time()
        time_since_last = now - self.last_request_time
        
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            print(f"Waiting {wait_time:.2f}s for rate limit...")
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def __enter__(self):
        self.wait_if_needed()
        return self
    
    def __exit__(self, *args):
        pass

# Usage
rate_limiter = RateLimitManager(requests_per_minute=100)

with rate_limiter:
    balance = client.wallet.get_balance("0x...")

with rate_limiter:
    tx = client.transaction.send("0x...", "0x...", "1000")
```

### Batch Requests with Rate Limiting

```python
from queue import Queue
import threading
import time

class BatchRequestQueue:
    def __init__(self, requests_per_minute=100):
        self.queue = Queue()
        self.requests_per_minute = requests_per_minute
        self.running = False
    
    def add_request(self, func, args=(), kwargs=None):
        """Add request to queue."""
        self.queue.put((func, args, kwargs or {}))
    
    def process_requests(self):
        """Process requests with rate limiting."""
        min_interval = 60.0 / self.requests_per_minute
        
        while self.running:
            if not self.queue.empty():
                func, args, kwargs = self.queue.get()
                
                try:
                    result = func(*args, **kwargs)
                    print(f"Request completed: {func.__name__}")
                except Exception as e:
                    print(f"Request failed: {e}")
                
                time.sleep(min_interval)
            else:
                time.sleep(0.1)
    
    def start(self):
        """Start processing requests."""
        self.running = True
        thread = threading.Thread(target=self.process_requests)
        thread.daemon = True
        thread.start()
        return thread
    
    def stop(self):
        """Stop processing."""
        self.running = False

# Usage
queue = BatchRequestQueue(requests_per_minute=100)
queue.start()

# Add requests
for i in range(1000):
    queue.add_request(
        client.wallet.get_balance,
        args=("0x...",)
    )

time.sleep(1000)  # Wait for completion
queue.stop()
```

---

## Best Practices

### 1. Monitor Rate Limit Status

```python
def make_request_with_monitoring(func):
    """Make request and monitor rate limit."""
    try:
        result = func()
        
        # Log remaining requests
        if hasattr(result, 'headers'):
            remaining = result.headers.get('X-RateLimit-Remaining')
            if remaining and int(remaining) < 10:
                print("WARNING: Low rate limit remaining")
        
        return result
    except RateLimitError as e:
        print(f"Rate limited: retry after {e.retry_after}s")
        raise
```

### 2. Use Batch Operations

```python
# Bad - 100 separate requests
for address in addresses:
    balance = client.wallet.get_balance(address)

# Good - batch if available
balances = client.wallet.get_balances(addresses)
```

### 3. Implement Exponential Backoff

```python
import time

def exponential_backoff_retry(func, max_retries=5):
    """Retry with exponential backoff."""
    delay = 1
    
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitError:
            if attempt < max_retries - 1:
                print(f"Retry {attempt + 1} after {delay}s")
                time.sleep(delay)
                delay *= 2
            else:
                raise
```

### 4. Cache Frequently Accessed Data

```python
import time
from functools import lru_cache

class CachedAPIClient:
    def __init__(self, client, cache_duration=60):
        self.client = client
        self.cache = {}
        self.cache_duration = cache_duration
    
    def get_balance(self, address):
        """Get balance with caching."""
        cache_key = f"balance:{address}"
        
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_duration:
                return cached_data
        
        # Fetch from API
        balance = self.client.wallet.get_balance(address)
        
        # Cache result
        self.cache[cache_key] = (balance, time.time())
        
        return balance

# Usage
cached_client = CachedAPIClient(client, cache_duration=300)
balance = cached_client.get_balance("0x...")  # First call hits API
balance = cached_client.get_balance("0x...")  # Second call uses cache
```

### 5. Use WebSocket for Real-time Data

```python
# Bad - polling with rate limit impact
while True:
    balance = client.wallet.get_balance("0x...")
    time.sleep(5)

# Good - subscribe via WebSocket
ws = websocket.create_connection("ws://localhost:5000/ws")
while True:
    message = ws.recv()
    data = json.loads(message)
    if data['type'] == 'balance_change':
        print(f"Balance: {data['data']['balance']}")
```

---

## Support

For WebSocket and rate limiting issues:
- **Documentation**: https://docs.xai-blockchain.io
- **GitHub Issues**: https://github.com/xai-blockchain/sdk-python/issues
- **Discord**: https://discord.gg/xai-blockchain
