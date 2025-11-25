# XAI Tokenomics & Distribution Summary

**Last Updated:** Current specification
**Total Supply:** 120,000,000 XAI

---

## Genesis Allocation (17% = 20,404,500 XAI)

### 11 Mystery Wallets: 1,004,500 XAI (Immediate)
- XAI7f3a9c2e1b8d4f6a5c9e2d1f8b4a7c3e9d2f1b: 137,500 XAI
- XAI4b8f2d9a6c3e1f7b4d9a2c8f1e6b3d7a9c2e: 97,600 XAI
- XAI9e2f1b4d7a3c6e8f2b4d9a1c7e3f6b8d2a9c: 112,300 XAI
- XAI3c6e8f1b4d7a2c9e4f2b8d1a6c3e7f9b2d4a: 89,400 XAI
- XAI8d2a9c4e6f1b3d7a2c9e8f4b1d6a3c7e2f9b: 103,700 XAI
- XAI2f9b4d6a1c8e3f7b2d9a4c6e1f8b3d7a2c9e: 78,900 XAI
- XAI6e3f7b2d9a1c4e8f3b6d2a9c1e7f4b8d3a2c: 94,200 XAI
- XAI1c4e7f9b3d2a6c8e1f4b7d9a2c3e6f8b1d4a: 121,000 XAI
- XAI7b2d9a4c1e6f8b3d7a2c9e4f1b6d8a3c2e7f: 68,500 XAI
- XAI4e8f2b6d1a9c3e7f4b2d8a1c6e9f3b7d2a4c: 82,300 XAI
- XAI9a3c2e6f1b8d4a7c2e9f3b1d6a8c4e2f7b9d: 14,600 XAI

### Founders Vesting: 3,000,000 XAI
- **Duration:** 12 years
- **Start Date:** December 12, 2026 (Year 1)
- **Release:** 250,000 XAI annually on December 12
- **Distribution:** Same ratios as 11 mystery wallets above
- **Timelock:** Locked until first vesting date

### Development Fund: 10,000,000 XAI
- **Duration:** 10 years
- **Start Date:** June 5, 2027 (Year 3)
- **Release:** 1,000,000 XAI annually on June 5
- **Purpose:** Protocol development, audits, infrastructure
- **Timelock:** Locked until Year 3

### Marketing Fund: 6,000,000 XAI
- **Duration:** 6 years
- **Start Date:** February 10, 2026 (Year 2)
- **Release:** 1,000,000 XAI annually on February 10
- **Purpose:** Exchange listings, marketing, partnerships
- **Timelock:** Locked until Year 2

### Operations Fund: 400,000 XAI
- **Status:** Immediate (unlocked)
- **Purpose:** Node bonuses (200 XAI/month for 30-day uptime)
- **Duration:** ~2,000 months until depleted
- **No vesting:** Available from genesis

---

## Early Adopter Wallets (4.86% = 5,835,000 XAI)

### TIER 1: Premium Wallets (2,746 total = 3,888,000 XAI)

**Split:**
- 2,323 for auto-distribution (first nodes)
- 423 reserved for timed release (YOUR control)

**Characteristics:**
- **Initial Balance:** 0 XAI (NO initial allocation)
- **Mining Proceeds:** ~1,416 XAI average (from pre-mine)
- **Total Value:** ~$255 @ $0.18 floor, ~$326 @ $0.23 floor
- **Claim Method:** Run a NODE (24/7 uptime required)
- **Ongoing Bonus:** 200 XAI/month (from operations fund)
- **Atomic Swaps:** All 11 currencies enabled
- **Double Rewards:** NO (removed)

### TIER 2: Miner Wallets (2,323 total = 822,000 XAI)

**Characteristics:**
- **Balance:** ~354 XAI each (25% of premium tier)
- **Total Value:** ~$64 @ $0.18 floor, ~$81 @ $0.23 floor
- **Claim Method:** Mine 1 block (proof of mining)
- **No Ongoing Bonus:** Mining only
- **Atomic Swaps:** All 11 currencies enabled

### TIER 3: Standard Wallets (10,000 total = 500,000 XAI)

**Characteristics:**
- **Balance:** 50 XAI each
- **Total Value:** ~$9 @ $0.18, ~$11.50 @ $0.23
- **Claim Method:** Run node OR mine
- **Purpose:** Rapid onboarding
- **Atomic Swaps:** All 11 currencies enabled

### TIER 4: Micro Wallets (25,000 total = 625,000 XAI)

**Characteristics:**
- **Balance:** 25 XAI each
- **Total Value:** ~$4.50 @ $0.18, ~$5.75 @ $0.23
- **Claim Method:** Run node OR mine
- **Purpose:** Mass adoption phase
- **Atomic Swaps:** All 11 currencies enabled

### TIER 5: Empty Wallets (Unlimited = 0 XAI)

**Characteristics:**
- **Balance:** 0 XAI
- **Claim Method:** Run node OR mine
- **Purpose:** Perpetual wallet assignment after others claimed
- **Atomic Swaps:** Enabled (but need to acquire XAI first)

---

## Pre-Mining Details

### Configuration
- **Total Blocks:** 64,800 blocks (~6 months @ 2 min/block)
- **Block Reward:** 60 XAI (NO double rewards)
- **Total Mined:** 64,800 × 60 = 3,888,000 XAI
- **Distribution:** ALL 2,746 premium wallets receive proceeds
- **Timestamp:** Randomized (±30 seconds variance)
- **Mining Pattern:** Weighted random selection ensures ALL wallets mine

### Distribution Algorithm
```
1. Create weighted pool of all 2,746 premium wallets
2. For each of 64,800 blocks:
   - Select random wallet from pool
   - Assign 60 XAI mining reward
   - Randomize timestamp (±30 sec)
   - Occasionally create inter-wallet transactions
3. Ensure ALL wallets receive mining proceeds
4. Average per wallet: 3,888,000 / 2,746 = ~1,416 XAI
```

### Result Files
- `blockchain_data/blocks.json` - All 64,800 pre-mined blocks
- `premium_wallets_PRIVATE.json` - Full wallet data (KEEP PRIVATE)
- `miner_wallets_public.json` - Addresses only (public release)
- `blockchain_data/premine_summary.json` - Statistics

---

## Easter Eggs & Hidden Features (0.375% = 450,000 XAI)

### Lucky Block Rewards (Random 2x)
- **Frequency:** ~1% of all blocks
- **Reward:** 120 XAI instead of 60 XAI
- **Deterministic:** Based on secret seed (not predictable)
- **Discovery:** Miners find out: "Wait, I got double rewards!"

### Hidden Treasure Wallets (100,000 XAI)
- **Count:** 100 hidden wallets
- **Balance Each:** 1,000 XAI
- **Clues:** Cryptic messages hidden in blocks 100-10,000
- **Discovery:** Users decode clues to find private keys
- **Total Prize Pool:** 100,000 XAI

### Mystery Airdrops (350,000 XAI)
- **Scheduled Drops:** 3 major airdrops over first year
  - 3 months: 50,000 XAI (100 recipients)
  - 6 months: 100,000 XAI (500 recipients)
  - 12 months: 200,000 XAI (1,000 recipients)
- **Clue System:** Cryptic messages appear in blocks before each drop
- **Criteria:** Various (active nodes, uptime, diamond hands)

---

## Remaining Supply (77.76% = 93,310,500 XAI)

### Ongoing Mining
- **Available for Mining:** 93,310,500 XAI
- **Block Reward Start:** 60 XAI per block (120 XAI if lucky!)
- **Lucky Blocks:** ~1% get 2x reward randomly
- **Halving Schedule:** Every 9 months
- **Total Duration:** ~16 years until all mined
- **Block Time:** 2 minutes average

---

## Free Market Pricing

- **No price floor** - Pure market discovery
- **Initial suggested valuation:** $0.18-$0.23 per XAI (marketing guidance only, not enforced)
- **Price determined by:** Supply and demand, features, adoption
- **Value drivers:** Easter eggs, airdrops, node rewards, liquidity pools, atomic swaps

---

## Node Incentives

### Premium Node Operators
- **Initial:** ~1,416 XAI from pre-mine
- **Monthly Bonus:** 200 XAI (30-day uptime required)
- **Total First Year:** 1,416 + (200 × 12) = 3,816 XAI
- **Value:** $687 - $878 in first year

### Why Nodes Get More
- Nodes = infrastructure (24/7 uptime)
- Miners = one-time contribution
- 4x difference incentivizes strong node network

---

## Atomic Swap Support (11 Currencies)

### Supported Pairs
1. **BTC** - Bitcoin (HTLC_UTXO)
2. **ETH** - Ethereum (HTLC_ETHEREUM)
3. **LTC** - Litecoin (HTLC_UTXO)
4. **DOGE** - Dogecoin (HTLC_UTXO)
5. **XMR** - Monero (HTLC_MONERO)
6. **BCH** - Bitcoin Cash (HTLC_UTXO)
7. **USDT** - Tether (HTLC_ETHEREUM)
8. **ZEC** - Zcash (HTLC_UTXO)
9. **DASH** - Dash (HTLC_UTXO)
10. **USDC** - USD Coin (HTLC_ETHEREUM)
11. **DAI** - Dai (HTLC_ETHEREUM)

### Price Discovery
- **NO External APIs** (maintains anonymity)
- **Market-Derived:** Pricing from on-chain swap history
- **Stablecoins:** Always $1
- **P2P Orderbook:** On-chain order matching
- **Genesis Ratios:** Fallback if no recent swaps

---

## Wallet Claim System

### Premium Wallet Claim (Tier 1)
```
1. Download XAI node software
2. Start node (requires 24/7 uptime)
3. System generates unique node ID
4. Auto-assigns next unclaimed premium wallet
5. Private key saved to node
6. Wallet contains ~1,416 XAI from pre-mine
7. Begin receiving 200 XAI monthly bonus
```

### Miner Wallet Claim (Tier 2)
```
1. Download XAI node software
2. Start mining
3. Mine 1 block (proof of commitment)
4. System assigns next unclaimed miner wallet
5. Private key saved to node
6. Wallet contains ~354 XAI
```

### Standard/Micro/Empty Claim (Tiers 3-5)
```
1. Download XAI node software
2. Start node OR mine
3. System auto-assigns next available wallet
4. Instant participation
```

### Sybil Protection
- **Node ID:** hash(hostname + mac_address + timestamp)
- **One Wallet Per Node ID:** Cannot claim twice
- **Claim Proof:** Recorded on-chain
- **Premium Tier:** Requires actual node operation (computational cost)

---

## Security & Anonymity

### Pre-Mining Process
- **Offline:** No network exposure
- **Local Generation:** All wallets created locally
- **Randomized Metadata:** Timestamps, nonces, transaction patterns
- **No Identifying Info:** Creator identity unknown

### Price Oracle Anonymity
- **NO External API Calls:** Would leak IP addresses
- **On-Chain Data Only:** Market-derived pricing
- **P2P Gossip:** Optional price sharing (peer-to-peer)
- **Stablecoin Focus:** Direct $1 = $1 calculation

### Wallet Distribution
- **Private Keys Encrypted:** In node storage
- **Merkle Root Verification:** Prevents tampering
- **Claim Proof On-Chain:** Public addresses visible
- **Private Keys Released:** Only on claim

---

## Implementation Files

### Scripts (Run These)
```
scripts/generate_early_adopter_wallets.py  - Generate all 40,069+ wallets
scripts/premine_blockchain.py              - Pre-mine 64,800 blocks
```

### Core Systems
```
core/wallet_claim_system.py                - Auto-assign wallets
core/blockchain.py                         - Blockchain core
core/wallet.py                             - Wallet management
```

### Released Files (Public GitHub)
```
xai-blockchain/atomic_swap_11_coins.py    - HTLC protocol
xai-blockchain/mystery_price_floor.py     - Price validation
xai-blockchain/genesis_new.json           - Genesis block
miner_wallets_public.json                  - Addresses only
standard_wallets_public.json               - Addresses only
wallet_merkle_root.txt                     - Verification
```

### Private Files (NEVER Release)
```
premium_wallets_PRIVATE.json               - Private keys
standard_wallets_PRIVATE.json              - Private keys
reserved_wallets_YOURS.json                - Your 423 wallets
blockchain_data/                           - Pre-mined blockchain
```

---

## Launch Sequence

### Phase 1: Local Pre-Mining (You, Offline)
1. Run `generate_early_adopter_wallets.py` → Creates 40,069 wallets
2. Run `premine_blockchain.py` → Mines 64,800 blocks offline
3. Verify all wallets received mining proceeds
4. Package blockchain_data.zip

### Phase 2: Anonymize & Upload
1. Strip all identifying metadata from files
2. Upload to GitHub anonymously (VPN + Tor)
3. Release files:
   - Node software
   - Public wallet lists (addresses only)
   - blockchain_data.zip (pre-mined blocks)
   - Documentation

### Phase 3: Announce
1. Post on crypto forums: "First 11,373 people get free crypto"
2. Reddit, Twitter, Discord announcements
3. Community spreads word virally

### Phase 4: Watch Adoption
- **Day 1:** 1,000+ downloads
- **Week 1:** Premium wallets claimed
- **Month 1:** Standard wallets claimed
- **Month 3:** Network established with thousands of nodes

---

## Economic Summary

| Component | XAI Amount | % of Supply | USD @ $0.18 | USD @ $0.23 |
|-----------|------------|-------------|-------------|-------------|
| Genesis (11 wallets) | 1,004,500 | 0.84% | $180,810 | $231,035 |
| Founders (vested) | 3,000,000 | 2.50% | $540,000 | $690,000 |
| Development (vested) | 10,000,000 | 8.33% | $1,800,000 | $2,300,000 |
| Marketing (vested) | 6,000,000 | 5.00% | $1,080,000 | $1,380,000 |
| Operations | 400,000 | 0.33% | $72,000 | $92,000 |
| **Genesis Total** | **20,404,500** | **17.00%** | **$3,672,810** | **$4,693,035** |
| Premium Wallets | 3,888,000 | 3.24% | $699,840 | $894,240 |
| Miner Wallets | 822,000 | 0.69% | $147,960 | $189,060 |
| Standard Wallets | 500,000 | 0.42% | $90,000 | $115,000 |
| Micro Wallets | 625,000 | 0.52% | $112,500 | $143,750 |
| **Early Adopters** | **5,835,000** | **4.86%** | **$1,050,300** | **$1,342,050** |
| Hidden Treasures | 100,000 | 0.08% | $18,000 | $23,000 |
| Mystery Airdrops | 350,000 | 0.29% | $63,000 | $80,500 |
| **Easter Eggs Total** | **450,000** | **0.375%** | **$81,000** | **$103,500** |
| **Ongoing Mining** | **93,310,500** | **77.76%** | **$16,795,890** | **$21,461,415** |
| **TOTAL SUPPLY** | **120,000,000** | **100%** | **$21,600,000** | **$27,600,000** |

---

## Key Differentiators

### vs Bitcoin
- ✅ Pre-funded wallets for early adopters ($255-326 each)
- ✅ Atomic swaps with 11 currencies (not just BTC)
- ✅ 2-minute blocks (vs 10 minutes)

### vs Ethereum
- ✅ No ICO required (free distribution)
- ✅ Built-in price floor protection
- ✅ Node operators incentivized (200 XAI/month)

### vs Other Altcoins
- ✅ Anonymous launch (no known founder)
- ✅ Wide distribution (40,069 wallet holders)
- ✅ Strong node network from day 1

---

---

## Easter Egg Discovery Guide

### Lucky Blocks (2x Rewards)
**How to discover:**
- Mine as normal
- Some blocks randomly give 120 XAI instead of 60
- Pattern is deterministic but unpredictable
- ~1 in 100 blocks are lucky

**Already active!** Miners will discover this organically.

### Hidden Treasure Wallets
**How to discover:**
- Cryptic clues hidden in blocks 100-10,000
- Read block metadata carefully
- Decode clues to find addresses
- Each treasure: 1,000 XAI

**Example clue types:**
- "Seek the block where [address] whispers"
- "Hash the genesis timestamp thrice, add [number], find truth"
- "Between the echoes of transactions, [code] awaits"

**Total: 100 wallets × 1,000 XAI = 100,000 XAI prize pool**

### Mystery Airdrops
**How they work:**
- Cryptic messages appear in blocks before each drop
- 4 clues per airdrop:
  - 30 days before: Very cryptic prophecy
  - 14 days before: Amount hint
  - 7 days before: Date hint
  - 24 hours before: Specific announcement

**Scheduled:**
1. **3 months** (50,000 XAI to 100 recipients)
2. **6 months** (100,000 XAI to 500 recipients)
3. **12 months** (200,000 XAI to 1,000 recipients)

**Example clue:**
```
Block 12,847: "When the moon completes 90 cycles,
              fortune smiles upon 100 souls"
```

---

## Community Engagement Strategy

### Easter Eggs Drive Engagement:
- ✅ Users explore blockchain looking for clues
- ✅ Community collaborates to decode messages
- ✅ Forum discussions: "Did you find treasure wallet #42?"
- ✅ Social media buzz: "I got a lucky block!"
- ✅ Mystery creates FOMO: "What else is hidden?"

### Viral Moments:
- First treasure wallet discovered → Reddit post → trending
- Lucky block miner posts screenshot → Twitter viral
- Airdrop clues decoded → Discord speculation
- Community treasure hunting → organic marketing

**Easter eggs = Free marketing + engaged community**

---

**End of tokenomics and distribution specification.**
