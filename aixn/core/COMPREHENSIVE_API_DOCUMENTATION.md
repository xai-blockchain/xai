# XAI Blockchain - Comprehensive API Documentation

## Overview

The XAI blockchain provides **three types of APIs** for different clients:

1. **REST API** - For browser plugins, desktop miners, wallets, explorers
2. **WebSocket API** - For real-time updates (mining, blocks, transactions)
3. **P2P Protocol** - For node-to-node communication

---

## 1. REST API Endpoints

### Base URL
```
http://localhost:8545
https://mainnet.xai-blockchain.com
```

### API Categories

#### A. Node Information
#### B. Blockchain Data
#### C. Transactions
#### D. Mining
#### E. Governance & AI Development
#### F. Node Operator Questioning
#### G. Wallet & Balance
#### H. Social Features
#### I. Algorithmic Features

---

## A. Node Information

### `GET /`
Get node status and available endpoints

**Response:**
```json
{
  "status": "online",
  "node": "XAI Full Node",
  "version": "2.0.0",
  "algorithmic_features": true,
  "endpoints": { ... }
}
```

### `GET /stats`
Get blockchain statistics

**Response:**
```json
{
  "chain_length": 12543,
  "difficulty": 4,
  "total_supply": 45231567.89,
  "pending_transactions": 12,
  "miner_address": "XAI1a2b3c...",
  "peers": 47,
  "is_mining": true,
  "node_uptime": 86400,
  "network_hashrate": "1.2 TH/s",
  "avg_block_time": 120
}
```

**Use Case:**
- Browser plugin: Display network stats
- Desktop miner: Monitor network health
- Nodes: Health checks

### `GET /peers`
Get list of connected peer nodes

**Response:**
```json
{
  "count": 47,
  "peers": [
    "http://node1.xai.com:8545",
    "http://node2.xai.com:8545",
    ...
  ]
}
```

---

## B. Blockchain Data

### `GET /blocks?limit=10&offset=0`
Get recent blocks (paginated)

**Parameters:**
- `limit` (int): Number of blocks to return (default: 10, max: 100)
- `offset` (int): Pagination offset (default: 0)

**Response:**
```json
{
  "total": 12543,
  "limit": 10,
  "offset": 0,
  "blocks": [
    {
      "index": 12543,
      "timestamp": 1734567890,
      "previous_hash": "000abc...",
      "hash": "000def...",
      "nonce": 4567890,
      "difficulty": 4,
      "miner": "XAI1a2b3c...",
      "reward": 25.5,
      "transactions": [ ... ]
    },
    ...
  ]
}
```

**Use Case:**
- Explorer: Display block history
- Analytics: Track block production
- Sync: Download blockchain

### `GET /blocks/<index>`
Get specific block by index

**Response:**
```json
{
  "index": 12543,
  "timestamp": 1734567890,
  "previous_hash": "000abc...",
  "hash": "000def...",
  "nonce": 4567890,
  "difficulty": 4,
  "miner": "XAI1a2b3c...",
  "reward": 25.5,
  "transactions": [ ... ],
  "merkle_root": "abc123..."
}
```

---

## C. Transactions

### `GET /transactions`
Get pending transactions (mempool)

**Response:**
```json
{
  "count": 12,
  "transactions": [
    {
      "txid": "tx123abc...",
      "sender": "XAI1a2b3c...",
      "recipient": "XAI4d5e6f...",
      "amount": 100.5,
      "fee": 0.01,
      "timestamp": 1734567890,
      "signature": "sig123..."
    },
    ...
  ]
}
```

**Use Case:**
- Miners: Get transactions to mine
- Wallets: Monitor pending transfers

### `GET /transaction/<txid>`
Get transaction details

**Response:**
```json
{
  "found": true,
  "block": 12543,
  "confirmations": 6,
  "transaction": {
    "txid": "tx123abc...",
    "sender": "XAI1a2b3c...",
    "recipient": "XAI4d5e6f...",
    "amount": 100.5,
    "fee": 0.01,
    "timestamp": 1734567890
  }
}
```

**Status Values:**
- `found: true, block: <num>` - Confirmed
- `found: true, status: 'pending'` - In mempool
- `found: false` - Not found

### `POST /send`
Submit new transaction

**Request:**
```json
{
  "sender": "XAI1a2b3c...",
  "recipient": "XAI4d5e6f...",
  "amount": 100.5,
  "fee": 0.01,
  "private_key": "abc123..." // Only in request, never stored
}
```

**Response:**
```json
{
  "success": true,
  "txid": "tx123abc...",
  "message": "Transaction submitted successfully"
}
```

**Use Case:**
- Wallets: Send XAI
- Payment processors: Automate transactions

---

## D. Mining API

### `POST /mine`
Mine pending transactions (single block)

**Request:** (empty body)

**Response:**
```json
{
  "success": true,
  "block": {
    "index": 12544,
    "hash": "000ghi...",
    "nonce": 9876543,
    "transactions": 12
  },
  "message": "Block 12544 mined successfully",
  "reward": 25.5
}
```

**Use Case:**
- Desktop miners: Manual mining
- Testing: Quick block generation

### `POST /mining/start` *(NEW - NEEDED)*
Start continuous mining

**Request:**
```json
{
  "miner_address": "XAI1a2b3c...",
  "threads": 4, // Number of CPU threads
  "intensity": "high" // "low", "medium", "high"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Mining started",
  "miner_address": "XAI1a2b3c...",
  "threads": 4,
  "expected_hashrate": "125 MH/s"
}
```

**Use Case:**
- Desktop miner: Start mining
- Browser plugin: Enable background mining

### `POST /mining/stop` *(NEW - NEEDED)*
Stop continuous mining

**Response:**
```json
{
  "success": true,
  "message": "Mining stopped",
  "total_blocks_mined": 5,
  "total_xai_earned": 127.5,
  "mining_duration": 3600
}
```

### `GET /mining/status` *(NEW - NEEDED)*
Get current mining status

**Response:**
```json
{
  "is_mining": true,
  "miner_address": "XAI1a2b3c...",
  "threads": 4,
  "hashrate": "125.3 MH/s",
  "blocks_mined_today": 5,
  "xai_earned_today": 127.5,
  "shares_submitted": 234,
  "shares_accepted": 229,
  "acceptance_rate": 97.9,
  "current_difficulty": 4,
  "estimated_time_to_block": 2400
}
```

**Use Case:**
- Browser plugin: Display mining stats
- Desktop miner: Real-time dashboard

### `POST /mining/register`
Register miner and check for early adopter bonus

**Request:**
```json
{
  "miner_address": "XAI1a2b3c...",
  "referral_code": "EARLY2024" // Optional
}
```

**Response:**
```json
{
  "success": true,
  "early_adopter": true,
  "bonus_multiplier": 1.5,
  "referral_bonus": 0.1,
  "total_multiplier": 1.6
}
```

### `GET /mining/achievements/<address>`
Get mining achievements for address

**Response:**
```json
{
  "total_blocks": 127,
  "total_xai_earned": 3175.5,
  "current_streak": 5,
  "best_streak": 12,
  "achievements": [
    "FIRST_BLOCK",
    "STREAK_7",
    "MILLIONAIRE"
  ]
}
```

### `GET /mining/leaderboard`
Get mining bonus leaderboard

**Response:**
```json
{
  "top_miners": [
    {
      "rank": 1,
      "address": "XAI1a2b3c...",
      "total_blocks": 567,
      "total_xai": 14175.5,
      "current_streak": 23
    },
    ...
  ]
}
```

---

## E. Governance & AI Development API *(NEW - NEEDED)*

### `POST /governance/proposals/submit`
Submit new AI development proposal

**Request:**
```json
{
  "title": "Add Cardano Atomic Swap Support",
  "proposer_address": "XAI1a2b3c...",
  "category": "atomic_swap",
  "description": "Enable trustless swaps with Cardano",
  "detailed_prompt": "Implement HTLC contracts for...",
  "estimated_tokens": 250000,
  "best_ai_model": "claude-opus-4",
  "expected_outcome": "Working Cardano swap functionality"
}
```

**Response:**
```json
{
  "success": true,
  "proposal_id": "prop_abc123",
  "status": "security_review",
  "message": "Proposal submitted for security analysis"
}
```

### `GET /governance/proposals?status=community_vote`
Get proposals by status

**Parameters:**
- `status`: `draft`, `security_review`, `community_vote`, `in_progress`, `deployed`
- `limit`, `offset`: Pagination

**Response:**
```json
{
  "count": 5,
  "proposals": [
    {
      "proposal_id": "prop_abc123",
      "title": "Add Cardano Atomic Swap Support",
      "status": "community_vote",
      "votes_for": 75234,
      "votes_against": 12890,
      "quorum": "82.3%",
      "time_remaining": 345600
    },
    ...
  ]
}
```

### `POST /governance/vote`
Vote on proposal

**Request:**
```json
{
  "proposal_id": "prop_abc123",
  "voter_address": "XAI1a2b3c...",
  "vote": "for", // "for", "against", "abstain"
  "private_key": "..."
}
```

**Response:**
```json
{
  "success": true,
  "proposal_id": "prop_abc123",
  "vote": "for",
  "voting_power": 7503.5,
  "breakdown": {
    "coin_power": 7000,
    "donation_power": 503.5
  },
  "snapshot": {
    "xai_balance": 10000,
    "snapshot_time": 1734567890
  }
}
```

### `GET /governance/proposals/<proposal_id>/votes`
Get all votes for a proposal

**Response:**
```json
{
  "proposal_id": "prop_abc123",
  "total_votes": 127,
  "total_weight": 458234.5,
  "votes": [
    {
      "voter": "XAI1a2b3c...",
      "vote": "for",
      "weight": 7503.5,
      "timestamp": 1734567890
    },
    ...
  ]
}
```

### `GET /governance/voting-power/<address>`
Calculate voting power for address

**Response:**
```json
{
  "address": "XAI1a2b3c...",
  "xai_balance": 10000,
  "ai_donations": {
    "total_tokens": 100000,
    "total_minutes": 10,
    "usd_value": 50
  },
  "voting_power": {
    "coin_power": 7000,
    "donation_power": 30,
    "total": 7030
  }
}
```

---

## F. Node Operator Questioning API *(NEW - NEEDED)*

### `POST /questioning/submit`
AI submits question to node operators

**Request:**
```json
{
  "task_id": "task_cardano_swap",
  "proposal_id": "prop_abc123",
  "question_text": "Should I use async or sync validation?",
  "question_type": "multiple_choice",
  "priority": "high",
  "context": "Implementing HTLC validation logic...",
  "options": [
    "Asynchronous validation (faster)",
    "Synchronous validation (simpler)",
    "Hybrid approach"
  ],
  "min_operators": 25,
  "timeout_seconds": 86400
}
```

**Response:**
```json
{
  "success": true,
  "question_id": "q_xyz789",
  "status": "open_for_voting",
  "voting_opened_at": 1734567890,
  "min_operators": 25,
  "timeout_at": 1734654290
}
```

### `POST /questioning/answer`
Node operator submits answer

**Request:**
```json
{
  "question_id": "q_xyz789",
  "node_address": "XAI_Node_1...",
  "selected_option_id": "option_2",
  "private_key": "..." // For signature
}
```

**Response:**
```json
{
  "success": true,
  "question_id": "q_xyz789",
  "total_votes": 18,
  "min_required": 25,
  "consensus_reached": false,
  "current_leading_answer": "Hybrid approach (61.2%)"
}
```

### `GET /questioning/pending`
Get pending questions needing answers

**Response:**
```json
{
  "count": 3,
  "questions": [
    {
      "question_id": "q_xyz789",
      "task_id": "task_cardano_swap",
      "question_text": "Should I use async or sync?",
      "question_type": "multiple_choice",
      "priority": "high",
      "total_votes": 18,
      "min_required": 25,
      "time_remaining": 82800,
      "options": [ ... ]
    },
    ...
  ]
}
```

**Use Case:**
- Node operator dashboard: Show questions needing answers

### `GET /questioning/consensus/<question_id>`
Get consensus answer (for AI)

**Request Headers:**
```
X-Task-ID: task_cardano_swap
```

**Response:**
```json
{
  "success": true,
  "question_id": "q_xyz789",
  "consensus_answer": "Hybrid approach",
  "confidence": 73.4,
  "total_votes": 27,
  "vote_weight": 234567.8,
  "answer_breakdown": {
    "Asynchronous validation (faster)": {
      "votes": 4,
      "percentage": 14.8
    },
    "Synchronous validation (simpler)": {
      "votes": 3,
      "percentage": 11.1
    },
    "Hybrid approach": {
      "votes": 20,
      "percentage": 74.1
    }
  }
}
```

---

## G. Wallet & Balance API

### `GET /balance/<address>`
Get XAI balance for address

**Response:**
```json
{
  "address": "XAI1a2b3c...",
  "balance": 1234.56,
  "locked": 0,
  "available": 1234.56
}
```

### `GET /history/<address>`
Get transaction history

**Response:**
```json
{
  "address": "XAI1a2b3c...",
  "transaction_count": 47,
  "transactions": [
    {
      "txid": "tx123...",
      "type": "received",
      "amount": 100.5,
      "from": "XAI4d5e6f...",
      "timestamp": 1734567890,
      "confirmations": 12
    },
    {
      "txid": "tx456...",
      "type": "sent",
      "amount": -50.25,
      "to": "XAI7g8h9i...",
      "fee": -0.01,
      "timestamp": 1734567800,
      "confirmations": 15
    },
    ...
  ]
}
```

### `POST /wallet/create` *(NEW - NEEDED)*
Create new wallet (for browser plugin)

**Response:**
```json
{
  "success": true,
  "address": "XAI1a2b3c...",
  "public_key": "04abc123...",
  "private_key": "def456...", // Show once, user must save
  "mnemonic": "word1 word2 word3 ...", // 12-24 words
  "warning": "Save private key securely. Cannot be recovered."
}
```

**Use Case:**
- Browser plugin: First-time setup
- Desktop wallet: New wallet creation

---

## H. Social Features API

### `GET /airdrop/winners`
Get recent airdrop winners

### `GET /mining/streaks`
Get mining streak leaderboard

### `POST /treasure/create`
Create treasure hunt

### `POST /treasure/claim`
Claim treasure by solving puzzle

### `POST /recovery/setup`
Set up social recovery guardians

*(These endpoints already exist - see existing documentation)*

---

## I. Algorithmic Features API

### `GET /algo/fee-estimate`
Get AI-optimized fee recommendation

**Response:**
```json
{
  "recommended_fee": 0.012,
  "network_load": "medium",
  "confirmation_time_estimate": "2-3 minutes",
  "fee_range": {
    "low": 0.008,
    "medium": 0.012,
    "high": 0.020
  }
}
```

**Use Case:**
- Wallets: Auto-calculate optimal fee
- Payment processors: Minimize costs

### `POST /algo/fraud-check`
Check transaction for fraud patterns

**Request:**
```json
{
  "sender": "XAI1a2b3c...",
  "recipient": "XAI4d5e6f...",
  "amount": 10000,
  "transaction_pattern": "recent_history"
}
```

**Response:**
```json
{
  "fraud_risk": "low",
  "risk_score": 12.5,
  "flags": [],
  "recommendation": "approve"
}
```

### AML Reporting Endpoints

- `GET /regulator/flagged`: returns the most recent flagged transactions with `risk_score`, `risk_level`, and `flag_reasons`. Query optional `min_score` (default 61) and `limit` to tune results.
- `GET /regulator/high-risk`: lists addresses whose average reported risk exceeds `min_score` (default 70) along with counts and maximum risk seen.
- `GET /mini-apps/manifest`: describes available mini-apps (polls, votes, games, AML guard) and how to embed them via iframes/React. Returns `mini_apps` with `recommended_flow` plus `aml_context` so GUIs can tip flows toward safe/guarded behavior; supply `address` to personalize for on-chain AML metadata.

### Light Client Endpoints

- `GET /light-client/headers?count=25&start=5000`: fetch a window of compact block headers (`index`, `hash`, `previous_hash`, `merkle_root`, `difficulty`, `nonce`). Defaults to the latest `count=20` headers.
- `GET /light-client/checkpoint`: single header + pending transaction count for quick “am I up to date?” checks.
- `GET /light-client/tx-proof/<txid>`: returns the block header, merkle root, transaction body, and sibling hash path so SPV wallets can verify inclusion.

### Mobile Bridge Endpoints

- `POST /mobile/transactions/draft`: create an unsigned transaction draft. Body accepts `sender`, `recipient`, `amount`, `priority`, optional `memo`/`metadata`. Response contains `draft_id`, `unsigned_transaction`, `fee_quote`, and `qr_payload`.
- `GET /mobile/transactions/draft/<draft_id>`: inspect a draft (status, fee quote, expiry).
- `POST /mobile/transactions/commit`: submit a signed payload. Body must include `draft_id`, `signature`, and `public_key`. On success the transaction is added to the mempool and the `txid` is returned.
- `GET /mobile/cache/summary?address=XAI...`: memoized snapshot (latest block, pending counts, wallet reminder stats, optional risk profile for the supplied address) to help mobile apps render instantly.

These endpoints are meant for explorers, auditors, or compliance dashboards to consume the AML metadata without exposing private keys.

---

## 2. WebSocket API *(NEW - NEEDED)*

### Connection
```javascript
const ws = new WebSocket('ws://localhost:8545/ws');
```

### Subscribe to Events

**Mining Updates:**
```json
{
  "action": "subscribe",
  "channel": "mining"
}
```

**Receive:**
```json
{
  "channel": "mining",
  "event": "hashrate_update",
  "data": {
    "current_hashrate": "125.3 MH/s",
    "avg_hashrate": "118.7 MH/s",
    "shares_accepted": 230,
    "timestamp": 1734567890
  }
}
```

**New Block Events:**
```json
{
  "action": "subscribe",
  "channel": "blocks"
}
```

**Receive:**
```json
{
  "channel": "blocks",
  "event": "new_block",
  "data": {
    "index": 12544,
    "hash": "000abc...",
    "miner": "XAI1a2b3c...",
    "reward": 25.5,
    "transactions": 12
  }
}
```

**Transaction Confirmations:**
```json
{
  "action": "subscribe",
  "channel": "transactions",
  "filter": {
    "txid": "tx123abc..."
  }
}
```

**Receive:**
```json
{
  "channel": "transactions",
  "event": "confirmation",
  "data": {
    "txid": "tx123abc...",
    "confirmations": 6,
    "block": 12544
  }
}
```

**Node Operator Questions:**
```json
{
  "action": "subscribe",
  "channel": "questioning"
}
```

**Receive:**
```json
{
  "channel": "questioning",
  "event": "new_question",
  "data": {
    "question_id": "q_xyz789",
    "question_text": "Should I use async or sync?",
    "priority": "high",
    "min_operators": 25,
    "timeout_at": 1734654290
  }
}
```

---

## 3. P2P Protocol

### Node Discovery

**Bootstrap Nodes:**
```
bootstrap1.xai-blockchain.com:8546
bootstrap2.xai-blockchain.com:8546
bootstrap3.xai-blockchain.com:8546
```

**Protocol:** TCP with JSON messages

### Message Types

#### 1. Handshake
```json
{
  "type": "handshake",
  "version": "2.0.0",
  "node_id": "node_abc123",
  "best_height": 12543,
  "genesis_hash": "000genesis...",
  "timestamp": 1734567890
}
```

#### 2. Block Announcement
```json
{
  "type": "block",
  "action": "announce",
  "block": {
    "index": 12544,
    "hash": "000abc...",
    "previous_hash": "000def...",
    ...
  }
}
```

#### 3. Transaction Propagation
```json
{
  "type": "transaction",
  "action": "propagate",
  "transaction": { ... }
}
```

#### 4. Sync Request
```json
{
  "type": "sync",
  "action": "request",
  "from_height": 12000,
  "to_height": 12543
}
```

---

## Client Implementation Examples

### Browser Mining Plugin

```javascript
// Initialize connection
const api = 'http://localhost:8545';
const ws = new WebSocket('ws://localhost:8545/ws');

// Start mining
async function startMining(address) {
  const response = await fetch(`${api}/mining/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      miner_address: address,
      threads: 2, // Browser uses fewer threads
      intensity: 'low'
    })
  });

  const result = await response.json();
  console.log('Mining started:', result);
}

// Subscribe to mining updates
ws.send(JSON.stringify({
  action: 'subscribe',
  channel: 'mining'
}));

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.channel === 'mining') {
    updateUI(data.data); // Update browser UI
  }
};
```

### Desktop Miner

```python
import requests
import websocket
import json

api = 'http://localhost:8545'

# Start high-performance mining
response = requests.post(f'{api}/mining/start', json={
    'miner_address': 'XAI1a2b3c...',
    'threads': 8, # Use all cores
    'intensity': 'high'
})

print(response.json())

# Monitor via WebSocket
def on_message(ws, message):
    data = json.loads(message)
    if data['channel'] == 'mining':
        print(f"Hashrate: {data['data']['current_hashrate']}")

ws = websocket.WebSocketApp('ws://localhost:8545/ws',
                            on_message=on_message)
ws.send(json.dumps({'action': 'subscribe', 'channel': 'mining'}))
ws.run_forever()
```

### Node Operator Dashboard

```javascript
// Subscribe to questions needing answers
ws.send(JSON.stringify({
  action: 'subscribe',
  channel: 'questioning'
}));

ws.onmessage = async (event) => {
  const data = JSON.parse(event.data);

  if (data.event === 'new_question') {
    // Show notification
    showNotification(`New AI question: ${data.data.question_text}`);

    // Load pending questions
    const response = await fetch(`${api}/questioning/pending`);
    const questions = await response.json();
    updateQuestionsList(questions);
  }
};

// Submit answer
async function submitAnswer(questionId, optionId) {
  const response = await fetch(`${api}/questioning/answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question_id: questionId,
      node_address: myAddress,
      selected_option_id: optionId,
      private_key: myPrivateKey
    })
  });

  const result = await response.json();
  console.log('Answer submitted:', result);
}
```

---

## Summary

### For Browser Mining Plugins:
✅ Use REST API for control (`/mining/start`, `/mining/stop`, `/mining/status`)
✅ Use WebSocket for real-time hashrate updates
✅ Use `/wallet/create` for first-time setup
✅ Lightweight, low CPU usage (2 threads, low intensity)

### For Desktop Miners:
✅ Use REST API for configuration
✅ Use WebSocket for real-time stats
✅ High-performance settings (8+ threads, high intensity)
✅ Advanced features (pool mining, overclocking)

### For Node Operators:
✅ Use Governance API for voting
✅ Use Questioning API for AI guidance
✅ Use WebSocket for real-time notifications
✅ Use P2P protocol for blockchain sync

### Next Steps:
1. ✅ REST API endpoints defined
2. ⏳ WebSocket implementation needed
3. ⏳ Add missing endpoints (`/mining/start`, `/mining/stop`, etc.)
4. ⏳ Client SDKs (JavaScript, Python)
5. ⏳ API rate limiting & authentication

This gives you **everything** needed to build browser plugins, desktop miners, and node operator dashboards! 🚀
## Z. Micro-Assistance Network (Personal AI)

- `GET /personal-ai/assistants`: returns the available micro-assistant profiles plus aggregate learning metrics (total requests, tokens, trending skills). Clients can highlight favorites and expose the list to users.
- Include `X-AI-Assistant` (e.g., `Guiding Mentor`, `Trading Sage`) in any personal AI request to route the call through that profile. Responses include `assistant_profile` and `assistant_aggregate` so frontends can display which assistant handled the request and how the network is evolving.

See `docs/MICRO_ASSISTANTS.md` for full personalities, skills, and how to interpret the metrics.
