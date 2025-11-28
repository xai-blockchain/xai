# SIEM Webhook Integration

Use `XAI_SECURITY_WEBHOOK_URL` to forward `SecurityEventRouter` events (including `p2p.*` hardening alerts) to your SIEM or incident channel.

## Configuration (Kubernetes)

```yaml
data:
  XAI_SECURITY_WEBHOOK_URL: "https://siem.example.com/hooks/xai"
  XAI_SECURITY_WEBHOOK_TOKEN: "bearer-or-shared-secret"
```

Environment wiring:

```yaml
- name: XAI_SECURITY_WEBHOOK_URL
  valueFrom:
    configMapKeyRef:
      name: xai-blockchain-config
      key: XAI_SECURITY_WEBHOOK_URL
- name: XAI_SECURITY_WEBHOOK_TOKEN
  valueFrom:
    configMapKeyRef:
      name: xai-blockchain-config
      key: XAI_SECURITY_WEBHOOK_TOKEN
```

## Smoke Test

From `k8s/verify-deployment.sh`, set `XAI_SECURITY_WEBHOOK_URL` and run the SIEM probe:

```bash
./k8s/verify-deployment.sh --namespace xai-blockchain
```

This posts:

```json
{
  "event_type": "p2p.siem_probe",
  "severity": "WARNING",
  "details": {"probe": "verify-deployment"}
}
```

## Best Practices

- Use HTTPS and scoped tokens.
- Prefer allowlists on webhook listeners.
- Rate-limit inbound webhooks and emit 2xx on success.
- Monitor webhook failures; adjust `XAI_SECURITY_WEBHOOK_TIMEOUT` as needed.
