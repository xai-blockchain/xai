"""
Unit tests for per-address daily spending limits.
"""

import os
from xai.wallet.spending_limits import SpendingLimitManager


def test_spending_limits_basic(tmp_path):
    state_path = os.path.join(tmp_path, "spend.json")
    m = SpendingLimitManager(path=state_path, default_limit=10.0)

    addr = "XAI" + "a" * 40
    # Initially, can spend full limit
    allowed, used, limit = m.can_spend(addr, 4.0)
    assert allowed is True and used == 0.0 and limit == 10.0

    m.record_spend(addr, 4.0)
    # After recording, remaining is 6
    allowed, used, limit = m.can_spend(addr, 7.0)
    assert allowed is False and used == 4.0 and limit == 10.0

    # Set per-address limit and verify
    m.set_limit(addr, 20.0)
    allowed, used, limit = m.can_spend(addr, 7.0)
    assert allowed is True and limit == 20.0

