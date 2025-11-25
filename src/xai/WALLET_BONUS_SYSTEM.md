# Wallet Bonus System - User Experience

## What Happens When You Start a Node

### First-Time Node Startup (Premium Wallets Available)

```
$ python core/node.py

[Starting XAI Node...]
[Initializing blockchain...]
[Initializing wallet claim system...]

======================================================================
       CONGRATULATIONS!
======================================================================

You started a XAI coin node!

Find your bonus wallet here as a thank you:

  Tier: PREMIUM
  Address: XAI7f3a9c2e1b8d4f6a5c9e2d1f8b4a7c3e9d2f1b

How to access your wallet:
  1. Your private key is saved in: xai_og_wallet.json
  2. Check balance: /balance/<your_address>
  3. Send coins: /send endpoint with your private key
  4. BACKUP YOUR PRIVATE KEY IMMEDIATELY!

PREMIUM WALLET BONUSES:
  - Monthly reward: 200 XAI (requires 30-day uptime)
  - Keep your node running 24/7 to qualify

  Remaining premium wallets: 2,322

======================================================================

[SAVED] Wallet information saved to: xai_og_wallet.json
[WARNING] BACKUP THIS FILE IMMEDIATELY! Loss of private key = loss of funds!

XAI Node running on http://0.0.0.0:8545
```

---

### First-Time Node Startup (Premium Wallets Exhausted)

```
$ python core/node.py

[Starting XAI Node...]
[Initializing blockchain...]
[Initializing wallet claim system...]

[INFO] Premium wallets claimed. Run node for 30 minutes to qualify for early adopter wallet!

XAI Node running on http://0.0.0.0:8545

[... 30 minutes later ...]

======================================================================
       WELCOME TO XAI COIN!
======================================================================

Here is your early adopter bonus wallet:

  Address: XAI4b8f2d9a6c3e1f7b4d9a2c8f1e6b3d7a9c2e

How to access your wallet:
  1. Your private key is saved in: xai_early_adopter_wallet.json
  2. Check balance: /balance/<your_address>
  3. Send coins: /send endpoint with your private key
  4. BACKUP YOUR PRIVATE KEY IMMEDIATELY!

  Remaining early adopter wallets: 9,999

Thank you for supporting XAI!
======================================================================

[SAVED] Wallet information saved to: xai_early_adopter_wallet.json
[WARNING] BACKUP THIS FILE IMMEDIATELY! Loss of private key = loss of funds!
```

---

### Subsequent Node Startups (Already Have Wallet)

```
$ python core/node.py

[Starting XAI Node...]
[Initializing blockchain...]
[Initializing wallet claim system...]

======================================================================
You have a bonus wallet!
======================================================================
Address: XAI7f3a9c2e1b8d4f6a5c9e2d1f8b4a7c3e9d2f1b
Balance: Check blockchain XAI
Wallet file: xai_og_wallet.json or xai_early_adopter_wallet.json
======================================================================

XAI Node running on http://0.0.0.0:8545
```

---

### Node Startup (All Wallets Claimed)

```
$ python core/node.py

[Starting XAI Node...]
[Initializing blockchain...]
[Initializing wallet claim system...]

[INFO] All bonus wallets have been claimed. Mine to earn XAI!

XAI Node running on http://0.0.0.0:8545
```

---

## Wallet File: `xai_early_adopter_wallet.json`

```json
{
  "address": "XAI7f3a9c2e1b8d4f6a5c9e2d1f8b4a7c3e9d2f1b",
  "private_key": "a1b2c3d4e5f6...",
  "public_key": "04f9a2b3c4d5...",
  "balance": 1416.00,
  "claimed_at": 1731168035.123,
  "node_id": "a1b2c3d4e5f6a7b8"
}
```

**CRITICAL:** This file contains your private key. Backup immediately!

---

## How It Works

### Node ID Generation

When you start a node, the system generates a unique ID:
```
node_id = hash(hostname + mac_address + timestamp)
```

This ensures:
- One wallet per node
- Cannot claim twice
- Sybil attack resistance

### Wallet Assignment Priority

1. **Check existing wallet** - If `xai_early_adopter_wallet.json` exists, show existing wallet
2. **Try premium wallet** - Auto-assign IMMEDIATELY if available (first 2,323 nodes)
3. **30-minute uptime requirement** - If premium exhausted, wait 30 minutes then assign standard/micro wallet
4. **Show message** - If all claimed, inform user to mine

### What User Gets

**Premium Wallet (First 2,323 nodes):**
- Assigned IMMEDIATELY on node startup
- ~1,416 XAI from pre-mine
- 200 XAI monthly bonus (30-day uptime required)
- Total first year: 3,816 XAI (~$878 @ $0.23)

**Standard Wallet (Next 10,000 nodes):**
- Assigned after 30 MINUTES of uptime
- 50 XAI
- No monthly bonus
- ~$11.50 @ $0.23

**Micro Wallet (Next 25,000 nodes):**
- Assigned after 30 MINUTES of uptime
- 25 XAI
- No monthly bonus
- ~$5.75 @ $0.23

**No Wallet (After all claimed):**
- Must mine to earn XAI
- Can purchase via atomic swaps

---

## User Actions

### Check Balance
```bash
curl http://localhost:8545/balance/XAI7f3a9c2e1b8d4f6a5c9e2d1f8b4a7c3e9d2f1b
```

### Send XAI
```bash
curl -X POST http://localhost:8545/send \
  -H "Content-Type: application/json" \
  -d '{
    "sender": "XAI7f3a...",
    "recipient": "XAI9e2f...",
    "amount": 100,
    "private_key": "a1b2c3d4..."
  }'
```

### Backup Wallet
```bash
# Copy file to secure location
cp xai_early_adopter_wallet.json ~/Backups/xai_wallet_backup_$(date +%Y%m%d).json

# Or print private key
cat xai_early_adopter_wallet.json | grep private_key
```

---

## Security

**Private Key Storage:**
- Saved locally in `xai_early_adopter_wallet.json`
- Not stored on blockchain
- User responsible for backup

**Sybil Protection:**
- One wallet per unique node ID
- Node ID based on hardware identifiers
- Claim proof recorded on-chain

**Backup Warnings:**
- Displayed on every wallet assignment
- Critical user responsibility
- No recovery if lost

---

## Technical Flow

```
Node Startup
    ↓
Generate Node ID (hash of hostname + MAC + timestamp)
    ↓
Check: Does xai_early_adopter_wallet.json exist?
    ↓
YES → Display existing wallet info
    ↓
NO → Try to claim premium wallet (IMMEDIATE)
    ↓
Premium Available? → Assign, Display, Save → DONE
    ↓
NO → Display "Run node for 30 minutes to qualify"
    ↓
Start background thread (30-minute timer)
    ↓
[... 30 minutes pass ...]
    ↓
Check: Does xai_early_adopter_wallet.json exist?
    ↓
YES → Already have wallet → DONE
    ↓
NO → Try to claim standard wallet
    ↓
Standard Available? → Assign, Display "WELCOME TO XAI!", Save → DONE
    ↓
NO → Try to claim micro wallet
    ↓
Micro Available? → Assign, Display "WELCOME TO XAI!", Save → DONE
    ↓
NO → Display "All claimed" message
```

---

## Files Involved

**System Files:**
- `core/wallet_claim_system.py` - Wallet assignment logic
- `core/node.py` - Node startup with wallet check
- `premium_wallets_PRIVATE.json` - Pool of premium wallets (private)
- `standard_wallets_PRIVATE.json` - Pool of standard wallets (private)
- `wallet_claims.json` - Record of all claims

**User Files:**
- `xai_og_wallet.json` - Premium wallet (first 2,323 nodes) (BACKUP THIS!)
- `xai_early_adopter_wallet.json` - Standard/Micro wallet (next 35,000 nodes) (BACKUP THIS!)

---

## Marketing Value

**Viral Message:**
"I just started a XAI node and got $300+ in free crypto!"

**Social Proof:**
- Screenshot of congratulations message
- Balance verification
- Remaining wallet countdown creates FOMO

**Zero Friction:**
1. Download node software
2. Run `python core/node.py`
3. Instant wallet with funds
4. Start transacting

No signup, no KYC, no purchase required.

---

## Implementation Complete

✓ Node ID generation
✓ Wallet assignment on startup
✓ Congratulations message with instructions
✓ Wallet file saved locally
✓ Existing wallet detection
✓ Fallback to standard/empty wallets
✓ Security warnings
✓ Backup reminders

**Status: Ready for launch**
