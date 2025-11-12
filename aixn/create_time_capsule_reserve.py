"""
Create Time Capsule Reserve Wallet

This wallet holds the funding source for time capsule bonuses:
- 920 wallets × 450 XAI bonus = 414,000 XAI total reserve

This is part of the pre-mine allocation and must be accounted for
in the genesis block.
"""

import json
import os
from core.wallet import Wallet

def create_time_capsule_reserve():
    """Create the Time Capsule Reserve wallet"""

    # Calculate total reserve needed
    num_time_capsule_wallets = 920
    bonus_per_wallet = 450
    total_reserve = num_time_capsule_wallets * bonus_per_wallet

    print(f"Time Capsule Reserve Calculation:")
    print(f"  - Number of eligible wallets: {num_time_capsule_wallets}")
    print(f"  - Bonus per wallet: {bonus_per_wallet} XAI")
    print(f"  - Total reserve needed: {total_reserve:,} XAI")
    print()

    # Generate reserve wallet
    reserve_wallet = Wallet()

    reserve_data = {
        'address': reserve_wallet.address,
        'private_key': reserve_wallet.private_key,
        'public_key': reserve_wallet.public_key,
        'initial_balance': total_reserve,
        'current_balance': total_reserve,
        'purpose': 'Time Capsule Protocol Reserve',
        'max_disbursements': num_time_capsule_wallets,
        'disbursement_amount': bonus_per_wallet,
        'disbursements_made': 0,
        'created_utc': '2025-01-01 00:00:00 UTC',
        'description': 'Holds 450 XAI bonuses for time capsule protocol participants'
    }

    # Save to file
    reserve_file = 'TIME_CAPSULE_RESERVE.json'

    with open(reserve_file, 'w') as f:
        json.dump(reserve_data, f, indent=2)

    print(f"✓ Time Capsule Reserve wallet created")
    print(f"✓ Reserve address: {reserve_wallet.address}")
    print(f"✓ Initial balance: {total_reserve:,} XAI")
    print(f"✓ Saved to: {reserve_file}")
    print()

    print("IMPORTANT: This wallet must be funded in the genesis block!")
    print(f"Add this to genesis block creation with {total_reserve:,} XAI balance")
    print()

    # Also create public reference (no private key)
    public_reference = {
        'address': reserve_wallet.address,
        'balance': total_reserve,
        'purpose': 'Time Capsule Protocol Reserve',
        'max_disbursements': num_time_capsule_wallets,
        'note': 'This wallet funds the 450 XAI bonuses for time capsule participants'
    }

    public_file = 'time_capsule_reserve_public.json'
    with open(public_file, 'w') as f:
        json.dump(public_reference, f, indent=2)

    print(f"✓ Public reference saved to: {public_file}")

    return reserve_data

if __name__ == "__main__":
    print("=" * 70)
    print("XAI BLOCKCHAIN - TIME CAPSULE RESERVE WALLET GENERATOR")
    print("=" * 70)
    print()

    reserve = create_time_capsule_reserve()

    print()
    print("=" * 70)
    print("[OK] Time Capsule Reserve created successfully!")
    print("=" * 70)
