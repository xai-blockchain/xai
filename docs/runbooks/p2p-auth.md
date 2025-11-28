---
title: P2P Invalid Signature Alert Runbook
---

# P2P Invalid/Stale Signatures (xai_p2p_invalid_signature_total)

## Summary
Invalid or stale P2P signatures indicate key misuse, replayed payloads, clock skew, or malicious peers. Alerts: `P2PInvalidSignatures`, `P2PInvalidSignatureFlood`.

## Triage (5–10 minutes)
- Metrics: `increase(xai_p2p_invalid_signature_total[5m])`, replay metrics, peer counts.
- Logs: grep `invalid_or_stale_signature` and `p2p.invalid_signature` in node logs to identify peer IDs/fingerprints.
- Verify mTLS and trust stores are loaded (`XAI_PEER_REQUIRE_CLIENT_CERT=1`, `/etc/xai/trust` files).
- Check clock skew: `kubectl exec ... -- date` compared to NTP source.

## Containment (15 minutes)
- Remove offenders from trust stores or ban via reputation manager.
- Rotate node identity keys if compromise suspected; redeploy with new secrets.
- Shorten nonce TTL (`XAI_PEER_NONCE_TTL_SECONDS`) temporarily if stale signatures correlate with long-lived payloads.

## Eradication
- Confirm client SDKs or partner nodes sign with correct chain/network IDs.
- Audit bootstrap/DNS seeds to ensure only trusted peers participate.
- Validate TLS cert chains (`XAI_P2P_CA_BUNDLE`) and re-issue if certificates are expired or mismatched.

## Recovery & Verification
- Ensure alerts stop and metric rate returns to baseline.
- Send a signed test message between trusted nodes; expect acceptance once and rejection on replay.
- Confirm SIEM webhook received the alert (check `SecurityEventRouter` webhook sink success logs).

## Lessons / Follow-up
- Document offending fingerprints and share with ops.
- Add integration test/synthetic job that asserts signature validation path after each deploy.
- Ensure SDK version pins include the current signing schema.
