import time

import pytest

from xai.blockchain.transfer_tax_manager import TransferTaxManager
from xai.blockchain.inflation_monitor import InflationMonitor
from xai.blockchain.token_supply_manager import TokenSupplyManager
from xai.blockchain.relayer_staking import RelayerStakingManager, Relayer
from xai.blockchain.slashing import SlashingManager, ValidatorStake


def test_transfer_tax_application():
    manager = TransferTaxManager(transfer_tax_rate_percentage=1.0, exempt_addresses=["0xTreasury"])
    net, tax = manager.apply_transfer_tax("0xUser", "0xOther", 100.0)
    assert net == pytest.approx(99.0)
    assert tax == pytest.approx(1.0)

    net_exempt, tax_exempt = manager.apply_transfer_tax("0xUser", "0xTreasury", 100.0)
    assert net_exempt == pytest.approx(100.0)
    assert tax_exempt == 0.0


def test_inflation_monitor_alert():
    supply_manager = TokenSupplyManager(max_supply=1_000_000)
    supply_manager.mint_tokens(100_000)
    monitor = InflationMonitor(supply_manager, alert_threshold_percentage=1.0, history_window_days=1)
    supply_manager.mint_tokens(10_000)
    triggered = monitor.check_for_alerts(24 * 3600, current_time=int(time.time()) + 1)
    assert triggered is True


def test_relayer_staking_bonding_and_unbonding():
    slashing = SlashingManager()
    slashing.add_validator_stake(ValidatorStake("0xExisting", 1000))
    manager = RelayerStakingManager(slashing, min_bond=1000, unbonding_period_seconds=5)
    relayer = manager.bond_stake("0xRelayer", 2000)
    assert relayer.bonded_amount == 2000
    manager.unbond_stake("0xRelayer")
    manager.finalize_unbonding("0xRelayer", int(time.time()))
    assert manager.get_relayer_status("0xRelayer") == "unbonding"
