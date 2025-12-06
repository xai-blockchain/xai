"""Withdrawal processing pipeline with risk controls and timelock enforcement."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Set

from xai.core.exchange_wallet import ExchangeWalletManager

logger = logging.getLogger(__name__)

STATE_FILE = "processor_state.json"


@dataclass
class WithdrawalDecision:
    """Structured decision returned by the withdrawal processor."""

    status: str
    reason: Optional[str] = None
    settlement_txid: Optional[str] = None
    release_timestamp: Optional[float] = None
    risk_score: float = 0.0


class WithdrawalProcessor:
    """Evaluates and settles pending withdrawals with layered safety checks."""

    def __init__(
        self,
        wallet_manager: ExchangeWalletManager,
        *,
        data_dir: str = os.path.join("data", "withdrawals"),
        lock_amount_threshold: float = 5_000.0,
        lock_duration_seconds: int = 3600,
        max_withdrawal_per_tx: float = 250_000.0,
        max_daily_volume: float = 1_000_000.0,
        manual_review_threshold: float = 0.65,
        blocked_destinations: Optional[Set[str]] = None,
    ) -> None:
        self.wallet_manager = wallet_manager
        self.data_dir = data_dir
        self.lock_amount_threshold = Decimal(str(lock_amount_threshold))
        self.lock_duration_seconds = int(lock_duration_seconds)
        self.max_withdrawal_per_tx = Decimal(str(max_withdrawal_per_tx))
        self.max_daily_volume = Decimal(str(max_daily_volume))
        self.manual_review_threshold = manual_review_threshold
        self.blocked_destinations = {dest.lower() for dest in blocked_destinations or set()}
        self.state_path = os.path.join(self.data_dir, STATE_FILE)
        self.daily_totals: Dict[str, Dict[str, float]] = {}
        self.processed_withdrawals: Dict[str, Dict[str, Any]] = {}
        self._load_state()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _load_state(self) -> None:
        if not os.path.exists(self.state_path):
            return
        try:
            with open(self.state_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load withdrawal processor state: %s", exc)
            return

        self.daily_totals = data.get("daily_totals", {})
        self.processed_withdrawals = data.get("processed_withdrawals", {})

    def _save_state(self) -> None:
        os.makedirs(self.data_dir, exist_ok=True)
        snapshot = {
            "daily_totals": self.daily_totals,
            "processed_withdrawals": self.processed_withdrawals,
            "saved_at": time.time(),
        }
        tmp_path = f"{self.state_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, indent=2)
        os.replace(tmp_path, self.state_path)

    # ------------------------------------------------------------------
    # Core processing
    # ------------------------------------------------------------------
    def process_queue(self, current_timestamp: Optional[float] = None) -> Dict[str, Any]:
        """Process all pending withdrawals and return structured statistics."""
        now = current_timestamp or time.time()
        pending = self.wallet_manager.list_pending_withdrawals()
        pending.sort(key=lambda tx: tx["timestamp"])

        stats = {
            "checked": len(pending),
            "completed": 0,
            "flagged": 0,
            "failed": 0,
            "deferred": 0,
            "decisions": [],
        }

        for tx in pending:
            decision = self._evaluate_withdrawal(tx, now)
            stats["decisions"].append(
                {
                    "transaction_id": tx["id"],
                    "status": decision.status,
                    "reason": decision.reason,
                    "risk_score": round(decision.risk_score, 3),
                    "release_timestamp": decision.release_timestamp,
                    "settlement_txid": decision.settlement_txid,
                }
            )

            if decision.status == "completed":
                stats["completed"] += 1
                self.wallet_manager.update_withdrawal_status(
                    tx["id"],
                    "completed",
                    settlement_txid=decision.settlement_txid,
                    completed_at=now,
                    risk_score=decision.risk_score,
                )
                self.processed_withdrawals[tx["id"]] = {
                    "status": "completed",
                    "settlement_txid": decision.settlement_txid,
                    "completed_at": now,
                    "risk_score": decision.risk_score,
                }
            elif decision.status == "flagged":
                stats["flagged"] += 1
                self.wallet_manager.update_withdrawal_status(
                    tx["id"],
                    "flagged",
                    reason=decision.reason,
                    risk_score=decision.risk_score,
                )
                self.processed_withdrawals[tx["id"]] = {
                    "status": "flagged",
                    "reason": decision.reason,
                    "flagged_at": now,
                    "risk_score": decision.risk_score,
                }
            elif decision.status == "failed":
                stats["failed"] += 1
                self.wallet_manager.update_withdrawal_status(
                    tx["id"],
                    "failed",
                    reason=decision.reason,
                    risk_score=decision.risk_score,
                )
                self.processed_withdrawals[tx["id"]] = {
                    "status": "failed",
                    "reason": decision.reason,
                    "failed_at": now,
                    "risk_score": decision.risk_score,
                }
            else:
                stats["deferred"] += 1
                # Keep pending, but annotate release timestamp for API consumers
                self.wallet_manager.update_withdrawal_status(
                    tx["id"],
                    "pending",
                    release_timestamp=decision.release_timestamp,
                    risk_score=decision.risk_score,
                    reason=decision.reason,
                )

        self._save_state()
        return stats

    def _evaluate_withdrawal(self, tx: Dict[str, Any], now: float) -> WithdrawalDecision:
        """Return the action that should be applied to a pending withdrawal."""
        try:
            amount = Decimal(str(tx["amount"]))
        except (InvalidOperation, TypeError) as exc:
            logger.error("Invalid withdrawal amount for %s: %s", tx.get("id"), exc)
            return WithdrawalDecision(status="failed", reason="invalid_amount", risk_score=1.0)

        if amount <= 0:
            return WithdrawalDecision(status="failed", reason="amount_not_positive", risk_score=1.0)

        if amount > self.max_withdrawal_per_tx:
            return WithdrawalDecision(
                status="flagged",
                reason="exceeds_single_withdrawal_limit",
                risk_score=0.95,
            )

        destination = str(tx.get("destination", "")).lower()
        if destination in self.blocked_destinations:
            return WithdrawalDecision(
                status="failed", reason="blocked_destination", risk_score=1.0
            )

        risk_score = self._calculate_risk_score(tx, amount)
        release_ts = self._calculate_release_timestamp(amount, tx["timestamp"])

        if risk_score >= 0.99:
            return WithdrawalDecision(status="failed", reason="risk_score_unacceptable", risk_score=risk_score)

        if risk_score >= self.manual_review_threshold:
            return WithdrawalDecision(
                status="flagged",
                reason="manual_review_required",
                risk_score=risk_score,
            )

        if release_ts > now:
            return WithdrawalDecision(
                status="deferred",
                reason="time_lock_active",
                release_timestamp=release_ts,
                risk_score=risk_score,
            )

        if not self._can_execute_today(tx["user_address"], amount, now):
            return WithdrawalDecision(
                status="deferred",
                reason="daily_limit_reached",
                release_timestamp=self._next_window_start(tx["user_address"], now),
                risk_score=risk_score,
            )

        settlement_tx = self._simulate_settlement(tx, now)
        self._update_daily_total(tx["user_address"], amount, now)
        return WithdrawalDecision(
            status="completed",
            settlement_txid=settlement_tx,
            risk_score=risk_score,
        )

    # ------------------------------------------------------------------
    # Risk & compliance helpers
    # ------------------------------------------------------------------
    def _calculate_risk_score(self, tx: Dict[str, Any], amount: Decimal) -> float:
        """Derive a deterministic risk score between 0 and 1."""
        score = 0.15

        normalized = amount / self.lock_amount_threshold if self.lock_amount_threshold > 0 else Decimal("0")
        if normalized >= 1:
            score += min(float(normalized) * 0.25, 0.35)

        currency = str(tx.get("currency", "")).upper()
        crypto_weights = {
            "BTC": 0.18,
            "ETH": 0.16,
            "USDT": 0.12,
            "XAI": 0.10,
        }
        score += crypto_weights.get(currency, 0.05)

        compliance = tx.get("compliance") or {}
        if not compliance.get("two_factor_verified", False):
            score += 0.1
        if compliance.get("kyc_score", 100) < 70:
            score += 0.2
        if compliance.get("country_code") in {"IR", "KP", "SY"}:
            score = 0.99
        if compliance.get("pep_flagged"):
            score = 1.0

        destination = str(tx.get("destination", "")).lower()
        if destination.startswith("custodial:"):
            score -= 0.05

        return max(0.0, min(1.0, score))

    def _calculate_release_timestamp(self, amount: Decimal, created_at: float) -> float:
        """Apply dynamic timelock durations for large withdrawals."""
        if amount < self.lock_amount_threshold:
            return created_at
        multiplier = min(float(amount / self.lock_amount_threshold), 4.0)
        duration = int(self.lock_duration_seconds * multiplier)
        return created_at + duration

    def _can_execute_today(self, user: str, amount: Decimal, now: float) -> bool:
        """Check if the user stays within rolling 24h withdrawal limits."""
        window = self.daily_totals.get(user)
        if not window or now - window["window_start"] >= 86400:
            return amount <= self.max_daily_volume
        running_total = Decimal(str(window["amount"]))
        return running_total + amount <= self.max_daily_volume

    def _next_window_start(self, user: str, now: float) -> float:
        window = self.daily_totals.get(user)
        if not window:
            return now
        elapsed = now - window["window_start"]
        if elapsed >= 86400:
            return now
        return window["window_start"] + 86400

    def _update_daily_total(self, user: str, amount: Decimal, now: float) -> None:
        """Persist new withdrawal volume in the rolling 24h window."""
        window = self.daily_totals.get(user)
        if not window or now - window["window_start"] >= 86400:
            window = {"window_start": now, "amount": 0.0}
        window["amount"] = float(float(window["amount"]) + float(amount))
        self.daily_totals[user] = window

    def _simulate_settlement(self, tx: Dict[str, Any], now: float) -> str:
        """Generate deterministic settlement identifiers for auditability."""
        payload = f"{tx['id']}|{tx['user_address']}|{tx['currency']}|{tx['amount']}|{now}"
        digest = hashlib.sha256(payload.encode()).hexdigest()
        logger.info(
            "Withdrawal %s settled to %s",
            tx["id"],
            tx.get("destination"),
            extra={"event": "withdrawal.settled", "tx_id": tx["id"], "destination": tx.get("destination")},
        )
        return digest

    # ------------------------------------------------------------------
    # Manual overrides
    # ------------------------------------------------------------------
    def mark_manual_review(self, tx_id: str, reason: str) -> dict:
        """Flag a transaction for manual review."""
        logger.warning("Manual review requested for withdrawal %s: %s", tx_id, reason)
        record = self.wallet_manager.update_withdrawal_status(
            tx_id, "flagged", reason=reason, risk_score=1.0
        )
        self.processed_withdrawals[tx_id] = {"status": "flagged", "reason": reason, "manual": True}
        self._save_state()
        return record

    def force_complete(self, tx_id: str, settlement_txid: str) -> dict:
        """Force-complete a withdrawal after manual approval."""
        logger.info("Force completing withdrawal %s", tx_id, extra={"event": "withdrawal.force_complete"})
        record = self.wallet_manager.update_withdrawal_status(
            tx_id, "completed", settlement_txid=settlement_txid, completed_at=time.time()
        )
        self.processed_withdrawals[tx_id] = {"status": "completed", "settlement_txid": settlement_txid, "manual": True}
        self._save_state()
        return record
