"""
AXN Hot/Cold Wallet Manager
Implements security-focused crypto custody with 90% cold storage, 10% hot wallet split
"""

import json
import os
import time
from decimal import Decimal
from typing import Dict, List, Optional
import hashlib


class WalletType:
    """Wallet type constants"""
    HOT = 'hot'
    COLD = 'cold'


class ColdWallet:
    """Represents a cold storage wallet (offline, secure)"""

    def __init__(self, currency: str, address: str):
        self.currency = currency
        self.address = address
        self.balance = Decimal('0')
        self.last_updated = time.time()

    def to_dict(self) -> dict:
        return {
            'currency': self.currency,
            'address': self.address,
            'balance': float(self.balance),
            'last_updated': self.last_updated,
            'type': WalletType.COLD
        }


class HotWallet:
    """Represents a hot wallet (online, for withdrawals)"""

    def __init__(self, currency: str, address: str):
        self.currency = currency
        self.address = address
        self.balance = Decimal('0')
        self.min_reserve = Decimal('0')  # Minimum balance to maintain
        self.max_reserve = Decimal('0')  # Maximum balance allowed
        self.last_updated = time.time()

    def needs_refill(self) -> bool:
        """Check if hot wallet needs funds from cold storage"""
        return self.balance < self.min_reserve

    def needs_sweep(self) -> bool:
        """Check if hot wallet has excess funds to sweep to cold storage"""
        return self.balance > self.max_reserve

    def to_dict(self) -> dict:
        return {
            'currency': self.currency,
            'address': self.address,
            'balance': float(self.balance),
            'min_reserve': float(self.min_reserve),
            'max_reserve': float(self.max_reserve),
            'last_updated': self.last_updated,
            'type': WalletType.HOT,
            'status': {
                'needs_refill': self.needs_refill(),
                'needs_sweep': self.needs_sweep()
            }
        }


class HotColdWalletManager:
    """
    Manages hot/cold wallet split for maximum security

    Strategy:
    - 90% of funds in cold storage (offline, ultra-secure)
    - 10% of funds in hot wallets (online, for withdrawals)
    - Automatic sweep operations when hot wallet exceeds threshold
    - Manual refill process when hot wallet runs low
    """

    def __init__(self, data_dir: str = 'custody_data'):
        self.data_dir = data_dir
        self.hot_wallets: Dict[str, HotWallet] = {}
        self.cold_wallets: Dict[str, ColdWallet] = {}

        # Security configuration
        self.hot_wallet_ratio = Decimal('0.10')  # 10% hot, 90% cold
        self.hot_wallet_buffer = Decimal('0.20')  # 20% buffer for hot wallet fluctuations

        # Supported currencies
        self.supported_currencies = [
            'AXN', 'BTC', 'ETH', 'USDT', 'LTC', 'BNB',
            'SOL', 'XRP', 'DOGE', 'SHIB', 'MATIC', 'DOT',
            'AVAX', 'LINK', 'UNI', 'ADA'
        ]

        # Minimum balances to maintain in hot wallets (prevent running dry)
        self.min_hot_balances = {
            'AXN': Decimal('10000'),     # 10K AXN minimum
            'BTC': Decimal('0.1'),       # 0.1 BTC minimum
            'ETH': Decimal('1.0'),       # 1 ETH minimum
            'USDT': Decimal('5000'),     # $5K USDT minimum
            'LTC': Decimal('10'),        # 10 LTC minimum
            'BNB': Decimal('10'),        # 10 BNB minimum
            'SOL': Decimal('50'),        # 50 SOL minimum
            'XRP': Decimal('5000'),      # 5K XRP minimum
            'DOGE': Decimal('50000'),    # 50K DOGE minimum
            'SHIB': Decimal('10000000'), # 10M SHIB minimum
            'MATIC': Decimal('5000'),    # 5K MATIC minimum
            'DOT': Decimal('500'),       # 500 DOT minimum
            'AVAX': Decimal('100'),      # 100 AVAX minimum
            'LINK': Decimal('500'),      # 500 LINK minimum
            'UNI': Decimal('500'),       # 500 UNI minimum
            'ADA': Decimal('10000')      # 10K ADA minimum
        }

        self.operations_log: List[dict] = []
        self.load_wallets()

    def initialize_wallets(self, currency: str, hot_address: str, cold_address: str):
        """Initialize hot and cold wallets for a currency"""

        if currency not in self.supported_currencies:
            raise ValueError(f"Unsupported currency: {currency}")

        # Create hot wallet
        hot = HotWallet(currency, hot_address)
        hot.min_reserve = self.min_hot_balances.get(currency, Decimal('0'))
        hot.max_reserve = hot.min_reserve * (Decimal('1') + self.hot_wallet_buffer)
        self.hot_wallets[currency] = hot

        # Create cold wallet
        cold = ColdWallet(currency, cold_address)
        self.cold_wallets[currency] = cold

        self.save_wallets()

        return {
            'success': True,
            'currency': currency,
            'hot_wallet': hot.to_dict(),
            'cold_wallet': cold.to_dict()
        }

    def update_balance(self, currency: str, wallet_type: str, new_balance: float):
        """Update wallet balance (typically after blockchain scan)"""

        balance_decimal = Decimal(str(new_balance))

        if wallet_type == WalletType.HOT:
            if currency not in self.hot_wallets:
                raise ValueError(f"Hot wallet not initialized for {currency}")

            old_balance = self.hot_wallets[currency].balance
            self.hot_wallets[currency].balance = balance_decimal
            self.hot_wallets[currency].last_updated = time.time()

            # Log the update
            self._log_operation({
                'type': 'balance_update',
                'wallet_type': WalletType.HOT,
                'currency': currency,
                'old_balance': float(old_balance),
                'new_balance': float(balance_decimal),
                'timestamp': time.time()
            })

        elif wallet_type == WalletType.COLD:
            if currency not in self.cold_wallets:
                raise ValueError(f"Cold wallet not initialized for {currency}")

            old_balance = self.cold_wallets[currency].balance
            self.cold_wallets[currency].balance = balance_decimal
            self.cold_wallets[currency].last_updated = time.time()

            # Log the update
            self._log_operation({
                'type': 'balance_update',
                'wallet_type': WalletType.COLD,
                'currency': currency,
                'old_balance': float(old_balance),
                'new_balance': float(balance_decimal),
                'timestamp': time.time()
            })

        self.save_wallets()
        return {'success': True, 'new_balance': float(balance_decimal)}

    def get_sweep_operations(self) -> List[dict]:
        """
        Get list of hot wallets that need to be swept to cold storage

        Returns list of operations needed to move excess funds from hot to cold
        """
        sweep_ops = []

        for currency, hot_wallet in self.hot_wallets.items():
            if hot_wallet.needs_sweep():
                # Calculate amount to sweep (everything above max reserve)
                sweep_amount = hot_wallet.balance - hot_wallet.max_reserve

                if currency in self.cold_wallets:
                    sweep_ops.append({
                        'currency': currency,
                        'from_address': hot_wallet.address,
                        'to_address': self.cold_wallets[currency].address,
                        'amount': float(sweep_amount),
                        'operation': 'sweep',
                        'priority': 'high',
                        'reason': f'Hot wallet balance ({float(hot_wallet.balance)}) exceeds max reserve ({float(hot_wallet.max_reserve)})'
                    })

        return sweep_ops

    def get_refill_operations(self) -> List[dict]:
        """
        Get list of hot wallets that need to be refilled from cold storage

        Returns list of operations needed to move funds from cold to hot
        """
        refill_ops = []

        for currency, hot_wallet in self.hot_wallets.items():
            if hot_wallet.needs_refill():
                # Calculate amount to refill (to max reserve level)
                refill_amount = hot_wallet.max_reserve - hot_wallet.balance

                if currency in self.cold_wallets:
                    cold_wallet = self.cold_wallets[currency]

                    # Check if cold wallet has enough funds
                    if cold_wallet.balance >= refill_amount:
                        refill_ops.append({
                            'currency': currency,
                            'from_address': cold_wallet.address,
                            'to_address': hot_wallet.address,
                            'amount': float(refill_amount),
                            'operation': 'refill',
                            'priority': 'critical',
                            'reason': f'Hot wallet balance ({float(hot_wallet.balance)}) below min reserve ({float(hot_wallet.min_reserve)})'
                        })
                    else:
                        refill_ops.append({
                            'currency': currency,
                            'from_address': cold_wallet.address,
                            'to_address': hot_wallet.address,
                            'amount': float(cold_wallet.balance),
                            'operation': 'refill',
                            'priority': 'critical',
                            'warning': 'Insufficient cold wallet balance',
                            'reason': f'Hot wallet needs {float(refill_amount)} but cold wallet only has {float(cold_wallet.balance)}'
                        })

        return refill_ops

    def record_sweep(self, currency: str, amount: float, tx_hash: str):
        """Record a completed sweep operation"""

        amount_decimal = Decimal(str(amount))

        # Update balances
        if currency in self.hot_wallets:
            self.hot_wallets[currency].balance -= amount_decimal

        if currency in self.cold_wallets:
            self.cold_wallets[currency].balance += amount_decimal

        # Log operation
        self._log_operation({
            'type': 'sweep',
            'currency': currency,
            'amount': float(amount_decimal),
            'tx_hash': tx_hash,
            'from_wallet': WalletType.HOT,
            'to_wallet': WalletType.COLD,
            'timestamp': time.time()
        })

        self.save_wallets()

    def record_refill(self, currency: str, amount: float, tx_hash: str):
        """Record a completed refill operation"""

        amount_decimal = Decimal(str(amount))

        # Update balances
        if currency in self.cold_wallets:
            self.cold_wallets[currency].balance -= amount_decimal

        if currency in self.hot_wallets:
            self.hot_wallets[currency].balance += amount_decimal

        # Log operation
        self._log_operation({
            'type': 'refill',
            'currency': currency,
            'amount': float(amount_decimal),
            'tx_hash': tx_hash,
            'from_wallet': WalletType.COLD,
            'to_wallet': WalletType.HOT,
            'timestamp': time.time()
        })

        self.save_wallets()

    def get_total_custody(self, currency: str) -> dict:
        """Get total custody balance across hot and cold wallets"""

        hot_balance = Decimal('0')
        cold_balance = Decimal('0')

        if currency in self.hot_wallets:
            hot_balance = self.hot_wallets[currency].balance

        if currency in self.cold_wallets:
            cold_balance = self.cold_wallets[currency].balance

        total = hot_balance + cold_balance

        return {
            'currency': currency,
            'total': float(total),
            'hot': float(hot_balance),
            'cold': float(cold_balance),
            'hot_percentage': float((hot_balance / total * 100) if total > 0 else 0),
            'cold_percentage': float((cold_balance / total * 100) if total > 0 else 0)
        }

    def get_custody_report(self) -> dict:
        """Get comprehensive custody report for all currencies"""

        report = {
            'total_currencies': len(self.supported_currencies),
            'initialized_currencies': len(self.hot_wallets),
            'currencies': {},
            'needs_action': {
                'sweeps': self.get_sweep_operations(),
                'refills': self.get_refill_operations()
            },
            'timestamp': time.time()
        }

        for currency in self.supported_currencies:
            if currency in self.hot_wallets or currency in self.cold_wallets:
                report['currencies'][currency] = self.get_total_custody(currency)

        return report

    def _log_operation(self, operation: dict):
        """Log custody operation"""
        self.operations_log.append(operation)

        # Keep only last 10,000 operations
        if len(self.operations_log) > 10000:
            self.operations_log = self.operations_log[-10000:]

    def save_wallets(self):
        """Save wallet state to disk"""
        os.makedirs(self.data_dir, exist_ok=True)

        # Save hot wallets
        hot_file = os.path.join(self.data_dir, 'hot_wallets.json')
        hot_data = {
            currency: wallet.to_dict()
            for currency, wallet in self.hot_wallets.items()
        }
        with open(hot_file, 'w') as f:
            json.dump(hot_data, f, indent=2)

        # Save cold wallets
        cold_file = os.path.join(self.data_dir, 'cold_wallets.json')
        cold_data = {
            currency: wallet.to_dict()
            for currency, wallet in self.cold_wallets.items()
        }
        with open(cold_file, 'w') as f:
            json.dump(cold_data, f, indent=2)

        # Save operations log
        ops_file = os.path.join(self.data_dir, 'custody_operations.json')
        with open(ops_file, 'w') as f:
            json.dump(self.operations_log[-10000:], f, indent=2)

    def load_wallets(self):
        """Load wallet state from disk"""

        # Load hot wallets
        hot_file = os.path.join(self.data_dir, 'hot_wallets.json')
        if os.path.exists(hot_file):
            with open(hot_file, 'r') as f:
                hot_data = json.load(f)

            for currency, data in hot_data.items():
                wallet = HotWallet(currency, data['address'])
                wallet.balance = Decimal(str(data['balance']))
                wallet.min_reserve = Decimal(str(data['min_reserve']))
                wallet.max_reserve = Decimal(str(data['max_reserve']))
                wallet.last_updated = data['last_updated']
                self.hot_wallets[currency] = wallet

        # Load cold wallets
        cold_file = os.path.join(self.data_dir, 'cold_wallets.json')
        if os.path.exists(cold_file):
            with open(cold_file, 'r') as f:
                cold_data = json.load(f)

            for currency, data in cold_data.items():
                wallet = ColdWallet(currency, data['address'])
                wallet.balance = Decimal(str(data['balance']))
                wallet.last_updated = data['last_updated']
                self.cold_wallets[currency] = wallet

        # Load operations log
        ops_file = os.path.join(self.data_dir, 'custody_operations.json')
        if os.path.exists(ops_file):
            with open(ops_file, 'r') as f:
                self.operations_log = json.load(f)


if __name__ == '__main__':
    import sys
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("AXN Hot/Cold Wallet Manager")
    print("=" * 60)

    manager = HotColdWalletManager()

    # Initialize some test wallets
    print("\nInitializing test wallets...")
    print("-" * 60)

    test_currencies = ['AXN', 'BTC', 'ETH']
    for currency in test_currencies:
        result = manager.initialize_wallets(
            currency=currency,
            hot_address=f"{currency}_HOT_ADDRESS_{currency}",
            cold_address=f"{currency}_COLD_ADDRESS_{currency}"
        )
        print(f"\n{currency} Wallets Initialized:")
        print(f"  Hot Address: {result['hot_wallet']['address']}")
        print(f"  Hot Min Reserve: {result['hot_wallet']['min_reserve']}")
        print(f"  Hot Max Reserve: {result['hot_wallet']['max_reserve']}")
        print(f"  Cold Address: {result['cold_wallet']['address']}")

    # Simulate some balances
    print("\n" + "=" * 60)
    print("Simulating balance updates...")
    print("-" * 60)

    manager.update_balance('AXN', WalletType.HOT, 5000)  # Below minimum
    manager.update_balance('AXN', WalletType.COLD, 500000)

    manager.update_balance('BTC', WalletType.HOT, 0.5)  # Above maximum
    manager.update_balance('BTC', WalletType.COLD, 10.0)

    manager.update_balance('ETH', WalletType.HOT, 1.5)  # Optimal range
    manager.update_balance('ETH', WalletType.COLD, 50.0)

    # Get custody report
    print("\n" + "=" * 60)
    print("Custody Report:")
    print("-" * 60)

    report = manager.get_custody_report()

    for currency, data in report['currencies'].items():
        print(f"\n{currency}:")
        print(f"  Total: {data['total']}")
        print(f"  Hot: {data['hot']} ({data['hot_percentage']:.1f}%)")
        print(f"  Cold: {data['cold']} ({data['cold_percentage']:.1f}%)")

    # Show needed operations
    print("\n" + "=" * 60)
    print("Required Operations:")
    print("-" * 60)

    refills = report['needs_action']['refills']
    sweeps = report['needs_action']['sweeps']

    if refills:
        print(f"\nRefills Needed: {len(refills)}")
        for op in refills:
            print(f"  {op['currency']}: {op['amount']} (Priority: {op['priority']})")
            print(f"    Reason: {op['reason']}")
    else:
        print("\nNo refills needed")

    if sweeps:
        print(f"\nSweeps Needed: {len(sweeps)}")
        for op in sweeps:
            print(f"  {op['currency']}: {op['amount']} (Priority: {op['priority']})")
            print(f"    Reason: {op['reason']}")
    else:
        print("\nNo sweeps needed")
