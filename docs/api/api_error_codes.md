# API Error & Response Reference

This guide catalogs the HTTP/WebSocket error codes emitted by the node along with payload shapes and remediation tips. Use it with `docs/api/openapi.yaml`, `docs/api/rate_limits.md`, and `docs/api/websocket_messages.md` for endpoint‑specific details.

## REST Error Codes

| HTTP | Error field            | Description / Remediation                                                                                                  |
| ---- | ---------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| 400  | `invalid_request`      | Malformed JSON, missing fields, invalid types, or request too large. Rebuild the payload using canonical JSON and resend. |
| 401  | `unauthorized`         | `X-API-Key` or `Authorization` header missing/invalid. Provide valid credentials or refresh expired tokens.              |
| 403  | `forbidden`            | CSRF failure, insufficient privileges, or disallowed CORS origin. Refresh CSRF token via `/csrf-token` and confirm origin. |
| 404  | `not_found`            | Block/transaction/resource absent. Verify identifiers before retrying.                                                    |
| 409  | `conflict`             | Nonce/txid conflicts or double-spend attempts. Update nonce and rebuild the transaction.                                  |
| 413  | `payload_too_large`    | Body exceeds `Config.API_MAX_JSON_BYTES` / proxy limit. Compress or split requests.                                       |
| 414  | `uri_too_long`         | Query/path exceeds `SecurityConfig.MAX_URL_LENGTH`. Move filters into the body.                                           |
| 415  | `unsupported_media`    | Content-Type not `application/json`. Set correct headers.                                                                  |
| 422  | `validation_error`     | Domain-specific validation failure (e.g., fee bounds). Inspect `details` array for field-level errors.                    |
| 429  | `rate_limited`         | Rate limit exceeded (global or endpoint-specific). Back off per `Retry-After` header.                                      |
| 500  | `internal_error`       | Unexpected server failure. Check structured logs (`event` field) before retrying.                                         |
| 503  | `service_unavailable`  | Node temporarily unavailable (maintenance, syncing). Retry with exponential backoff.                                       |

### REST Error Payload

```json
{
  "success": false,
  "error": "rate_limited",
  "message": "Rate limit exceeded. Please try again later.",
  "details": { "limit": 20, "window_seconds": 60 }
}
```

- `details` is optional and may include field errors, remaining retries, or validation context.
- Rate-limit responses include `X-RateLimit-Remaining` header (remaining requests for the endpoint) and may set `Retry-After`.
- Structured logs emit `event` metadata (e.g., `api.rate_limit`, `api.validation_error`) for SIEM correlation.

## WebSocket Error Codes

| Error code       | Description / Remediation                                                                 |
| ---------------- | ----------------------------------------------------------------------------------------- |
| `unauthorized`   | Missing/invalid auth headers. Socket is closed immediately. Use the same auth as REST.   |
| `invalid_message`| JSON parse failure, missing `topics`, or unknown `type`. Rebuild message; see spec.      |
| `rate_limited`   | Too many subscribe/unsubscribe operations (>5/sec) or >50 topics. Back off before retry. |
| `idle_timeout`   | No `ping` for 60 s. Reconnect and send heartbeats every ≤30 s.                            |
| `internal_error` | Unexpected server issue. Connection closes; reconnect after brief backoff.               |

WebSocket errors follow:

```json
{ "type": "error", "error": "rate_limited", "message": "Too many subscriptions" }
```

## Request Size, CORS & Security Guards

- Body size: `Config.API_MAX_JSON_BYTES` (surfaced via `XAI_API_MAX_JSON_BYTES`) and `SecurityConfig.MAX_BODY_SIZE`. Set proxies (Nginx `client_max_body_size`, Envoy `max_request_bytes`) to match.
- URL length: Enforced by `SecurityConfig.MAX_URL_LENGTH`; excessive query strings trigger 414 errors.
- CORS: Requests from origins not in `Config.API_ALLOWED_ORIGINS`/`XAI_API_ALLOWED_ORIGINS` are denied with 403 and logged (`event: api.cors_reject`).
- CSRF: State-changing endpoints require a current token via `/csrf-token`; stale/missing tokens produce 403 with `error: "csrf_invalid"`.

## Diagnostic Tips

- Check `event` fields in logs for unique identifiers (e.g., `api.txid_mismatch`, `api.timestamp_stale`).
- When automating, persist the response body + headers on errors; they include enough context for debugging and support.
- Align client-side retries with `Retry-After` and exponential backoff to avoid compounding rate-limit bans.

Keeping clients aligned with these error contracts prevents blind retries and accelerates incident triage.***
