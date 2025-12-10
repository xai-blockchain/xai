# API Rate Limits & Configuration

This document expands on the limits enforced by `SecurityConfig` and the REST/WebSocket middleware.

## Default Guards

- **Global REST**: `SecurityConfig.RATE_LIMIT_REQUESTS` requests per `SecurityConfig.RATE_LIMIT_WINDOW` seconds (per-IP).
- **Burst limiter**: `SecurityConfig.RATE_LIMIT_BURST` (token bucket) smooths spikes; exceeding it triggers an immediate 429.
- **Suspicious activity**: After `SUSPICIOUS_ACTIVITY_THRESHOLD` violations an IP is blocked for `BLOCK_DURATION` seconds. Security logs emit `event: api.rate_limit_block`.
- **Request size**: Enforced separately via `Config.API_MAX_JSON_BYTES` / `SecurityConfig.MAX_BODY_SIZE`.

## Endpoint-Specific Caps

`SecurityConfig.ENDPOINT_LIMITS` defines per-endpoint `(max_requests, window_seconds)` tuples. Defaults:

| Endpoint         | Limit (requests / window)      | Notes                               |
| ---------------- | ------------------------------ | ----------------------------------- |
| `/wallet/create` | 5 / 3600 s                     | Prevents brute-force wallet spam.   |
| `/wallet/send`   | 20 / 60 s                      | Protects mempool.                   |
| `/mine`          | 100 / 60 s                     | Miner RPC guard.                    |
| `/transaction`   | 50 / 60 s                      | Submission replay guard.            |
| `/contracts/*`   | 30 / 60 s                      | ABI/events queries.                 |
| `/governance/*`  | 60 / 60 s                      | Proposal/vote spam protection.      |

Tune these values via config if your deployment has different traffic characteristics.

## WebSocket Limits

The `/ws` handler reuses the same auth and adds:

- Max 5 subscribe/unsubscribe operations per second per connection.
- Max 50 active topics per connection (`rate_limited` error if exceeded).
- Idle timeout: no `ping` in 60 s ⇒ `idle_timeout` error + disconnect.

See `docs/api/websocket_messages.md` for message shapes.

## Configuration Steps

1. **Environment variables**: set `XAI_API_RATE_LIMIT`, `XAI_API_RATE_WINDOW_SECONDS`, `XAI_API_ALLOWED_ORIGINS`, `XAI_API_MAX_JSON_BYTES`. For deterministic allowlists use JSON arrays:  
   `export XAI_API_ALLOWED_ORIGINS='["https://wallet.example.com","https://dashboard.example.com"]'`
2. **Config YAML**: mirror the values under `api:` / `security:` sections for infra-as-code parity.
3. **Reverse proxies**: configure consistent limits (`client_max_body_size`, `limit_req_zone`) so the first layer enforces the same ceilings.
4. **Clients**: inspect `X-RateLimit-Remaining` headers returned by REST endpoints and honor `Retry-After`.

## Monitoring & Testing

- Prometheus metrics (`api_rate_limit_hits_total`, `api_rate_limit_blocks_total`) and structured logs track violations.
- Dashboards should alert on sustained `429` or `rate_limited` events per IP.
- `scripts/tools/send_rejection_smoke_test.sh` simulates `/send` rejections to verify alerts and telemetry.
- Add synthetic WebSocket clients that deliberately exceed the topic cap to ensure `rate_limited` events emit as expected.

## Error Responses

REST responses on limit breach:

```json
{
  "success": false,
  "error": "rate_limited",
  "message": "Rate limit exceeded. Please try again later.",
  "details": { "limit": 20, "window_seconds": 60 }
}
```

Headers:
- `X-RateLimit-Remaining`: requests left in the current window.
- `Retry-After` (optional): seconds until the window resets.

WebSocket responses use `{ "type": "error", "error": "rate_limited", "message": "..." }`.

Following these guidelines keeps traffic predictable and prevents abuse without surprising legitimate clients.
