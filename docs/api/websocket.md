# WebSocket Specification

The `/ws` endpoint delivers real-time events. Use this alongside `docs/api/websocket_messages.md`.

## Connection

- URL: `/ws`
- Auth: Same as REST (API key or Bearer token). Unauthorized clients are rejected.
- Protocol: JSON messages with a mandatory `type` field.

## Client Messages

- `subscribe`: `{ "type": "subscribe", "topics": ["blocks", "transactions", "mempool"] }`
- `unsubscribe`: `{ "type": "unsubscribe", "topics": ["mempool"] }`
- `ping`: `{ "type": "ping", "id": "<optional-correlation>" }`

## Server Messages

- `block`: New block header summary.
- `tx`: New transaction summary.
- `mempool_stats`: Pending counts + fee percentiles.
- `pong`: Keepalive response (echoes `id` if provided).
- `error`: `{ "type": "error", "error": "unauthorized|invalid_message|rate_limited", "message": "..." }`

## Rate Limits & Errors

- Same per-IP limits as REST; excessive churn or invalid messages return `error` and may close the socket.
- Handle disconnects gracefully and resubscribe after backoff.

## Best Practices

- Use correlation IDs on `ping` to measure latency.
- Subscribe only to needed topics; avoid wildcard fan-out.
- Validate JSON and handle unknown `type` values defensively.***
