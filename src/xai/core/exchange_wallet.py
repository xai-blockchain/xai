from __future__ import annotations

"""
AXN Exchange Wallet Manager - Multi-Currency Custody System
Handles deposits, withdrawals, and balance management for all supported currencies
"""

import hashlib
import json
import os
import threading
import time
from decimal import Decimal
from typing import Any

from xai.core.constants import (
    MAX_TRANSACTION_HISTORY_SIZE,
    MIN_WITHDRAWAL_BTC,
    MIN_WITHDRAWAL_ETH,
    MIN_WITHDRAWAL_USD,
    MIN_WITHDRAWAL_USDT,
    MIN_WITHDRAWAL_XAI,
)

class ExchangeWallet:
    """Manages multi-currency balances for a single user"""

    def __init__(self, user_address: str):
        self.user_address = user_address
        self.balances: dict[str, Decimal] = {
            "USD": Decimal("0"),
            "AXN": Decimal("0"),
            "BTC": Decimal("0"),
            "ETH": Decimal("0"),
            "USDT": Decimal("0"),
            "LTC": Decimal("0"),
            "BNB": Decimal("0"),
        }
        self.locked_balances: dict[str, Decimal] = {
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

    _WITHDRAWAL_STATUSES = {"pending", "completed", "failed", "flagged"}

    def __init__(self, data_dir: str = "exchange_data"):
        self.data_dir = data_dir
        self.wallets: dict[str, ExchangeWallet] = {}
        self.transactions: list[dict] = []
        self.pending_withdrawals: dict[str, dict] = {}
        self.lock = threading.RLock()
        self.load_wallets()
        self._refresh_pending_withdrawals()

    def _refresh_pending_withdrawals(self) -> None:
        """Rebuild the cache of pending withdrawal transactions."""
        with self.lock:
            self.pending_withdrawals = {
                tx["id"]: tx
                for tx in self.transactions
                if tx.get("type") == "withdrawal" and tx.get("status") == "pending"
            }

    def get_wallet(self, user_address: str) -> ExchangeWallet:
        """Get or create wallet for user"""
        with self.lock:
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
        tx_hash: str | None = None,
    ) -> dict:
        """Deposit funds into user's exchange wallet"""
        amount_decimal = Decimal(str(amount))
        with self.lock:
            wallet = self.get_wallet(user_address)

            if wallet.deposit(currency, amount_decimal):
                tx = {
                    "id": self._generate_tx_id(),
                    "type": "deposit",
                    "user_address": user_address,
                    "currency": currency,
                    "amount": float(amount_decimal),
                    "deposit_type": deposit_type,
                    "tx_hash": tx_hash,
                    "timestamp": time.time(),
                    "status": "completed",
                }
                self.transactions.append(tx)
                self.save_wallets()

                return {
                    "success": True,
                    "transaction": tx.copy(),
                    "new_balance": float(wallet.get_total_balance(currency)),
                }

        return {"success": False, "error": "Invalid deposit amount"}

    def withdraw(
        self,
        user_address: str,
        currency: str,
        amount: float,
        destination: str,
        *,
        compliance_metadata: dict[str, Any] | None = None,
    ) -> dict:
        """Withdraw funds from user's exchange wallet"""
        min_withdrawals = {
            "USD": MIN_WITHDRAWAL_USD,
            "AXN": MIN_WITHDRAWAL_XAI,
            "BTC": MIN_WITHDRAWAL_BTC,
            "ETH": MIN_WITHDRAWAL_ETH,
            "USDT": MIN_WITHDRAWAL_USDT,
        }
        if amount < min_withdrawals.get(currency, 0):
            return {
                "success": False,
                "error": f"Minimum withdrawal: {min_withdrawals.get(currency, 0)} {currency}",
            }

        amount_decimal = Decimal(str(amount))
        with self.lock:
            wallet = self.get_wallet(user_address)
            if wallet.withdraw(currency, amount_decimal):
                timestamp = time.time()
                tx = {
                    "id": self._generate_tx_id(),
                    "type": "withdrawal",
                    "user_address": user_address,
                    "currency": currency,
                    "amount": float(amount_decimal),
                    "destination": destination,
                    "timestamp": timestamp,
                    "status": "pending",
                    "compliance": compliance_metadata or {},
                }
                self.transactions.append(tx)
                self.pending_withdrawals[tx["id"]] = tx
                self.save_wallets()

                return {
                    "success": True,
                    "transaction": tx.copy(),
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
        base_amt = Decimal(str(base_amount))
        quote_amt = Decimal(str(quote_amount))

        with self.lock:
            buyer_wallet = self.get_wallet(buyer_address)
            seller_wallet = self.get_wallet(seller_address)

            if buyer_wallet.get_available_balance(quote_currency) < quote_amt:
                return {"success": False, "error": f"Buyer insufficient {quote_currency} balance"}

            if seller_wallet.get_available_balance(base_currency) < base_amt:
                return {"success": False, "error": f"Seller insufficient {base_currency} balance"}

            buyer_wallet.withdraw(quote_currency, quote_amt)
            buyer_wallet.deposit(base_currency, base_amt)
            seller_wallet.withdraw(base_currency, base_amt)
            seller_wallet.deposit(quote_currency, quote_amt)

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
                "transaction": tx.copy(),
                "buyer_balances": buyer_wallet.to_dict()["available_balances"],
                "seller_balances": seller_wallet.to_dict()["available_balances"],
            }

    def lock_for_order(self, user_address: str, currency: str, amount: float) -> bool:
        """Lock balance when placing order"""
        with self.lock:
            wallet = self.get_wallet(user_address)
            return wallet.lock_balance(currency, Decimal(str(amount)))

    def unlock_from_order(self, user_address: str, currency: str, amount: float) -> bool:
        """Unlock balance when order cancelled"""
        with self.lock:
            wallet = self.get_wallet(user_address)
            return wallet.unlock_balance(currency, Decimal(str(amount)))

    def get_balance(self, user_address: str, currency: str) -> dict:
        """Get balance for specific currency"""
        with self.lock:
            wallet = self.get_wallet(user_address)
            return {
                "currency": currency,
                "total": float(wallet.get_total_balance(currency)),
                "available": float(wallet.get_available_balance(currency)),
                "locked": float(wallet.locked_balances.get(currency, Decimal("0"))),
            }

    def get_all_balances(self, user_address: str) -> dict:
        """Get all balances for user"""
        with self.lock:
            wallet = self.get_wallet(user_address)
            return wallet.to_dict()

    def get_transaction_history(self, user_address: str, limit: int = 50) -> list[dict]:
        """Get transaction history for user"""
        with self.lock:
            user_txs = [
                tx
                for tx in self.transactions
                if tx.get("user_address") == user_address
                or tx.get("buyer") == user_address
                or tx.get("seller") == user_address
            ]
            user_txs.sort(key=lambda x: x["timestamp"], reverse=True)
            return [tx.copy() for tx in user_txs[:limit]]

    def get_pending_count(self) -> int:
        """Return the total number of pending withdrawals."""
        with self.lock:
            return len(self.pending_withdrawals)

    def list_pending_withdrawals(self) -> list[dict]:
        """Return all pending withdrawal transactions."""
        with self.lock:
            pending = sorted(
                self.pending_withdrawals.values(), key=lambda tx: tx["timestamp"], reverse=True
            )
            return [tx.copy() for tx in pending]

    def get_withdrawal_counts(self) -> dict[str, int]:
        """Return counts of withdrawals grouped by status."""
        with self.lock:
            counts = {
                "pending": len(self.pending_withdrawals),
                "completed": 0,
                "failed": 0,
                "flagged": 0,
            }
            for tx in self.transactions:
                if tx.get("type") != "withdrawal":
                    continue
                status = tx.get("status")
                if status in counts and status != "pending":
                    counts[status] += 1
            counts["total"] = sum(counts.values())
            return counts

    def get_withdrawals_by_status(self, status: str, limit: int = 50) -> list[dict]:
        """Return withdrawals that match a status ordered by recency."""
        normalized = status.lower()
        if normalized not in self._WITHDRAWAL_STATUSES:
            raise ValueError(f"Unsupported withdrawal status '{status}'")
        with self.lock:
            if normalized == "pending":
                items: Iterable[dict] = self.pending_withdrawals.values()
            else:
                items = (
                    tx
                    for tx in self.transactions
                    if tx.get("type") == "withdrawal" and tx.get("status") == normalized
                )
            sorted_items = sorted(items, key=lambda tx: tx["timestamp"], reverse=True)
            return [tx.copy() for tx in sorted_items[: max(1, limit)]]

    def get_pending_withdrawal(self, tx_id: str) -> dict | None:
        """Fetch a pending withdrawal by transaction id."""
        with self.lock:
            tx = self.pending_withdrawals.get(tx_id)
            return tx.copy() if tx else None

    def update_withdrawal_status(self, tx_id: str, status: str, **fields: Any) -> dict:
        """Update the status of a specific withdrawal transaction."""
        valid_status = {"pending", "completed", "failed", "flagged"}
        if status not in valid_status:
            raise ValueError(f"Unsupported withdrawal status '{status}'")

        with self.lock:
            tx = self.pending_withdrawals.get(tx_id)
            if not tx:
                for entry in self.transactions:
                    if entry.get("id") == tx_id and entry.get("type") == "withdrawal":
                        tx = entry
                        break
            if not tx:
                raise KeyError(f"Withdrawal {tx_id} not found")

            tx.update(fields)
            tx["status"] = status
            if status != "pending":
                self.pending_withdrawals.pop(tx_id, None)
            if status == "failed" and not tx.get("refunded"):
                self._refund_withdrawal_locked(tx)
            self.save_wallets()
            return tx.copy()

    def _refund_withdrawal_locked(self, tx: dict) -> None:
        """Refund a failed withdrawal back to the user's available balance."""
        wallet = self.get_wallet(tx["user_address"])
        wallet.deposit(tx["currency"], Decimal(str(tx["amount"])))
        tx["refunded"] = True

    def _generate_tx_id(self) -> str:
        """Generate unique transaction ID"""
        data = f"{time.time()}_{len(self.transactions)}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def save_wallets(self):
        """Save wallets to disk"""
        with self.lock:
            os.makedirs(self.data_dir, exist_ok=True)
            wallets_file = os.path.join(self.data_dir, "wallets.json")
            wallets_data = {
                address: {
                    "balances": {k: float(v) for k, v in wallet.balances.items()},
                    "locked_balances": {k: float(v) for k, v in wallet.locked_balances.items()},
                }
                for address, wallet in self.wallets.items()
            }
            with open(wallets_file, "w", encoding="utf-8") as handle:
                json.dump(wallets_data, handle, indent=2)

            tx_file = os.path.join(self.data_dir, "transactions.json")
            with open(tx_file, "w", encoding="utf-8") as handle:
                json.dump(self.transactions[-MAX_TRANSACTION_HISTORY_SIZE:], handle, indent=2)

    def load_wallets(self):
        """Load wallets from disk"""
        wallets_file = os.path.join(self.data_dir, "wallets.json")
        tx_file = os.path.join(self.data_dir, "transactions.json")
        with self.lock:
            if os.path.exists(wallets_file):
                with open(wallets_file, "r", encoding="utf-8") as handle:
                    wallets_data = json.load(handle)

                for address, data in wallets_data.items():
                    wallet = ExchangeWallet(address)
                    wallet.balances = {k: Decimal(str(v)) for k, v in data["balances"].items()}
                    wallet.locked_balances = {
                        k: Decimal(str(v)) for k, v in data["locked_balances"].items()
                    }
                    self.wallets[address] = wallet

            if os.path.exists(tx_file):
                with open(tx_file, "r", encoding="utf-8") as handle:
                    self.transactions = json.load(handle)
            else:
                self.transactions = []
        self._refresh_pending_withdrawals()

    def get_stats(self) -> dict:
        """Get exchange statistics"""
        with self.lock:
            total_users = len(self.wallets)
            total_volume: dict[str, float] = {}
            for tx in self.transactions:
                if tx.get("type") == "trade":
                    currency = tx["quote_currency"]
                    amount = tx["quote_amount"]
                    total_volume[currency] = total_volume.get(currency, 0) + amount

            pending_count = len(self.pending_withdrawals)
            total_transactions = len(self.transactions)

        return {
            "total_users": total_users,
            "total_transactions": total_transactions,
            "total_volume_24h": total_volume,
            "pending_withdrawals": pending_count,
            "currencies_supported": ["USD", "AXN", "BTC", "ETH", "USDT", "LTC", "BNB"],
        }
