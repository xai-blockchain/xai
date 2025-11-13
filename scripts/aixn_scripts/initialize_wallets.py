"""
Initialize Hot/Cold Wallets for All Supported Currencies
Generates wallet addresses and sets up custody infrastructure
"""

import sys
import os
from src.aixn.core.hot_cold_wallet_manager import HotColdWalletManager
import hashlib
import time

def generate_wallet_address(currency: str, wallet_type: str) -> str:
    """Generate a wallet address for a currency"""
    # In production, use proper HD wallet derivation (BIP32/BIP44)
    # For now, generate deterministic addresses based on currency and type

    seed = f"XAI_EXCHANGE_{currency}_{wallet_type}_{int(time.time())}"
    address_hash = hashlib.sha256(seed.encode()).hexdigest()

    # Format address based on currency
    if currency in ['BTC', 'LTC', 'DOGE']:
        if currency == 'BTC':
            return f"bc1q{address_hash[:40]}"
        elif currency == 'LTC':
            return f"ltc1q{address_hash[:40]}"
        elif currency == 'DOGE':
            return f"D{address_hash[:33]}"

    elif currency in ['ETH', 'USDT', 'SHIB', 'MATIC', 'LINK', 'UNI', 'BNB', 'AVAX']:
        return f"0x{address_hash[:40]}"

    elif currency == 'XAI':
        return f"XAI{address_hash[:40]}"

    elif currency == 'SOL':
        return f"{address_hash[:44]}"

    elif currency == 'XRP':
        return f"r{address_hash[:33]}"

    elif currency == 'DOT':
        return f"1{address_hash[:47]}"

    elif currency == 'ADA':
        return f"addr1{address_hash[:55]}"

    else:
        return f"{currency}_{address_hash[:40]}"


def main():
    print("=" * 80)
    print("XAI Exchange - Hot/Cold Wallet Initialization")
    print("=" * 80)
    print()

    manager = HotColdWalletManager()

    currencies = [
        'XAI', 'BTC', 'ETH', 'USDT', 'LTC', 'BNB',
        'SOL', 'XRP', 'DOGE', 'SHIB', 'MATIC', 'DOT',
        'AVAX', 'LINK', 'UNI', 'ADA'
    ]

    print(f"Initializing wallets for {len(currencies)} currencies...")
    print()

    results = []

    for currency in currencies:
        print(f"Initializing {currency}...")

        # Generate addresses
        hot_address = generate_wallet_address(currency, 'HOT')
        cold_address = generate_wallet_address(currency, 'COLD')

        try:
            result = manager.initialize_wallets(
                currency=currency,
                hot_address=hot_address,
                cold_address=cold_address
            )

            results.append({
                'currency': currency,
                'status': 'SUCCESS',
                'hot_address': hot_address,
                'cold_address': cold_address,
                'hot_min': result['hot_wallet']['min_reserve'],
                'hot_max': result['hot_wallet']['max_reserve']
            })

            print(f"  Hot Wallet:  {hot_address}")
            print(f"  Cold Wallet: {cold_address}")
            print(f"  Min Reserve: {result['hot_wallet']['min_reserve']}")
            print(f"  Max Reserve: {result['hot_wallet']['max_reserve']}")
            print(f"  Status: SUCCESS")

        except Exception as e:
            results.append({
                'currency': currency,
                'status': 'FAILED',
                'error': str(e)
            })
            print(f"  Status: FAILED - {e}")

        print()

    # Summary
    print("=" * 80)
    print("INITIALIZATION SUMMARY")
    print("=" * 80)
    print()

    successful = [r for r in results if r['status'] == 'SUCCESS']
    failed = [r for r in results if r['status'] == 'FAILED']

    print(f"Total Currencies: {len(currencies)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print()

    if successful:
        print("Successfully Initialized:")
        print("-" * 80)
        for r in successful:
            print(f"  {r['currency']:6s} - Hot: {r['hot_address'][:20]}... | Cold: {r['cold_address'][:20]}...")
        print()

    if failed:
        print("Failed Initializations:")
        print("-" * 80)
        for r in failed:
            print(f"  {r['currency']:6s} - Error: {r['error']}")
        print()

    # Get custody report
    print("=" * 80)
    print("CUSTODY REPORT")
    print("=" * 80)
    print()

    report = manager.get_custody_report()

    print(f"Initialized Currencies: {report['initialized_currencies']}/{report['total_currencies']}")
    print()

    print("Current Balances:")
    print("-" * 80)
    print(f"{'Currency':<10} {'Total':>15} {'Hot':>15} {'Cold':>15} {'Hot %':>10}")
    print("-" * 80)

    for currency, data in report['currencies'].items():
        print(f"{currency:<10} {data['total']:>15.8f} {data['hot']:>15.8f} "
              f"{data['cold']:>15.8f} {data['hot_percentage']:>9.2f}%")

    print()
    print("=" * 80)
    print("IMPORTANT NEXT STEPS")
    print("=" * 80)
    print()
    print("1. SECURE COLD WALLET ADDRESSES")
    print("   - Store cold wallet private keys in offline hardware wallets")
    print("   - Use air-gapped computers for key generation")
    print("   - Create encrypted backups in multiple secure locations")
    print()
    print("2. FUND WALLETS")
    print("   - Transfer initial crypto to hot wallets for operations")
    print("   - Keep 90% in cold storage, 10% in hot wallets")
    print()
    print("3. SET UP MONITORING")
    print("   - Run daily custody report checks")
    print("   - Monitor sweep/refill operations")
    print("   - Set up alerts for low hot wallet balances")
    print()
    print("4. IMPLEMENT MULTI-SIG (Phase 2)")
    print("   - Require 2-of-3 or 3-of-5 signatures for cold wallet withdrawals")
    print("   - Distribute keys among trusted team members")
    print()

    print("Wallet initialization complete!")
    print()


if __name__ == '__main__':
    main()
