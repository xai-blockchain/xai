## Explorer Integration with Signed Backfills

Block explorers and auditors can now verify wallet-trade history by consuming `/wallet-trades/backfill`.

- **Fetch signed events**:
  ```
  GET /wallet-trades/backfill?limit=50
  ```
  Response includes `events` (payload + signature + public key). Verify each `payload` locally with the provided `public_key` (ECDSA secp256k1).
- **Replay events** to reconstruct orderbook state and surface `type`, `match_id`, `order_id`, and settlement fees in your UI.
- **Compare** replayed orders with on-chain logs by matching `order_id`/`match_id` and exported `payload` fields.
- **Store** the audit signer’s public key (from `audit_signer.py`) in your explorer for future verification.

This signed stream gives your audience immutable proof that orders/matches existed exactly as described, fulfilling compliance expectations.

## Wallet Seed Snapshot

The premine manifest (`premine_manifest.json`) is signed and can be delivered through `GET /wallet-seeds/snapshot`, which returns:

- `manifest`: the signed metadata plus the auditor’s `public_key`.
- `summary`: the wallet list (no private keys).

Use this endpoint when provisioning new nodes or explorers so every participant builds the same early-adopter set using the signed manifest; if the manifest changes you’ll get an HTTP 404 until it’s regenerated. 
