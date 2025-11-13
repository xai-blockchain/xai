"""
Create AIXN Founder Wallets and Update Genesis Block
Allocates 121M AIXN with proper distribution
"""

import sys
import os
from src.aixn.core.wallet import Wallet
import json
import time

# Allocation (121M total)
TOTAL_SUPPLY = 121000000.0
FOUNDER_IMMEDIATE = 5000000.0       # 5M immediate
FOUNDER_VESTED = 19200000.0         # 19.2M vested over 3 years
DEV_FUND = 12100000.0               # 12.1M for development
MARKETING_FUND = 12100000.0         # 12.1M for marketing
MINING_POOL = 72600000.0            # 72.6M for block rewards

def create_founder_wallets():
    """Generate all founder wallets with ECDSA keys"""

    print("=" * 70)
    print("AIXN FOUNDER WALLET GENERATION")
    print("=" * 70)
    print()

    wallets = {}

    # 1. Founder wallet (immediate 5M)
    print("1. Creating FOUNDER wallet (5M AIXN immediate)...")
    founder_wallet = Wallet()
    wallets['founder'] = {
        'address': founder_wallet.address,
        'public_key': founder_wallet.public_key,
        'private_key': founder_wallet.private_key,
        'allocation': FOUNDER_IMMEDIATE,
        'purpose': 'Founder immediate allocation'
    }
    print(f"   Address: {founder_wallet.address}")
    print(f"   Allocation: {FOUNDER_IMMEDIATE:,.0f} AIXN")
    print()

    # 2. Founder vesting wallet (19.2M over 3 years)
    print("2. Creating FOUNDER_VESTING wallet (19.2M AIXN - 3 year vest)...")
    vesting_wallet = Wallet()
    wallets['founder_vesting'] = {
        'address': vesting_wallet.address,
        'public_key': vesting_wallet.public_key,
        'private_key': vesting_wallet.private_key,
        'allocation': FOUNDER_VESTED,
        'purpose': 'Founder vesting allocation (unlock 6.4M per year)',
        'vesting_schedule': {
            'year_1': 6400000.0,
            'year_2': 6400000.0,
            'year_3': 6400000.0
        }
    }
    print(f"   Address: {vesting_wallet.address}")
    print(f"   Allocation: {FOUNDER_VESTED:,.0f} AIXN")
    print(f"   Vesting: 6.4M/year for 3 years")
    print()

    # 3. Development fund
    print("3. Creating DEV_FUND wallet (12.1M AIXN)...")
    dev_wallet = Wallet()
    wallets['dev_fund'] = {
        'address': dev_wallet.address,
        'public_key': dev_wallet.public_key,
        'private_key': dev_wallet.private_key,
        'allocation': DEV_FUND,
        'purpose': 'Development fund (salaries, audits, infrastructure)'
    }
    print(f"   Address: {dev_wallet.address}")
    print(f"   Allocation: {DEV_FUND:,.0f} AIXN")
    print()

    # 4. Marketing fund
    print("4. Creating MARKETING_FUND wallet (12.1M AIXN)...")
    marketing_wallet = Wallet()
    wallets['marketing_fund'] = {
        'address': marketing_wallet.address,
        'public_key': marketing_wallet.public_key,
        'private_key': marketing_wallet.private_key,
        'allocation': MARKETING_FUND,
        'purpose': 'Marketing fund (exchange listings, partnerships, ads)'
    }
    print(f"   Address: {marketing_wallet.address}")
    print(f"   Allocation: {MARKETING_FUND:,.0f} AIXN")
    print()

    # 5. Mining pool (reserve for block rewards)
    print("5. Creating MINING_POOL wallet (72.6M AIXN)...")
    mining_wallet = Wallet()
    wallets['mining_pool'] = {
        'address': mining_wallet.address,
        'public_key': mining_wallet.public_key,
        'private_key': mining_wallet.private_key,
        'allocation': MINING_POOL,
        'purpose': 'Mining rewards pool (distributed via block rewards)'
    }
    print(f"   Address: {mining_wallet.address}")
    print(f"   Allocation: {MINING_POOL:,.0f} AIXN")
    print()

    # Save wallets to JSON file
    print("Saving wallets to founder_wallets.json...")
    with open('founder_wallets.json', 'w') as f:
        json.dump(wallets, f, indent=2)
    print("✅ Saved!")
    print()

    # Create updated genesis block
    print("Creating updated genesis.json with proper allocations...")
    genesis_timestamp = 1730851200.0  # Same as original

    genesis_data = {
        "index": 0,
        "timestamp": genesis_timestamp,
        "transactions": [
            {
                "sender": "COINBASE",
                "recipient": wallets['founder']['address'],
                "amount": FOUNDER_IMMEDIATE,
                "fee": 0.0,
                "timestamp": genesis_timestamp,
                "signature": None,
                "txid": f"founder_immediate_{int(genesis_timestamp)}"
            },
            {
                "sender": "COINBASE",
                "recipient": wallets['founder_vesting']['address'],
                "amount": FOUNDER_VESTED,
                "fee": 0.0,
                "timestamp": genesis_timestamp,
                "signature": None,
                "txid": f"founder_vesting_{int(genesis_timestamp)}"
            },
            {
                "sender": "COINBASE",
                "recipient": wallets['dev_fund']['address'],
                "amount": DEV_FUND,
                "fee": 0.0,
                "timestamp": genesis_timestamp,
                "signature": None,
                "txid": f"dev_fund_{int(genesis_timestamp)}"
            },
            {
                "sender": "COINBASE",
                "recipient": wallets['marketing_fund']['address'],
                "amount": MARKETING_FUND,
                "fee": 0.0,
                "timestamp": genesis_timestamp,
                "signature": None,
                "txid": f"marketing_fund_{int(genesis_timestamp)}"
            },
            {
                "sender": "COINBASE",
                "recipient": wallets['mining_pool']['address'],
                "amount": MINING_POOL,
                "fee": 0.0,
                "timestamp": genesis_timestamp,
                "signature": None,
                "txid": f"mining_pool_{int(genesis_timestamp)}"
            }
        ],
        "previous_hash": "0",
        "nonce": 0,
        "difficulty": 4,
        "hash": "0000000000000000000000000000000000000000000000000000000000000000",
        "merkle_root": "AIXN_GENESIS_121M_FOUNDER_ALLOCATION"
    }

    with open('genesis.json', 'w') as f:
        json.dump(genesis_data, f, indent=2)
    print("✅ Genesis block updated!")
    print()

    # Print summary
    print("=" * 70)
    print("ALLOCATION SUMMARY")
    print("=" * 70)
    print(f"Total Supply:        {TOTAL_SUPPLY:>15,.0f} AIXN (100%)")
    print(f"Founder (immediate): {FOUNDER_IMMEDIATE:>15,.0f} AIXN ({FOUNDER_IMMEDIATE/TOTAL_SUPPLY*100:.1f}%)")
    print(f"Founder (vested):    {FOUNDER_VESTED:>15,.0f} AIXN ({FOUNDER_VESTED/TOTAL_SUPPLY*100:.1f}%)")
    print(f"Development Fund:    {DEV_FUND:>15,.0f} AIXN ({DEV_FUND/TOTAL_SUPPLY*100:.1f}%)")
    print(f"Marketing Fund:      {MARKETING_FUND:>15,.0f} AIXN ({MARKETING_FUND/TOTAL_SUPPLY*100:.1f}%)")
    print(f"Mining Pool:         {MINING_POOL:>15,.0f} AIXN ({MINING_POOL/TOTAL_SUPPLY*100:.1f}%)")
    print("=" * 70)
    print()

    print("🔐 IMPORTANT: Save founder_wallets.json securely!")
    print("   This file contains all private keys!")
    print()
    print("✅ Ready to deploy genesis.json to all nodes!")
    print()

    return wallets

if __name__ == "__main__":
    wallets = create_founder_wallets()
