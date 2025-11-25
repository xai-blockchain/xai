"""
AXN Exchange Wallet Manager - Multi-Currency Custody System
Handles deposits, withdrawals, and balance management for all supported currencies
"""

import json
import os
import time
from decimal import Decimal
from typing import Dict, List, Optional
import hashlib


class ExchangeWallet:
    """Manages multi-currency balances for a single user"""

    def __init__(self, user_address: str):
        self.user_address = user_address
        self.balances: Dict[str, Decimal] = {
            "USD": Decimal("0"),
            "AXN": Decimal("0"),
            "BTC": Decimal("0"),
            "ETH": Decimal("0"),
            "USDT": Decimal("0"),
            "LTC": Decimal("0"),
            "BNB": Decimal("0"),
        }
        self.locked_balances: Dict[str, Decimal] = {
            "USD": Decimal("0"),
            "AXN": Decimal("0"),
            "BTC": Decimal("0"),
            "ETH": Decimal("0"),
            "USDT": Decimal("0"),
            "LTC": Decimal("0"),
            "BNB": Decimal("0"),
        }

    def get_available_balance(self, currency: str) -> Decimal:
        """Get available (unlocked) balance"""
        total = self.balances.get(currency, Decimal("0"))
        locked = self.locked_balances.get(currency, Decimal("0"))
        return total - locked

    def get_total_balance(self, currency: str) -> Decimal:
        """Get total balance including locked funds"""
        return self.balances.get(currency, Decimal("0"))

    def deposit(self, currency: str, amount: Decimal) -> bool:
        """Add funds to wallet"""
        if amount <= 0:
            return False

        if currency not in self.balances:
            self.balances[currency] = Decimal("0")

        self.balances[currency] += amount
        return True

    def withdraw(self, currency: str, amount: Decimal) -> bool:
        """Remove funds from wallet"""
        if amount <= 0:
            return False

        available = self.get_available_balance(currency)
        if available < amount:
            return False

        self.balances[currency] -= amount
        return True

    def lock_balance(self, currency: str, amount: Decimal) -> bool:
        """Lock balance for pending orders"""
        available = self.get_available_balance(currency)
        if available < amount:
            return False

        if currency not in self.locked_balances:
            self.locked_balances[currency] = Decimal("0")

        self.locked_balances[currency] += amount
        return True

    def unlock_balance(self, currency: str, amount: Decimal) -> bool:
        """Unlock balance when order cancelled"""
        if currency not in self.locked_balances:
            return False

        locked = self.locked_balances[currency]
        if locked < amount:
            return False

        self.locked_balances[currency] -= amount
        return True

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "user_address": self.user_address,
            "balances": {k: float(v) for k, v in self.balances.items()},
            "locked_balances": {k: float(v) for k, v in self.locked_balances.items()},
            "available_balances": {
                k: float(self.get_available_balance(k)) for k in self.balances.keys()
            },
        }


class ExchangeWalletManager:
    """Manages all user wallets and handles custody"""

    def __init__(self, data_dir: str = "exchange_data"):
        self.data_dir = data_dir
        self.wallets: Dict[str, ExchangeWallet] = {}
        self.transactions: List[dict] = []
        self.load_wallets()

    def get_wallet(self, user_address: str) -> ExchangeWallet:
        """Get or create wallet for user"""
        if user_address not in self.wallets:
            wallet = ExchangeWallet(user_address)
            self.wallets[user_address] = wallet

        return self.wallets[user_address]

    def deposit(
        self,
        user_address: str,
        currency: str,
        amount: float,
        deposit_type: str = "manual",
        tx_hash: Optional[str] = None,
    ) -> dict:
        """Deposit funds into user's exchange wallet"""
        wallet = self.get_wallet(user_address)
        amount_decimal = Decimal(str(amount))

        if wallet.deposit(currency, amount_decimal):
            # Record transaction
            tx = {
                "id": self._generate_tx_id(),
                "type": "deposit",
                "user_address": user_address,
                "currency": currency,
                "amount": float(amount_decimal),
                "deposit_type": deposit_type,  # manual, bank_transfer, crypto_deposit
                "tx_hash": tx_hash,
                "timestamp": time.time(),
                "status": "completed",
            }
            self.transactions.append(tx)
            self.save_wallets()

            return {
                "success": True,
                "transaction": tx,
                "new_balance": float(wallet.get_total_balance(currency)),
            }

        return {"success": False, "error": "Invalid deposit amount"}

    def withdraw(self, user_address: str, currency: str, amount: float, destination: str) -> dict:
        """Withdraw funds from user's exchange wallet"""
        wallet = self.get_wallet(user_address)
        amount_decimal = Decimal(str(amount))

        # Check minimum withdrawal
        min_withdrawals = {"USD": 10.0, "AXN": 100.0, "BTC": 0.001, "ETH": 0.01, "USDT": 10.0}

        if amount < min_withdrawals.get(currency, 0):
            return {
                "success": False,
                "error": f"Minimum withdrawal: {min_withdrawals.get(currency, 0)} {currency}",
            }

        if wallet.withdraw(currency, amount_decimal):
            # Record transaction
            tx = {
                "id": self._generate_tx_id(),
                "type": "withdrawal",
                "user_address": user_address,
                "currency": currency,
                "amount": float(amount_decimal),
                "destination": destination,
                "timestamp": time.time(),
                "status": "pending",  # Would be processed by withdrawal processor
            }
            self.transactions.append(tx)
            self.save_wallets()

            return {
                "success": True,
                "transaction": tx,
                "new_balance": float(wallet.get_total_balance(currency)),
            }

        return {"success": False, "error": "Insufficient balance"}

    def execute_trade(
        self,
        buyer_address: str,
        seller_address: str,
        base_currency: str,
        quote_currency: str,
        base_amount: float,
        quote_amount: float,
    ) -> dict:
        """Execute a trade between two users with balance transfers"""
        buyer_wallet = self.get_wallet(buyer_address)
        seller_wallet = self.get_wallet(seller_address)

        base_amt = Decimal(str(base_amount))
        quote_amt = Decimal(str(quote_amount))

        # Verify buyer has enough quote currency (USD/BTC/ETH)
        if buyer_wallet.get_available_balance(quote_currency) < quote_amt:
            return {"success": False, "error": f"Buyer insufficient {quote_currency} balance"}

        # Verify seller has enough base currency (AXN)
        if seller_wallet.get_available_balance(base_currency) < base_amt:
            return {"success": False, "error": f"Seller insufficient {base_currency} balance"}

        # Execute transfers
        # Buyer: pays quote currency, receives base currency
        buyer_wallet.withdraw(quote_currency, quote_amt)
        buyer_wallet.deposit(base_currency, base_amt)

        # Seller: pays base currency, receives quote currency
        seller_wallet.withdraw(base_currency, base_amt)
        seller_wallet.deposit(quote_currency, quote_amt)

        # Record transaction
        tx = {
            "id": self._generate_tx_id(),
            "type": "trade",
            "buyer": buyer_address,
            "seller": seller_address,
            "base_currency": base_currency,
            "quote_currency": quote_currency,
            "base_amount": float(base_amt),
            "quote_amount": float(quote_amt),
            "price": float(quote_amt / base_amt),
            "timestamp": time.time(),
        }
        self.transactions.append(tx)
        self.save_wallets()

        return {
            "success": True,
            "transaction": tx,
            "buyer_balances": buyer_wallet.to_dict()["available_balances"],
            "seller_balances": seller_wallet.to_dict()["available_balances"],
        }

    def lock_for_order(self, user_address: str, currency: str, amount: float) -> bool:
        """Lock balance when placing order"""
        wallet = self.get_wallet(user_address)
        return wallet.lock_balance(currency, Decimal(str(amount)))

    def unlock_from_order(self, user_address: str, currency: str, amount: float) -> bool:
        """Unlock balance when order cancelled"""
        wallet = self.get_wallet(user_address)
        return wallet.unlock_balance(currency, Decimal(str(amount)))

    def get_balance(self, user_address: str, currency: str) -> dict:
        """Get balance for specific currency"""
        wallet = self.get_wallet(user_address)
        return {
            "currency": currency,
            "total": float(wallet.get_total_balance(currency)),
            "available": float(wallet.get_available_balance(currency)),
            "locked": float(wallet.locked_balances.get(currency, Decimal("0"))),
        }

    def get_all_balances(self, user_address: str) -> dict:
        """Get all balances for user"""
        wallet = self.get_wallet(user_address)
        return wallet.to_dict()

    def get_transaction_history(self, user_address: str, limit: int = 50) -> List[dict]:
        """Get transaction history for user"""
        user_txs = [
            tx
            for tx in self.transactions
            if tx.get("user_address") == user_address
            or tx.get("buyer") == user_address
            or tx.get("seller") == user_address
        ]

        # Sort by timestamp, most recent first
        user_txs.sort(key=lambda x: x["timestamp"], reverse=True)
        return user_txs[:limit]

    def _generate_tx_id(self) -> str:
        """Generate unique transaction ID"""
        data = f"{time.time()}_{len(self.transactions)}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def save_wallets(self):
        """Save wallets to disk"""
        os.makedirs(self.data_dir, exist_ok=True)

        # Save wallets
        wallets_file = os.path.join(self.data_dir, "wallets.json")
        wallets_data = {
            address: {
                "balances": {k: float(v) for k, v in wallet.balances.items()},
                "locked_balances": {k: float(v) for k, v in wallet.locked_balances.items()},
            }
            for address, wallet in self.wallets.items()
        }

        with open(wallets_file, "w") as f:
            json.dump(wallets_data, f, indent=2)

        # Save transactions (keep last 10000)
        tx_file = os.path.join(self.data_dir, "transactions.json")
        with open(tx_file, "w") as f:
            json.dump(self.transactions[-10000:], f, indent=2)

    def load_wallets(self):
        """Load wallets from disk"""
        wallets_file = os.path.join(self.data_dir, "wallets.json")
        tx_file = os.path.join(self.data_dir, "transactions.json")

        # Load wallets
        if os.path.exists(wallets_file):
            with open(wallets_file, "r") as f:
                wallets_data = json.load(f)

            for address, data in wallets_data.items():
                wallet = ExchangeWallet(address)
                wallet.balances = {k: Decimal(str(v)) for k, v in data["balances"].items()}
                wallet.locked_balances = {
                    k: Decimal(str(v)) for k, v in data["locked_balances"].items()
                }
                self.wallets[address] = wallet

        # Load transactions
        if os.path.exists(tx_file):
            with open(tx_file, "r") as f:
                self.transactions = json.load(f)

    def get_stats(self) -> dict:
        """Get exchange statistics"""
        total_users = len(self.wallets)
        total_volume = {}

        for tx in self.transactions:
            if tx["type"] == "trade":
                currency = tx["quote_currency"]
                amount = tx["quote_amount"]
                total_volume[currency] = total_volume.get(currency, 0) + amount

        return {
            "total_users": total_users,
            "total_transactions": len(self.transactions),
            "total_volume_24h": total_volume,
            "currencies_supported": ["USD", "AXN", "BTC", "ETH", "USDT", "LTC", "BNB"],
        }
