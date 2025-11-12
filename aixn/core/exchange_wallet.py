"""
XAI Multi-Currency Exchange Wallet

Tracks balances, locks, and trades for every supported asset.
"""

import hashlib
import json
import os
import time
from decimal import Decimal
from typing import Dict, List, Optional


SUPPORTED_TOKENS = [
    'XAI', 'BTC', 'ETH', 'USDT', 'USDC', 'DAI', 'LTC',
    'BCH', 'DOGE', 'BNB', 'ADA', 'MATIC', 'LINK', 'AVAX', 'SOL'
]


def _normalize_currency(currency: str) -> str:
    return currency.strip().upper()


class ExchangeWallet:
    """Holds balances and locked funds for a single user"""

    def __init__(self, user_address: str):
        self.user_address = user_address
        self.balances: Dict[str, Decimal] = {
            symbol: Decimal('0') for symbol in SUPPORTED_TOKENS
        }
        self.locked_balances: Dict[str, Decimal] = {
            symbol: Decimal('0') for symbol in SUPPORTED_TOKENS
        }

    def _ensure_currency(self, currency: str):
        currency = _normalize_currency(currency)
        if currency not in self.balances:
            self.balances[currency] = Decimal('0')
            self.locked_balances[currency] = Decimal('0')
        return currency

    def get_available_balance(self, currency: str) -> Decimal:
        currency = self._ensure_currency(currency)
        return self.balances[currency] - self.locked_balances.get(currency, Decimal('0'))

    def get_total_balance(self, currency: str) -> Decimal:
        currency = self._ensure_currency(currency)
        return self.balances[currency]

    def deposit(self, currency: str, amount: Decimal) -> bool:
        currency = self._ensure_currency(currency)
        if amount <= 0:
            return False
        self.balances[currency] += amount
        return True

    def withdraw(self, currency: str, amount: Decimal) -> bool:
        currency = self._ensure_currency(currency)
        if amount <= 0:
            return False

        available = self.get_available_balance(currency)
        if available < amount:
            return False

        self.balances[currency] -= amount
        return True

    def lock_balance(self, currency: str, amount: Decimal) -> bool:
        currency = self._ensure_currency(currency)
        if amount <= 0:
            return False

        available = self.get_available_balance(currency)
        if available < amount:
            return False

        self.locked_balances[currency] += amount
        return True

    def unlock_balance(self, currency: str, amount: Decimal) -> bool:
        currency = self._ensure_currency(currency)
        locked = self.locked_balances.get(currency, Decimal('0'))
        if locked < amount or amount <= 0:
            return False

        self.locked_balances[currency] -= amount
        return True

    def to_dict(self) -> dict:
        return {
            'user_address': self.user_address,
            'balances': {k: float(v) for k, v in self.balances.items()},
            'locked_balances': {k: float(v) for k, v in self.locked_balances.items()},
            'available_balances': {
                k: float(self.get_available_balance(k)) for k in self.balances.keys()
            }
        }


class ExchangeWalletManager:
    """Manages custody operations for every user wallet"""

    def __init__(self, data_dir: str = 'exchange_data'):
        self.data_dir = data_dir
        self.wallets: Dict[str, ExchangeWallet] = {}
        self.transactions: List[dict] = []
        os.makedirs(self.data_dir, exist_ok=True)
        self.load_wallets()

    def get_wallet(self, user_address: str) -> ExchangeWallet:
        if user_address not in self.wallets:
            self.wallets[user_address] = ExchangeWallet(user_address)
        return self.wallets[user_address]

    def deposit(self, user_address: str, currency: str, amount: float,
                deposit_type: str = 'manual', tx_hash: Optional[str] = None) -> dict:
        wallet = self.get_wallet(user_address)
        if wallet.deposit(_normalize_currency(currency), Decimal(str(amount))):
            tx = {
                'id': self._generate_tx_id(),
                'type': 'deposit',
                'user_address': user_address,
                'currency': currency.upper(),
                'amount': float(amount),
                'deposit_type': deposit_type,
                'tx_hash': tx_hash,
                'timestamp': time.time(),
                'status': 'completed'
            }
            self.transactions.append(tx)
            self.save_wallets()
            return {'success': True, 'transaction': tx, 'new_balance': float(wallet.get_total_balance(currency))}
        return {'success': False, 'error': 'Invalid deposit amount'}

    def withdraw(self, user_address: str, currency: str, amount: float,
                 destination: str) -> dict:
        wallet = self.get_wallet(user_address)
        amount_decimal = Decimal(str(amount))

        min_withdrawals = {
            'USD': 10.0,
            'XAI': 50.0,
            'BTC': 0.001,
            'ETH': 0.01,
            'USDT': 10.0
        }

        if amount < min_withdrawals.get(currency.upper(), 0):
            return {
                'success': False,
                'error': f'Minimum withdrawal: {min_withdrawals.get(currency.upper(), 0)} {currency.upper()}'
            }

        if wallet.withdraw(currency, amount_decimal):
            tx = {
                'id': self._generate_tx_id(),
                'type': 'withdrawal',
                'user_address': user_address,
                'currency': currency.upper(),
                'amount': float(amount_decimal),
                'destination': destination,
                'timestamp': time.time(),
                'status': 'pending'
            }
            self.transactions.append(tx)
            self.save_wallets()
            return {'success': True, 'transaction': tx, 'new_balance': float(wallet.get_total_balance(currency))}

        return {'success': False, 'error': 'Insufficient balance'}

    def execute_trade(self, buyer_address: str, seller_address: str,
                     base_currency: str, quote_currency: str,
                     base_amount: float, quote_amount: float) -> dict:
        buyer_wallet = self.get_wallet(buyer_address)
        seller_wallet = self.get_wallet(seller_address)

        base_amt = Decimal(str(base_amount))
        quote_amt = Decimal(str(quote_amount))

        if buyer_wallet.get_available_balance(quote_currency) < quote_amt:
            return {'success': False, 'error': f'Buyer insufficient {quote_currency} balance'}

        if seller_wallet.get_available_balance(base_currency) < base_amt:
            return {'success': False, 'error': f'Seller insufficient {base_currency} balance'}

        buyer_wallet.withdraw(quote_currency, quote_amt)
        buyer_wallet.deposit(base_currency, base_amt)

        seller_wallet.withdraw(base_currency, base_amt)
        seller_wallet.deposit(quote_currency, quote_amt)

        tx = {
            'id': self._generate_tx_id(),
            'type': 'trade',
            'buyer': buyer_address,
            'seller': seller_address,
            'base_currency': base_currency.upper(),
            'quote_currency': quote_currency.upper(),
            'base_amount': float(base_amt),
            'quote_amount': float(quote_amt),
            'price': float(quote_amt / base_amt),
            'timestamp': time.time()
        }
        self.transactions.append(tx)
        self.save_wallets()

        return {
            'success': True,
            'transaction': tx,
            'buyer_balances': buyer_wallet.to_dict()['available_balances'],
            'seller_balances': seller_wallet.to_dict()['available_balances']
        }

    def lock_for_order(self, user_address: str, currency: str, amount: float) -> bool:
        wallet = self.get_wallet(user_address)
        return wallet.lock_balance(currency, Decimal(str(amount)))

    def unlock_from_order(self, user_address: str, currency: str, amount: float) -> bool:
        wallet = self.get_wallet(user_address)
        return wallet.unlock_balance(currency, Decimal(str(amount)))

    def get_balance(self, user_address: str, currency: str) -> dict:
        wallet = self.get_wallet(user_address)
        currency = currency.upper()
        return {
            'currency': currency,
            'total': float(wallet.get_total_balance(currency)),
            'available': float(wallet.get_available_balance(currency)),
            'locked': float(wallet.locked_balances.get(currency, Decimal('0')))
        }

    def get_all_balances(self, user_address: str) -> dict:
        wallet = self.get_wallet(user_address)
        return wallet.to_dict()

    def get_transaction_history(self, user_address: str, limit: int = 50) -> List[dict]:
        user_txs = [
            tx for tx in self.transactions
            if tx.get('user_address') == user_address
            or tx.get('buyer') == user_address
            or tx.get('seller') == user_address
        ]

        user_txs.sort(key=lambda x: x['timestamp'], reverse=True)
        return user_txs[:limit]

    def _generate_tx_id(self) -> str:
        data = f"{time.time()}_{len(self.transactions)}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def save_wallets(self):
        wallets_file = os.path.join(self.data_dir, 'wallets.json')
        tx_file = os.path.join(self.data_dir, 'transactions.json')

        wallets_data = {
            address: {
                'balances': {k: float(v) for k, v in wallet.balances.items()},
                'locked_balances': {k: float(v) for k, v in wallet.locked_balances.items()}
            }
            for address, wallet in self.wallets.items()
        }

        with open(wallets_file, 'w') as f:
            json.dump(wallets_data, f, indent=2)

        with open(tx_file, 'w') as f:
            json.dump(self.transactions[-10000:], f, indent=2)

    def load_wallets(self):
        wallets_file = os.path.join(self.data_dir, 'wallets.json')
        tx_file = os.path.join(self.data_dir, 'transactions.json')

        if os.path.exists(wallets_file):
            with open(wallets_file, 'r') as f:
                wallets_data = json.load(f)

            for address, data in wallets_data.items():
                wallet = ExchangeWallet(address)
                wallet.balances = {k: Decimal(str(v)) for k, v in data['balances'].items()}
                wallet.locked_balances = {
                    k: Decimal(str(v)) for k, v in data['locked_balances'].items()
                }
                self.wallets[address] = wallet

        if os.path.exists(tx_file):
            with open(tx_file, 'r') as f:
                self.transactions = json.load(f)

    def get_stats(self) -> dict:
        total_users = len(self.wallets)
        total_volume: Dict[str, float] = {}

        for tx in self.transactions:
            if tx['type'] == 'trade':
                currency = tx['quote_currency']
                amount = tx['quote_amount']
                total_volume[currency] = total_volume.get(currency, 0) + amount

        return {
            'total_users': total_users,
            'total_transactions': len(self.transactions),
            'total_volume': total_volume,
            'currencies_supported': SUPPORTED_TOKENS
        }
