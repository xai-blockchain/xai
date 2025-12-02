"""
Mark 920 random standard wallets as eligible for Time Capsule Protocol

Time Capsule Protocol:
- 920 of the 10,000 standard wallets (50 XAI) get special offer
- Can lock 500 XAI (50 + 450 bonus) for 1 year
- Receive new empty wallet immediately to use
- After 1 year, can claim the 500 XAI

SECURITY NOTE:
- Uses cryptographically secure randomness (secrets module) to prevent
  predictable wallet selection
- Selection is logged to time_capsule_selection.log for auditability
- Previous version used random.seed(42) which was deterministic and insecure
"""

import json
import secrets
import os
import hashlib
from datetime import datetime


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

    # SECURITY: Cryptographically secure random selection
    # Uses secrets module to prevent predictable wallet selection
    # Each run produces different, unpredictable results

    # Generate cryptographically secure random selection
    # We use Fisher-Yates shuffle with secrets.randbelow for unbiased selection
    all_indices = list(range(len(wallets)))
    time_capsule_indices = []

    for _ in range(920):
        # Cryptographically secure random index selection
        random_index = secrets.randbelow(len(all_indices))
        selected_wallet_idx = all_indices.pop(random_index)
        time_capsule_indices.append(selected_wallet_idx)

    # Sort for cleaner output
    time_capsule_indices.sort()

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

    # AUDITABILITY: Log the selection for transparency
    # Create a verifiable audit trail of which wallets were selected
    log_file = "time_capsule_selection.log"
    timestamp = datetime.utcnow().isoformat()

    # Create audit record with hash of selected addresses
    selected_addresses = [wallets[i]["address"] for i in time_capsule_indices]
    addresses_str = ",".join(sorted(selected_addresses))
    selection_hash = hashlib.sha256(addresses_str.encode()).hexdigest()

    with open(log_file, "a") as f:
        f.write(f"\n{'=' * 70}\n")
        f.write(f"Time Capsule Selection - {timestamp}\n")
        f.write(f"{'=' * 70}\n")
        f.write(f"Total wallets: {len(wallets)}\n")
        f.write(f"Selected: 920\n")
        f.write(f"Selection hash: {selection_hash}\n")
        f.write(f"\nSelected wallet indices:\n")
        f.write(f"{time_capsule_indices}\n")
        f.write(f"\nSelected addresses (first 10):\n")
        for addr in selected_addresses[:10]:
            f.write(f"  {addr}\n")
        f.write(f"  ... ({len(selected_addresses) - 10} more)\n")
        f.write(f"{'=' * 70}\n")

    print(f"✓ Successfully marked 920 wallets as time capsule eligible")
    print(f"✓ Time capsule bonus: 450 XAI (total: 500 XAI when locked)")
    print(f"✓ Lock period: 1 year")
    print(f"✓ Updated {wallet_file}")
    print(f"✓ Audit log: {log_file}")
    print(f"✓ Selection hash: {selection_hash[:16]}...")

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
