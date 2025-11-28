import pytest

from xai.blockchain.front_running_protection import FrontRunningProtectionManager
from xai.blockchain.mev_mitigation import MEVMitigationManager


def test_commit_reveal_and_slippage():
    manager = FrontRunningProtectionManager()
    tx = {"type": "swap", "amount": 10}
    salt = "salt"
    commit_hash = manager._hash_transaction_with_salt(tx, salt)

    manager.commit_transaction("0xUser", commit_hash)
    with pytest.raises(ValueError):
        manager.commit_transaction("0xUser", commit_hash)

    manager.reveal_transaction("0xUser", tx, salt)
    with pytest.raises(ValueError):
        manager.reveal_transaction("0xUser", tx, salt)

    manager.process_mempool_with_fair_ordering()
    assert manager.revealed_transactions == {}

    assert manager.check_slippage(100.0, 99.5, max_slippage_percent=1.0) is True
    assert manager.check_slippage(100.0, 95.0, max_slippage_percent=1.0) is False


def test_mev_private_and_bundle_processing():
    fr_manager = FrontRunningProtectionManager()
    mev_manager = MEVMitigationManager(fr_manager)

    mev_manager.submit_private_transaction({"type": "swap"}, "0xUser")
    assert len(mev_manager.private_transactions_queue) == 1
    mev_manager.process_private_transactions()
    assert len(mev_manager.private_transactions_queue) == 0

    mev_manager.submit_transaction_bundle([{"type": "approve"}, {"type": "swap"}], "0xUser")
    assert len(mev_manager.transaction_bundles) == 1
    mev_manager.process_transaction_bundles()
    assert len(mev_manager.transaction_bundles) == 0


def test_mev_sandwich_detection():
    fr_manager = FrontRunningProtectionManager()
    mev_manager = MEVMitigationManager(fr_manager)
    target_tx = {"type": "swap", "token": "ETH"}

    assert (
        mev_manager.detect_sandwich_attack(target_tx, pre_tx_price=100.0, post_tx_price=100.5, current_mempool_transactions=[])
        is False
    )

    mempool = [
        {"type": "buy", "token": "ETH"},
        target_tx,
        {"type": "sell", "token": "ETH"},
    ]
    assert (
        mev_manager.detect_sandwich_attack(target_tx, pre_tx_price=100.0, post_tx_price=102.0, current_mempool_transactions=mempool)
        is True
    )
