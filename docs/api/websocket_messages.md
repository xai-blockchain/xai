# WebSocket Message Formats

The `/ws` endpoint uses the same authentication path as REST (`X-API-Key` or `Authorization: Bearer <JWT>`). Connections that fail auth receive `{"type":"error","error":"unauthorized"}` and are closed immediately. All payloads are JSON objects containing at least a `type` field for routing.

## Connection Lifecycle

1. **Connect** to `wss://<host>/ws` with the proper auth headers/cookies.
2. Optionally receive a server hello describing supported topics.
3. Send periodic heartbeats: `{ "type": "ping", "id": "<optional-correlation>" }` every ≤30 s.
4. The server replies with `{ "type": "pong", "id": "<same id>" }`. If a client goes idle for >60 s, the node emits `{"type":"error","error":"idle_timeout"}` and closes the socket.

## Client → Server Messages

```jsonc
// Subscribe to feeds
{ "type": "subscribe", "topics": ["blocks", "transactions", "mempool_stats"] }

// Unsubscribe
{ "type": "unsubscribe", "topics": ["mempool_stats"] }

// Ping (keepalive)
{ "type": "ping", "id": "optional-correlation-id" }
```

### Topics

| Topic            | Description                                          |
| ---------------- | ---------------------------------------------------- |
| `blocks`         | Finalized block headers                              |
| `transactions`   | New mempool transactions (ordered by node policy)    |
| `mempool_stats`  | Pending counts, fee percentiles, backlog estimates   |
| `alerts`         | Security events (peer bans, rate-limit trips, etc.)  |
| `governance`     | Proposal/vote status changes                         |

- Subscriptions are idempotent; duplicate topics are ignored.
- Each request must include a `topics` array. Omitted/empty arrays trigger `invalid_message`.
- Clients may subscribe to at most 50 topics per connection (enforced by rate limiter).

## Server → Client Messages

```json
// Block header
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

// Transaction summary
{
  "type": "tx",
  "tx": {
    "txid": "0x...",
    "sender": "XAI...",
    "recipient": "XAI...",
    "amount": 1.23,
    "fee": 0.001,
    "nonce": 87,
    "timestamp": 1700000001,
    "status": "mempool"
  }
}

// Mempool telemetry
{
  "type": "mempool_stats",
  "pending": 1024,
  "pressure": "high",
  "p50_fee": 0.0005,
  "p95_fee": 0.002,
  "backlog_seconds": 180
}

// Alert (optional subscription)
{
  "type": "alert",
  "event": "p2p.reset_storm_detected",
  "severity": "WARNING",
  "metadata": {
    "peer": "0200abcd...",
    "count": 57
  }
}

// Governance update (optional subscription)
{
  "type": "governance",
  "proposal_id": "gov-2025-09",
  "state": "passed",
  "tally": { "yes": 120000, "no": 3500, "abstain": 500 }
}

// Keepalive & errors
{ "type": "pong", "id": "echoed-correlation-id" }
{ "type": "error", "error": "rate_limited", "message": "Too many subscriptions" }
```

## Error Codes & Limits

| Error code        | Description                                                                 |
| ----------------- | --------------------------------------------------------------------------- |
| `unauthorized`    | Missing/invalid auth headers. Connection closed immediately.                |
| `invalid_message` | JSON parse failure, unknown `type`, or missing `topics`.                    |
| `rate_limited`    | >5 subscribe/unsubscribe ops per second or >50 active topics.               |
| `idle_timeout`    | Missed heartbeat for 60 s. Socket closed after error is sent.               |

- Errors are delivered as `{ "type": "error", "error": "<code>", "message": "<detail>" }`.
- Payload size per message is capped at 64 KB. Larger results include `"truncated": true` and should prompt the client to fall back to REST pagination.
- Disconnections include a close reason code; clients must back off exponentially before reconnecting to avoid bans.

## Best Practices

- Reuse the same auth tokens as REST and refresh them before they expire mid-session.
- Keep a single connection per logical client whenever possible; fan-out topics using server-side subscriptions.
- Validate unexpected `type` values defensively; new message categories may be added over time.
- Log ping correlation IDs to track round-trip latency and detect stalled sockets.
- Combine WebSocket updates with periodic REST polling for reconciliation (e.g., `GET /mempool/stats` every minute).

Following this specification ensures wallets, explorers, and monitoring agents interoperate reliably with the XAI real-time feed.
