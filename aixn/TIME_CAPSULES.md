# Time Capsules

Lock cryptocurrency until a future date.

## Features

**XAI Capsules**
- Lock XAI coins until specific date
- Optional message to future
- Gift to others with unlock date

**Cross-Chain Capsules**
- Lock BTC, ETH, LTC, DOGE, XMR, BCH, ZEC, DASH
- Uses HTLC + time-lock mechanism
- Retrieve preimage when time expires

## Quick Examples

### 1-Year Savings (XAI)
```bash
POST /time-capsule/create/xai
{
  "creator": "XAI1a2b3c...",
  "amount": 1000,
  "unlock_days": 365,
  "message": "Future self: Don't spend it all at once!"
}
```

### Birthday Gift (XAI)
```bash
POST /time-capsule/create/xai
{
  "creator": "XAI_parent...",
  "beneficiary": "XAI_child...",
  "amount": 500,
  "unlock_date": "2025-12-25",
  "message": "Happy Birthday!"
}
```

### Bitcoin Time Capsule
```bash
POST /time-capsule/create/cross-chain
{
  "creator": "XAI1a2b3c...",
  "coin_type": "BTC",
  "amount": 0.1,
  "unlock_days": 1825,
  "htlc_hash": "...",
  "htlc_preimage": "...",
  "origin_chain_tx": "..."
}
```

## API Endpoints

```
POST /time-capsule/create/xai           - Create XAI capsule
POST /time-capsule/create/cross-chain   - Create cross-chain capsule
POST /time-capsule/claim/<id>           - Claim unlocked capsule
GET  /time-capsule/user/<address>       - List user's capsules
GET  /time-capsule/unlocked/<address>   - List ready to claim
GET  /time-capsule/<id>                 - Get capsule details
GET  /time-capsule/stats                - Network statistics
```

## How Cross-Chain Works

1. Lock BTC/ETH on origin blockchain (HTLC)
2. Store preimage on XAI blockchain (time-locked)
3. When unlock time arrives, retrieve preimage from XAI
4. Use preimage to claim BTC/ETH from origin chain

Trustless. Decentralized. Secure.

## Use Cases

- Forced savings
- Birthday/anniversary gifts
- Inheritance planning
- Investment discipline
- Message to future self
- Delayed rewards
