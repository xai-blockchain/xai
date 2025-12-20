---
sidebar_position: 1
---

# REST API Reference

The XAI REST API provides HTTP endpoints for interacting with the blockchain.

## Base URL

```
Testnet: http://localhost:12001
Mainnet: http://localhost:8546
```

## Authentication

Most endpoints do not require authentication. Sensitive operations (like sending transactions) require signatures.

## Endpoints

### Blockchain

#### Get Blockchain Info

```http
GET /blockchain/info
```

**Response:**
```json
{
  "height": 12345,
  "best_block_hash": "abc123...",
  "difficulty": 4,
  "total_supply": 1000000.0
}
```

#### Get Block

```http
GET /block/<height>
```

**Parameters:**
- `height` (integer): Block height

**Response:**
```json
{
  "index": 12345,
  "timestamp": 1640000000,
  "transactions": [...],
  "previous_hash": "abc123...",
  "hash": "def456...",
  "nonce": 123456,
  "difficulty": 4
}
```

### Wallet

#### Get Balance

```http
GET /balance/<address>
```

**Parameters:**
- `address` (string): Wallet address

**Response:**
```json
{
  "address": "TXAI_ADDRESS",
  "balance": 100.5
}
```

#### Send Transaction

```http
POST /send
```

**Request Body:**
```json
{
  "sender": "TXAI_FROM",
  "recipient": "TXAI_TO",
  "amount": 10.0,
  "fee": 0.01,
  "signature": "...",
  "public_key": "..."
}
```

**Response:**
```json
{
  "success": true,
  "txid": "abc123...",
  "message": "Transaction sent successfully"
}
```

### Mining

#### Mine Block

```http
POST /mine
```

**Request Body:**
```json
{
  "miner_address": "TXAI_MINER_ADDRESS"
}
```

**Response:**
```json
{
  "success": true,
  "block_hash": "abc123...",
  "block_height": 12346,
  "reward": 12.0
}
```

### Smart Contracts

#### Deploy Contract

```http
POST /contract/deploy
```

**Request Body:**
```json
{
  "bytecode": "0x...",
  "constructor_args": [],
  "sender": "TXAI_DEPLOYER",
  "signature": "..."
}
```

**Response:**
```json
{
  "success": true,
  "contract_address": "0xABC123...",
  "txid": "def456..."
}
```

#### Execute Contract

```http
POST /contract/execute
```

**Request Body:**
```json
{
  "contract_address": "0xABC123...",
  "method": "transfer",
  "args": ["TXAI_RECIPIENT", 100],
  "sender": "TXAI_CALLER",
  "signature": "..."
}
```

**Response:**
```json
{
  "success": true,
  "result": {...},
  "txid": "ghi789..."
}
```

### Faucet (Testnet Only)

#### Request Tokens

```http
POST /faucet/claim
```

**Request Body:**
```json
{
  "address": "TXAI_ADDRESS"
}
```

**Response:**
```json
{
  "success": true,
  "amount": 100.0,
  "txid": "abc123...",
  "message": "Testnet faucet claim successful!"
}
```

## Error Responses

All endpoints return errors in this format:

```json
{
  "success": false,
  "error": "Error message here"
}
```

**Common Error Codes:**
- `400`: Bad Request
- `404`: Not Found
- `500`: Internal Server Error

## Rate Limiting

API endpoints are rate limited to 120 requests per minute per IP address.

## Examples

### cURL

```bash
# Get blockchain info
curl http://localhost:12001/blockchain/info

# Get balance
curl http://localhost:12001/balance/TXAI_ADDRESS

# Request faucet (testnet)
curl -X POST http://localhost:12001/faucet/claim \
  -H "Content-Type: application/json" \
  -d '{"address": "TXAI_ADDRESS"}'
```

### Python

```python
import requests

# Get blockchain info
response = requests.get("http://localhost:12001/blockchain/info")
info = response.json()

# Get balance
response = requests.get("http://localhost:12001/balance/TXAI_ADDRESS")
balance = response.json()

# Request faucet
response = requests.post(
    "http://localhost:12001/faucet/claim",
    json={"address": "TXAI_ADDRESS"}
)
result = response.json()
```

## Resources

- [WebSocket API](websocket)
- [Python SDK](../developers/python-sdk)
- [Developer Overview](../developers/overview)
