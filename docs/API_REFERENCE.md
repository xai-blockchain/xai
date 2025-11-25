# XAI Blockchain API Reference

Comprehensive documentation for the XAI Blockchain REST API and Python SDK.

## Table of Contents

- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [API Base URLs](#api-base-urls)
- [Rate Limiting](#rate-limiting)
- [Error Handling](#error-handling)
- [Wallet API](#wallet-api)
- [Transaction API](#transaction-api)
- [Blockchain API](#blockchain-api)
- [Mining API](#mining-api)
- [Governance API](#governance-api)
- [Trading API](#trading-api)
- [WebSocket API](#websocket-api)
- [SDK Installation](#sdk-installation)
- [SDK Usage](#sdk-usage)
- [Code Examples](#code-examples)

---

## Quick Start

### Python SDK Quick Start

```python
from xai_sdk import XAIClient

# Initialize client
client = XAIClient(api_key="your-api-key")

# Create a wallet
wallet = client.wallet.create()
print(f"Wallet address: {wallet.address}")

# Get balance
balance = client.wallet.get_balance(wallet.address)
print(f"Balance: {balance.balance}")

# Send transaction
tx = client.transaction.send(
    from_address=wallet.address,
    to_address="0x...",
    amount="1000"
)
print(f"Transaction hash: {tx.hash}")

# Close client
client.close()
```

### REST API Quick Start

```bash
# Create a wallet
curl -X POST http://localhost:5000/wallet/create \
  -H "Content-Type: application/json"

# Get wallet balance
curl -X GET http://localhost:5000/wallet/0x.../balance \
  -H "X-API-Key: your-api-key"

# Send transaction
curl -X POST http://localhost:5000/transaction/send \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "from": "0x...",
    "to": "0x...",
    "amount": "1000"
  }'
```

---

## Authentication

### Methods

The API supports two authentication methods:

#### 1. API Key (Header)

```bash
curl -H "X-API-Key: your-api-key" \
  https://api.xai-blockchain.io/wallet/balance
```

#### 2. JWT Bearer Token

```bash
curl -H "Authorization: Bearer your-jwt-token" \
  https://api.xai-blockchain.io/wallet/balance
```

### Obtaining API Keys

1. Create an account on the XAI blockchain platform
2. Navigate to API settings
3. Generate an API key
4. Store it securely (use environment variables)

### Python SDK Authentication

```python
from xai_sdk import XAIClient
import os

# Using API key
api_key = os.environ.get("XAI_API_KEY")
client = XAIClient(api_key=api_key)

# Using context manager (auto-cleanup)
with XAIClient(api_key=api_key) as client:
    wallet = client.wallet.create()
```

---

## API Base URLs

| Environment | URL |
|---|---|
| Local Development | `http://localhost:5000` |
| Testnet | `https://testnet-api.xai-blockchain.io` |
| Mainnet | `https://api.xai-blockchain.io` |

### Python SDK - Switching Environments

```python
# Local development
client = XAIClient()

# Testnet
client = XAIClient(base_url="https://testnet-api.xai-blockchain.io")

# Mainnet
client = XAIClient(
    base_url="https://api.xai-blockchain.io",
    api_key="your-api-key"
)
```

---

## Rate Limiting

### Limits

- **Standard**: 100 requests per minute
- **Premium**: 1000 requests per minute
- **Enterprise**: Custom limits

### Headers

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1699564800
```

### Handling Rate Limits

```python
from xai_sdk import XAIClient, RateLimitError
import time

client = XAIClient(api_key="your-api-key")

try:
    balance = client.wallet.get_balance("0x...")
except RateLimitError as e:
    # Wait before retrying
    wait_time = e.retry_after or 60
    print(f"Rate limited. Waiting {wait_time} seconds...")
    time.sleep(wait_time)
    balance = client.wallet.get_balance("0x...")
```

---

## Error Handling

### Error Response Format

```json
{
  "code": 400,
  "message": "Invalid address format",
  "error": "VALIDATION_ERROR",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Error Codes

| Code | Name | Description |
|---|---|---|
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 404 | Not Found | Resource not found |
| 429 | Rate Limited | Rate limit exceeded |
| 500 | Internal Error | Server error |
| 503 | Unavailable | Service temporarily unavailable |

### Python SDK Error Handling

```python
from xai_sdk import (
    XAIClient,
    XAIError,
    AuthenticationError,
    ValidationError,
    RateLimitError,
    NetworkError,
    TransactionError,
    WalletError,
)

client = XAIClient(api_key="your-api-key")

try:
    wallet = client.wallet.create()
except ValidationError as e:
    print(f"Validation error: {e.message}")
except AuthenticationError as e:
    print(f"Authentication failed: {e.message}")
except RateLimitError as e:
    print(f"Rate limited. Retry after: {e.retry_after}s")
except NetworkError as e:
    print(f"Network error: {e.message}")
except XAIError as e:
    print(f"Error: {e.message} (Code: {e.code})")
```

---

## Wallet API

### Create Wallet

Creates a new blockchain wallet.

**REST Endpoint:**
```
POST /wallet/create
```

**Request Body:**
```json
{
  "wallet_type": "standard",
  "name": "My Wallet"
}
```

**Response:**
```json
{
  "address": "0x1234567890abcdef",
  "public_key": "0x...",
  "private_key": "0x...",
  "created_at": "2024-01-15T10:30:00Z",
  "wallet_type": "standard"
}
```

**Python SDK:**
```python
from xai_sdk import XAIClient, WalletType

client = XAIClient()

# Create standard wallet
wallet = client.wallet.create()
print(f"Address: {wallet.address}")
print(f"Private key: {wallet.private_key}")

# Create embedded wallet
embedded = client.wallet.create(wallet_type=WalletType.EMBEDDED)

# Create with name
named = client.wallet.create(name="My Trading Wallet")
```

### Get Wallet

Retrieves wallet information.

**REST Endpoint:**
```
GET /wallet/{address}
```

**Response:**
```json
{
  "address": "0x1234567890abcdef",
  "public_key": "0x...",
  "created_at": "2024-01-15T10:30:00Z",
  "wallet_type": "standard",
  "nonce": 5
}
```

**Python SDK:**
```python
wallet = client.wallet.get("0x1234567890abcdef")
print(f"Nonce: {wallet.nonce}")
print(f"Type: {wallet.wallet_type}")
```

### Get Balance

Retrieves wallet balance.

**REST Endpoint:**
```
GET /wallet/{address}/balance
```

**Response:**
```json
{
  "address": "0x1234567890abcdef",
  "balance": "1000000000000000000",
  "locked_balance": "0",
  "available_balance": "1000000000000000000",
  "nonce": 5
}
```

**Python SDK:**
```python
balance = client.wallet.get_balance("0x1234567890abcdef")
print(f"Balance: {balance.balance}")
print(f"Available: {balance.available_balance}")
print(f"Locked: {balance.locked_balance}")
```

### Get Transactions

Retrieves wallet transaction history.

**REST Endpoint:**
```
GET /wallet/{address}/transactions?limit=50&offset=0
```

**Response:**
```json
{
  "transactions": [
    {
      "hash": "0x...",
      "from": "0x...",
      "to": "0x...",
      "amount": "1000000000000000000",
      "timestamp": "2024-01-15T10:30:00Z",
      "status": "confirmed"
    }
  ],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

**Python SDK:**
```python
history = client.wallet.get_transactions("0x1234567890abcdef", limit=20)
for tx in history["transactions"]:
    print(f"{tx.hash}: {tx.amount}")
```

---

## Transaction API

### Send Transaction

Sends a transaction to the blockchain.

**REST Endpoint:**
```
POST /transaction/send
```

**Request Body:**
```json
{
  "from": "0x...",
  "to": "0x...",
  "amount": "1000000000000000000",
  "gas_limit": "21000",
  "gas_price": "1000000000",
  "data": "optional data"
}
```

**Response:**
```json
{
  "hash": "0x...",
  "from": "0x...",
  "to": "0x...",
  "amount": "1000000000000000000",
  "fee": "21000000000000",
  "status": "pending",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Python SDK:**
```python
tx = client.transaction.send(
    from_address="0x...",
    to_address="0x...",
    amount="1000000000000000000",
    gas_limit="21000",
    gas_price="1000000000"
)
print(f"Transaction hash: {tx.hash}")
print(f"Status: {tx.status}")
```

### Get Transaction

Retrieves transaction details.

**REST Endpoint:**
```
GET /transaction/{hash}
```

**Python SDK:**
```python
tx = client.transaction.get("0x...")
print(f"Confirmations: {tx.confirmations}")
print(f"Block: {tx.block_number}")
print(f"Status: {tx.status}")
```

### Get Transaction Status

Gets current transaction status.

**REST Endpoint:**
```
GET /transaction/{hash}/status
```

**Python SDK:**
```python
status = client.transaction.get_status("0x...")
print(f"Status: {status['status']}")
print(f"Confirmations: {status['confirmations']}")
```

### Estimate Fee

Estimates transaction fee.

**REST Endpoint:**
```
POST /transaction/estimate-fee
```

**Python SDK:**
```python
estimate = client.transaction.estimate_fee(
    from_address="0x...",
    to_address="0x...",
    amount="1000000000000000000"
)
print(f"Estimated fee: {estimate['estimated_fee']}")
print(f"Gas limit: {estimate['gas_limit']}")
```

### Wait for Confirmation

Waits for transaction confirmation.

**Python SDK:**
```python
# Wait for 1 confirmation
confirmed_tx = client.transaction.wait_for_confirmation(
    tx_hash="0x...",
    confirmations=1,
    timeout=600,  # 10 minutes
    poll_interval=5  # Check every 5 seconds
)
print(f"Transaction confirmed!")
```

---

## Blockchain API

### Get Block

Retrieves block details.

**REST Endpoint:**
```
GET /blockchain/blocks/{block_number}
```

**Python SDK:**
```python
block = client.blockchain.get_block(12345)
print(f"Hash: {block.hash}")
print(f"Miner: {block.miner}")
print(f"Transactions: {block.transactions}")
```

### List Blocks

Lists recent blocks.

**REST Endpoint:**
```
GET /blockchain/blocks?limit=20&offset=0
```

**Python SDK:**
```python
result = client.blockchain.list_blocks(limit=10)
for block in result["blocks"]:
    print(f"Block {block.number}: {block.hash}")
print(f"Total blocks: {result['total']}")
```

### Get Blockchain Stats

Retrieves blockchain statistics.

**REST Endpoint:**
```
GET /stats
```

**Python SDK:**
```python
stats = client.blockchain.get_stats()
print(f"Total blocks: {stats.total_blocks}")
print(f"Total transactions: {stats.total_transactions}")
print(f"Total supply: {stats.total_supply}")
print(f"Average block time: {stats.average_block_time}s")
```

### Get Sync Status

Retrieves blockchain sync status.

**REST Endpoint:**
```
GET /blockchain/sync
```

**Python SDK:**
```python
status = client.blockchain.get_sync_status()
print(f"Syncing: {status['syncing']}")
print(f"Current block: {status['current_block']}")
print(f"Highest block: {status['highest_block']}")

# Check if synced
if client.blockchain.is_synced():
    print("Blockchain is synchronized")
```

### Health Check

Checks node health.

**REST Endpoint:**
```
GET /health
```

**Python SDK:**
```python
health = client.blockchain.get_health()
print(f"Status: {health['status']}")
print(f"Uptime: {health['uptime_seconds']}s")
print(f"Peers: {health['peers_connected']}")
```

---

## Mining API

### Start Mining

Starts mining on the node.

**REST Endpoint:**
```
POST /mining/start
Content-Type: application/json
X-API-Key: your-api-key

{
  "threads": 4
}
```

**Python SDK:**
```python
result = client.mining.start(threads=4)
print(f"Mining started with {result['threads']} threads")
```

### Stop Mining

Stops mining on the node.

**REST Endpoint:**
```
POST /mining/stop
```

**Python SDK:**
```python
result = client.mining.stop()
print(f"Mining stopped: {result['status']}")
```

### Get Mining Status

Retrieves mining status.

**REST Endpoint:**
```
GET /mining/status
```

**Python SDK:**
```python
status = client.mining.get_status()
print(f"Mining: {status.mining}")
print(f"Hashrate: {status.hashrate}")
print(f"Blocks found: {status.blocks_found}")
print(f"Difficulty: {status.current_difficulty}")
```

### Get Mining Rewards

Retrieves mining rewards for an address.

**REST Endpoint:**
```
GET /mining/rewards?address=0x...
```

**Python SDK:**
```python
rewards = client.mining.get_rewards("0x1234567890abcdef")
print(f"Total rewards: {rewards['total_rewards']}")
print(f"Pending rewards: {rewards['pending_rewards']}")
print(f"Claimed rewards: {rewards['claimed_rewards']}")
```

---

## Governance API

### List Proposals

Lists governance proposals.

**REST Endpoint:**
```
GET /governance/proposals?status=active&limit=20
```

**Python SDK:**
```python
result = client.governance.list_proposals(status="active", limit=20)
for proposal in result["proposals"]:
    print(f"Proposal {proposal.id}: {proposal.title}")
    print(f"  Status: {proposal.status}")
    print(f"  Votes for: {proposal.votes_for}")
    print(f"  Votes against: {proposal.votes_against}")
```

### Get Proposal

Retrieves proposal details.

**REST Endpoint:**
```
GET /governance/proposals/{proposal_id}
```

**Python SDK:**
```python
proposal = client.governance.get_proposal(1)
print(f"Title: {proposal.title}")
print(f"Description: {proposal.description}")
print(f"Creator: {proposal.creator}")
print(f"Status: {proposal.status}")
print(f"Voting ends: {proposal.voting_ends_at}")
```

### Create Proposal

Creates a new governance proposal.

**REST Endpoint:**
```
POST /governance/proposals
Content-Type: application/json
X-API-Key: your-api-key
```

**Python SDK:**
```python
proposal = client.governance.create_proposal(
    title="Increase mining reward",
    description="Proposal to increase block rewards by 10%",
    proposer="0x1234567890abcdef",
    duration=604800  # 7 days in seconds
)
print(f"Created proposal {proposal.id}")
```

### Vote on Proposal

Casts a vote on a proposal.

**REST Endpoint:**
```
POST /governance/proposals/{proposal_id}/vote
Content-Type: application/json
X-API-Key: your-api-key

{
  "voter": "0x...",
  "choice": "yes"
}
```

**Python SDK:**
```python
vote = client.governance.vote(
    proposal_id=1,
    voter="0x1234567890abcdef",
    choice="yes"  # "yes", "no", or "abstain"
)
print(f"Vote recorded: {vote['choice']}")
```

### Get Active Proposals

Gets all active proposals.

**Python SDK:**
```python
active = client.governance.get_active_proposals()
for proposal in active:
    print(f"{proposal.title} - {proposal.votes_for} votes for")
```

---

## Trading API

### Register Trade Session

Registers a trading session.

**REST Endpoint:**
```
POST /wallet-trades/register
```

**Python SDK:**
```python
session = client.trading.register_session(
    wallet_address="0x1234567890abcdef",
    peer_id="peer-123"
)
print(f"Session ID: {session['session_id']}")
print(f"Expires: {session['expires_at']}")
```

### List Trade Orders

Lists active trade orders.

**REST Endpoint:**
```
GET /wallet-trades/orders
```

**Python SDK:**
```python
orders = client.trading.list_orders()
for order in orders:
    print(f"Order {order.id}:")
    print(f"  From: {order.from_address} ({order.from_amount})")
    print(f"  To: {order.to_address} ({order.to_amount})")
    print(f"  Status: {order.status}")
```

### Create Trade Order

Creates a trade order.

**REST Endpoint:**
```
POST /wallet-trades/orders
```

**Python SDK:**
```python
order = client.trading.create_order(
    from_address="0x1234567890abcdef",
    to_address="0x...",
    from_amount="1000000000000000000",
    to_amount="500000000000000000",
    timeout=3600  # 1 hour
)
print(f"Created order {order.id}")
print(f"Status: {order.status}")
```

---

## WebSocket API

### Connection

Establishes a WebSocket connection for real-time updates.

**Endpoint:**
```
ws://localhost:5000/ws
wss://api.xai-blockchain.io/ws
```

### Events

**Block Event:**
```json
{
  "type": "block",
  "data": {
    "number": 12345,
    "hash": "0x...",
    "timestamp": 1699564800,
    "transactions": 150
  }
}
```

**Transaction Event:**
```json
{
  "type": "transaction",
  "data": {
    "hash": "0x...",
    "from": "0x...",
    "to": "0x...",
    "amount": "1000000000000000000",
    "status": "pending"
  }
}
```

**Balance Change Event:**
```json
{
  "type": "balance_change",
  "data": {
    "address": "0x...",
    "balance": "1000000000000000000",
    "timestamp": 1699564800
  }
}
```

### Python WebSocket Example

```python
import websocket
import json
import threading

def on_message(ws, message):
    data = json.loads(message)
    print(f"Event: {data['type']}")
    print(f"Data: {data['data']}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Connection closed")

def on_open(ws):
    print("WebSocket connected")

# Connect to WebSocket
ws = websocket.WebSocketApp(
    "ws://localhost:5000/ws",
    on_open=on_open,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)

ws.run_forever()
```

---

## SDK Installation

### Requirements

- Python 3.10 or higher
- pip package manager

### Install from PyPI

```bash
pip install xai-blockchain-sdk
```

### Install from Source

```bash
git clone https://github.com/xai-blockchain/sdk-python
cd sdk-python
pip install -e .
```

### Development Installation

```bash
pip install -e ".[dev]"
```

---

## SDK Usage

### Basic Usage

```python
from xai_sdk import XAIClient

# Create client
client = XAIClient(api_key="your-api-key")

# Create wallet
wallet = client.wallet.create()

# Send transaction
tx = client.transaction.send(
    from_address=wallet.address,
    to_address="0x...",
    amount="1000"
)

# Check transaction status
status = client.transaction.get_status(tx.hash)

# Close client
client.close()
```

### Context Manager Usage

```python
from xai_sdk import XAIClient

# Auto cleanup on exit
with XAIClient(api_key="your-api-key") as client:
    wallet = client.wallet.create()
    tx = client.transaction.send(
        from_address=wallet.address,
        to_address="0x...",
        amount="1000"
    )
```

### Custom Configuration

```python
from xai_sdk import XAIClient

client = XAIClient(
    base_url="https://api.xai-blockchain.io",
    api_key="your-api-key",
    timeout=60,  # 60 second timeout
    max_retries=5  # Retry up to 5 times
)
```

---

## Code Examples

### Create and Fund a Wallet

```python
from xai_sdk import XAIClient

client = XAIClient(api_key="your-api-key")

# Create new wallet
wallet = client.wallet.create(name="Trading Wallet")
print(f"Created wallet: {wallet.address}")
print(f"Private key: {wallet.private_key}")

# Get balance
balance = client.wallet.get_balance(wallet.address)
print(f"Current balance: {balance.balance}")

client.close()
```

### Send and Track Transaction

```python
from xai_sdk import XAIClient, TransactionStatus
import time

client = XAIClient(api_key="your-api-key")

# Send transaction
tx = client.transaction.send(
    from_address="0x...",
    to_address="0x...",
    amount="1000000000000000000"
)
print(f"Sent transaction: {tx.hash}")

# Wait for confirmation
try:
    confirmed = client.transaction.wait_for_confirmation(
        tx_hash=tx.hash,
        confirmations=3,
        timeout=600
    )
    print(f"Transaction confirmed with {confirmed.confirmations} confirmations")
except Exception as e:
    print(f"Transaction confirmation failed: {e}")

client.close()
```

### Vote on Governance Proposal

```python
from xai_sdk import XAIClient

client = XAIClient(api_key="your-api-key")

# List active proposals
active = client.governance.get_active_proposals()
for proposal in active:
    print(f"Proposal {proposal.id}: {proposal.title}")

# Vote on a proposal
if active:
    proposal = active[0]
    vote = client.governance.vote(
        proposal_id=proposal.id,
        voter="0x...",
        choice="yes"
    )
    print(f"Voted on proposal {proposal.id}")

client.close()
```

### Mining Operations

```python
from xai_sdk import XAIClient

client = XAIClient(api_key="your-api-key")

# Start mining
print("Starting mining...")
result = client.mining.start(threads=4)
print(f"Mining threads: {result['threads']}")

# Get mining status
status = client.mining.get_status()
print(f"Mining active: {status.mining}")
print(f"Hashrate: {status.hashrate}")
print(f"Blocks found: {status.blocks_found}")

# Get rewards
rewards = client.mining.get_rewards("0x...")
print(f"Total rewards: {rewards['total_rewards']}")

# Stop mining
client.mining.stop()
print("Mining stopped")

client.close()
```

---

## Troubleshooting

### Connection Issues

```python
from xai_sdk import XAIClient, NetworkError

try:
    client = XAIClient(base_url="https://api.xai-blockchain.io")
    info = client.get_info()
except NetworkError as e:
    print(f"Cannot connect to API: {e}")
```

### Authentication Errors

```python
from xai_sdk import AuthenticationError

try:
    client = XAIClient(api_key="invalid-key")
    wallet = client.wallet.create()
except AuthenticationError:
    print("Invalid API key")
```

### Handling Rate Limits

```python
from xai_sdk import RateLimitError
import time

for attempt in range(3):
    try:
        balance = client.wallet.get_balance("0x...")
        break
    except RateLimitError as e:
        wait_time = e.retry_after or 60
        if attempt < 2:
            print(f"Rate limited. Waiting {wait_time}s...")
            time.sleep(wait_time)
        else:
            raise
```

---

## Support

- **Documentation**: https://docs.xai-blockchain.io
- **GitHub**: https://github.com/xai-blockchain
- **Discord**: https://discord.gg/xai-blockchain
- **Email**: support@xai-blockchain.io

---

## License

MIT License - See LICENSE file for details
