# Light Client & SPV Support

The node now exposes lightweight sync endpoints so mobile or bandwidth-
constrained wallets can grab block headers, checkpoints, and transaction
proofs without downloading the full chain.

## Endpoints

| Endpoint | Description |
| --- | --- |
| `GET /light-client/headers?count=25&start=5000` | Returns compact headers (`index`, `hash`, `previous_hash`, `merkle_root`, `nonce`, `difficulty`) for `count` blocks starting at `start`. If `start` is omitted, the most recent `count` headers are returned. |
| `GET /light-client/checkpoint` | Provides the latest header (height + hash) along with the current pending transaction count—handy for “is my view fresh?” checks. |
| `GET /light-client/tx-proof/<txid>` | Returns the block header, merkle root, and a sibling hash path for a confirmed transaction. Wallets can use this to verify an inclusion proof on-device. |

All three endpoints require no authentication. The responses are tiny (<3 KB) and easily cacheable by mobile apps.

## Sample Usage

```bash
# Grab the latest 10 headers.
curl "http://localhost:5000/light-client/headers?count=10"

# Fetch a checkpoint and update the UI badge.
curl "http://localhost:5000/light-client/checkpoint"

# Verify a transaction made it on-chain.
curl "http://localhost:5000/light-client/tx-proof/d7cbe8...f0"
```

## Integration Tips

- Cache the header list locally and only ask for new headers after
  comparing the returned `latest_height`.
- The `proof` array returned by `/light-client/tx-proof/<txid>` already includes
  positions (`left`/`right`), so SPV wallets can recompute the merkle root and
  ensure it matches the supplied header.
- Combine this data with the `/mobile/cache/summary` endpoint so the UI can begin
  rendering balances immediately, then reconcile full details in the background.
