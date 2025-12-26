# XAI RPC API Reference

Complete REST API documentation for the XAI blockchain node. All endpoints use JSON for request/response bodies.

**Base URL:** `http://localhost:12001/api/v1`

**Authentication:** Most endpoints require an API key in the `X-API-Key` header.

## Core Endpoints

### GET /

Get node information and available endpoints.

**Response:**
```json
{
  "status": "online",
  "node": "AXN Full Node",
  "version": "1.0.0",
  "algorithmic_features": true,
  "endpoints": ["/blocks", "/transactions", "/wallet", ...]
}
```

**curl:**
```bash
curl http://localhost:12001/api/v1/
```

### GET /health

Health check endpoint for monitoring and Docker.

**Response (200):**
```json
{
  "status": "healthy",
  "timestamp": 1704067200.0,
  "blockchain": {
    "accessible": true,
    "height": 12345,
    "difficulty": "1000000",
    "total_supply": "21000000",
    "latest_block_hash": "0x..."
  },
  "services": {
    "api": "running",
    "storage": "healthy",
    "p2p": "running"
  },
  "network": {
    "peers": 8
  },
  "backlog": {
    "pending_transactions": 50,
    "orphan_blocks": 0
  }
}
```

**Response (503 - Degraded):**
```json
{
  "status": "degraded",
  "error": "no_connected_peers",
  ...
}
```

### GET /stats

Get blockchain statistics.

**Response:**
```json
{
  "chain_height": 12345,
  "difficulty": "1000000",
  "total_circulating_supply": "10000000",
  "pending_transactions_count": 50,
  "orphan_blocks_count": 0,
  "miner_address": "XAI...",
  "peers": 8,
  "is_mining": true,
  "node_uptime": 86400
}
```

### GET /metrics

Prometheus metrics endpoint.

**Response (text/plain):**
```
# HELP xai_blocks_total Total blocks in chain
# TYPE xai_blocks_total counter
xai_blocks_total 12345
# HELP xai_transactions_total Total transactions
# TYPE xai_transactions_total counter
xai_transactions_total 50000
```

### GET /mempool

Get mempool overview.

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 100 | Max transactions to return (max 1000) |

**Response:**
```json
{
  "success": true,
  "limit": 100,
  "mempool": {
    "pending_count": 50,
    "size_bytes": 25000,
    "avg_fee": 10.0,
    "transactions": [...]
  }
}
```

### GET /mempool/stats

Get mempool fee statistics and congestion indicators.

**Response:**
```json
{
  "success": true,
  "timestamp": 1704067200.0,
  "fees": {
    "average_fee": 10.0,
    "median_fee": 8.0,
    "average_fee_rate": 0.5,
    "median_fee_rate": 0.4,
    "min_fee_rate": 0.1,
    "max_fee_rate": 2.0,
    "recommended_fee_rates": {
      "slow": 0.3,
      "standard": 0.4,
      "priority": 0.5
    }
  },
  "pressure": {
    "status": "normal",
    "capacity_ratio": 0.05,
    "pending_transactions": 50,
    "max_transactions": 1000,
    "age_pressure": 0.1
  }
}
```

### GET /checkpoint/provenance

Get checkpoint provenance for diagnostics.

**Response:**
```json
{
  "provenance": [
    {"height": 10000, "hash": "0x...", "timestamp": 1704067200}
  ]
}
```

---

## Blockchain Endpoints

### GET /blocks

Get all blocks with pagination.

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 10 | Blocks per page (max 200) |
| `offset` | int | 0 | Pagination offset |

**Response:**
```json
{
  "total": 12345,
  "limit": 10,
  "offset": 0,
  "blocks": [
    {
      "index": 12345,
      "hash": "0x...",
      "parent_hash": "0x...",
      "timestamp": 1704067200,
      "miner": "XAI...",
      "difficulty": "1000000",
      "transactions": 5
    }
  ]
}
```

**curl:**
```bash
curl "http://localhost:12001/api/v1/blocks?limit=10&offset=0"
```

### GET /blocks/{index}

Get block by index.

**Path Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `index` | int | Block number (0-indexed) |

**Response (200):**
```json
{
  "index": 12345,
  "hash": "0x...",
  "parent_hash": "0x...",
  "merkle_root": "0x...",
  "timestamp": 1704067200,
  "miner": "XAI...",
  "difficulty": "1000000",
  "nonce": 123456,
  "transactions": [...]
}
```

**Response (404):**
```json
{"error": "Block not found"}
```

**Headers:**
- `ETag`: Block hash for caching
- `Cache-Control`: `public, max-age=31536000, immutable`

### GET /block/{hash}

Get block by hash.

**Path Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `hash` | string | Block hash (64 hex chars, optional 0x prefix) |

**Response:** Same as GET /blocks/{index}

### POST /block/receive

Receive block from peer (P2P endpoint).

**Headers Required:**
- `X-API-Key`: API key
- `X-Peer-Signature`: Signed message

**Request Body:**
```json
{
  "header": {
    "index": 12346,
    "previous_hash": "0x...",
    "merkle_root": "0x...",
    "timestamp": 1704067200,
    "difficulty": "1000000",
    "nonce": 123456
  },
  "transactions": [...]
}
```

**Response (200):**
```json
{"success": true, "height": 12346}
```

---

## Transaction Endpoints

### GET /transactions

Get pending transactions.

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 50 | Max transactions (max 500) |
| `offset` | int | 0 | Pagination offset |

**Response:**
```json
{
  "count": 50,
  "limit": 50,
  "offset": 0,
  "transactions": [
    {
      "txid": "0x...",
      "sender": "XAI...",
      "recipient": "XAI...",
      "amount": "1000",
      "fee": "10",
      "timestamp": 1704067200,
      "nonce": 5
    }
  ]
}
```

### GET /transaction/{txid}

Get transaction by ID.

**Path Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `txid` | string | Transaction hash |

**Response (200 - Confirmed):**
```json
{
  "found": true,
  "block": 12345,
  "confirmations": 6,
  "transaction": {
    "txid": "0x...",
    "sender": "XAI...",
    "recipient": "XAI...",
    "amount": "1000",
    "fee": "10",
    "status": "confirmed"
  }
}
```

**Response (200 - Pending):**
```json
{
  "found": true,
  "status": "pending",
  "transaction": {...}
}
```

**Response (404):**
```json
{"found": false, "error": "Transaction not found"}
```

### POST /send

Submit a new transaction.

**Headers Required:** `X-API-Key`

**Request Body:**
```json
{
  "sender": "XAI_SENDER_ADDRESS",
  "recipient": "XAI_RECIPIENT_ADDRESS",
  "amount": "1000",
  "fee": "10",
  "public_key": "04...",
  "signature": "304...",
  "nonce": 5,
  "timestamp": 1704067200,
  "txid": "0x...",
  "metadata": {}
}
```

**Response (200):**
```json
{
  "success": true,
  "txid": "0x...",
  "message": "Transaction submitted successfully"
}
```

**Response (400):**
```json
{
  "success": false,
  "error": "Invalid signature",
  "code": "invalid_signature"
}
```

**Response (429):**
```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "code": "rate_limited"
}
```

**curl:**
```bash
curl -X POST http://localhost:12001/api/v1/send \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "sender": "XAI...",
    "recipient": "XAI...",
    "amount": "1000",
    "fee": "10",
    "public_key": "04...",
    "signature": "304...",
    "nonce": 5,
    "timestamp": 1704067200
  }'
```

### POST /transaction/receive

Receive transaction from peer (P2P endpoint).

**Headers Required:** `X-API-Key`, `X-Peer-Signature`

**Request Body:** Same as POST /send

---

## Wallet Endpoints

### GET /balance/{address}

Get balance for an address.

**Path Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `address` | string | Wallet address |

**Response:**
```json
{
  "address": "XAI...",
  "balance": 1000000
}
```

### GET /address/{address}/nonce

Get nonce information for an address.

**Response:**
```json
{
  "address": "XAI...",
  "confirmed_nonce": 5,
  "next_nonce": 6,
  "pending_nonce": null
}
```

### GET /history/{address}

Get transaction history for an address.

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 50 | Max transactions (max 500) |
| `offset` | int | 0 | Pagination offset |

**Response:**
```json
{
  "address": "XAI...",
  "transaction_count": 100,
  "limit": 50,
  "offset": 0,
  "transactions": [...]
}
```

---

## Mining Endpoints

### POST /mine

Mine a single block (requires pending transactions).

**Headers Required:** `X-API-Key`

**Response (200):**
```json
{
  "success": true,
  "block": {...},
  "message": "Block 12346 mined successfully",
  "reward": 50
}
```

**Response (400):**
```json
{"error": "No pending transactions to mine"}
```

### POST /auto-mine/start

Start automatic continuous mining.

**Headers Required:** `X-API-Key`

**Response:**
```json
{"message": "Auto-mining started"}
```

### POST /auto-mine/stop

Stop automatic mining.

**Headers Required:** `X-API-Key`

**Response:**
```json
{"message": "Auto-mining stopped"}
```

---

## Smart Contract Endpoints

### POST /contracts/deploy

Deploy a smart contract.

**Headers Required:** `X-API-Key`

**Request Body:**
```json
{
  "sender": "XAI_DEPLOYER",
  "bytecode": "608060...",
  "value": 0,
  "fee": 100,
  "gas_limit": 1000000,
  "public_key": "04...",
  "signature": "304...",
  "nonce": 5,
  "metadata": {
    "abi": [...]
  }
}
```

**Response:**
```json
{
  "success": true,
  "txid": "0x...",
  "contract_address": "XAI_CONTRACT...",
  "message": "Contract deployment queued"
}
```

### POST /contracts/call

Call a contract function.

**Headers Required:** `X-API-Key`

**Request Body:**
```json
{
  "sender": "XAI_CALLER",
  "contract_address": "XAI_CONTRACT",
  "value": 0,
  "fee": 10,
  "gas_limit": 100000,
  "payload": {"function": "transfer", "args": [...]},
  "public_key": "04...",
  "signature": "304...",
  "nonce": 6
}
```

**Response:**
```json
{
  "success": true,
  "txid": "0x...",
  "message": "Contract call queued"
}
```

### GET /contracts/{address}/state

Get contract state storage.

**Response:**
```json
{
  "success": true,
  "contract_address": "XAI_CONTRACT",
  "state": {
    "key1": "value1",
    "key2": "value2"
  }
}
```

### GET /contracts/{address}/abi

Get contract ABI.

**Response:**
```json
{
  "success": true,
  "contract_address": "XAI_CONTRACT",
  "abi": [
    {"type": "function", "name": "transfer", ...}
  ]
}
```

### GET /contracts/{address}/interfaces

Detect supported ERC interfaces.

**Response:**
```json
{
  "success": true,
  "contract_address": "XAI_CONTRACT",
  "interfaces": ["ERC20", "ERC165"],
  "metadata": {
    "detected_at": 1704067200,
    "source": "erc165_probe",
    "cached": false
  }
}
```

### GET /contracts/{address}/events

Get contract events.

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 50 | Max events (max 500) |
| `offset` | int | 0 | Pagination offset |

**Response:**
```json
{
  "success": true,
  "contract_address": "XAI_CONTRACT",
  "events": [...],
  "count": 10,
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

### GET /contracts/governance/status

Get smart contract feature status.

**Response:**
```json
{
  "success": true,
  "feature_name": "smart_contracts",
  "config_enabled": true,
  "governance_enabled": true,
  "contract_manager_ready": true,
  "contracts_tracked": 50,
  "receipts_tracked": 200
}
```

### POST /contracts/governance/feature

Toggle smart contract feature via governance.

**Headers Required:** Admin authentication

**Request Body:**
```json
{
  "enabled": true,
  "reason": "Enable smart contracts for mainnet"
}
```

---

## Peer Management Endpoints

### GET /peers

Get connected peers.

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `verbose` | string | "false" | Set "true" for detailed info |

**Response:**
```json
{
  "verbose": false,
  "count": 8,
  "peers": ["http://peer1:12001", "http://peer2:12001"]
}
```

### POST /peers/add

Add a peer node.

**Headers Required:** `X-API-Key`

**Request Body:**
```json
{"url": "http://new-peer:12001"}
```

**Response:**
```json
{"success": true, "message": "Peer http://new-peer:12001 added"}
```

### POST /sync

Trigger blockchain synchronization.

**Headers Required:** `X-API-Key`

**Response:**
```json
{
  "synced": true,
  "chain_length": 12345
}
```

---

## Sync Endpoints (Mobile/Light Client)

### GET /sync/snapshot/latest

Get latest snapshot metadata for chunked sync.

**Response:**
```json
{
  "status": "ok",
  "snapshot": {
    "id": "height_12345_abc123",
    "height": 12345,
    "total_chunks": 100,
    "chunk_size": 1048576,
    "created_at": 1704067200
  }
}
```

### GET /sync/snapshot/{id}

Get specific snapshot metadata.

### GET /sync/snapshot/{id}/chunks

List all chunks for a snapshot.

**Response:**
```json
{
  "status": "ok",
  "snapshot_id": "height_12345_abc123",
  "total_chunks": 100,
  "chunks": [
    {"chunk_index": 0, "priority": 1, "url": "/sync/snapshot/.../chunk/0"}
  ]
}
```

### GET /sync/snapshot/{id}/chunk/{index}

Download a specific chunk (supports HTTP Range headers).

**Response Headers:**
```
Content-Type: application/octet-stream
X-Chunk-Index: 0
X-Total-Chunks: 100
X-Chunk-Checksum: sha256:...
X-Compressed: true
Accept-Ranges: bytes
```

### POST /sync/snapshot/resume

Resume interrupted sync.

**Request Body:**
```json
{"snapshot_id": "height_12345_abc123"}
```

**Response:**
```json
{
  "status": "ok",
  "snapshot_id": "height_12345_abc123",
  "progress_percent": 45.5,
  "downloaded_chunks": [0, 1, 2, ...],
  "remaining_chunks": [45, 46, 47, ...],
  "failed_chunks": [],
  "total_chunks": 100
}
```

### GET /sync/snapshots

List all available snapshots.

### GET /api/v1/sync/progress

Get current sync progress.

### GET /api/v1/sync/headers/status

Get header sync status.

### GET /api/v1/sync/headers/progress

Get detailed header sync progress.

---

## Faucet Endpoints (Testnet Only)

### POST /faucet/claim

Claim testnet tokens.

**Headers Required:** `X-API-Key`

**Request Body:**
```json
{"address": "XAI_TESTNET_ADDRESS"}
```

**Response (200):**
```json
{
  "success": true,
  "amount": 100,
  "txid": "0x...",
  "message": "Testnet faucet claim successful!",
  "note": "This is testnet XAI - it has no real value!"
}
```

**Response (403):**
```json
{
  "success": false,
  "error": "Faucet is only available on the testnet",
  "code": "faucet_unavailable"
}
```

---

## Gamification Endpoints

### GET /airdrop/winners

Get recent airdrop winners.

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 10 | Max airdrops to return |

### GET /airdrop/user/{address}

Get airdrop history for a user.

### GET /mining/streaks

Get mining streak leaderboard.

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 10 | Max entries |
| `sort_by` | string | "current_streak" | Sort field |

### GET /mining/streak/{address}

Get mining streak for a specific miner.

### GET /treasure/active

Get active treasure hunts.

### POST /treasure/create

Create a treasure hunt (requires auth).

### POST /treasure/claim

Claim a treasure by solving its puzzle.

### GET /treasure/details/{id}

Get treasure hunt details.

### GET /timecapsule/pending

Get pending time capsules.

### GET /timecapsule/{address}

Get user's time capsules.

### GET /refunds/stats

Get system refund statistics.

### GET /refunds/{address}

Get user refund history.

---

## Algorithmic Features Endpoints

### GET /algo/status

Get algorithmic features status.

**Response:**
```json
{
  "enabled": true,
  "features": [
    {
      "name": "Fee Optimizer",
      "description": "Statistical fee prediction using EMA",
      "status": "active",
      "transactions_analyzed": 1000,
      "confidence": 100
    },
    {
      "name": "Fraud Detector",
      "status": "active",
      "addresses_tracked": 500,
      "flagged_addresses": 5
    }
  ]
}
```

### GET /algo/fee-estimate

Estimate optimal transaction fee.

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `priority` | string | "normal" | "low", "normal", or "high" |

**Response:**
```json
{
  "recommended_fee": 10,
  "fee_rate": 0.5,
  "priority": "normal",
  "mempool_status": "normal",
  "confidence": 0.95
}
```

### POST /algo/fraud-check

Analyze transaction for fraud.

**Headers Required:** `X-API-Key`

**Request Body:**
```json
{
  "payload": {
    "sender": "XAI...",
    "recipient": "XAI...",
    "amount": 10000,
    "timestamp": 1704067200
  }
}
```

**Response:**
```json
{
  "risk_score": 0.15,
  "risk_level": "low",
  "factors": [
    {"factor": "new_address", "weight": 0.1},
    {"factor": "normal_amount", "weight": 0.0}
  ],
  "recommendation": "approve"
}
```

---

## Social Recovery Endpoints

### POST /recovery/setup

Set up social recovery guardians.

**Request Body:**
```json
{
  "owner_address": "XAI_OWNER",
  "guardians": ["XAI_GUARDIAN1", "XAI_GUARDIAN2", "XAI_GUARDIAN3"],
  "threshold": 2,
  "signature": "304..."
}
```

### POST /recovery/request

Initiate account recovery.

### POST /recovery/vote

Vote on recovery request.

### GET /recovery/status/{address}

Get recovery status for an account.

### POST /recovery/cancel

Cancel active recovery request.

### POST /recovery/execute

Execute approved recovery.

### GET /recovery/config/{address}

Get recovery configuration.

### GET /recovery/guardian/{address}

Get guardian duties.

### GET /recovery/requests

List all recovery requests.

### GET /recovery/stats

Get system recovery statistics.

---

## Push Notification Endpoints

### POST /notifications/register

Register device for push notifications.

**Request Body:**
```json
{
  "user_address": "XAI...",
  "device_token": "fcm_token_or_apns_token",
  "platform": "android",
  "notification_types": ["transaction", "confirmation"],
  "metadata": {"app_version": "1.0.0"}
}
```

### DELETE /notifications/unregister

Unregister device.

### GET /notifications/settings/{token}

Get notification settings.

### PUT /notifications/settings/{token}

Update notification settings.

### POST /notifications/test

Send test notification.

### GET /notifications/devices/{address}

Get devices for an address.

### GET /notifications/stats

Get notification system statistics.

---

## Light Client Endpoints

### GET /api/v1/light/chains

List registered cross-chain light clients.

### GET /api/v1/light/evm/{chain}/header/{height}

Get EVM block header.

### GET /api/v1/light/cosmos/{chain}/header/{height}

Get Cosmos block header.

### POST /api/v1/light/verify-proof

Verify cross-chain proof.

### GET /api/v1/light/status/{type}/{chain}

Get chain status.

### GET /api/v1/light/cache/stats

Get verification cache stats.

### POST /api/v1/light/cache/clear

Clear verification cache.

---

## Admin Endpoints

### GET /admin/emergency/status

Get emergency pause and circuit breaker status.

**Required Role:** admin, operator, or auditor

### POST /admin/emergency/pause

Manually pause node operations.

**Required Role:** admin or operator

**Request Body:**
```json
{"reason": "Emergency maintenance"}
```

### POST /admin/emergency/unpause

Resume node operations.

**Required Role:** admin or operator

### POST /admin/emergency/circuit-breaker/trip

Force-open circuit breaker.

**Required Role:** admin

### POST /admin/emergency/circuit-breaker/reset

Reset circuit breaker.

**Required Role:** admin

---

## Error Responses

All error responses follow this format:

```json
{
  "success": false,
  "error": "Error description",
  "code": "error_code",
  "context": {}
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 304 | Not Modified (cached) |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Missing/invalid API key |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found |
| 429 | Rate Limited |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

### Common Error Codes

| Code | Description |
|------|-------------|
| `invalid_pagination` | Invalid limit/offset parameters |
| `invalid_payload` | Request body validation failed |
| `invalid_signature` | Transaction signature invalid |
| `invalid_address` | Malformed blockchain address |
| `rate_limited` | Rate limit exceeded |
| `transaction_rejected` | Transaction validation failed |
| `block_rejected` | Block validation failed |
| `vm_feature_disabled` | Smart contracts not enabled |
| `service_unavailable` | Service temporarily down |

---

## Rate Limits

| Endpoint Category | Limit |
|-------------------|-------|
| Read endpoints | 100/minute |
| Transaction submission | 10/minute |
| Mining operations | 5/minute |
| Faucet | 1/hour per address |
| Admin endpoints | 10/minute |

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704067200
Retry-After: 60
```

---

## WebSocket (Coming Soon)

WebSocket endpoint for real-time updates:

```
ws://localhost:12001/ws
```

Subscription topics:
- `blocks` - New block notifications
- `transactions` - Transaction confirmations
- `mempool` - Mempool updates
- `price` - Price feed updates
