"""
Mobile cache helpers for quick sync summaries.

Builds a compact snapshot (latest header, wallet reminders, AML cues) that
mobile apps can cache locally and refresh periodically.
"""

import time
from typing import Any, Dict, Optional


class MobileCacheService:
    """Memoizes small snapshots for mobile dashboards."""

    CACHE_TTL_SECONDS = 5

    def __init__(self, node):
        self.node = node
        self._last_summary: Optional[Dict[str, Any]] = None
        self._last_built_at: float = 0.0

    def build_summary(self, address: Optional[str] = None, use_cache: bool = True) -> Dict[str, Any]:
        now = time.time()
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

        if address:
            snapshot = self.node.regulator_dashboard.get_address_risk_profile(address)
        else:
            snapshot = None

        summary = dict(summary)
        summary['address_risk'] = snapshot
        return summary

    def _build_fresh_summary(self) -> Dict[str, Any]:
        blockchain = self.node.blockchain
        latest_block = blockchain.get_latest_block()
        wallet_tracker = getattr(self.node, 'wallet_claiming_tracker', None)
        pending_claims = wallet_tracker.pending_claims_summary() if wallet_tracker else []

        return {
            'timestamp': time.time(),
            'latest_block': {
                'index': latest_block.index,
                'hash': latest_block.hash,
                'timestamp': latest_block.timestamp,
                'pending_transactions': len(blockchain.pending_transactions),
            },
            'wallet_claims_pending': len(pending_claims),
            'notifications_due': [
                {
                    'identifier': claim['identifier'],
                    'next_notification_due': claim['next_notification_due_iso']
                }
                for claim in pending_claims[:10]
            ],
            'mining': {
                'difficulty': blockchain.difficulty,
                'queue_depth': len(blockchain.pending_transactions)
            }
        }
