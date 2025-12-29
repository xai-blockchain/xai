"""
Unit tests for XAITokenManager mint/transfer/vesting wiring.
"""

from types import SimpleNamespace

from xai.core.governance.xai_token_manager import XAITokenManager


class StubLogger:
    """No-op logger to avoid file writes."""

    def info(self, *a, **k):
        pass

    def warn(self, *a, **k):
        pass

    def error(self, *a, **k):
        pass


def test_mint_and_transfer_updates_balances():
    """Minting increases supply and balances; transfer moves funds."""
    mgr = XAITokenManager(initial_supply=0, supply_cap=100, logger=StubLogger())

    assert mgr.mint_tokens("a", 10) is True
    assert mgr.get_balance("a") == 10
    assert mgr.get_total_supply() == 10

    assert mgr.transfer_tokens("a", "b", 4) is True
    assert mgr.get_balance("a") == 6
    assert mgr.get_balance("b") == 4


def test_mint_rejects_non_positive_amount():
    """Minting zero/negative amounts fails."""
    mgr = XAITokenManager(initial_supply=0, supply_cap=100, logger=StubLogger())
    assert mgr.mint_tokens("a", 0) is False
    assert mgr.get_total_supply() == 0


def test_create_vesting_schedule_persists_to_token():
    """Vesting schedule creation returns True and stores schedule."""
    mgr = XAITokenManager(initial_supply=0, supply_cap=100, logger=StubLogger())
    # Seed user balance to satisfy vesting creation requirement
    mgr.mint_tokens("a", 20)
    # Ensure vesting contract has funds to transfer when schedule releases
    mgr.xai_token.balances["vesting_contract_address"] = 10
    created = mgr.create_vesting_schedule("a", amount=10, cliff_duration=5, total_duration=10)
    assert created is True
    assert "a" in mgr.xai_token.vesting_schedules
