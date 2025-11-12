# Wallet Claiming & Time Capsule Protocol - Complete Implementation

## Overview

This document describes the complete implementation of the multi-mechanism wallet claiming system and Time Capsule Protocol, ensuring **NO EARLY ADOPTER MISSES OUT** regardless of how they interact with the XAI blockchain.

---

## Problem Solved

**Original Issue**: Browser miners could mine blocks without ever knowing they're entitled to an early adopter wallet!

**Solution**: Three-mechanism claiming system with persistent notifications

---

## 1. Triple-Mechanism Wallet Claiming System

### Mechanism 1: Full Node Startup (Original)
**Status**: ✓ Already Implemented

- Triggers when user runs full node: `python core/node.py`
- Premium wallets (first 2,323): Assigned IMMEDIATELY
- Standard/Micro wallets: Assigned after 30 MINUTES uptime
- Wallet files: `xai_og_wallet.json` (premium) or `xai_early_adopter_wallet.json` (standard/micro)

### Mechanism 2: Explicit Claiming API (NEW)
**Status**: ✓ Implemented

**Endpoint**: `POST /claim-wallet`

**Request**:
```json
{
  "identifier": "node_id_or_miner_address",
  "uptime_minutes": 30
}
```

**Response (Premium)**:
```json
{
  "success": true,
  "tier": "premium",
  "wallet": {
    "address": "AIXN...",
    "file": "xai_og_wallet.json"
  },
  "message": "CONGRATULATIONS! Premium wallet claimed!",
  "remaining_premium": 2322
}
```

**Response (Standard with Time Capsule Offer)**:
```json
{
  "success": true,
  "tier": "standard",
  "wallet": {
    "address": "AIXN...",
    "balance": 50,
    "file": "xai_early_adopter_wallet.json"
  },
  "message": "WELCOME TO XAI COIN! Standard wallet claimed!",
  "time_capsule_offer": {
    "eligible": true,
    "current_balance": 50,
    "locked_balance": 500,
    "bonus_amount": 450,
    "lock_period_days": 365,
    "offer_message": "╔═══════...╗  Turn your 50 XAI into 500 XAI!  ..."
  }
}
```

### Mechanism 3: Automatic Mining Check (NEW)
**Status**: ✓ Implemented

**Triggers**: Every time `/mine` endpoint is called

**Auto-Check Process**:
1. User mines block via `POST /mine`
2. System automatically checks if miner has unclaimed wallet
3. If eligible for premium: Auto-assigns immediately
4. If premium exhausted: Returns notification about 30-minute requirement

**Mining Response with Auto-Claim**:
```json
{
  "success": true,
  "block": {...},
  "message": "Block 123 mined successfully",
  "reward": 50,
  "bonus_wallet": {
    "claimed": true,
    "tier": "premium",
    "address": "AIXN...",
    "file": "xai_og_wallet.json",
    "message": "🎁 CONGRATULATIONS! Premium wallet auto-assigned!",
    "remaining_premium": 2321
  }
}
```

**Mining Response with Notification**:
```json
{
  "success": true,
  "block": {...},
  "message": "Block 123 mined successfully",
  "reward": 50,
  "wallet_notification": {
    "message": "🎁 WALLET AVAILABLE! Run node for 30 minutes to claim early adopter wallet",
    "action": "Call POST /claim-wallet with your miner address after 30 minutes"
  }
}
```

---

## 2. Persistent Notification System

**Status**: ✓ Implemented

**Purpose**: Users receive wallet notifications on EVERY mining operation until claimed

**Endpoint**: `GET /check-unclaimed-wallet/<identifier>`

**Response**:
```json
{
  "unclaimed": true,
  "notification": {
    "message": "🎁 UNCLAIMED WALLET AVAILABLE!",
    "details": "You have an unclaimed early adopter wallet waiting!",
    "action": "Call POST /claim-wallet to claim your wallet",
    "notification_number": 5
  }
}
```

**Tracking**: System maintains `pending_wallet_claims.json` with:
- Who is eligible
- How many times they've been notified
- Whether they've claimed

---

## 3. Time Capsule Protocol

### Overview

**920 of the 10,000 standard wallets** are randomly selected for special Time Capsule Protocol eligibility.

**Offer**: Turn 50 XAI into 500 XAI by locking for 1 year

### Funding Source

**Reserve Wallet**: 414,000 XAI (920 × 450 XAI bonus)

**File**: `TIME_CAPSULE_RESERVE.json`

**Generation**:
```bash
python create_time_capsule_reserve.py
```

**Reserve Tracking**:
- Initial balance: 414,000 XAI
- Current balance: Tracked and updated with each time capsule creation
- Disbursements made: Counter increments with each accepted offer
- Each time capsule deducts 450 XAI from reserve

### Time Capsule Flow

1. **User Claims Standard Wallet** (via any mechanism)
   - If wallet is one of the 920 selected: `time_capsule_offer` included in response
   - User sees offer message

2. **User Accepts Offer** via `POST /accept-time-capsule`

**Request**:
```json
{
  "wallet_address": "AIXN...",
  "accept": true
}
```

**Process**:
1. Verify wallet eligibility
2. Check reserve has 450 XAI available
3. Transfer 450 XAI from reserve to locked wallet
4. Create time-locked wallet record (unlock date: 1 year, UTC)
5. Generate NEW empty replacement wallet
6. Save replacement wallet to `xai_early_adopter_wallet.json`
7. Display protocol engagement message

**Response**:
```json
{
  "success": true,
  "message": "Time Capsule Protocol Engaged",
  "locked_wallet": {
    "address": "AIXN...",
    "amount": 500,
    "unlock_date_utc": "2026-11-09 12:34:56 UTC",
    "unlock_timestamp_utc": 1762876496
  },
  "replacement_wallet": {
    "address": "AIXN<new>...",
    "balance": 0,
    "file": "xai_early_adopter_wallet.json (updated)"
  },
  "unlock_message": "You may claim your wallet with 500 XAI on 09 November 2026 at 12:34:56 UTC"
}
```

**Console Output**:
```
======================================================================
       TIME CAPSULE PROTOCOL ENGAGED
======================================================================

Your 500 XAI has been sealed on the XAI blockchain for 1 year.

  Locked Amount: 500 XAI
  Unlock Date: 09 November 2026 at 12:34:56 UTC

You may claim your wallet with 500 XAI on 09 November 2026 at 12:34:56 UTC

A new empty wallet has been issued for immediate use.
Check your wallet file for the replacement wallet details.

======================================================================
```

3. **After 1 Year**: User can claim locked wallet via blockchain

### Random Selection Process

**Script**: `mark_time_capsule_wallets.py`

```python
# Deterministic random selection (seed=42 for reproducibility)
random.seed(42)
time_capsule_indices = random.sample(range(10000), 920)

for i in time_capsule_indices:
    wallets[i]['time_capsule_eligible'] = True
    wallets[i]['time_capsule_bonus'] = 450
```

**Run Once**:
```bash
python mark_time_capsule_wallets.py
```

---

## 4. UTC Timestamps for Anonymity

**All timestamps use UTC** to protect the anonymity of blockchain origin:

### Implementation

**Time Capsule Protocol**:
```python
current_utc = datetime.utcnow()
unlock_date = current_utc + timedelta(days=365)

locked_wallet = {
    'lock_timestamp_utc': current_utc.timestamp(),
    'unlock_timestamp_utc': unlock_timestamp,
    'unlock_date_utc': unlock_date.strftime('%Y-%m-%d %H:%M:%S UTC')
}
```

**Wallet Claims**:
```python
claim_record = {
    'timestamp_utc': datetime.utcnow().timestamp()
}
```

**Display Format**: Always shows "UTC" suffix
- Example: `09 November 2026 at 12:34:56 UTC`

---

## 5. Files Created/Modified

### New Files Created

1. **`mark_time_capsule_wallets.py`** - Marks 920 random standard wallets as eligible
2. **`create_time_capsule_reserve.py`** - Creates 414,000 XAI reserve wallet
3. **`core/time_capsule_protocol.py`** - Time capsule system with reserve tracking
4. **`core/wallet_claiming_api.py`** - Multi-mechanism claiming API
5. **`TIME_CAPSULE_RESERVE.json`** - Reserve wallet with 414,000 XAI (generated)
6. **`time_capsule_reserve_public.json`** - Public reference (no private key)
7. **`time_capsules.json`** - Active time capsule records (generated)
8. **`pending_wallet_claims.json`** - Unclaimed wallet tracker (generated)

### Modified Files

1. **`core/node.py`**:
   - Added auto-check to `/mine` endpoint (line 320-359)
   - Integrated wallet claiming API (line 1706-1709)

2. **`core/wallet_claim_system.py`**:
   - Added time capsule offer to `claim_standard_wallet()` (line 204-234)
   - Added `_generate_time_capsule_offer_message()` method (line 391-421)

---

## 6. API Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/claim-wallet` | POST | Explicit wallet claiming |
| `/check-unclaimed-wallet/<id>` | GET | Check for unclaimed wallet notification |
| `/accept-time-capsule` | POST | Accept time capsule protocol offer |
| `/mine` | POST | Mine block (now includes auto-check) |

---

## 7. User Experience Examples

### Example 1: Browser Miner (NEW - Previously Would Miss Out!)

**Before** (Problem):
```
1. User creates browser miner
2. Mines 100 blocks
3. Never knows they had unclaimed wallet ❌
```

**After** (Fixed):
```
1. User creates browser miner
2. Calls POST /mine for first block
3. Response includes:
   {
     "bonus_wallet": {
       "message": "🎁 CONGRATULATIONS! Premium wallet auto-assigned!"
     }
   }
4. Wallet automatically saved ✓
```

### Example 2: Full Node Operator with Time Capsule

```
1. User starts full node: python core/node.py
2. Premium wallets exhausted
3. After 30 minutes: "WELCOME TO XAI COIN!" message
4. Wallet file created: xai_early_adopter_wallet.json
5. Response includes time_capsule_offer (if selected)
6. User calls POST /accept-time-capsule with {"accept": true}
7. "TIME CAPSULE PROTOCOL ENGAGED" message displayed
8. 450 XAI transferred from reserve to locked wallet
9. New empty wallet replaces original file
10. User can use new wallet immediately
11. After 1 year: Claim 500 XAI from locked wallet
```

### Example 3: Late Joiner Checking

```
1. User heard about XAI from friend
2. Calls POST /claim-wallet {"identifier": "my_node_123"}
3. Response:
   {
     "success": false,
     "error": "Uptime requirement not met",
     "required_uptime_minutes": 30,
     "current_uptime_minutes": 5
   }
4. User waits 25 more minutes
5. Calls POST /claim-wallet again
6. Response: "WELCOME TO XAI COIN! Standard wallet claimed!"
```

---

## 8. Security & Verification

### Reserve Wallet Verification

**Before accepting time capsule offers, system verifies**:
1. Reserve wallet exists
2. Reserve has >= 450 XAI available
3. If insufficient: Offer not presented

**Reserve Balance Tracking**:
```python
# Before creating time capsule
if self.reserve_balance < bonus_amount:
    return {'error': 'Insufficient reserve funds'}

# After successful creation
self._update_reserve_balance(450)  # Deduct from reserve
```

### Funding Transparency

**Every time capsule record includes**:
```json
{
  "reserve_transfer": {
    "from_address": "AIXN<reserve>...",
    "to_address": "AIXN<locked>...",
    "amount": 450,
    "timestamp_utc": 1731168035.123,
    "purpose": "Time Capsule Protocol Bonus"
  },
  "funded_from_reserve": true
}
```

---

## 9. Testing & Validation

### Setup Steps

1. **Generate Standard Wallets** (if not already done):
   ```bash
   python wallet_generator.py
   ```

2. **Mark Time Capsule Eligible Wallets**:
   ```bash
   python mark_time_capsule_wallets.py
   ```
   Output:
   ```
   ✓ Successfully marked 920 wallets as time capsule eligible
   ✓ Time capsule bonus: 450 XAI (total: 500 XAI when locked)
   ```

3. **Create Reserve Wallet**:
   ```bash
   python create_time_capsule_reserve.py
   ```
   Output:
   ```
   ✓ Time Capsule Reserve wallet created
   ✓ Reserve address: AIXN...
   ✓ Initial balance: 414,000 XAI
   ```

4. **Start Node**:
   ```bash
   python core/node.py
   ```
   Output:
   ```
   [Time Capsule Reserve] Loaded: 414,000 XAI available
   ✓ Wallet Claiming API initialized (browser miners protected!)
   ```

### Testing Claiming

**Test Premium Claim**:
```bash
curl -X POST http://localhost:8545/claim-wallet \
  -H "Content-Type: application/json" \
  -d '{"identifier": "test_node_1", "uptime_minutes": 0}'
```

**Test Standard Claim with Time Capsule**:
```bash
# Wait for premium exhaustion
curl -X POST http://localhost:8545/claim-wallet \
  -H "Content-Type: application/json" \
  -d '{"identifier": "test_node_2", "uptime_minutes": 31}'
```

**Test Time Capsule Acceptance**:
```bash
curl -X POST http://localhost:8545/accept-time-capsule \
  -H "Content-Type: application/json" \
  -d '{"wallet_address": "AIXN...", "accept": true}'
```

**Test Browser Miner Auto-Claim**:
```bash
# Mine block
curl -X POST http://localhost:8545/mine

# Response should include bonus_wallet or wallet_notification
```

---

## 10. Statistics & Monitoring

**Get Time Capsule Stats**:
```python
from core.time_capsule_protocol import TimeCapsuleProtocol

protocol = TimeCapsuleProtocol()
stats = protocol.get_time_capsule_stats()

print(f"Active Locked: {stats['active_locked']}")
print(f"Total Claimed: {stats['total_claimed']}")
print(f"Total Locked Value: {stats['total_locked_value']:,} XAI")
print(f"Total Claimed Value: {stats['total_claimed_value']:,} XAI")
```

**Check Reserve Balance**:
```bash
cat TIME_CAPSULE_RESERVE.json | grep current_balance
```

---

## 11. Key Features Summary

✓ **Triple-Mechanism Claiming** - Full node, explicit API, automatic mining check
✓ **Persistent Notifications** - Users notified until claimed
✓ **Time Capsule Protocol** - 920 wallets eligible for 50→500 XAI offer
✓ **Proper Funding** - 414,000 XAI reserve wallet tracks all bonuses
✓ **UTC Timestamps** - Protects blockchain origin anonymity
✓ **Browser Miner Protection** - Auto-check ensures no one misses out
✓ **Replacement Wallet** - Immediate empty wallet when time capsule engaged
✓ **Reserve Tracking** - Every 450 XAI deducted and verified
✓ **Deterministic Selection** - Reproducible random selection (seed=42)

---

## 12. Important Notes

### For Launch

1. **Generate Reserve BEFORE Launch**:
   ```bash
   python create_time_capsule_reserve.py
   ```

2. **Fund Reserve in Genesis Block**:
   - Reserve address must receive 414,000 XAI in genesis block
   - Address found in: `TIME_CAPSULE_RESERVE.json`

3. **Mark Wallets BEFORE Distribution**:
   ```bash
   python mark_time_capsule_wallets.py
   ```

### Marketing Messages

**For Premium Wallets** (First 2,323):
> "Start an XAI node and get a premium wallet with ~$300 in XAI INSTANTLY!"

**For Standard Wallets with Time Capsule** (920 of 10,000):
> "Got a standard wallet? You might be one of the lucky 920 selected for the Time Capsule Protocol - turn 50 XAI into 500 XAI!"

**For Browser Miners**:
> "Mine from your browser and get a FREE wallet automatically - no setup required!"

---

## Implementation Complete

**Status**: READY FOR PRODUCTION

All mechanisms tested and integrated. No early adopter can miss their wallet regardless of how they interact with XAI blockchain.

**Total Reserve Commitment**: 414,000 XAI
**Total Protected**: All early adopters (browser miners, full nodes, API users)
**Zero Friction**: Automatic detection and persistent notifications

---

**Generated**: 2025-11-09 (UTC)
**Version**: 1.0
**Status**: Production Ready ✓
