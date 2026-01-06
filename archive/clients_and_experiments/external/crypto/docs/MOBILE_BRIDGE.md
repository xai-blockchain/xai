# Mobile Wallet Bridge & Draft Flow

Mobile devices can now draft unsigned transactions, hand them to an
air-gapped signer via QR/USB, and later submit the signed payload back to
the node—all without exposing private keys.

## Draft → Sign → Commit

1. **Draft**

   ```bash
   curl -X POST http://localhost:5000/mobile/transactions/draft \
     -H "Content-Type: application/json" \
     -d '{
           "sender": "XAI1...",
           "recipient": "XAI1...",
           "amount": 12.5,
           "priority": "normal",
           "memo": "Gift"
         }'
   ```

   Response includes:
   - `draft_id`
   - `unsigned_transaction` (sender, recipient, amount, fee, nonce)
   - `qr_payload` (base64 JSON ready to render as a QR code)
   - `expires_at` (default 15 minutes)

2. **Sign offline**  
   The air-gapped device reads the QR/JSON, signs the payload with the
   user's private key, and produces `signature` + `public_key`.

3. **Commit**
   ```bash
   curl -X POST http://localhost:5000/mobile/transactions/commit \
     -H "Content-Type: application/json" \
     -d '{
           "draft_id": "UUID-from-step-1",
           "public_key": "hex",
           "signature": "hex"
         }'
   ```
   If the signature is valid, the transaction enters the pending pool and
   a `txid` is returned.

## Design Notes

- Only one active draft per sender is allowed (nonces stay sequential).
- Drafts expire automatically after 15 minutes—unused drafts never expose
  partial data.
- `fee_quote.recommended_fee` comes from the fee optimizer and accounts for
  current mempool congestion.

## Mobile Cache Summary

`GET /mobile/cache/summary?address=XAI1...` returns a memoized snapshot:

```json
{
  "summary": {
    "timestamp": 1734567890,
    "latest_block": { "index": 12345, "hash": "abc...", "pending_transactions": 84 },
    "wallet_claims_pending": 12,
    "notifications_due": [ ... ],
    "address_risk": { ... }   // only when ?address= is supplied
  }
}
```

Use it to populate dashboards instantly while heavier sync operations run in the background.
