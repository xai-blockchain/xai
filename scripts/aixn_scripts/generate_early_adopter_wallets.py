"""
XAI Early Adopter Wallet Generation System

TIER 1: 1,373 Premium Wallets (~$600 each)
- 1,150 for first miners/node operators
- 223 reserved for timed release
- Double mining rewards for first 6 months
- All receive mining proceeds during pre-mine

TIER 2: 10,000 Standard Wallets (50 XAI each)
- Auto-assigned to next 10,000 adopters
- Instant participation
"""

import json
import sys
import os
import hashlib
import random
import ecdsa
import base58

from src.aixn.core.wallet import Wallet

# Constants
PREMIUM_COUNT = 1373
PREMIUM_BASE_AMOUNT = 12000  # ~$600 at $0.05/XAI
PREMIUM_VARIANCE = 0.15  # ±15% randomization

STANDARD_COUNT = 10000
STANDARD_AMOUNT = 50  # XAI per wallet

INITIAL_XAI_PRICE = 0.05  # $0.05 per XAI


def generate_premium_wallets(count=1373):
    """Generate premium wallets for early miners/node operators"""

    print(f"\n{'='*70}")
    print(f"GENERATING {count} PREMIUM WALLETS")
    print(f"{'='*70}")

    wallets = []

    for i in range(count):
        wallet = Wallet()

        # Randomize initial amount (±15% of base)
        variance = random.uniform(1 - PREMIUM_VARIANCE, 1 + PREMIUM_VARIANCE)
        initial_amount = PREMIUM_BASE_AMOUNT * variance

        # Determine tier
        tier = "miner" if i < 1150 else "reserved"

        wallet_data = {
            "index": i + 1,
            "address": wallet.address,
            "public_key": wallet.public_key,
            "private_key": wallet.private_key,
            "tier": tier,
            "initial_balance": round(initial_amount, 2),
            "usd_value": round(initial_amount * INITIAL_XAI_PRICE, 2),
            "mining_proceeds": 0.0,  # Will be updated during pre-mining
            "total_balance": round(initial_amount, 2),
            "claimed": False,
            "claimed_by": None,
            "claimed_timestamp": None,
            "claim_method": "proof_of_mining",  # Must mine 1 block to claim
            "atomic_swap_enabled": True,  # All 11 currencies
            "double_rewards_eligible": True,  # First 6 months
            "created_timestamp": 1704067200,  # Jan 1, 2024
        }

        wallets.append(wallet_data)

        if (i + 1) % 100 == 0:
            print(f"  Generated {i + 1}/{count} premium wallets...")

    print(f"\n✓ {count} premium wallets generated")

    # Statistics
    miner_wallets = [w for w in wallets if w["tier"] == "miner"]
    reserved_wallets = [w for w in wallets if w["tier"] == "reserved"]

    total_xai = sum(w["initial_balance"] for w in wallets)
    total_usd = sum(w["usd_value"] for w in wallets)

    print(f"\n  Distribution:")
    print(f"    Miner tier: {len(miner_wallets)} wallets")
    print(f"    Reserved tier: {len(reserved_wallets)} wallets")
    print(f"\n  Initial Allocation:")
    print(f"    Total XAI: {total_xai:,.2f}")
    print(f"    Total USD value: ${total_usd:,.2f}")
    print(f"    Avg per wallet: {total_xai/count:,.2f} XAI (${total_usd/count:,.2f})")

    return wallets


def generate_standard_wallets(count=10000):
    """Generate standard wallets for rapid onboarding"""

    print(f"\n{'='*70}")
    print(f"GENERATING {count} STANDARD WALLETS")
    print(f"{'='*70}")

    wallets = []

    for i in range(count):
        wallet = Wallet()

        wallet_data = {
            "index": i + 1,
            "address": wallet.address,
            "public_key": wallet.public_key,
            "private_key": wallet.private_key,
            "tier": "standard",
            "initial_balance": STANDARD_AMOUNT,
            "usd_value": STANDARD_AMOUNT * INITIAL_XAI_PRICE,
            "total_balance": STANDARD_AMOUNT,
            "claimed": False,
            "claimed_by": None,
            "claimed_timestamp": None,
            "claim_method": "auto_assign",  # Automatic on node start
            "atomic_swap_enabled": True,
            "double_rewards_eligible": False,
            "created_timestamp": 1704067200,  # Jan 1, 2024
        }

        wallets.append(wallet_data)

        if (i + 1) % 1000 == 0:
            print(f"  Generated {i + 1}/{count} standard wallets...")

    print(f"\n✓ {count} standard wallets generated")

    total_xai = count * STANDARD_AMOUNT
    total_usd = total_xai * INITIAL_XAI_PRICE

    print(f"\n  Initial Allocation:")
    print(f"    Total XAI: {total_xai:,} ({STANDARD_AMOUNT} each)")
    print(f"    Total USD value: ${total_usd:,.2f}")

    return wallets


def save_wallets(premium_wallets, standard_wallets):
    """Save wallet data to multiple files"""

    print(f"\n{'='*70}")
    print("SAVING WALLET DATA")
    print(f"{'='*70}")

    # 1. Full premium wallets (KEEP PRIVATE until release)
    premium_file = os.path.join(os.path.dirname(__file__), "..", "premium_wallets_PRIVATE.json")
    with open(premium_file, "w") as f:
        json.dump(premium_wallets, f, indent=2)
    print(f"✓ Premium wallets (full): {premium_file}")

    # 2. Full standard wallets (KEEP PRIVATE until release)
    standard_file = os.path.join(os.path.dirname(__file__), "..", "standard_wallets_PRIVATE.json")
    with open(standard_file, "w") as f:
        json.dump(standard_wallets, f, indent=2)
    print(f"✓ Standard wallets (full): {standard_file}")

    # 3. Miner tier only (1,150 wallets for public release)
    miner_wallets = [w for w in premium_wallets if w["tier"] == "miner"]
    miner_public = []
    for w in miner_wallets:
        miner_public.append(
            {
                "index": w["index"],
                "address": w["address"],
                "initial_balance": w["initial_balance"],
                "claimed": False,
            }
        )

    miner_file = os.path.join(os.path.dirname(__file__), "..", "miner_wallets_public.json")
    with open(miner_file, "w") as f:
        json.dump(miner_public, f, indent=2)
    print(f"✓ Miner wallets (public list): {miner_file}")

    # 4. Standard wallets public list (addresses only)
    standard_public = []
    for w in standard_wallets:
        standard_public.append(
            {
                "index": w["index"],
                "address": w["address"],
                "balance": w["initial_balance"],
                "claimed": False,
            }
        )

    standard_pub_file = os.path.join(
        os.path.dirname(__file__), "..", "standard_wallets_public.json"
    )
    with open(standard_pub_file, "w") as f:
        json.dump(standard_public, f, indent=2)
    print(f"✓ Standard wallets (public list): {standard_pub_file}")

    # 5. Reserved wallets (YOUR 223 wallets)
    reserved_wallets = [w for w in premium_wallets if w["tier"] == "reserved"]
    reserved_file = os.path.join(os.path.dirname(__file__), "..", "reserved_wallets_YOURS.json")
    with open(reserved_file, "w") as f:
        json.dump(reserved_wallets, f, indent=2)
    print(f"✓ Reserved wallets (YOUR 223): {reserved_file}")

    # 6. Merkle root for verification
    all_addresses = [w["address"] for w in premium_wallets] + [
        w["address"] for w in standard_wallets
    ]
    merkle_root = calculate_merkle_root(all_addresses)

    merkle_file = os.path.join(os.path.dirname(__file__), "..", "wallet_merkle_root.txt")
    with open(merkle_file, "w") as f:
        f.write(f"Premium Wallets: {len(premium_wallets)}\n")
        f.write(f"Standard Wallets: {len(standard_wallets)}\n")
        f.write(f"Total Wallets: {len(all_addresses)}\n")
        f.write(f"Merkle Root: {merkle_root}\n")
    print(f"✓ Merkle root: {merkle_file}")


def calculate_merkle_root(items):
    """Calculate merkle root of wallet addresses"""
    if len(items) == 0:
        return hashlib.sha256(b"").hexdigest()
    if len(items) == 1:
        return hashlib.sha256(items[0].encode()).hexdigest()

    hashes = [hashlib.sha256(item.encode()).hexdigest() for item in items]

    while len(hashes) > 1:
        if len(hashes) % 2 == 1:
            hashes.append(hashes[-1])

        next_level = []
        for i in range(0, len(hashes), 2):
            combined = hashes[i] + hashes[i + 1]
            next_level.append(hashlib.sha256(combined.encode()).hexdigest())
        hashes = next_level

    return hashes[0]


def display_summary(premium_wallets, standard_wallets):
    """Display comprehensive summary"""

    print(f"\n{'='*70}")
    print("EARLY ADOPTER WALLET SYSTEM SUMMARY")
    print(f"{'='*70}")

    # Premium breakdown
    miner_wallets = [w for w in premium_wallets if w["tier"] == "miner"]
    reserved_wallets = [w for w in premium_wallets if w["tier"] == "reserved"]

    premium_xai = sum(w["initial_balance"] for w in premium_wallets)
    standard_xai = sum(w["initial_balance"] for w in standard_wallets)
    total_xai = premium_xai + standard_xai

    print(f"\nTIER 1: PREMIUM WALLETS ({len(premium_wallets)} total)")
    print(f"  Miner tier: {len(miner_wallets)} wallets")
    print(f"    - Auto-assigned to first 1,150 node operators")
    print(f"    - Claim method: Mine 1 block to prove commitment")
    print(f"    - Avg balance: {premium_xai/len(premium_wallets):,.2f} XAI")
    print(f"    - Double rewards: First 6 months (blocks 0-64,800)")
    print(f"    - Atomic swaps: All 11 currencies enabled")
    print(f"")
    print(f"  Reserved tier: {len(reserved_wallets)} wallets")
    print(f"    - YOU control release timing")
    print(f"    - Release randomly over time for airdrops/contests")
    print(f"")
    print(f"  Total premium allocation: {premium_xai:,.2f} XAI")
    print(f"  USD value: ${premium_xai * INITIAL_XAI_PRICE:,.2f}")

    print(f"\nTIER 2: STANDARD WALLETS ({len(standard_wallets)} total)")
    print(f"  - Auto-assigned to next 10,000 adopters")
    print(f"  - Claim method: Simply run a node (instant)")
    print(f"  - Balance: {STANDARD_AMOUNT} XAI each")
    print(f"  - Total allocation: {standard_xai:,} XAI")
    print(f"  - USD value: ${standard_xai * INITIAL_XAI_PRICE:,.2f}")

    print(f"\nTOTAL EARLY ADOPTER ALLOCATION:")
    print(f"  {total_xai:,.2f} XAI (~{(total_xai/120000000)*100:.2f}% of 120M supply)")
    print(f"  ${total_xai * INITIAL_XAI_PRICE:,.2f} USD value")

    print(f"\nREMAINING FOR ONGOING MINING:")
    print(f"  {120000000 - total_xai:,.2f} XAI (~{((120000000-total_xai)/120000000)*100:.2f}%)")

    print(f"\n{'='*70}")
    print("DOUBLE REWARDS (First 6 Months)")
    print(f"{'='*70}")
    print(f"  Block reward: 120 XAI (normally 60)")
    print(f"  Duration: Blocks 0-64,800")
    print(f"  Time: ~6 months (270 days × 24 hrs × 60 min / 2 min blocks)")
    print(f"  Only premium wallets receive double rewards")

    print(f"\n{'='*70}")
    print("CLAIM PROCESS")
    print(f"{'='*70}")
    print(f"TIER 1 (Premium - 1,150 wallets):")
    print(f"  1. User downloads node software")
    print(f"  2. User mines 1 block (proof of commitment)")
    print(f"  3. System assigns next unclaimed premium wallet")
    print(f"  4. User receives private key with ~12,000 XAI")
    print(f"  5. Wallet already has mining proceeds from pre-mine")
    print(f"")
    print(f"TIER 2 (Standard - 10,000 wallets):")
    print(f"  1. User downloads node software")
    print(f"  2. Node starts (no mining required)")
    print(f"  3. System auto-assigns next standard wallet")
    print(f"  4. User receives private key with 50 XAI")
    print(f"  5. User can start transacting immediately")

    print(f"\n{'='*70}")
    print("FILE SECURITY")
    print(f"{'='*70}")
    print(f"KEEP PRIVATE (do NOT upload to GitHub):")
    print(f"  - premium_wallets_PRIVATE.json")
    print(f"  - standard_wallets_PRIVATE.json")
    print(f"  - reserved_wallets_YOURS.json")
    print(f"")
    print(f"UPLOAD TO GITHUB (public):")
    print(f"  - miner_wallets_public.json (addresses only)")
    print(f"  - standard_wallets_public.json (addresses only)")
    print(f"  - wallet_merkle_root.txt (verification)")

    print(f"\n{'='*70}")


if __name__ == "__main__":
    print(f"\n{'#'*70}")
    print(f"#{'':^68}#")
    print(f"#{'XAI EARLY ADOPTER WALLET GENERATOR':^68}#")
    print(f"#{'':^68}#")
    print(f"{'#'*70}\n")

    # Generate wallets
    premium_wallets = generate_premium_wallets(PREMIUM_COUNT)
    standard_wallets = generate_standard_wallets(STANDARD_COUNT)

    # Save to files
    save_wallets(premium_wallets, standard_wallets)

    # Display summary
    display_summary(premium_wallets, standard_wallets)

    print(f"\n{'='*70}")
    print("NEXT STEPS")
    print(f"{'='*70}")
    print("1. Run pre-mining script to distribute mining rewards")
    print("2. Add wallet claim system to node.py")
    print("3. Test claiming process locally")
    print("4. Upload public files only to GitHub")
    print("5. Package private files with blockchain for release")
    print(f"{'='*70}\n")
