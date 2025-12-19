# External Secrets Operator with Vault

## Overview
Centralized secrets management using HashiCorp Vault + External Secrets Operator.

## Components
- **Vault**: Secrets backend (dev mode in `vault` namespace)
- **ESO**: Syncs secrets from Vault → K8s (in `external-secrets` namespace)

## Architecture
```
[Vault] ──(ESO polls)──> [K8s Secret]
  │                           │
  └── secret/xai/...    xai-secrets-from-vault
```

## Quick Commands

### Store secret in Vault
```bash
kubectl exec -n vault vault-0 -- vault kv put secret/xai/validator-keys \
  validator-key="my-key" node-key="my-node-key" jwt-secret="my-jwt"
```

### Check sync status
```bash
kubectl get externalsecret -n xai
kubectl get secret xai-secrets-from-vault -n xai -o yaml
```

## Installed Components
| Component | Namespace | Access |
|-----------|-----------|--------|
| Vault | vault | http://vault.vault.svc:8200 |
| ESO | external-secrets | ClusterSecretStore: vault-backend |

## Test Results
| Test | Status |
|------|--------|
| Vault installation | ✅ PASS |
| ESO installation | ✅ PASS |
| ClusterSecretStore creation | ✅ PASS |
| ExternalSecret sync | ✅ PASS |
| Secret values verified | ✅ PASS |

## Production Notes
- Dev mode Vault uses in-memory storage (data lost on restart)
- For production: use persistent storage and proper unsealing
- Token auth is simple; consider Kubernetes auth for production
