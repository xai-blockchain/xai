import pytest

from xai.blockchain.anti_whale_manager import AntiWhaleManager
from xai.blockchain.token_supply_manager import TokenSupplyManager


def test_token_supply_manager_mint_and_burn():
    manager = TokenSupplyManager(max_supply=1000.0)
    assert manager.get_current_supply() == 0.0

    manager.mint_tokens(250.0)
    assert manager.get_current_supply() == 250.0

    with pytest.raises(ValueError):
        manager.mint_tokens(800.0)  # would exceed max supply

    manager.burn_tokens(50.0)
    assert manager.get_current_supply() == 200.0

    with pytest.raises(ValueError):
        manager.burn_tokens(500.0)  # more than current supply


def test_anti_whale_vote_capping():
    supply = TokenSupplyManager(max_supply=1000.0)
    supply.mint_tokens(1000.0)
    manager = AntiWhaleManager(supply, max_governance_voting_power_percentage=5.0)

    assert manager.check_governance_vote("small", 20.0) == 20.0
    capped = manager.check_governance_vote("whale", 80.0)
    assert pytest.approx(capped) == 50.0  # 5% of 1000


def test_anti_whale_transaction_limits():
    supply = TokenSupplyManager(max_supply=1000.0)
    manager = AntiWhaleManager(
        supply,
        max_governance_voting_power_percentage=10.0,
        max_transaction_size_percentage_of_total_supply=1.0,
    )

    # With zero supply every transfer should fail
    assert manager.check_transaction_size("addr", 1.0) is False

    supply.mint_tokens(500.0)
    assert manager.check_transaction_size("addr", 5.0) is True  # exactly 1%
    assert manager.check_transaction_size("addr", 6.0) is False


def test_invalid_configuration_rejected():
    supply = TokenSupplyManager(max_supply=1000.0)
    with pytest.raises(ValueError):
        AntiWhaleManager(supply, max_governance_voting_power_percentage=0)
    with pytest.raises(ValueError):
        AntiWhaleManager(supply, max_transaction_size_percentage_of_total_supply=0)
