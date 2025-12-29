"""
Tests for RefundSweepManager expired swap detection.
"""

from xai.core.wallets.refund_sweep_manager import RefundSweepManager


def test_find_expired_swaps_respects_status_and_margin():
    mgr = RefundSweepManager(safety_margin_seconds=10)
    now = 100
    swaps = [
        {"id": "a", "timelock": now - 5, "status": "FUNDED"},   # not past margin
        {"id": "b", "timelock": now - 15, "status": "FUNDED"},  # should expire
        {"id": "c", "timelock": now - 20, "status": "claimed"},  # claimed, skip
        {"id": "d", "timelock": now + 100, "status": "FUNDED"},  # future
    ]
    expired = mgr.find_expired_swaps(swaps, now=now)
    expired_ids = {s["id"] for s in expired}
    assert expired_ids == {"b"}


def test_missing_timelock_ignored():
    mgr = RefundSweepManager()
    swaps = [{"id": "x", "status": "FUNDED"}]
    assert mgr.find_expired_swaps(swaps, now=0) == []
