# REST API Documentation

## Overview

The blockchain REST API provides a comprehensive interface for interacting with the blockchain network. All endpoints follow RESTful conventions and return JSON responses.

## Base URL

```
Development: http://localhost:5000/api/v1
Production: https://api.blockchain-project.io/v1
Testnet: https://testnet-api.blockchain-project.io/v1
```

## Authentication

Most read operations are public. Write operations require authentication.

### API Key Authentication

Include your API key in the request header:

```http
Authorization: Bearer YOUR_API_KEY
```

### Request Signing

For enhanced security, critical operations require request signing:

```http
X-Signature: HMAC_SHA256(request_body, api_secret)
X-Timestamp: 1699999999
X-Nonce: unique_nonce_value
```

## Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/blockchain/info` | GET | Get blockchain information |
| `/blocks` | GET | List recent blocks |
| `/blocks/{hash}` | GET | Get block by hash |
| `/transactions` | GET | List transactions |
| `/transactions/{hash}` | GET | Get transaction details |
| `/transactions/send` | POST | Broadcast transaction |
| `/addresses/{address}` | GET | Get address information |
| `/addresses/{address}/balance` | GET | Get address balance |
| `/addresses/{address}/transactions` | GET | Get address transactions |
| `/wallet/create` | POST | Create new wallet |
| `/wallet/balance` | GET | Get wallet balance |
| `/mempool` | GET | Get mempool status |
| `/peers` | GET | List connected peers |

## Blockchain Endpoints

### Get Blockchain Info

Get current blockchain statistics and status.

**Endpoint:** `GET /blockchain/info`

**Response:**

```json
{
  "success": true,
  "data": {
    "height": 123456,
    "best_block_hash": "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",
    "difficulty": 12345.67,
    "total_transactions": 789012,
    "chain_work": "0000000000000000000000000000000000000000000000a1b2c3d4e5f6a7b8",
    "median_time": 1699999999,
    "verification_progress": 1.0,
    "pruned": false,
    "size_on_disk": 450000000000
  }
}
```

### Get Chain Height

**Endpoint:** `GET /blockchain/height`

**Response:**

```json
{
  "success": true,
  "data": {
    "height": 123456
  }
}
```

## Block Endpoints

### List Blocks

Get a list of recent blocks with pagination.

**Endpoint:** `GET /blocks`

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `limit` | integer | 10 | Results per page (max 100) |
| `sort` | string | desc | Sort order (asc/desc) |

**Response:**

```json
{
  "success": true,
  "data": {
    "blocks": [
      {
        "hash": "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",
        "height": 123456,
        "timestamp": 1699999999,
        "transaction_count": 250,
        "miner": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        "size": 1234567,
        "weight": 3999000,
        "difficulty": 12345.67,
        "nonce": 2083236893,
        "reward": 6.25
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 10,
      "total": 123456,
      "pages": 12346
    }
  }
}
```

### Get Block by Hash

**Endpoint:** `GET /blocks/{hash}`

**Path Parameters:**

- `hash` - Block hash (64 hex characters)

**Response:**

```json
{
  "success": true,
  "data": {
    "hash": "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",
    "height": 123456,
    "version": 1,
    "previous_hash": "0000000000000000000000000000000000000000000000000000000000000000",
    "merkle_root": "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b",
    "timestamp": 1699999999,
    "bits": "1d00ffff",
    "nonce": 2083236893,
    "difficulty": 12345.67,
    "size": 1234567,
    "weight": 3999000,
    "transaction_count": 250,
    "transactions": [
      "tx_hash_1",
      "tx_hash_2"
    ],
    "miner": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    "reward": 6.25,
    "confirmations": 10
  }
}
```

### Get Block by Height

**Endpoint:** `GET /blocks/height/{height}`

**Path Parameters:**

- `height` - Block height (integer)

## Transaction Endpoints

### List Transactions

**Endpoint:** `GET /transactions`

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | integer | Page number |
| `limit` | integer | Results per page |
| `type` | string | Filter by type (standard, coinbase) |
| `min_value` | float | Minimum transaction value |

**Response:**

```json
{
  "success": true,
  "data": {
    "transactions": [
      {
        "hash": "a1b2c3d4...",
        "block_hash": "000000...",
        "block_height": 123456,
        "timestamp": 1699999999,
        "size": 250,
        "virtual_size": 141,
        "fee": 0.0001,
        "input_count": 1,
        "output_count": 2,
        "value": 1.5,
        "confirmations": 10
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 10,
      "total": 50000,
      "pages": 5000
    }
  }
}
```

### Get Transaction Details

**Endpoint:** `GET /transactions/{hash}`

**Response:**

```json
{
  "success": true,
  "data": {
    "hash": "a1b2c3d4e5f6...",
    "version": 2,
    "size": 250,
    "virtual_size": 141,
    "weight": 564,
    "locktime": 0,
    "block_hash": "000000...",
    "block_height": 123456,
    "timestamp": 1699999999,
    "confirmations": 10,
    "fee": 0.0001,
    "fee_rate": 1.0,
    "inputs": [
      {
        "previous_output": {
          "hash": "prev_tx_hash",
          "index": 0
        },
        "script_sig": "483045022100...",
        "sequence": 4294967295,
        "witness": [],
        "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        "value": 1.5001
      }
    ],
    "outputs": [
      {
        "index": 0,
        "value": 1.0,
        "script_pubkey": "76a914...",
        "address": "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2",
        "spent": true,
        "spent_by": "spending_tx_hash"
      },
      {
        "index": 1,
        "value": 0.5,
        "script_pubkey": "76a914...",
        "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        "spent": false
      }
    ]
  }
}
```

### Send Transaction

Broadcast a signed transaction to the network.

**Endpoint:** `POST /transactions/send`

**Request Body:**

```json
{
  "transaction": "01000000..." // Hex-encoded signed transaction
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "hash": "a1b2c3d4e5f6...",
    "message": "Transaction broadcast successfully"
  }
}
```

**Error Response:**

```json
{
  "success": false,
  "error": {
    "code": "INVALID_TRANSACTION",
    "message": "Transaction validation failed: insufficient funds"
  }
}
```

## Address Endpoints

### Get Address Information

**Endpoint:** `GET /addresses/{address}`

**Response:**

```json
{
  "success": true,
  "data": {
    "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    "balance": 10.5,
    "total_received": 100.5,
    "total_sent": 90.0,
    "transaction_count": 150,
    "unspent_output_count": 5,
    "first_seen": 1699999999,
    "last_seen": 1700000000
  }
}
```

### Get Address Balance

**Endpoint:** `GET /addresses/{address}/balance`

**Response:**

```json
{
  "success": true,
  "data": {
    "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    "confirmed_balance": 10.5,
    "unconfirmed_balance": 0.5,
    "total_balance": 11.0
  }
}
```

### Get Address Transactions

**Endpoint:** `GET /addresses/{address}/transactions`

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | integer | Page number |
| `limit` | integer | Results per page |
| `confirmed` | boolean | Filter by confirmation status |

## Wallet Endpoints

### Create Wallet

**Endpoint:** `POST /wallet/create`

**Request Body:**

```json
{
  "password": "secure_password_here",
  "mnemonic_length": 12 // Optional: 12, 15, 18, 21, 24
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    "public_key": "04678afdb...",
    "mnemonic": "word1 word2 word3 ... word12",
    "warning": "Store your mnemonic phrase securely. It cannot be recovered."
  }
}
```

### Get Wallet Balance

**Endpoint:** `GET /wallet/balance`

**Headers:** Requires authentication

## Mempool Endpoints

### Get Mempool Status

**Endpoint:** `GET /mempool`

**Response:**

```json
{
  "success": true,
  "data": {
    "size": 5000,
    "bytes": 2500000,
    "usage": 5000000,
    "max_mempool": 300000000,
    "mempool_min_fee": 0.00001,
    "min_relay_fee": 0.00001,
    "unbroadcast_count": 10
  }
}
```

### Get Mempool Transactions

**Endpoint:** `GET /mempool/transactions`

**Query Parameters:**

- `limit` - Number of results (default: 100, max: 1000)

## Network Endpoints

### List Peers

**Endpoint:** `GET /peers`

**Response:**

```json
{
  "success": true,
  "data": {
    "peer_count": 8,
    "peers": [
      {
        "id": "peer_1",
        "address": "192.168.1.100:8333",
        "version": 70016,
        "subversion": "/Satoshi:0.21.0/",
        "connected_time": 3600,
        "last_send": 1699999999,
        "last_recv": 1699999999,
        "bytes_sent": 1000000,
        "bytes_recv": 2000000,
        "ping_time": 0.050
      }
    ]
  }
}
```

## Error Handling

### Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Request validation failed |
| `UNAUTHORIZED` | 401 | Authentication required |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

## Rate Limiting

API requests are rate-limited to prevent abuse.

**Limits:**
- Unauthenticated: 100 requests/hour
- Authenticated: 1000 requests/hour
- Premium: 10000 requests/hour

**Rate Limit Headers:**

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1699999999
```

## Pagination

All list endpoints support pagination.

**Parameters:**
- `page` - Page number (starts at 1)
- `limit` - Items per page (default: 10, max: 100)

**Response:**

```json
{
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 1000,
    "pages": 100
  }
}
```

## Webhooks

Subscribe to blockchain events via webhooks.

### Available Events

- `block.new` - New block mined
- `transaction.confirmed` - Transaction confirmed
- `address.received` - Address received funds
- `address.spent` - Address spent funds

### Webhook Configuration

**Endpoint:** `POST /webhooks`

```json
{
  "url": "https://your-server.com/webhook",
  "events": ["block.new", "transaction.confirmed"],
  "secret": "webhook_secret_for_verification"
}
```

## Code Examples

### JavaScript/Node.js

```javascript
const axios = require('axios');

// Get blockchain info
async function getBlockchainInfo() {
  const response = await axios.get('http://localhost:5000/api/v1/blockchain/info');
  console.log(response.data);
}

// Send transaction
async function sendTransaction(txHex) {
  const response = await axios.post(
    'http://localhost:5000/api/v1/transactions/send',
    { transaction: txHex },
    {
      headers: {
        'Authorization': 'Bearer YOUR_API_KEY',
        'Content-Type': 'application/json'
      }
    }
  );
  return response.data;
}
```

### Python

```python
import requests

# Get block by hash
def get_block(block_hash):
    url = f"http://localhost:5000/api/v1/blocks/{block_hash}"
    response = requests.get(url)
    return response.json()

# Get address balance
def get_balance(address):
    url = f"http://localhost:5000/api/v1/addresses/{address}/balance"
    response = requests.get(url)
    return response.json()
```

### cURL

```bash
# Get blockchain info
curl http://localhost:5000/api/v1/blockchain/info

# Send transaction
curl -X POST http://localhost:5000/api/v1/transactions/send \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"transaction": "01000000..."}'

# Get address transactions
curl "http://localhost:5000/api/v1/addresses/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa/transactions?page=1&limit=10"
```

## Best Practices

1. **Use HTTPS in production** - Always use encrypted connections
2. **Implement retry logic** - Handle temporary failures gracefully
3. **Cache responses** - Reduce unnecessary API calls
4. **Validate inputs** - Check data before sending requests
5. **Handle rate limits** - Implement exponential backoff
6. **Secure API keys** - Never commit keys to version control
7. **Monitor usage** - Track your API consumption

## Support

- API Status: https://status.blockchain-project.io
- Documentation: https://docs.blockchain-project.io
- Support: api-support@blockchain-project.io

---

*API Version: 1.0 | Last Updated: 2025-11-12*
