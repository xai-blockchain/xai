# Wallet Signing & `/send` Payload Requirements

Production nodes now require **explicit hash acknowledgement** and canonical payloads for every signed transaction. This mirrors the expectations of professional blockchain deployments (Trail of Bits/OpenZeppelin audits).

## `/wallet/sign`

All callers must:

1. Build the canonical payload string (sorted JSON, no omitted fields).
2. Display the SHA-256 hash to the signer.
3. Capture at least the first 8 hex characters that the signer typed to acknowledge the hash.
4. Send the payload to `/wallet/sign`:

```json
POST /wallet/sign
{
  "message_hash": "7c1e1b7f9f41b4f6cf1a8c6b9b580d054736a2f3a7a8fd62b77aeb6800a5b0aa",
  "private_key": "<hex 64>",
  "ack_hash_prefix": "7c1e1b7f"
}
```

If the prefix does not match the hash, or is shorter than the configured minimum (default 8), the request is rejected. This prevents blind signing and aligns with community best practices.

## `/send`

The node now requires the submission payload to include:

| Field      | Description                                                                 |
|------------|-----------------------------------------------------------------------------|
| `timestamp`| UNIX seconds when the payload was signed. Must be recent (default ≤24h old).|
| `txid`     | Optional hash of the canonical payload. If supplied it must match the node’s recomputed hash. |

Example payload:

```json
POST /send
{
  "sender": "XAIaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "recipient": "XAIbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "amount": 12.5,
  "fee": 0.01,
  "public_key": "04....",
  "nonce": 42,
  "signature": "ab...",
  "timestamp": 1700001234,
  "txid": "7c1e1b7f9f41b4f6cf1a8c6b9b580d054736a2f3a7a8fd62b77aeb6800a5b0aa"
}
```

Requests outside the acceptable time window return `stale_timestamp` (or `future_timestamp`) errors. Txid mismatches return `txid_mismatch`.

## Rollout Expectations

- Wallets/SDKs should never ship private keys over HTTP. Always sign locally after showing the canonical hash.
- Automation/bot flows must log the hash that was acknowledged for auditability.
- Monitor `/send` rejections for `stale_timestamp` or `txid_mismatch`; they indicate client bugs or clock drift.

Following these rules ensures every signing surface meets the standards professional validators and auditors expect.
