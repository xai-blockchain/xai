"""
Production-grade crypto deposit manager with confirmation tracking.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class CryptoDepositManager:
    """
    Handles crypto deposit address lifecycle, confirmation tracking, and wallet crediting.
    """

    STATE_FILE = "deposits_state.json"
    DEFAULT_CONFIRMATIONS = {
        "BTC": 6,
        "ETH": 12,
        "USDT": 12,
        "USDC": 12,
        "DAI": 12,
        "XAI": 8,
    }

    def __init__(self, exchange_wallet_manager, data_dir: str = "crypto_deposits"):
        self.exchange_wallet_manager = exchange_wallet_manager
        self.data_dir = os.path.abspath(data_dir)
        self.state_path = os.path.join(self.data_dir, self.STATE_FILE)
        self.monitoring_active = False
        self.deposit_addresses: Dict[str, List[Dict[str, Any]]] = {}
        self.pending_deposits: List[Dict[str, Any]] = []
        self.confirmed_deposits: List[Dict[str, Any]] = []
        self._pending_by_tx: Dict[str, Dict[str, Any]] = {}
        self._confirmed_by_tx: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        os.makedirs(self.data_dir, exist_ok=True)
        self._load_state()

    # ===== State Management =====
    def _load_state(self) -> None:
        """Load persisted deposit state from disk."""
        if not os.path.exists(self.state_path):
            return
        try:
            with open(self.state_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Failed to load crypto deposit state", exc_info=exc)
            return

        self.deposit_addresses = data.get("deposit_addresses", {}) or {}
        self.pending_deposits = data.get("pending_deposits", []) or []
        self.confirmed_deposits = data.get("confirmed_deposits", []) or []
        self._rebuild_indexes()

    def _persist_state(self) -> None:
        """Persist current state to disk atomically."""
        payload = {
            "deposit_addresses": self.deposit_addresses,
            "pending_deposits": self.pending_deposits,
            "confirmed_deposits": self.confirmed_deposits,
        }
        tmp_path = f"{self.state_path}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
            os.replace(tmp_path, self.state_path)
        except OSError as exc:
            logger.error("Failed to persist crypto deposit state", exc_info=exc)

    def _rebuild_indexes(self) -> None:
        """Rebuild fast lookup indexes."""
        self._pending_by_tx = {
            deposit["tx_hash"]: deposit for deposit in self.pending_deposits if deposit.get("tx_hash")
        }
        self._confirmed_by_tx = {
            deposit["tx_hash"]: deposit for deposit in self.confirmed_deposits if deposit.get("tx_hash")
        }

    # ===== Address Management =====
    def start_monitoring(self) -> None:
        """Flip monitoring flag to indicate blockchain watchers are active."""
        self.monitoring_active = True

    def stop_monitoring(self) -> None:
        """Stop monitoring background workers."""
        self.monitoring_active = False

    def _build_address(self, user_address: str, currency: str) -> str:
        digest = hashlib.sha256(f"{user_address}-{currency}-{time.time()}".encode()).hexdigest()
        if currency.upper() == "BTC":
            return f"bc1q{digest[:40]}"
        return f"0x{digest[:40]}"

    def _default_confirmations(self, currency: str) -> int:
        return self.DEFAULT_CONFIRMATIONS.get(currency.upper(), 12)

    def generate_deposit_address(self, user_address: str, currency: str) -> Dict[str, Any]:
        """Generate and persist a deposit address for a user."""
        normalized_currency = currency.upper()
        address = self._build_address(user_address, normalized_currency)
        entry = {
            "user_address": user_address,
            "currency": normalized_currency,
            "deposit_address": address,
            "created_at": time.time(),
            "required_confirmations": self._default_confirmations(normalized_currency),
        }
        with self._lock:
            self.deposit_addresses.setdefault(user_address, []).append(entry)
            self._persist_state()
        return {
            "success": True,
            "deposit_address": address,
            "currency": normalized_currency,
            "user_address": user_address,
            "required_confirmations": entry["required_confirmations"],
            "message": "Deposit address generated",
        }

    def get_user_deposit_addresses(self, user_address: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [entry.copy() for entry in self.deposit_addresses.get(user_address, [])]

    def list_addresses_by_currency(self, currency: str) -> List[Dict[str, Any]]:
        """Return all address entries registered for the given currency."""
        normalized = currency.upper()
        with self._lock:
            entries: List[Dict[str, Any]] = []
            for user_entries in self.deposit_addresses.values():
                for entry in user_entries:
                    if entry.get("currency") == normalized:
                        entries.append(entry.copy())
            return entries

    # ===== Deposit Tracking =====
    def _find_address_entry(
        self, user_address: str, deposit_address: str, currency: str
    ) -> Optional[Dict[str, Any]]:
        addresses = self.deposit_addresses.get(user_address, [])
        for entry in addresses:
            if (
                entry.get("deposit_address") == deposit_address
                and entry.get("currency") == currency
            ):
                return entry
        return None

    def record_blockchain_deposit(
        self,
        user_address: str,
        currency: str,
        amount: float,
        tx_hash: str,
        deposit_address: str,
        *,
        confirmations: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record a new on-chain deposit detection.

        Returns status payload describing whether the deposit is pending or already credited.
        """
        normalized_currency = currency.upper()
        metadata = metadata or {}
        with self._lock:
            if tx_hash in self._pending_by_tx or tx_hash in self._confirmed_by_tx:
                existing = self._confirmed_by_tx.get(tx_hash) or self._pending_by_tx.get(tx_hash)
                return {
                    "success": True,
                    "status": existing.get("status", "pending"),
                    "confirmations": existing.get("confirmations", 0),
                }

            address_entry = self._find_address_entry(user_address, deposit_address, normalized_currency)
            if not address_entry:
                return {
                    "success": False,
                    "error": "UNKNOWN_DEPOSIT_ADDRESS",
                    "message": "Deposit address not registered for user/currency",
                }

            required_confirmations = address_entry.get(
                "required_confirmations", self._default_confirmations(normalized_currency)
            )
            deposit = {
                "tx_hash": tx_hash,
                "user_address": user_address,
                "currency": normalized_currency,
                "amount": float(amount),
                "deposit_address": deposit_address,
                "confirmations": max(0, int(confirmations)),
                "required_confirmations": required_confirmations,
                "status": "pending",
                "created_at": time.time(),
                "updated_at": time.time(),
                "metadata": metadata,
                "credited": False,
                "credit_tx": None,
                "confirmed_at": None,
            }
            self.pending_deposits.append(deposit)
            self._pending_by_tx[tx_hash] = deposit

            if deposit["confirmations"] >= required_confirmations:
                self._transition_to_confirmed(deposit)

            self._persist_state()
            return {
                "success": True,
                "status": deposit["status"],
                "confirmations": deposit["confirmations"],
            }

    def update_confirmations(self, tx_hash: str, new_confirmations: int) -> Dict[str, Any]:
        """Update confirmation count for a previously detected deposit."""
        if new_confirmations < 0:
            return {"success": False, "error": "INVALID_CONFIRMATIONS"}

        with self._lock:
            deposit = self._pending_by_tx.get(tx_hash)
            if not deposit:
                confirmed = self._confirmed_by_tx.get(tx_hash)
                if confirmed:
                    return {
                        "success": True,
                        "status": confirmed.get("status", "credited"),
                        "confirmations": confirmed.get("confirmations", confirmed.get("required_confirmations", 0)),
                    }
                return {"success": False, "error": "UNKNOWN_DEPOSIT"}

            deposit["confirmations"] = max(deposit["confirmations"], int(new_confirmations))
            deposit["updated_at"] = time.time()
            if deposit["confirmations"] >= deposit["required_confirmations"]:
                self._transition_to_confirmed(deposit)
            self._persist_state()
            return {
                "success": True,
                "status": deposit.get("status", "pending"),
                "confirmations": deposit["confirmations"],
            }

    def _transition_to_confirmed(self, deposit: Dict[str, Any]) -> None:
        """Mark deposit as confirmed and credit funds."""
        if deposit["tx_hash"] in self._pending_by_tx:
            self.pending_deposits = [
                entry for entry in self.pending_deposits if entry["tx_hash"] != deposit["tx_hash"]
            ]
            self._pending_by_tx.pop(deposit["tx_hash"], None)

        deposit["status"] = "confirmed"
        deposit["confirmations"] = max(
            deposit["confirmations"], deposit["required_confirmations"]
        )
        deposit["confirmed_at"] = time.time()
        credit_result = self._credit_exchange_wallet(deposit)
        if credit_result.get("success"):
            deposit["status"] = "credited"
            deposit["credited"] = True
            deposit["credit_tx"] = credit_result["transaction"]["id"]
        else:
            deposit["status"] = "credit_failed"
            deposit["credited"] = False

        self.confirmed_deposits.append(deposit)
        self._confirmed_by_tx[deposit["tx_hash"]] = deposit

    def _credit_exchange_wallet(self, deposit: Dict[str, Any]) -> Dict[str, Any]:
        """Credit the user's exchange wallet and capture structured errors."""
        try:
            return self.exchange_wallet_manager.deposit(
                deposit["user_address"],
                deposit["currency"],
                deposit["amount"],
                deposit_type="crypto",
                tx_hash=deposit["tx_hash"],
            )
        except (ValueError, KeyError, AttributeError, TypeError, RuntimeError) as exc:  # pragma: no cover - defensive logging
            logger.exception("Failed to credit exchange wallet for crypto deposit", exc_info=exc, extra={"error_type": type(exc).__name__})
            return {"success": False, "error": str(exc)}

    # ===== Public Query APIs =====
    def get_pending_deposits(self, user_address: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            source = self.pending_deposits
            if user_address:
                source = [entry for entry in source if entry.get("user_address") == user_address]
            return [entry.copy() for entry in source]

    def get_deposit_history(self, user_address: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            history = [
                entry
                for entry in self.confirmed_deposits
                if entry.get("user_address") == user_address
            ]
            return [entry.copy() for entry in history[:limit]]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_addresses = sum(len(v) for v in self.deposit_addresses.values())
            total_pending = len(self.pending_deposits)
            total_confirmed = len(self.confirmed_deposits)
            total_credited = sum(1 for entry in self.confirmed_deposits if entry.get("credited"))
            total_volume = sum(entry.get("amount", 0.0) for entry in self.confirmed_deposits)
            return {
                "success": True,
                "total_addresses": total_addresses,
                "pending_deposits": total_pending,
                "confirmed_deposits": total_confirmed,
                "credited_deposits": total_credited,
                "confirmed_volume": total_volume,
                "monitoring_active": self.monitoring_active,
            }
