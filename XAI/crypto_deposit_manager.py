"""
Simple CryptoDepositManager stub to satisfy blockchain imports and APIs.
"""

import hashlib
import os
import time
from typing import Dict, List, Optional


class CryptoDepositManager:
    """Lightweight deposit manager that records addresses and mock history."""

    def __init__(self, exchange_wallet_manager, data_dir: str = 'crypto_deposits'):
        self.exchange_wallet_manager = exchange_wallet_manager
        self.data_dir = data_dir
        self.deposit_addresses: Dict[str, List[Dict]] = {}
        self.pending_deposits: List[Dict] = []
        self.confirmed_deposits: List[Dict] = []
        self.monitoring_active = False

    def start_monitoring(self):
        self.monitoring_active = True

    def _build_address(self, user_address: str, currency: str) -> str:
        digest = hashlib.sha256(f"{user_address}-{currency}-{time.time()}".encode()).hexdigest()
        if currency.upper() == 'BTC':
            return f"bc1q{digest[:40]}"
        return f"0x{digest[:40]}"

    def generate_deposit_address(self, user_address: str, currency: str) -> Dict:
        currency = currency.upper()
        address = self._build_address(user_address, currency)
        entry = {
            'user_address': user_address,
            'currency': currency,
            'deposit_address': address,
            'created_at': time.time(),
            'required_confirmations': 6 if currency == 'BTC' else 12
        }
        self.deposit_addresses.setdefault(user_address, []).append(entry)
        return {
            'success': True,
            'deposit_address': address,
            'currency': currency,
            'user_address': user_address,
            'required_confirmations': entry['required_confirmations'],
            'message': 'Deposit address generated'
        }

    def get_user_deposit_addresses(self, user_address: str) -> List[Dict]:
        return self.deposit_addresses.get(user_address, [])

    def get_pending_deposits(self, user_address: Optional[str] = None) -> List[Dict]:
        if user_address:
            return [deposit for deposit in self.pending_deposits if deposit.get('user_address') == user_address]
        return list(self.pending_deposits)

    def get_deposit_history(self, user_address: str, limit: int = 50) -> List[Dict]:
        history = [deposit for deposit in self.confirmed_deposits if deposit.get('user_address') == user_address]
        return history[:limit]

    def get_stats(self) -> Dict:
        total_addresses = sum(len(v) for v in self.deposit_addresses.values())
        return {
            'success': True,
            'total_addresses': total_addresses,
            'monitoring_active': self.monitoring_active
        }
