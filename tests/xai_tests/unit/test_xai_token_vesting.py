"""
Unit tests for XAITokenVesting release and validation.
"""

import time

from xai.core.governance.xai_token_vesting import XAITokenVesting
from xai.core.governance.xai_token_manager import XAITokenManager


class StubLogger:
    def info(self, *a, **k):
        pass

    def warn(self, *a, **k):
        pass

    def error(self, *a, **k):
        pass


def test_create_vesting_schedule_validation():
    """Invalid parameters return False and do not create schedule."""
    mgr = XAITokenManager(initial_supply=0, supply_cap=100, logger=StubLogger())
    vesting = XAITokenVesting(token_manager=mgr, logger=StubLogger())
    assert vesting.create_vesting_schedule("a", amount=-1, cliff_duration=0, total_duration=0) is False
    assert "a" not in mgr.xai_token.vesting_schedules


def test_release_vested_tokens_after_cliff(monkeypatch):
    """Tokens release proportionally after cliff end."""
    mgr = XAITokenManager(initial_supply=0, supply_cap=100, logger=StubLogger())
    # Seed vesting contract balance so transfers succeed
    mgr.xai_token.balances["vesting_contract_address"] = 50
    vesting = XAITokenVesting(token_manager=mgr, logger=StubLogger())

    now = 1000
    schedule = {
        "amount": 10,
        "released": 0.0,
        "cliff_end": now - 10,
        "cliff_duration": 5,
        "end_date": now + 30,
    }
    mgr.xai_token.vesting_schedules["user"] = schedule
    monkeypatch.setattr(time, "time", lambda: now + 10)

    released = vesting.release_vested_tokens("user")
    assert released > 0
    assert mgr.get_balance("user") == released
