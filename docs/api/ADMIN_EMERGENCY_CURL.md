# Admin RBAC + Emergency Endpoint Examples

Use admin-scoped API keys or admin tokens. Headers:
- API key: `X-API-Key: <key>`
- Admin token: `X-Admin-Token: <token>`

## Check Emergency Status
```bash
curl -H "X-Admin-Token: $ADMIN_TOKEN" \
  http://localhost:12001/admin/emergency/status
```

## Pause / Unpause Operations
```bash
# Pause with reason
curl -X POST -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "manual safety stop"}' \
  http://localhost:12001/admin/emergency/pause

# Unpause
curl -X POST -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "resume after inspection"}' \
  http://localhost:12001/admin/emergency/unpause
```

## Circuit Breaker Trip / Reset
```bash
# Force trip breaker (auto-pauses)
curl -X POST -H "X-Admin-Token: $ADMIN_TOKEN" \
  http://localhost:12001/admin/emergency/circuit-breaker/trip

# Reset breaker and clear automated pause
curl -X POST -H "X-Admin-Token: $ADMIN_TOKEN" \
  http://localhost:12001/admin/emergency/circuit-breaker/reset
```

## API Key Issuance (Scoped)
```bash
# Create admin key
curl -X POST -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"label": "ops-grafana", "scope": "admin"}' \
  http://localhost:12001/admin/api-keys
```
