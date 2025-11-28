import pytest

from xai.blockchain.bridge_fees_insurance import BridgeFeeManager
from xai.blockchain.insurance_fund import InsuranceFundManager


def test_bridge_fee_manager_collects_fees():
    manager = BridgeFeeManager(transfer_fee_percentage=0.01)
    fee = manager.collect_fee(1000.0)
    assert fee == 10.0
    assert manager.get_insurance_fund_balance() == 10.0
    with pytest.raises(ValueError):
        manager.collect_fee(-1.0)


def test_insurance_fund_claim_lifecycle():
    bridge_manager = BridgeFeeManager(transfer_fee_percentage=0.01)
    bridge_manager.collect_fee(1000.0)

    fund_manager = InsuranceFundManager(
        bridge_fee_manager=bridge_manager,
        authorized_payout_address="0xDAO",
    )

    claim_id = fund_manager.submit_claim("0xVictim", 5.0, "exploit")
    assert fund_manager.get_claim_status(claim_id) == "pending"

    with pytest.raises(PermissionError):
        fund_manager.approve_claim(claim_id, "0xAttacker")

    fund_manager.approve_claim(claim_id, "0xDAO")
    assert fund_manager.get_claim_status(claim_id) == "approved"

    fund_manager.process_payout(claim_id, "0xDAO")
    assert fund_manager.get_claim_status(claim_id) == "paid"
    assert fund_manager.fund_balance == pytest.approx(5.0)


def test_insufficient_funds_triggers_partial_payout():
    bridge_manager = BridgeFeeManager(transfer_fee_percentage=0.0)
    bridge_manager.insurance_fund_balance = 2.0
    fund_manager = InsuranceFundManager(bridge_manager, "0xDAO")
    claim_id = fund_manager.submit_claim("0xVictim", 5.0, "big exploit")
    fund_manager.approve_claim(claim_id, "0xDAO")
    fund_manager.process_payout(claim_id, "0xDAO")
    assert fund_manager.fund_balance == 0.0
    assert fund_manager.get_claim_status(claim_id) == "paid"
