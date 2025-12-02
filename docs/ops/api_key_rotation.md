# API Key Rotation & Admin Controls

`scripts/tools/api_key_rotate.py` manages API keys backed by `APIKeyStore` with audit logging and admin-scope alerts.

## Commands
```bash
# Issue
python scripts/tools/api_key_rotate.py issue --label "service-A" --scope user
python scripts/tools/api_key_rotate.py issue --label "admin-console" --scope admin   # emits WARNING security event

# Rotate (revokes old id, issues new)
python scripts/tools/api_key_rotate.py rotate <KEY_ID> --label "service-A" --scope user

# Revoke
python scripts/tools/api_key_rotate.py revoke <KEY_ID>
```

Flags:
- `--store-path`: override store path (default: Config.API_KEY_STORE_PATH or ./secure_keys/api_keys.json).

## Safeguards
- Simple rate limit (20 ops / 60s) persisted to `~/.xai/api_key_cli_rate.json`.
- Admin-scope issuance/rotation logs security events (`api_key_issue_admin`, `api_key_rotated`) for alerting.

## Operations SOP
- Keep store on encrypted disk or secret mount.
- Rotate admin keys quarterly; alert on unexpected admin key issuance/revocation.
- Persist audit logs (`<store>.log`) to SIEM for traceability.
