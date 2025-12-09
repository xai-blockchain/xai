# API Rate Limits

This document supplements `docs/api/api_error_codes.md` and `docs/deployment/local-setup.md` with detailed rate limiting guidance.

## Defaults

- **Global**: `SecurityConfig.RATE_LIMIT_REQUESTS` per `SecurityConfig.RATE_LIMIT_WINDOW` seconds (per-IP).
- **Bursts**: `SecurityConfig.RATE_LIMIT_BURST` caps short-term spikes.
- **Suspicious activity**: After `SUSPICIOUS_ACTIVITY_THRESHOLD` violations, an IP is blocked for `BLOCK_DURATION` seconds.

## Endpoint Overrides

Higher-risk endpoints have stricter limits via `SecurityConfig.ENDPOINT_LIMITS`:

- `/wallet/create`: 5 per hour
- `/wallet/send`: 20 per minute
- `/mine`: 100 per minute
- `/transaction`: 50 per minute

Tune these values in production to balance UX and abuse prevention.

## How to Configure

- **YAML/env**: Set `API_RATE_LIMIT`, `API_RATE_WINDOW_SECONDS`, and `API_MAX_JSON_BYTES` in config/env to adjust defaults. `SecurityConfig` is the authoritative source for security middleware enforcement.
- **CORS**: Configure `API_ALLOWED_ORIGINS` to an allowlist; disallowed origins are rejected before rate limiting.
- **Client guidance**: Back off on HTTP 429 responses; do not retry instantly.

## Monitoring

- `/metrics` and security logs include rate-limit counters; alert on sustained 429/403 rates.
- Use `scripts/tools/send_rejection_smoke_test.sh` to validate rejection telemetry during bring-up.

## Error Responses

- Exceeded limits return HTTP 429 with a JSON body:
  ```json
  { "error": "Rate limit exceeded. Please try again later." }
  ```
- Suspicious activity blocks return 429 until the block expires.***
