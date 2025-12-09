"""
Refund sweep helper for expired HTLC-based atomic swaps.

This skeleton filters swaps that are eligible for refund based on timelock
plus a safety margin, leaving construction/broadcast to upstream callers.
"""

from __future__ import annotations

import time
from typing import Iterable, List, Dict, Any


class RefundSweepManager:
    """Identify swaps that should be refunded."""

    def __init__(self, safety_margin_seconds: int = 1800):
        self.safety_margin_seconds = safety_margin_seconds

    def find_expired_swaps(self, swaps: Iterable[Dict[str, Any]], now: float | None = None) -> List[Dict[str, Any]]:
        """
        Return swaps whose timelock has passed plus safety margin and are not already claimed/refunded.
        """
        current = now if now is not None else time.time()
        expired = []
        for swap in swaps:
            timelock = swap.get("timelock")
            status = str(swap.get("status", "")).lower()
            if timelock is None:
                continue
            if status in {"claimed", "refunded"}:
                continue
            if current >= timelock + self.safety_margin_seconds:
                expired.append(swap)
        return expired
