"""
Generate 1,373 Unclaimed Wallets for Early Adopter Distribution
These wallets will receive mining rewards during pre-mining
Early node operators can claim them first-come-first-served
"""

import json
import sys
import os
import hashlib

from src.xai.core.wallet import Wallet


def generate_unclaimed_wallets(count=1373):
    """Generate wallets for early adopter distribution"""

    print(f"\nGenerating {count} unclaimed wallets...")
    print("=" * 60)

    wallets = []

    for i in range(count):
        # Generate wallet
        wallet = Wallet()

        wallet_data = {
            "index": i + 1,
            "address": wallet.address,
            "public_key": wallet.public_key,
            "private_key": wallet.private_key,
            "claimed": False,
            "claimed_by": None,
            "claimed_timestamp": None,
            "balance": 0.0,  # Will be updated during pre-mining
        }

        wallets.append(wallet_data)

        if (i + 1) % 100 == 0:
            print(f"Generated {i + 1}/{count} wallets...")

    print(f"\n✓ {count} wallets generated")

    # Save to JSON
    output_file = os.path.join(os.path.dirname(__file__), "..", "unclaimed_wallets.json")
    with open(output_file, "w") as f:
        json.dump(wallets, f, indent=2)

    print(f"✓ Saved to: {output_file}")

    # Generate wallet claim merkle root for verification
    addresses = [w["address"] for w in wallets]
    merkle_root = calculate_merkle_root(addresses)

    # Save merkle root separately (for verification)
    merkle_file = os.path.join(os.path.dirname(__file__), "..", "wallet_merkle_root.txt")
    with open(merkle_file, "w") as f:
        f.write(merkle_root)

    print(f"✓ Merkle root: {merkle_root[:32]}...")
    print(f"✓ Verification saved to: {merkle_file}")

    # Create public list (addresses only, no private keys)
    public_list = []
    for w in wallets:
        public_list.append({"index": w["index"], "address": w["address"], "claimed": False})

    public_file = os.path.join(os.path.dirname(__file__), "..", "unclaimed_wallets_public.json")
    with open(public_file, "w") as f:
        json.dump(public_list, f, indent=2)

    print(f"✓ Public list saved to: {public_file}")

    print("\n" + "=" * 60)
    print("DISTRIBUTION PLAN")
    print("=" * 60)
    print(f"Total wallets: {count}")
    print(f"These wallets will receive mining rewards during pre-mining")
    print(f"Early adopters can claim wallets by running nodes")
    print("\nClaim System:")
    print("  1. User runs node for first time")
    print("  2. Node generates proof-of-work (mining 1 block)")
    print("  3. System grants next unclaimed wallet")
    print("  4. User receives private key")
    print("  5. Wallet may contain pre-mined XAI")
    print("\n" + "=" * 60)

    return wallets


def calculate_merkle_root(items):
    """Calculate merkle root of wallet addresses"""
    if len(items) == 0:
        return hashlib.sha256(b"").hexdigest()

    if len(items) == 1:
        return hashlib.sha256(items[0].encode()).hexdigest()

    # Hash all items
    hashes = [hashlib.sha256(item.encode()).hexdigest() for item in items]

    # Build merkle tree
    while len(hashes) > 1:
        if len(hashes) % 2 == 1:
            hashes.append(hashes[-1])  # Duplicate last hash if odd

        next_level = []
        for i in range(0, len(hashes), 2):
            combined = hashes[i] + hashes[i + 1]
            next_level.append(hashlib.sha256(combined.encode()).hexdigest())

        hashes = next_level

    return hashes[0]


def get_statistics(wallets):
    """Get wallet distribution statistics"""

    total = len(wallets)
    claimed = sum(1 for w in wallets if w["claimed"])
    unclaimed = total - claimed
    total_balance = sum(w["balance"] for w in wallets)

    print("\n" + "=" * 60)
    print("WALLET STATISTICS")
    print("=" * 60)
    print(f"Total wallets: {total}")
    print(f"Claimed: {claimed}")
    print(f"Unclaimed: {unclaimed}")
    print(f"Total balance: {total_balance:,.2f} XAI")
    print(f"Avg balance: {total_balance/total:,.2f} XAI per wallet")
    print("=" * 60)


if __name__ == "__main__":
    # Generate 1,373 wallets
    wallets = generate_unclaimed_wallets(1373)
    get_statistics(wallets)

    print("\nNext steps:")
    print("1. Run pre-mining script to distribute rewards among wallets")
    print("2. Add wallet claim system to node.py")
    print("3. Upload unclaimed_wallets_public.json (addresses only)")
    print("4. Keep unclaimed_wallets.json PRIVATE until release")
