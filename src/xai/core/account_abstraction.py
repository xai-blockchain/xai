from __future__ import annotations

"""
Account abstraction helpers and embedded wallet management.
Task 178: Gas sponsorship for account abstraction

This module provides:
- Embedded wallet management for social/email login
- Gas sponsorship for gasless transactions (account abstraction)
- Rate limiting and budget controls for sponsors
- Full integration with the transaction pipeline

Gas Sponsorship Flow:
1. Sponsor registers with a budget and rate limit
2. User creates a transaction with gas_sponsor field set
3. Sponsor authorizes the transaction (signs approval)
4. Transaction validator checks sponsor authorization
5. Fee is deducted from sponsor's budget, not user's balance
6. Transaction is processed normally

Security Considerations:
- Sponsors must cryptographically authorize each transaction
- Rate limits prevent abuse (per user per day)
- Budget caps prevent unlimited spending
- Blacklist/whitelist support for access control
"""

import hashlib
import json
import logging
import os
import secrets
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from xai.core.config import Config
from xai.core.crypto_utils import sign_message_hex, verify_signature_hex
from xai.core.wallet import WalletManager

class SponsorSignatureError(RuntimeError):
    """Raised when sponsor signature generation fails."""

    def __init__(self, message: str, *, sponsor: str | None = None):
        super().__init__(message)
        self.sponsor = sponsor

class SponsorSignatureVerificationError(SponsorSignatureError):
    """Raised when sponsor signature verification fails due to malformed data."""

if TYPE_CHECKING:
    from xai.core.blockchain import Blockchain
    from xai.core.transaction import Transaction

logger = logging.getLogger(__name__)

class TransactionStatus(Enum):
    """Status of a sponsored transaction"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"

@dataclass
class RateLimitConfig:
    """
    Configuration for multi-tier rate limiting.

    Supports per-second, per-minute, per-hour, and per-day limits
    to prevent burst attacks on gas sponsorship.
    """
    per_second: int = 10      # Max transactions per second
    per_minute: int = 100     # Max transactions per minute
    per_hour: int = 500       # Max transactions per hour
    per_day: int = 1000       # Max transactions per day

    # Gas amount limits
    max_gas_per_second: float = 1.0    # Max total gas per second
    max_gas_per_minute: float = 10.0   # Max total gas per minute
    max_gas_per_hour: float = 50.0     # Max total gas per hour
    max_gas_per_day: float = 100.0     # Max total gas per day

    # Per-transaction limits
    max_gas_per_transaction: float = 0.1  # Max gas per single transaction
    max_cost_per_transaction: float = 1.0 # Max XAI cost per transaction

class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter for gas sponsorship.

    Tracks requests in a time-ordered queue and enforces limits
    across multiple time windows (second, minute, hour, day).

    This prevents burst attacks where an attacker drains the entire
    daily limit in seconds.

    Security Features:
    - Multi-tier rate limiting (per-second through per-day)
    - Gas amount tracking (prevents high-value burst attacks)
    - Sliding windows (more accurate than fixed-window counters)
    - Per-address isolation (one user can't block others)
    - Automatic cleanup of old entries

    Example:
        config = RateLimitConfig(per_second=10, per_minute=100)
        limiter = SlidingWindowRateLimiter(config)

        if limiter.is_allowed(gas_amount=0.01):
            # Process transaction
            pass
        else:
            retry_after = limiter.get_retry_after()
            # Reject with retry-after header
    """

    def __init__(self, config: RateLimitConfig):
        """
        Initialize rate limiter.

        Args:
            config: Rate limit configuration
        """
        self.config = config
        self.requests: deque[tuple[float, float]] = deque()  # (timestamp, gas_amount)

    def is_allowed(self, gas_amount: float = 0.0) -> bool:
        """
        Check if a request is allowed under current rate limits.

        Args:
            gas_amount: Amount of gas for this request

        Returns:
            True if request is allowed, False if rate limited
        """
        now = time.time()

        # Clean up old entries (older than 24 hours)
        self._cleanup_old_entries(now)

        # Check transaction count limits
        second_count = self._count_in_window(now, 1)
        minute_count = self._count_in_window(now, 60)
        hour_count = self._count_in_window(now, 3600)
        day_count = len(self.requests)

        if second_count >= self.config.per_second:
            logger.debug(
                "Rate limit exceeded: per-second transaction count",
                extra={
                    "event": "rate_limit.exceeded",
                    "window": "second",
                    "count": second_count,
                    "limit": self.config.per_second
                }
            )
            return False

        if minute_count >= self.config.per_minute:
            logger.debug(
                "Rate limit exceeded: per-minute transaction count",
                extra={
                    "event": "rate_limit.exceeded",
                    "window": "minute",
                    "count": minute_count,
                    "limit": self.config.per_minute
                }
            )
            return False

        if hour_count >= self.config.per_hour:
            logger.debug(
                "Rate limit exceeded: per-hour transaction count",
                extra={
                    "event": "rate_limit.exceeded",
                    "window": "hour",
                    "count": hour_count,
                    "limit": self.config.per_hour
                }
            )
            return False

        if day_count >= self.config.per_day:
            logger.debug(
                "Rate limit exceeded: per-day transaction count",
                extra={
                    "event": "rate_limit.exceeded",
                    "window": "day",
                    "count": day_count,
                    "limit": self.config.per_day
                }
            )
            return False

        # Check gas amount limits
        second_gas = self._sum_gas_in_window(now, 1)
        minute_gas = self._sum_gas_in_window(now, 60)
        hour_gas = self._sum_gas_in_window(now, 3600)
        day_gas = sum(gas for _, gas in self.requests)

        if second_gas + gas_amount > self.config.max_gas_per_second:
            logger.debug(
                "Rate limit exceeded: per-second gas amount",
                extra={
                    "event": "rate_limit.exceeded",
                    "window": "second",
                    "gas_used": second_gas,
                    "gas_requested": gas_amount,
                    "limit": self.config.max_gas_per_second
                }
            )
            return False

        if minute_gas + gas_amount > self.config.max_gas_per_minute:
            logger.debug(
                "Rate limit exceeded: per-minute gas amount",
                extra={
                    "event": "rate_limit.exceeded",
                    "window": "minute",
                    "gas_used": minute_gas,
                    "gas_requested": gas_amount,
                    "limit": self.config.max_gas_per_minute
                }
            )
            return False

        if hour_gas + gas_amount > self.config.max_gas_per_hour:
            logger.debug(
                "Rate limit exceeded: per-hour gas amount",
                extra={
                    "event": "rate_limit.exceeded",
                    "window": "hour",
                    "gas_used": hour_gas,
                    "gas_requested": gas_amount,
                    "limit": self.config.max_gas_per_hour
                }
            )
            return False

        if day_gas + gas_amount > self.config.max_gas_per_day:
            logger.debug(
                "Rate limit exceeded: per-day gas amount",
                extra={
                    "event": "rate_limit.exceeded",
                    "window": "day",
                    "gas_used": day_gas,
                    "gas_requested": gas_amount,
                    "limit": self.config.max_gas_per_day
                }
            )
            return False

        # Per-transaction limit
        if gas_amount > self.config.max_gas_per_transaction:
            logger.debug(
                "Rate limit exceeded: per-transaction gas limit",
                extra={
                    "event": "rate_limit.exceeded",
                    "gas_requested": gas_amount,
                    "limit": self.config.max_gas_per_transaction
                }
            )
            return False

        # All checks passed - record the request
        self.requests.append((now, gas_amount))
        return True

    def _cleanup_old_entries(self, now: float) -> None:
        """Remove entries older than 24 hours"""
        day_ago = now - 86400
        while self.requests and self.requests[0][0] < day_ago:
            self.requests.popleft()

    def _count_in_window(self, now: float, window_seconds: int) -> int:
        """Count requests in the last N seconds"""
        cutoff = now - window_seconds
        return sum(1 for ts, _ in self.requests if ts > cutoff)

    def _sum_gas_in_window(self, now: float, window_seconds: int) -> float:
        """Sum gas amounts in the last N seconds"""
        cutoff = now - window_seconds
        return sum(gas for ts, gas in self.requests if ts > cutoff)

    def get_retry_after(self) -> float:
        """
        Get time until next request would be allowed (in seconds).

        Returns:
            Seconds until retry, or 0 if immediately available
        """
        if not self.requests:
            return 0.0

        now = time.time()

        # Find the earliest window that's full
        # Check per-second limit
        if self._count_in_window(now, 1) >= self.config.per_second:
            # Wait until oldest request in last second expires
            oldest_in_window = now - 1
            for ts, _ in self.requests:
                if ts > oldest_in_window:
                    return ts - oldest_in_window

        # Check per-minute limit
        if self._count_in_window(now, 60) >= self.config.per_minute:
            oldest_in_window = now - 60
            for ts, _ in self.requests:
                if ts > oldest_in_window:
                    return ts - oldest_in_window

        # Check per-hour limit
        if self._count_in_window(now, 3600) >= self.config.per_hour:
            oldest_in_window = now - 3600
            for ts, _ in self.requests:
                if ts > oldest_in_window:
                    return ts - oldest_in_window

        # Check per-day limit
        if len(self.requests) >= self.config.per_day:
            # Wait until oldest request expires
            oldest_ts = self.requests[0][0]
            return (oldest_ts + 86400) - now

        return 0.0

    def get_current_usage(self) -> dict[str, any]:
        """
        Get current usage statistics.

        Returns:
            Dictionary with usage counts and gas amounts for each window
        """
        now = time.time()

        return {
            "counts": {
                "per_second": self._count_in_window(now, 1),
                "per_minute": self._count_in_window(now, 60),
                "per_hour": self._count_in_window(now, 3600),
                "per_day": len(self.requests)
            },
            "gas_used": {
                "per_second": self._sum_gas_in_window(now, 1),
                "per_minute": self._sum_gas_in_window(now, 60),
                "per_hour": self._sum_gas_in_window(now, 3600),
                "per_day": sum(gas for _, gas in self.requests)
            },
            "limits": {
                "counts": {
                    "per_second": self.config.per_second,
                    "per_minute": self.config.per_minute,
                    "per_hour": self.config.per_hour,
                    "per_day": self.config.per_day
                },
                "gas": {
                    "per_second": self.config.max_gas_per_second,
                    "per_minute": self.config.max_gas_per_minute,
                    "per_hour": self.config.max_gas_per_hour,
                    "per_day": self.config.max_gas_per_day,
                    "per_transaction": self.config.max_gas_per_transaction
                }
            }
        }

@dataclass
class SponsoredTransaction:
    """Record of a sponsored transaction"""
    user_address: str
    txid: str
    gas_amount: float
    timestamp: float
    sponsor_address: str
    status: str = "pending"  # TransactionStatus value
    blockchain_txid: str | None = None  # Final confirmed txid

class GasSponsor:
    """
    Gas sponsorship for account abstraction (Task 178)

    Allows sponsors to pay transaction fees on behalf of users,
    enabling gasless transactions for better UX.

    Security Features:
    - Multi-tier rate limiting (per-second, minute, hour, day)
    - Per-address rate limiting (prevents one user from consuming all capacity)
    - Gas amount limiting (prevents high-value burst attacks)
    - Global rate limiting (protects sponsor's total budget)
    - Whitelist/blacklist support
    """

    def __init__(
        self,
        sponsor_address: str,
        budget: float,
        rate_limit: int = 10,
        rate_limit_config: RateLimitConfig | None = None
    ):
        """
        Initialize gas sponsor

        Args:
            sponsor_address: Address of the sponsor
            budget: Total budget for sponsorship
            rate_limit: DEPRECATED - use rate_limit_config instead (kept for backwards compatibility)
            rate_limit_config: Multi-tier rate limit configuration
        """
        self.sponsor_address = sponsor_address
        self.total_budget = budget
        self.remaining_budget = budget

        # Legacy rate limit (kept for backwards compatibility)
        self.rate_limit = rate_limit

        # Multi-tier rate limiting
        if rate_limit_config is None:
            # Default configuration with reasonable limits; legacy rate_limit enforced separately
            legacy_limit = max(1, int(rate_limit))
            base_limit = max(legacy_limit, 10)
            rate_limit_config = RateLimitConfig(
                per_second=base_limit,
                per_minute=max(base_limit * 10, 100),
                per_hour=max(base_limit * 60, 500),
                per_day=max(legacy_limit, 1000),  # Use legacy rate_limit or default
                max_gas_per_second=1.0,
                max_gas_per_minute=10.0,
                max_gas_per_hour=50.0,
                max_gas_per_day=100.0,
                max_gas_per_transaction=0.1,
                max_cost_per_transaction=1.0
            )
        self.rate_limit_config = rate_limit_config

        # Global rate limiter (applies to all users combined) - more lenient to avoid penalizing legitimate multi-user bursts
        global_limit_config = RateLimitConfig(
            per_second=max(rate_limit_config.per_second * 5, rate_limit_config.per_second + 1),
            per_minute=max(rate_limit_config.per_minute * 5, rate_limit_config.per_minute + 10),
            per_hour=max(rate_limit_config.per_hour * 5, rate_limit_config.per_hour + 60),
            per_day=max(rate_limit_config.per_day * 2, rate_limit_config.per_day + 1000),
            max_gas_per_second=rate_limit_config.max_gas_per_second * 5,
            max_gas_per_minute=rate_limit_config.max_gas_per_minute * 5,
            max_gas_per_hour=rate_limit_config.max_gas_per_hour * 5,
            max_gas_per_day=rate_limit_config.max_gas_per_day * 2,
            max_gas_per_transaction=rate_limit_config.max_gas_per_transaction,
            max_cost_per_transaction=rate_limit_config.max_cost_per_transaction,
        )
        self.global_rate_limiter = SlidingWindowRateLimiter(global_limit_config)

        # Per-address rate limiters (isolates users from each other)
        self.user_rate_limiters: dict[str, SlidingWindowRateLimiter] = {}

        # Transaction tracking
        self.sponsored_transactions: list[SponsoredTransaction] = []
        self._txid_map: dict[str, SponsoredTransaction] = {}  # preliminary_txid -> transaction

        # Legacy tracking (kept for backwards compatibility)
        self.user_daily_usage: dict[str, list[float]] = {}  # user -> timestamps

        # Access control
        self.whitelist: list[str] = []  # Whitelisted user addresses
        self.blacklist: list[str] = []  # Blacklisted user addresses

        # Limits
        self.min_balance_required = 0.0  # Minimum balance user must have
        self.max_gas_per_transaction = rate_limit_config.max_gas_per_transaction
        self.max_cost_per_transaction = rate_limit_config.max_cost_per_transaction

        # Control
        self.enabled = True

    def _generate_preliminary_txid(self, user_address: str, gas_amount: float, timestamp: float) -> str:
        """
        Generate preliminary transaction ID from transaction parameters.

        This provides a unique identifier before the blockchain txid is available.

        Args:
            user_address: User address
            gas_amount: Amount of gas
            timestamp: Transaction timestamp

        Returns:
            SHA256 hash as preliminary txid
        """
        data = f"{user_address}:{gas_amount}:{timestamp}:{self.sponsor_address}".encode()
        return hashlib.sha256(data).hexdigest()

    def sponsor_transaction(self, user_address: str, gas_amount: float) -> str | None:
        """
        Sponsor a transaction for a user.

        Performs multi-tier rate limiting:
        1. Global rate limiting (all users combined)
        2. Per-address rate limiting (isolates users)
        3. Budget checks
        4. Access control (whitelist/blacklist)

        Args:
            user_address: User address
            gas_amount: Amount of gas needed

        Returns:
            Preliminary transaction ID if approved, None if rejected
        """
        if not self.enabled:
            logger.debug(
                "Sponsorship rejected: sponsor disabled",
                extra={"event": "gas_sponsor.rejected", "reason": "disabled"}
            )
            return None

        # Check blacklist
        if user_address in self.blacklist:
            logger.debug(
                "Sponsorship rejected: user blacklisted",
                extra={
                    "event": "gas_sponsor.rejected",
                    "reason": "blacklisted",
                    "user": user_address[:16] + "..."
                }
            )
            return None

        # Check whitelist (if configured)
        if self.whitelist and user_address not in self.whitelist:
            logger.debug(
                "Sponsorship rejected: user not whitelisted",
                extra={
                    "event": "gas_sponsor.rejected",
                    "reason": "not_whitelisted",
                    "user": user_address[:16] + "..."
                }
            )
            return None

        # Legacy per-user rate limit (transactions per day)
        if not self._check_rate_limit(user_address):
            logger.warning(
                "Sponsorship rejected: legacy rate limit exceeded",
                extra={
                    "event": "gas_sponsor.rejected",
                    "reason": "legacy_rate_limit",
                    "user": user_address[:16] + "...",
                    "limit": self.rate_limit,
                }
            )
            return None

        # Check budget
        if gas_amount > self.remaining_budget:
            logger.warning(
                "Sponsorship rejected: insufficient budget",
                extra={
                    "event": "gas_sponsor.rejected",
                    "reason": "insufficient_budget",
                    "requested": gas_amount,
                    "remaining": self.remaining_budget
                }
            )
            return None

        # Check per-transaction gas limit
        if gas_amount > self.max_gas_per_transaction:
            logger.warning(
                "Sponsorship rejected: exceeds per-tx gas limit",
                extra={
                    "event": "gas_sponsor.rejected",
                    "reason": "exceeds_gas_limit",
                    "requested": gas_amount,
                    "limit": self.max_gas_per_transaction
                }
            )
            return None

        # Check per-transaction cost limit
        if gas_amount > self.max_cost_per_transaction:
            logger.warning(
                "Sponsorship rejected: exceeds per-tx cost limit",
                extra={
                    "event": "gas_sponsor.rejected",
                    "reason": "exceeds_cost_limit",
                    "requested": gas_amount,
                    "limit": self.max_cost_per_transaction
                }
            )
            return None

        # Check global rate limit (all users combined)
        if not self.global_rate_limiter.is_allowed(gas_amount):
            retry_after = self.global_rate_limiter.get_retry_after()
            logger.warning(
                "Sponsorship rejected: global rate limit exceeded",
                extra={
                    "event": "gas_sponsor.rejected",
                    "reason": "global_rate_limit",
                    "user": user_address[:16] + "...",
                    "retry_after_seconds": retry_after,
                    "gas_requested": gas_amount
                }
            )
            return None

        # Get or create per-address rate limiter
        if user_address not in self.user_rate_limiters:
            # Create per-user rate limiter with same config as global
            # This isolates users from each other
            self.user_rate_limiters[user_address] = SlidingWindowRateLimiter(
                self.rate_limit_config
            )

        # Check per-address rate limit
        user_limiter = self.user_rate_limiters[user_address]
        if not user_limiter.is_allowed(gas_amount):
            retry_after = user_limiter.get_retry_after()
            logger.warning(
                "Sponsorship rejected: user rate limit exceeded",
                extra={
                    "event": "gas_sponsor.rejected",
                    "reason": "user_rate_limit",
                    "user": user_address[:16] + "...",
                    "retry_after_seconds": retry_after,
                    "gas_requested": gas_amount
                }
            )
            return None

        # All checks passed - approve sponsorship
        self.remaining_budget -= gas_amount

        # Generate preliminary txid
        timestamp = time.time()
        preliminary_txid = self._generate_preliminary_txid(user_address, gas_amount, timestamp)

        # Record transaction with preliminary txid
        tx = SponsoredTransaction(
            user_address=user_address,
            txid=preliminary_txid,
            gas_amount=gas_amount,
            timestamp=timestamp,
            sponsor_address=self.sponsor_address,
            status=TransactionStatus.PENDING.value,
            blockchain_txid=None
        )
        self.sponsored_transactions.append(tx)
        self._txid_map[preliminary_txid] = tx

        # Update legacy user usage tracking (kept for backwards compatibility)
        if user_address not in self.user_daily_usage:
            self.user_daily_usage[user_address] = []
        self.user_daily_usage[user_address].append(timestamp)

        logger.info(
            "Transaction sponsored",
            extra={
                "event": "gas_sponsor.sponsored",
                "preliminary_txid": preliminary_txid[:16] + "...",
                "user": user_address[:16] + "...",
                "gas_amount": gas_amount,
                "remaining_budget": self.remaining_budget
            }
        )

        return preliminary_txid

    def confirm_sponsored_transaction(self, preliminary_txid: str, blockchain_txid: str) -> bool:
        """
        Update sponsored transaction with confirmed blockchain txid.

        This should be called after the transaction is confirmed in a block.

        Args:
            preliminary_txid: Preliminary txid returned from sponsor_transaction()
            blockchain_txid: Actual blockchain transaction ID

        Returns:
            True if transaction found and updated
        """
        tx = self._txid_map.get(preliminary_txid)
        if not tx:
            logger.warning(
                "Cannot confirm transaction: preliminary txid not found",
                extra={
                    "event": "gas_sponsor.confirm_failed",
                    "preliminary_txid": preliminary_txid[:16] + "..."
                }
            )
            return False

        tx.blockchain_txid = blockchain_txid
        tx.status = TransactionStatus.CONFIRMED.value

        logger.info(
            "Sponsored transaction confirmed",
            extra={
                "event": "gas_sponsor.tx_confirmed",
                "preliminary_txid": preliminary_txid[:16] + "...",
                "blockchain_txid": blockchain_txid[:16] + "...",
                "user": tx.user_address[:16] + "...",
                "gas_amount": tx.gas_amount
            }
        )

        return True

    def fail_sponsored_transaction(self, preliminary_txid: str, reason: str = "") -> bool:
        """
        Mark a sponsored transaction as failed.

        This should be called if the transaction fails to be confirmed.
        The gas amount will be refunded to the sponsor's budget.

        Args:
            preliminary_txid: Preliminary txid returned from sponsor_transaction()
            reason: Optional reason for failure

        Returns:
            True if transaction found and updated
        """
        tx = self._txid_map.get(preliminary_txid)
        if not tx:
            logger.warning(
                "Cannot fail transaction: preliminary txid not found",
                extra={
                    "event": "gas_sponsor.fail_failed",
                    "preliminary_txid": preliminary_txid[:16] + "..."
                }
            )
            return False

        # Only refund if still pending (not already confirmed)
        if tx.status == TransactionStatus.PENDING.value:
            self.remaining_budget += tx.gas_amount
            tx.status = TransactionStatus.FAILED.value

            logger.info(
                "Sponsored transaction failed",
                extra={
                    "event": "gas_sponsor.tx_failed",
                    "preliminary_txid": preliminary_txid[:16] + "...",
                    "user": tx.user_address[:16] + "...",
                    "gas_amount": tx.gas_amount,
                    "refunded": True,
                    "reason": reason,
                    "remaining_budget": self.remaining_budget
                }
            )

            return True

        logger.warning(
            "Cannot fail transaction: already in final state",
            extra={
                "event": "gas_sponsor.fail_rejected",
                "preliminary_txid": preliminary_txid[:16] + "...",
                "status": tx.status
            }
        )
        return False

    def get_transaction_by_preliminary_txid(self, preliminary_txid: str) -> SponsoredTransaction | None:
        """
        Get transaction by preliminary txid.

        Args:
            preliminary_txid: Preliminary transaction ID

        Returns:
            SponsoredTransaction if found, None otherwise
        """
        return self._txid_map.get(preliminary_txid)

    def get_transaction_by_blockchain_txid(self, blockchain_txid: str) -> SponsoredTransaction | None:
        """
        Get transaction by blockchain txid.

        Args:
            blockchain_txid: Blockchain transaction ID

        Returns:
            SponsoredTransaction if found, None otherwise
        """
        for tx in self.sponsored_transactions:
            if tx.blockchain_txid == blockchain_txid:
                return tx
        return None

    def _check_rate_limit(self, user_address: str) -> bool:
        """Check if user has exceeded rate limit"""
        if user_address not in self.user_daily_usage:
            return True

        # Clean up old entries (older than 24 hours)
        current_time = time.time()
        day_ago = current_time - 86400

        self.user_daily_usage[user_address] = [
            ts for ts in self.user_daily_usage[user_address]
            if ts > day_ago
        ]

        # Check count
        return len(self.user_daily_usage[user_address]) < self.rate_limit

    def add_budget(self, amount: float) -> None:
        """Add more budget to sponsor"""
        self.total_budget += amount
        self.remaining_budget += amount

    def set_whitelist(self, addresses: list[str]) -> None:
        """Set whitelist of allowed users"""
        self.whitelist = addresses

    def set_blacklist(self, addresses: list[str]) -> None:
        """Set blacklist of denied users"""
        self.blacklist = addresses

    def set_max_gas_per_transaction(self, amount: float) -> None:
        """Set maximum gas per transaction"""
        self.max_gas_per_transaction = amount

    def set_rate_limit(self, limit: int) -> None:
        """
        Set legacy rate limit (transactions per user per day).

        DEPRECATED: Use update_rate_limit_config() instead for multi-tier limiting.
        This method is kept for backwards compatibility.
        """
        self.rate_limit = limit
        # Update the config's per-day limit to match
        self.rate_limit_config.per_day = limit

    def update_rate_limit_config(self, config: RateLimitConfig) -> None:
        """
        Update the multi-tier rate limit configuration.

        Args:
            config: New rate limit configuration
        """
        self.rate_limit_config = config
        self.max_gas_per_transaction = config.max_gas_per_transaction
        self.max_cost_per_transaction = config.max_cost_per_transaction

        # Update global rate limiter
        self.global_rate_limiter = SlidingWindowRateLimiter(config)

        # Update all existing user rate limiters
        for user_address in self.user_rate_limiters:
            self.user_rate_limiters[user_address] = SlidingWindowRateLimiter(config)

        logger.info(
            "Rate limit configuration updated",
            extra={
                "event": "gas_sponsor.config_updated",
                "sponsor": self.sponsor_address[:16] + "...",
                "config": {
                    "per_second": config.per_second,
                    "per_minute": config.per_minute,
                    "per_hour": config.per_hour,
                    "per_day": config.per_day
                }
            }
        )

    def enable(self) -> None:
        """Enable sponsorship"""
        self.enabled = True

    def disable(self) -> None:
        """Disable sponsorship"""
        self.enabled = False

    def get_stats(self) -> dict[str, any]:
        """Get comprehensive sponsorship statistics"""
        total_sponsored = sum(tx.gas_amount for tx in self.sponsored_transactions)
        unique_users = len(set(tx.user_address for tx in self.sponsored_transactions))

        # Get global rate limit usage
        global_usage = self.global_rate_limiter.get_current_usage()

        return {
            "sponsor_address": self.sponsor_address,
            "total_budget": self.total_budget,
            "remaining_budget": self.remaining_budget,
            "spent": total_sponsored,
            "transaction_count": len(self.sponsored_transactions),
            "unique_users": unique_users,
            "enabled": self.enabled,
            "rate_limit": self.rate_limit,  # Legacy
            "rate_limit_config": {
                "per_second": self.rate_limit_config.per_second,
                "per_minute": self.rate_limit_config.per_minute,
                "per_hour": self.rate_limit_config.per_hour,
                "per_day": self.rate_limit_config.per_day,
                "max_gas_per_second": self.rate_limit_config.max_gas_per_second,
                "max_gas_per_minute": self.rate_limit_config.max_gas_per_minute,
                "max_gas_per_hour": self.rate_limit_config.max_gas_per_hour,
                "max_gas_per_day": self.rate_limit_config.max_gas_per_day,
                "max_gas_per_transaction": self.rate_limit_config.max_gas_per_transaction,
                "max_cost_per_transaction": self.rate_limit_config.max_cost_per_transaction
            },
            "global_usage": global_usage,
            "active_users": len(self.user_rate_limiters)
        }

    def get_user_usage(self, user_address: str) -> dict[str, any]:
        """Get usage stats for a specific user"""
        user_txs = [
            tx for tx in self.sponsored_transactions
            if tx.user_address == user_address
        ]

        total_gas = sum(tx.gas_amount for tx in user_txs)

        # Count today's transactions (legacy)
        current_time = time.time()
        day_ago = current_time - 86400
        today_count = len([
            ts for ts in self.user_daily_usage.get(user_address, [])
            if ts > day_ago
        ])

        # Get detailed rate limit usage if user has a limiter
        user_usage = None
        if user_address in self.user_rate_limiters:
            user_usage = self.user_rate_limiters[user_address].get_current_usage()

        return {
            "user_address": user_address,
            "total_transactions": len(user_txs),
            "total_gas_sponsored": total_gas,
            "transactions_today": today_count,  # Legacy
            "rate_limit_remaining": max(0, self.rate_limit - today_count),  # Legacy
            "rate_limit_usage": user_usage  # New multi-tier stats
        }

    def get_retry_after(self, user_address: str | None = None) -> float:
        """
        Get time until next request would be allowed (in seconds).

        Args:
            user_address: Optional user address to check. If None, checks global limit.

        Returns:
            Seconds until retry, or 0 if immediately available
        """
        # Check global limit
        global_retry = self.global_rate_limiter.get_retry_after()

        # If user specified, check their limit too
        if user_address and user_address in self.user_rate_limiters:
            user_retry = self.user_rate_limiters[user_address].get_retry_after()
            # Return the maximum (most restrictive)
            return max(global_retry, user_retry)

        return global_retry

class EmbeddedWalletRecord:
    def __init__(self, alias: str, contact: str, wallet_name: str, address: str, secret_hash: str):
        self.alias = alias
        self.contact = contact
        self.wallet_name = wallet_name
        self.address = address
        self.secret_hash = secret_hash

    def to_dict(self) -> dict[str, str]:
        return {
            "alias": self.alias,
            "contact": self.contact,
            "wallet_name": self.wallet_name,
            "address": self.address,
            "secret_hash": self.secret_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "EmbeddedWalletRecord":
        return cls(
            alias=data["alias"],
            contact=data["contact"],
            wallet_name=data["wallet_name"],
            address=data["address"],
            secret_hash=data["secret_hash"],
        )

class AccountAbstractionManager:
    """Manage embedded wallets that map to social/email identities."""

    def __init__(self, wallet_manager: WalletManager, storage_path: str | None = None):
        self.wallet_manager = wallet_manager
        self.storage_path = storage_path or Config.EMBEDDED_WALLET_DIR
        os.makedirs(self.storage_path, exist_ok=True)
        self.records_file = os.path.join(self.storage_path, "embedded_wallets.json")
        self.records: dict[str, EmbeddedWalletRecord] = {}
        self.sessions: dict[str, str] = {}
        self.gas_sponsors: dict[str, 'GasSponsor'] = {}  # Task 178: Gas sponsorship
        self._load()

    def _hash_secret(self, secret: str) -> str:
        salted = f"{secret}{Config.EMBEDDED_WALLET_SALT}"
        return hashlib.sha256(salted.encode()).hexdigest()

    def _wallet_filename(self, alias: str) -> str:
        safe_alias = alias.replace(" ", "_")
        return os.path.join(self.storage_path, f"{safe_alias}.wallet")

    def _load(self):
        if os.path.exists(self.records_file):
            with open(self.records_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for entry in data:
                    record = EmbeddedWalletRecord.from_dict(entry)
                    self.records[record.alias] = record

    def _save(self):
        with open(self.records_file, "w", encoding="utf-8") as f:
            json.dump([rec.to_dict() for rec in self.records.values()], f, indent=2)

    def create_embedded_wallet(self, alias: str, contact: str, secret: str) -> EmbeddedWalletRecord:
        if alias in self.records:
            raise ValueError("Alias already exists")

        wallet_name = f"embedded_{alias}"
        password = secret or Config.WALLET_PASSWORD or secrets.token_hex(16)
        wallet = self.wallet_manager.create_wallet(wallet_name, password=password)
        record = EmbeddedWalletRecord(
            alias=alias,
            contact=contact,
            wallet_name=wallet_name,
            address=wallet.address,
            secret_hash=self._hash_secret(secret),
        )
        self.records[alias] = record
        self.sessions[alias] = secrets.token_hex(16)
        self._save()
        return record

    def authenticate(self, alias: str, secret: str) -> str | None:
        record = self.records.get(alias)
        if not record:
            return None
        if record.secret_hash != self._hash_secret(secret):
            return None
        token = secrets.token_hex(16)
        self.sessions[alias] = token
        return token

    def get_session_token(self, alias: str) -> str | None:
        return self.sessions.get(alias)

    def get_session(self, alias: str) -> str | None:
        return self.sessions.get(alias)

    def get_record(self, alias: str) -> EmbeddedWalletRecord | None:
        return self.records.get(alias)

    def add_gas_sponsor(self, sponsor_address: str, budget: float, rate_limit: int = 10) -> 'GasSponsor':
        """
        Add a gas sponsor for account abstraction (Task 178)

        Args:
            sponsor_address: Address of the sponsor
            budget: Total budget for gas sponsorship
            rate_limit: Maximum transactions per user per day

        Returns:
            GasSponsor instance
        """
        sponsor = GasSponsor(sponsor_address, budget, rate_limit)
        self.gas_sponsors[sponsor_address] = sponsor
        return sponsor

    def get_gas_sponsor(self, sponsor_address: str) -> 'GasSponsor' | None:
        """Get gas sponsor by address"""
        return self.gas_sponsors.get(sponsor_address)

    def request_sponsored_gas(
        self,
        user_address: str,
        sponsor_address: str,
        gas_amount: float
    ) -> str | None:
        """
        Request sponsored gas for a transaction

        Args:
            user_address: User requesting sponsorship
            sponsor_address: Sponsor address
            gas_amount: Amount of gas needed

        Returns:
            Preliminary transaction ID if approved, None if rejected
        """
        sponsor = self.gas_sponsors.get(sponsor_address)
        if not sponsor:
            return None

        return sponsor.sponsor_transaction(user_address, gas_amount)

class SponsorshipResult(Enum):
    """Result of sponsorship validation"""
    APPROVED = "approved"
    NO_SPONSOR = "no_sponsor"
    SPONSOR_NOT_FOUND = "sponsor_not_found"
    SPONSOR_DISABLED = "sponsor_disabled"
    INSUFFICIENT_BUDGET = "insufficient_budget"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    GLOBAL_RATE_LIMIT_EXCEEDED = "global_rate_limit_exceeded"
    USER_RATE_LIMIT_EXCEEDED = "user_rate_limit_exceeded"
    GAS_RATE_LIMIT_EXCEEDED = "gas_rate_limit_exceeded"
    USER_BLACKLISTED = "user_blacklisted"
    USER_NOT_WHITELISTED = "user_not_whitelisted"
    INVALID_SIGNATURE = "invalid_signature"
    FEE_TOO_HIGH = "fee_too_high"
    COST_TOO_HIGH = "cost_too_high"

@dataclass
class SponsorshipValidation:
    """Result of sponsorship validation"""
    result: SponsorshipResult
    sponsor_address: str | None = None
    fee_amount: float = 0.0
    message: str = ""
    retry_after: float = 0.0  # Seconds until retry allowed (for rate limiting)

class SponsoredTransactionProcessor:
    """
    Processes sponsored transactions for account abstraction.

    This processor integrates with the blockchain to enable gasless transactions
    where sponsors pay fees on behalf of users.

    Usage:
        processor = SponsoredTransactionProcessor()

        # Register a sponsor
        sponsor = processor.register_sponsor(
            sponsor_address="XAI...",
            sponsor_private_key="...",
            budget=100.0,
            rate_limit=50
        )

        # Create sponsored transaction
        tx = Transaction(
            sender="XAIuser...",
            recipient="XAIrecipient...",
            amount=10.0,
            fee=0.001,
            gas_sponsor="XAIsponsor..."
        )

        # Authorize and process
        processor.authorize_transaction(tx, sponsor_private_key)
        validation = processor.validate_sponsored_transaction(tx)
        if validation.result == SponsorshipResult.APPROVED:
            blockchain.add_transaction(tx)
    """

    def __init__(self):
        """Initialize the sponsored transaction processor"""
        self.sponsors: dict[str, GasSponsor] = {}
        self.sponsor_keys: dict[str, str] = {}  # sponsor_address -> public_key
        self._persistence_path: str | None = None

    def register_sponsor(
        self,
        sponsor_address: str,
        sponsor_public_key: str,
        budget: float,
        rate_limit: int = 50,
        max_fee_per_tx: float = 0.1,
        whitelist: list[str] | None = None,
        blacklist: list[str] | None = None,
        rate_limit_config: RateLimitConfig | None = None,
    ) -> GasSponsor:
        """
        Register a new gas sponsor.

        Args:
            sponsor_address: Address of the sponsor
            sponsor_public_key: Public key for signature verification
            budget: Total budget for sponsorship (in XAI)
            rate_limit: DEPRECATED - use rate_limit_config instead (kept for backwards compatibility)
            max_fee_per_tx: Maximum fee sponsor will pay per transaction (DEPRECATED - use rate_limit_config)
            whitelist: Optional list of allowed user addresses
            blacklist: Optional list of blocked user addresses
            rate_limit_config: Multi-tier rate limit configuration (recommended)

        Returns:
            GasSponsor instance

        Example (legacy):
            sponsor = processor.register_sponsor(
                sponsor_address="XAI1234...",
                sponsor_public_key="04abc...",
                budget=100.0,
                rate_limit=50,
                max_fee_per_tx=0.01
            )

        Example (recommended):
            config = RateLimitConfig(
                per_second=10,
                per_minute=100,
                per_hour=500,
                per_day=1000,
                max_gas_per_second=1.0,
                max_gas_per_minute=10.0,
                max_gas_per_hour=50.0,
                max_gas_per_day=100.0,
                max_gas_per_transaction=0.1
            )
            sponsor = processor.register_sponsor(
                sponsor_address="XAI1234...",
                sponsor_public_key="04abc...",
                budget=100.0,
                rate_limit_config=config
            )
        """
        # If no config provided, create one from legacy parameters
        if rate_limit_config is None:
            rate_limit_config = RateLimitConfig(
                per_second=10,
                per_minute=100,
                per_hour=500,
                per_day=max(rate_limit, 1000),
                max_gas_per_second=1.0,
                max_gas_per_minute=10.0,
                max_gas_per_hour=50.0,
                max_gas_per_day=100.0,
                max_gas_per_transaction=max_fee_per_tx,
                max_cost_per_transaction=max_fee_per_tx
            )

        sponsor = GasSponsor(sponsor_address, budget, rate_limit, rate_limit_config)

        if whitelist:
            sponsor.set_whitelist(whitelist)
        if blacklist:
            sponsor.set_blacklist(blacklist)

        self.sponsors[sponsor_address] = sponsor
        self.sponsor_keys[sponsor_address] = sponsor_public_key

        logger.info(
            "Registered gas sponsor",
            extra={
                "event": "gas_sponsor.registered",
                "sponsor": sponsor_address[:16] + "...",
                "budget": budget,
                "rate_limit": rate_limit,  # Legacy
                "rate_limit_config": {
                    "per_second": rate_limit_config.per_second,
                    "per_minute": rate_limit_config.per_minute,
                    "per_hour": rate_limit_config.per_hour,
                    "per_day": rate_limit_config.per_day
                }
            }
        )

        return sponsor

    def authorize_transaction(
        self,
        transaction: "Transaction",
        sponsor_private_key: str
    ) -> bool:
        """
        Authorize a sponsored transaction by signing with sponsor's key.

        This creates a signature proving the sponsor approves paying the fee
        for this specific transaction.

        Args:
            transaction: Transaction to authorize
            sponsor_private_key: Sponsor's private key for signing

        Returns:
            True if authorization successful
        """
        if not transaction.gas_sponsor:
            logger.warning("Cannot authorize: no gas_sponsor set on transaction")
            return False

        # Create authorization message: sponsor_address + txid + fee + timestamp
        auth_data = {
            "sponsor": transaction.gas_sponsor,
            "sender": transaction.sender,
            "recipient": transaction.recipient,
            "amount": transaction.amount,
            "fee": transaction.fee,
            "timestamp": transaction.timestamp,
        }
        auth_message = json.dumps(auth_data, sort_keys=True)
        auth_hash = hashlib.sha256(auth_message.encode()).hexdigest()

        try:
            signature = sign_message_hex(sponsor_private_key, auth_hash.encode())
        except (ValueError, TypeError) as exc:
            logger.error(
                "Failed to authorize transaction due to invalid signing key: %s",
                type(exc).__name__,
                extra={
                    "event": "gas_sponsor.auth_failed",
                    "sponsor": transaction.gas_sponsor[:16] + "...",
                },
                exc_info=True,
            )
            raise SponsorSignatureError(
                "Failed to authorize transaction: invalid sponsor key material",
                sponsor=transaction.gas_sponsor,
            ) from exc
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:  # pragma: no cover - unexpected crypto failures
            logger.error(
                "Unexpected error during sponsor authorization: %s",
                type(exc).__name__,
                extra={
                    "event": "gas_sponsor.auth_failed",
                    "sponsor": transaction.gas_sponsor[:16] + "...",
                },
                exc_info=True,
            )
            raise SponsorSignatureError(
                "Failed to authorize transaction due to unexpected signing error",
                sponsor=transaction.gas_sponsor,
            ) from exc

        transaction.gas_sponsor_signature = signature

        logger.debug(
            "Transaction authorized by sponsor",
            extra={
                "event": "gas_sponsor.authorized",
                "sponsor": transaction.gas_sponsor[:16] + "...",
                "txid": transaction.txid[:16] + "..." if transaction.txid else "pending"
            }
        )
        return True

    def verify_sponsor_signature(self, transaction: "Transaction") -> bool:
        """
        Verify the sponsor's authorization signature.

        Args:
            transaction: Transaction with gas_sponsor_signature

        Returns:
            True if signature is valid
        """
        if not transaction.gas_sponsor or not transaction.gas_sponsor_signature:
            return False

        sponsor_public_key = self.sponsor_keys.get(transaction.gas_sponsor)
        if not sponsor_public_key:
            return False

        # Recreate authorization message
        auth_data = {
            "sponsor": transaction.gas_sponsor,
            "sender": transaction.sender,
            "recipient": transaction.recipient,
            "amount": transaction.amount,
            "fee": transaction.fee,
            "timestamp": transaction.timestamp,
        }
        auth_message = json.dumps(auth_data, sort_keys=True)
        auth_hash = hashlib.sha256(auth_message.encode()).hexdigest()

        try:
            return verify_signature_hex(
                sponsor_public_key,
                auth_hash.encode(),
                transaction.gas_sponsor_signature
            )
        except ValueError as exc:
            logger.error(
                "Sponsor signature malformed for %s: %s",
                transaction.gas_sponsor[:16] + "...",
                str(exc),
                extra={"event": "gas_sponsor.sig_verify_failed"},
                exc_info=True,
            )
            raise SponsorSignatureVerificationError(
                "Malformed sponsor signature payload",
                sponsor=transaction.gas_sponsor,
            ) from exc
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:  # pragma: no cover - unexpected crypto failures
            logger.error(
                "Unexpected error verifying sponsor signature for %s: %s",
                transaction.gas_sponsor[:16] + "...",
                type(exc).__name__,
                extra={"event": "gas_sponsor.sig_verify_failed"},
                exc_info=True,
            )
            raise SponsorSignatureVerificationError(
                "Unexpected error verifying sponsor signature",
                sponsor=transaction.gas_sponsor,
            ) from exc

    def validate_sponsored_transaction(
        self,
        transaction: "Transaction"
    ) -> SponsorshipValidation:
        """
        Validate a sponsored transaction.

        Checks:
        1. Sponsor exists and is enabled
        2. Sponsor has sufficient budget
        3. User hasn't exceeded rate limit
        4. User is not blacklisted (and is whitelisted if required)
        5. Fee doesn't exceed per-transaction limit
        6. Sponsor signature is valid

        Args:
            transaction: Transaction to validate

        Returns:
            SponsorshipValidation with result and details
        """
        # Check if transaction has a sponsor
        if not transaction.gas_sponsor:
            return SponsorshipValidation(
                result=SponsorshipResult.NO_SPONSOR,
                message="Transaction has no gas sponsor"
            )

        sponsor = self.sponsors.get(transaction.gas_sponsor)
        if not sponsor:
            return SponsorshipValidation(
                result=SponsorshipResult.SPONSOR_NOT_FOUND,
                sponsor_address=transaction.gas_sponsor,
                message=f"Sponsor {transaction.gas_sponsor[:16]}... not registered"
            )

        # Check sponsor is enabled
        if not sponsor.enabled:
            return SponsorshipValidation(
                result=SponsorshipResult.SPONSOR_DISABLED,
                sponsor_address=transaction.gas_sponsor,
                message="Sponsor is disabled"
            )

        # Check blacklist
        if transaction.sender in sponsor.blacklist:
            return SponsorshipValidation(
                result=SponsorshipResult.USER_BLACKLISTED,
                sponsor_address=transaction.gas_sponsor,
                message=f"User {transaction.sender[:16]}... is blacklisted"
            )

        # Check whitelist (if configured)
        if sponsor.whitelist and transaction.sender not in sponsor.whitelist:
            return SponsorshipValidation(
                result=SponsorshipResult.USER_NOT_WHITELISTED,
                sponsor_address=transaction.gas_sponsor,
                message=f"User {transaction.sender[:16]}... not in whitelist"
            )

        # Check fee limit
        if transaction.fee > sponsor.max_gas_per_transaction:
            return SponsorshipValidation(
                result=SponsorshipResult.FEE_TOO_HIGH,
                sponsor_address=transaction.gas_sponsor,
                fee_amount=transaction.fee,
                message=f"Fee {transaction.fee} exceeds limit {sponsor.max_gas_per_transaction}"
            )

        # Check budget
        if transaction.fee > sponsor.remaining_budget:
            return SponsorshipValidation(
                result=SponsorshipResult.INSUFFICIENT_BUDGET,
                sponsor_address=transaction.gas_sponsor,
                fee_amount=transaction.fee,
                message=f"Insufficient budget: {sponsor.remaining_budget} < {transaction.fee}"
            )

        # Check rate limit (this is now handled by the new rate limiters in sponsor_transaction,
        # but we keep this check for backwards compatibility and validation-only scenarios)
        retry_after = sponsor.get_retry_after(transaction.sender)
        if retry_after > 0:
            return SponsorshipValidation(
                result=SponsorshipResult.RATE_LIMIT_EXCEEDED,
                sponsor_address=transaction.gas_sponsor,
                message=f"Rate limit exceeded. Retry after {retry_after:.1f} seconds",
                retry_after=retry_after
            )

        # Verify sponsor signature
        try:
            signature_valid = self.verify_sponsor_signature(transaction)
        except SponsorSignatureVerificationError as exc:
            logger.warning(
                "SponsorSignatureVerificationError in validate_sponsored_transaction",
                extra={
                    "error_type": "SponsorSignatureVerificationError",
                    "error": str(exc),
                    "function": "validate_sponsored_transaction"
                }
            )
            return SponsorshipValidation(
                result=SponsorshipResult.INVALID_SIGNATURE,
                sponsor_address=transaction.gas_sponsor,
                message=f"Sponsor signature verification error: {exc}"
            )

        if not signature_valid:
            return SponsorshipValidation(
                result=SponsorshipResult.INVALID_SIGNATURE,
                sponsor_address=transaction.gas_sponsor,
                message="Invalid sponsor authorization signature"
            )

        # All checks passed
        return SponsorshipValidation(
            result=SponsorshipResult.APPROVED,
            sponsor_address=transaction.gas_sponsor,
            fee_amount=transaction.fee,
            message="Sponsorship approved"
        )

    def deduct_sponsor_fee(
        self,
        transaction: "Transaction",
        preliminary_txid: str | None = None
    ) -> bool:
        """
        Deduct the fee from sponsor's budget after transaction is processed.

        This should be called after the transaction is successfully added
        to the mempool or confirmed in a block.

        Args:
            transaction: The processed transaction
            preliminary_txid: Optional preliminary txid if transaction was pre-authorized

        Returns:
            True if deduction successful
        """
        if not transaction.gas_sponsor:
            return False

        sponsor = self.sponsors.get(transaction.gas_sponsor)
        if not sponsor:
            return False

        # If preliminary_txid provided, update existing record
        if preliminary_txid:
            existing_tx = sponsor.get_transaction_by_preliminary_txid(preliminary_txid)
            if existing_tx:
                # Update with blockchain txid
                if transaction.txid:
                    sponsor.confirm_sponsored_transaction(preliminary_txid, transaction.txid)
                logger.info(
                    "Sponsor fee deducted (existing authorization)",
                    extra={
                        "event": "gas_sponsor.fee_deducted",
                        "sponsor": transaction.gas_sponsor[:16] + "...",
                        "user": transaction.sender[:16] + "...",
                        "fee": transaction.fee,
                        "preliminary_txid": preliminary_txid[:16] + "...",
                        "blockchain_txid": (transaction.txid[:16] + "...") if transaction.txid else "none",
                        "remaining_budget": sponsor.remaining_budget
                    }
                )
                return True

        # New transaction not pre-authorized
        # Generate preliminary txid and create new record
        timestamp = time.time()
        new_preliminary_txid = sponsor._generate_preliminary_txid(
            transaction.sender,
            transaction.fee,
            timestamp
        )

        # Deduct fee from budget
        sponsor.remaining_budget -= transaction.fee

        # Record the sponsored transaction
        sponsored_tx = SponsoredTransaction(
            user_address=transaction.sender,
            txid=new_preliminary_txid,
            gas_amount=transaction.fee,
            timestamp=timestamp,
            sponsor_address=transaction.gas_sponsor,
            status=TransactionStatus.CONFIRMED.value if transaction.txid else TransactionStatus.PENDING.value,
            blockchain_txid=transaction.txid
        )
        sponsor.sponsored_transactions.append(sponsored_tx)
        sponsor._txid_map[new_preliminary_txid] = sponsored_tx

        # Update rate limit tracking
        if transaction.sender not in sponsor.user_daily_usage:
            sponsor.user_daily_usage[transaction.sender] = []
        sponsor.user_daily_usage[transaction.sender].append(timestamp)

        logger.info(
            "Sponsor fee deducted (new transaction)",
            extra={
                "event": "gas_sponsor.fee_deducted",
                "sponsor": transaction.gas_sponsor[:16] + "...",
                "user": transaction.sender[:16] + "...",
                "fee": transaction.fee,
                "preliminary_txid": new_preliminary_txid[:16] + "...",
                "blockchain_txid": (transaction.txid[:16] + "...") if transaction.txid else "none",
                "remaining_budget": sponsor.remaining_budget
            }
        )

        return True

    def get_sponsor(self, sponsor_address: str) -> GasSponsor | None:
        """Get a registered sponsor by address"""
        return self.sponsors.get(sponsor_address)

    def get_all_sponsors(self) -> dict[str, Dict]:
        """Get stats for all registered sponsors"""
        return {
            addr: sponsor.get_stats()
            for addr, sponsor in self.sponsors.items()
        }

    def is_sponsored_transaction(self, transaction: "Transaction") -> bool:
        """Check if a transaction has gas sponsorship"""
        return bool(transaction.gas_sponsor)

# Global processor instance for integration with blockchain
_global_processor: SponsoredTransactionProcessor | None = None

def get_sponsored_transaction_processor() -> SponsoredTransactionProcessor:
    """
    Get the global sponsored transaction processor.

    This provides a singleton processor that can be used across the codebase
    for consistent gas sponsorship management.

    Returns:
        SponsoredTransactionProcessor instance
    """
    global _global_processor
    if _global_processor is None:
        _global_processor = SponsoredTransactionProcessor()
    return _global_processor

def process_sponsored_transaction(
    transaction: "Transaction",
    blockchain: "Blockchain" | None = None
) -> tuple[bool, str]:
    """
    Process a sponsored transaction through the full pipeline.

    This is a convenience function that:
    1. Validates the sponsorship
    2. If valid, allows the transaction to proceed (fee paid by sponsor)
    3. Deducts the fee from sponsor's budget

    Args:
        transaction: Transaction to process
        blockchain: Optional blockchain instance for additional validation

    Returns:
        Tuple of (success, message)

    Example:
        success, message = process_sponsored_transaction(tx)
        if success:
            print(f"Transaction sponsored: {message}")
        else:
            print(f"Sponsorship failed: {message}")
    """
    processor = get_sponsored_transaction_processor()

    # Validate sponsorship
    validation = processor.validate_sponsored_transaction(transaction)

    if validation.result != SponsorshipResult.APPROVED:
        return False, validation.message

    # Sponsorship approved - fee will be covered by sponsor
    # The actual fee deduction happens when the transaction is confirmed
    return True, f"Sponsored by {validation.sponsor_address[:16]}..."
