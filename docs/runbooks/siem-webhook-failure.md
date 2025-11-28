# SIEM Webhook Failure Runbook

## Summary
Security events failed to deliver to SIEM via `XAI_SECURITY_WEBHOOK_URL`. This impacts alert visibility for P2P/security events.

## Triage (5–10 minutes)
- Check `k8s/verify-deployment.sh` SIEM probe output or CI `scripts/ci/smoke_siem_webhook.sh`.
- Inspect pod logs for `security_webhook` or `p2p.siem_probe` failures.
- Verify env/config: `XAI_SECURITY_WEBHOOK_URL`, `XAI_SECURITY_WEBHOOK_TOKEN`, network egress, TLS errors.

## Containment
- If the webhook endpoint is down, route temporarily to a backup channel (secondary webhook URL) and redeploy ConfigMap.
- If auth fails, rotate token/secret and update ConfigMap + rollout.
- If egress blocked, adjust NetworkPolicy or egress rules to allow webhook host:443.

## Recovery & Verification
- Re-run `k8s/verify-deployment.sh --namespace xai-blockchain` to confirm probe success.
- Ensure `SecurityEventRouter` sink is registered (check logs) and events resume in SIEM.
- Send a synthetic event: `SecurityEventRouter.dispatch("p2p.siem_probe", {"probe": "manual"}, "WARNING")`.

## Follow-up
- Add uptime monitoring for the SIEM webhook endpoint.
- Document rotation cadence for webhook tokens/secrets.
- Review NetworkPolicy egress allowlists for the SIEM host.
