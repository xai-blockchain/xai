# API Key Rotation & Admin Controls

`scripts/tools/api_key_rotate.py` manages API keys backed by `APIKeyStore` with audit logging and admin-scope alerts.

## Commands
```bash
# Issue
python scripts/tools/api_key_rotate.py issue --label "service-A" --scope user --ttl-days 30
python scripts/tools/api_key_rotate.py issue --label "admin-console" --scope admin --ttl-days 7   # emits WARNING security event

# Rotate (revokes old id, issues new)
python scripts/tools/api_key_rotate.py rotate <KEY_ID> --label "service-A" --scope user --ttl-days 30

# Revoke
python scripts/tools/api_key_rotate.py revoke <KEY_ID>
```

Flags:
- `--store-path`: override store path (default: Config.API_KEY_STORE_PATH or ./secure_keys/api_keys.json).
- `--ttl-days/--ttl-hours`: override Config-defined default TTL for the new key (clamped to the configured max).
- `--permanent`: request a non-expiring key (requires `XAI_API_KEY_ALLOW_PERMANENT=1`, otherwise rejected).

Each CLI action now prints the `EXPIRES_AT` timestamp and whether the key is marked `PERMANENT`. Admin API responses also include these fields (`expires_at`, `permanent`) and accept `expires_in_days`, `expires_in_hours`, and `permanent` payload options for `/admin/api-keys`.

## Token Expiration Policy
- Default TTL: `XAI_API_KEY_DEFAULT_TTL_DAYS` (90 days) – applied automatically when no TTL is provided.
- Maximum TTL: `XAI_API_KEY_MAX_TTL_DAYS` (365 days) – hard clamp for any API/CLI overrides.
- Permanent keys (`expires_at` = null) are disabled by default; set `XAI_API_KEY_ALLOW_PERMANENT=1` only for tightly-controlled bootstrap flows.
- Existing permanent keys are automatically converted to time-bound keys when permanent issuance is disabled to avoid zombie credentials.

## Safeguards
- Simple rate limit (20 ops / 60s) persisted to `~/.xai/api_key_cli_rate.json`.
- Admin-scope issuance/rotation logs security events (`api_key_issue_admin`, `api_key_rotated`) for alerting.
- Expired key usage attempts trigger `api_key_expired_attempt` security events and are rejected at the API layer.

## Operations SOP
- Keep store on encrypted disk or secret mount.
- Rotate admin keys quarterly; alert on unexpected admin key issuance/revocation.
- Persist audit logs (`<store>.log`) to SIEM for traceability.
