"""
Mark 920 random standard wallets as eligible for Time Capsule Protocol

Time Capsule Protocol:
- 920 of the 10,000 standard wallets (50 XAI) get special offer
- Can lock 500 XAI (50 + 450 bonus) for 1 year
- Receive new empty wallet immediately to use
- After 1 year, can claim the 500 XAI
"""

import json
import random
import os


def mark_time_capsule_wallets():
    """Mark 920 random standard wallets for time capsule eligibility"""

    wallet_file = "standard_wallets_PRIVATE.json"

    if not os.path.exists(wallet_file):
        print(f"[ERROR] {wallet_file} not found!")
        print("Please generate standard wallets first using wallet_generator.py")
        return False

    # Load standard wallets
    with open(wallet_file, "r") as f:
        wallets = json.load(f)

    print(f"Loaded {len(wallets)} standard wallets")

    if len(wallets) < 920:
        print(f"[ERROR] Need at least 920 standard wallets, found {len(wallets)}")
        return False

    # Randomly select 920 wallets for time capsule eligibility
    # Use random.seed for reproducibility if needed
    random.seed(42)  # Deterministic selection

    # Get indices for time capsule eligible wallets
    time_capsule_indices = random.sample(range(len(wallets)), 920)

    # Mark selected wallets
    for i in time_capsule_indices:
        wallets[i]["time_capsule_eligible"] = True
        wallets[i]["time_capsule_bonus"] = 450  # Bonus to add (50 + 450 = 500)
        wallets[i]["time_capsule_claimed"] = False

    # Mark remaining wallets as not eligible
    for i in range(len(wallets)):
        if i not in time_capsule_indices:
            wallets[i]["time_capsule_eligible"] = False

    # Save updated wallets
    with open(wallet_file, "w") as f:
        json.dump(wallets, f, indent=2)

    print(f"✓ Successfully marked 920 wallets as time capsule eligible")
    print(f"✓ Time capsule bonus: 450 XAI (total: 500 XAI when locked)")
    print(f"✓ Lock period: 1 year")
    print(f"✓ Updated {wallet_file}")

    return True


if __name__ == "__main__":
    print("=" * 70)
    print("XAI BLOCKCHAIN - TIME CAPSULE WALLET MARKER")
    print("=" * 70)
    print()

    success = mark_time_capsule_wallets()

    print()
    if success:
        print("[OK] Time capsule wallets marked successfully!")
    else:
        print("[FAILED] Could not mark time capsule wallets")
    print("=" * 70)
