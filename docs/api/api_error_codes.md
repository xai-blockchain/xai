# API Error Codes and Rate Limits

This document summarizes common HTTP responses and rate limiting rules for the XAI node API. Use it alongside `docs/api/openapi.yaml` for endpoint‑specific contracts.

## Common Responses

- **400 Bad Request** – Input validation failed (missing fields, invalid JSON, request too large). The body includes `error` with a human‑readable message.
- **401 Unauthorized** – API key or session token missing/invalid. Ensure `X-API-Key` or `Authorization: Bearer <token>` is provided when required.
- **403 Forbidden** – CSRF or authZ failure (e.g., admin token required). Refresh CSRF token via `/csrf-token` before POST/PUT/DELETE.
- **404 Not Found** – Resource does not exist (block/tx/address/etc.).
- **413 Payload Too Large** – Request exceeds `Config.API_MAX_JSON_BYTES` / Flask `MAX_CONTENT_LENGTH`.
- **414 URI Too Long** – Path/query length exceeds `SecurityConfig.MAX_URL_LENGTH`.
- **429 Too Many Requests** – Rate limit exceeded (global or endpoint‑specific). Back off and retry after the window resets.
- **500 Internal Server Error** – Unexpected server error. Inspect logs for `event` fields; retries should be cautious.

## Rate Limiting

- **Global defaults**: `RATE_LIMIT_REQUESTS` per `RATE_LIMIT_WINDOW` seconds (see `SecurityConfig`).
- **Endpoint overrides**: Higher‑risk endpoints (e.g., `/wallet/create`, `/wallet/send`, `/mine`, `/transaction`) use stricter `(max_requests, window)` pairs defined in `SecurityConfig.ENDPOINT_LIMITS`.
- **Mempool/API size caps**: `/mempool/stats`, `/transactions`, and history endpoints enforce pagination caps (default 500) to avoid heavy scans.
- **Behavior**: Limits are per IP and per endpoint; suspicious behavior trips a temporary block (`SUSPICIOUS_ACTIVITY_THRESHOLD`, `BLOCK_DURATION`).

## Request Size & CORS

- JSON bodies are limited by `Config.API_MAX_JSON_BYTES` and `SecurityConfig.MAX_BODY_SIZE`.
- URLs are limited by `SecurityConfig.MAX_URL_LENGTH`.
- Allowed origins are whitelisted via `Config.API_ALLOWED_ORIGINS`; disallowed origins receive 403 with CORS rejection.

## Error Payload Shape

Most error responses return:

```json
{
  "success": false,
  "error": "<CODE_OR_MESSAGE>",
  "message": "<human readable detail>"
}
```

Authentication/authorization errors may omit `success` for compatibility but always include an `error` field. Structured logs include `event` keys for SIEM correlation.***
