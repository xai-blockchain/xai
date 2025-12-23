"""
Mobile cache helpers for quick sync summaries.

Builds a compact snapshot (latest header, wallet reminders, AML cues) that
mobile apps can cache locally and refresh periodically.
"""

import time
from collections import OrderedDict
from typing import Any, Dict, Optional


class MobileCacheService:
    """
    Memoizes small snapshots for mobile dashboards with LRU eviction.

    Caches per-address summaries with configurable size limit to prevent
    unbounded memory growth.
    """

    CACHE_TTL_SECONDS = 5
    CACHE_MAX_SIZE = 1000  # Maximum cached address summaries

    def __init__(self, node):
        self.node = node
        # Global summary cache (single entry, TTL-based)
        self._last_summary: Optional[Dict[str, Any]] = None
        self._last_built_at: float = 0.0

        # Per-address cache with LRU eviction
        self._address_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._address_cache_timestamps: Dict[str, float] = {}

    def build_summary(
        self, address: Optional[str] = None, use_cache: bool = True
    ) -> Dict[str, Any]:
        now = time.time()

        # Check global summary cache first
        if (
            use_cache
            and self._last_summary is not None
            and (now - self._last_built_at) < self.CACHE_TTL_SECONDS
        ):
            summary = dict(self._last_summary)
        else:
            summary = self._build_fresh_summary()
            self._last_summary = summary
            self._last_built_at = now

        # Handle per-address risk profile with LRU cache
        if address:
            if use_cache and address in self._address_cache:
                # Check if cached entry is still valid
                cache_age = now - self._address_cache_timestamps.get(address, 0)
                if cache_age < self.CACHE_TTL_SECONDS:
                    # Move to end (LRU)
                    self._address_cache.move_to_end(address)
                    snapshot = self._address_cache[address]
                else:
                    # Expired, fetch fresh
                    snapshot = self._fetch_and_cache_risk_profile(address, now)
            else:
                # Not in cache, fetch fresh
                snapshot = self._fetch_and_cache_risk_profile(address, now)
        else:
            snapshot = None

        summary = dict(summary)
        summary["address_risk"] = snapshot
        return summary

    def _fetch_and_cache_risk_profile(self, address: str, now: float) -> Optional[Dict[str, Any]]:
        """
        Fetch address risk profile and cache it with LRU eviction

        Args:
            address: Address to fetch profile for
            now: Current timestamp

        Returns:
            Risk profile dict or None
        """
        snapshot = self.node.regulator_dashboard.get_address_risk_profile(address)

        # Cache the result
        self._address_cache[address] = snapshot
        self._address_cache_timestamps[address] = now

        # Move to end (most recently used)
        self._address_cache.move_to_end(address)

        # Evict LRU if over size limit
        while len(self._address_cache) > self.CACHE_MAX_SIZE:
            evicted_address, _ = self._address_cache.popitem(last=False)
            if evicted_address in self._address_cache_timestamps:
                del self._address_cache_timestamps[evicted_address]

        return snapshot

    def _build_fresh_summary(self) -> Dict[str, Any]:
        blockchain = self.node.blockchain
        latest_block = blockchain.get_latest_block()
        wallet_tracker = getattr(self.node, "wallet_claiming_tracker", None)
        pending_claims = wallet_tracker.pending_claims_summary() if wallet_tracker else []

        return {
            "timestamp": time.time(),
            "latest_block": {
                "index": latest_block.index,
                "hash": latest_block.hash,
                "timestamp": latest_block.timestamp,
                "pending_transactions": len(blockchain.pending_transactions),
            },
            "wallet_claims_pending": len(pending_claims),
            "notifications_due": [
                {
                    "identifier": claim["identifier"],
                    "next_notification_due": claim["next_notification_due_iso"],
                }
                for claim in pending_claims[:10]
            ],
            "mining": {
                "difficulty": blockchain.difficulty,
                "queue_depth": len(blockchain.pending_transactions),
            },
        }
